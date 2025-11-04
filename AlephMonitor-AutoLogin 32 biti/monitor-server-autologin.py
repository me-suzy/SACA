import paramiko
import time
import requests
from datetime import datetime
import subprocess
import logging
import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import ctypes
import psutil

# Constante Windows pentru prevenirea sleep/hibernate
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002
ES_AWAYMODE_REQUIRED = 0x00000040

# Configurare logging
log_file = os.path.join(os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(__file__), 'aleph_monitor.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Configurații server (CRITICE - fără acestea nu funcționează nimic!)
SERVER_IP = "182.16.11.44"
SSH_PORT = 22
SSH_USER = "root"
SSH_PASS = "YOUR-PASSWORD"  # PAROLA CRITICĂ pentru SSH - fără ea nu poți accesa serverul!
CATALOG_URL = f"http://{SERVER_IP}:8991/F"
CATALOG_EXE = r"C:\AL500\catalog\bin\Catalog.exe"
CHECK_INTERVAL = 30
TEMP_DATE = "12 JAN 2012 08:00:00"

def prevent_sleep():
    """Previne intrarea calculatorului în sleep/hibernate."""
    try:
        # Setează flag-uri pentru a preveni sleep-ul
        # ES_CONTINUOUS - Menține setările până la resetare
        # ES_SYSTEM_REQUIRED - Previne sleep automat
        # ES_DISPLAY_REQUIRED - Menține ecranul pornit
        ctypes.windll.kernel32.SetThreadExecutionState(
            ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
        )
        logging.info("✓ Prevenire sleep/hibernate activată")
        return True
    except Exception as e:
        logging.warning(f"Nu s-a putut activa prevenirea sleep: {e}")
        return False

def allow_sleep():
    """Permite din nou intrarea în sleep/hibernate."""
    try:
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        logging.info("✓ Prevenire sleep/hibernate dezactivată")
        return True
    except Exception as e:
        logging.warning(f"Nu s-a putut dezactiva prevenirea sleep: {e}")
        return False

def is_backup_window():
    """Returnează True între 22:00 și 03:00 ora locală (pauză pentru backup)."""
    now_hour = datetime.now().hour
    return now_hour >= 22 or now_hour < 3

class AlephMonitorAutoLogin:
    def __init__(self):
        # ACTIVEAZĂ PREVENIREA SLEEP/HIBERNATE IMEDIAT
        prevent_sleep()
        
        self.root = tk.Tk()
        self.root.title("Monitor Server ALEPH - Auto Login")
        self.root.geometry("600x500")
        self.root.resizable(False, False)

        # Variabile
        self.monitoring = False
        self.monitor_thread = None
        self.catalog_user = "admin"  # Utilizator implicit
        self.catalog_pass = "admin123"  # Parola implicită

        # Stil
        style = ttk.Style()
        style.theme_use('clam')

        self.create_main_screen()

    def create_main_screen(self):
        """Ecran principal cu buton de pornire directă."""
        # Clear window
        for widget in self.root.winfo_children():
            widget.destroy()

        # Frame principal
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Logo/Titlu
        title_label = tk.Label(main_frame, text="🖥️ Server ALEPH", font=("Arial", 24, "bold"), fg="#2c3e50")
        title_label.pack(pady=20)

        subtitle_label = tk.Label(main_frame, text="Monitor Automat", font=("Arial", 12), fg="#7f8c8d")
        subtitle_label.pack(pady=5)

        # Info despre credențiale SSH
        ssh_info = tk.Label(main_frame, 
                           text=f"SSH Server: {SERVER_IP}\nUtilizator SSH: {SSH_USER}\nParola SSH: {'*' * len(SSH_PASS)}",
                           font=("Arial", 10), fg="#95a5a6", justify=tk.CENTER)
        ssh_info.pack(pady=10)

        # Buton principal - MĂRIT
        start_btn = tk.Button(main_frame, text="🚀 Pornire Monitor", command=self.start_monitoring,
                             bg="#27ae60", fg="white", font=("Arial", 14, "bold"),
                             padx=40, pady=20, cursor="hand2", height=2)
        start_btn.pack(pady=30)

        # Info
        info_label = tk.Label(main_frame,
                             text="Monitorul va verifica serverul la fiecare 2 minute\nși va reporni automat Catalog.exe\n\nUtilizator implicit: admin / admin123\n\n⚠️ IMPORTANT: Calculatorul NU va intra în sleep/hibernate\ncât timp aplicația rulează!",
                             font=("Arial", 9), fg="#95a5a6", justify=tk.CENTER)
        info_label.pack(pady=10)

    def create_monitor_screen(self):
        """Ecran de monitorizare."""
        # Clear
        for w in self.root.winfo_children():
            w.destroy()

        self.root.update_idletasks()

        import tkinter as tk
        from tkinter import ttk

        HEIGHT_PX = 100

        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Folosim GRID pentru întreg ecranul ---
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(2, weight=1)
        main_frame.grid_rowconfigure(3, minsize=HEIGHT_PX, weight=0)

        # Header
        header_frame = ttk.LabelFrame(main_frame)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0,10))

        title_label = tk.Label(header_frame, text="🟢 Monitor Activ",
                               font=("Arial", 18, "bold"), fg="#27ae60")
        title_label.pack()
        user_label = tk.Label(header_frame, text=f"Utilizator: {self.catalog_user} (Auto Login)",
                              font=("Arial", 10), fg="#7f8c8d")
        user_label.pack()

        # Status
        status_frame = ttk.LabelFrame(main_frame, text="Status Server", padding="15")
        status_frame.grid(row=1, column=0, sticky="ew", pady=10)

        self.status_label = tk.Label(status_frame, text="Verificare în curs...",
                                     font=("Arial", 12), fg="#3498db")
        self.status_label.pack(pady=10)

        self.last_check_label = tk.Label(status_frame, text="",
                                         font=("Arial", 9), fg="#95a5a6")
        self.last_check_label.pack()

        # Jurnal
        log_frame = ttk.LabelFrame(main_frame, text="Jurnal Activitate", padding="10")
        log_frame.grid(row=2, column=0, sticky="nsew", pady=10)

        self.log_text = tk.Text(log_frame, height=10, width=70, font=("Courier", 9),
                                 bg="#ecf0f1", fg="#2c3e50", state=tk.DISABLED)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)

        # Butoane
        button_frame = tk.Frame(main_frame)
        button_frame.grid(row=3, column=0, sticky="nsew", pady=(5,0))
        button_frame.grid_columnconfigure(0, weight=1, uniform="btns")
        button_frame.grid_columnconfigure(1, weight=1, uniform="btns")
        button_frame.grid_rowconfigure(0, weight=0)

        self.restart_btn = tk.Button(
            button_frame, text="🔄 Repornire Manuală",
            command=self.manual_restart, bg="#3498db", fg="white",
            font=("Arial", 12, "bold"), cursor="hand2", bd=0, relief="flat",
            height=2, pady=5
        )
        self.restart_btn.grid(row=0, column=0, padx=6, pady=6, sticky="nsew")

        logout_btn = tk.Button(
            button_frame, text="🚪 Deconectare",
            command=self.logout, bg="#e74c3c", fg="white",
            font=("Arial", 12, "bold"), cursor="hand2", bd=0, relief="flat",
            height=2, pady=5
        )
        logout_btn.grid(row=0, column=1, padx=6, pady=6, sticky="nsew")

    def add_log(self, message, level="INFO"):
        """Adaugă mesaj în log-ul vizual."""
        self.log_text.config(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M:%S")

        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def update_status(self, status, color):
        """Actualizează status-ul vizual."""
        self.status_label.config(text=status, fg=color)
        self.last_check_label.config(text=f"Ultima verificare: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")

    def start_monitoring(self):
        """Pornește monitorizarea direct fără autentificare."""
        # Asigură-te că prevenirea sleep este activă
        prevent_sleep()
        
        # Respectă fereastra de backup 22:00-03:00
        if is_backup_window():
            message = "⏸ Pauză pentru backup (22:00-03:00) - monitorizarea va fi suspendată."
            self.add_log(message, "WARNING")
            messagebox.showinfo("Pauză Backup", message)
            self.create_monitor_screen()
            self.update_status("⏸ Pauză backup (22:00-03:00)", "#e67e22")
            # pornește totuși threadul pentru a afișa statusul și a relua după interval
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
            self.monitor_thread.start()
            return
        
        self.create_monitor_screen()
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.add_log("✓ Monitor pornit cu auto-login", "SUCCESS")
        self.add_log(f"✓ Utilizator: {self.catalog_user}", "INFO")
        self.add_log(f"✓ SSH Server: {SERVER_IP} ({SSH_USER})", "INFO")
        self.add_log("✓ Prevenire sleep/hibernate ACTIVĂ - calculatorul NU va intra în sleep!", "SUCCESS")

    def monitor_loop(self):
        """Loop principal de monitorizare."""
        consecutive_failures = 0
        max_failures = 2

        while self.monitoring:
            try:
                # Pauză în fereastra de backup
                if is_backup_window():
                    self.root.after(0, lambda: self.update_status("⏸ Pauză backup (22:00-03:00)", "#e67e22"))
                    self.root.after(0, lambda: self.add_log("⏸ Pauză backup activă - nu se fac acțiuni", "WARNING"))
                    time.sleep(CHECK_INTERVAL)
                    continue

                if self.check_server_status():
                    consecutive_failures = 0
                    self.root.after(0, lambda: self.update_status("🟢 Server Activ", "#27ae60"))
                    self.root.after(0, lambda: self.add_log("✓ Server funcționează normal", "SUCCESS"))
                else:
                    consecutive_failures += 1
                    self.root.after(0, lambda: self.update_status("🟡 Server Nu Răspunde", "#f39c12"))
                    self.root.after(0, lambda: self.add_log(f"⚠ Eșec #{consecutive_failures} la verificare", "WARNING"))

                    if consecutive_failures >= max_failures:
                        self.root.after(0, lambda: self.update_status("🔴 Server Căzut - Repornire...", "#e74c3c"))
                        self.root.after(0, lambda: self.add_log("🔄 Inițiere procedură repornire automată", "WARNING"))

                        if self.restart_server_sequence():
                            consecutive_failures = 0
                            self.root.after(0, lambda: self.add_log("✓✓✓ Repornire reușită!", "SUCCESS"))
                        else:
                            consecutive_failures = 0
                            self.root.after(0, lambda: self.add_log("✗ Repornire eșuată", "ERROR"))

                time.sleep(CHECK_INTERVAL)

            except Exception as e:
                logging.error(f"Eroare în monitor loop: {e}")
                self.root.after(0, lambda: self.add_log(f"✗ Eroare: {str(e)}", "ERROR"))
                time.sleep(CHECK_INTERVAL)

    def check_server_status(self):
        """Verifică dacă serverul răspunde."""
        try:
            response = requests.get(CATALOG_URL, timeout=15, allow_redirects=True)
            if response.status_code in [200, 302, 301]:
                content = response.text.lower()
                if 'aleph' in content or 'catalog' in content or len(response.text) > 100:
                    logging.info("✓ Server ALEPH activ")
                    return True
            return False
        except:
            return False

    def restart_server_sequence(self):
        """Execută secvența de repornire - ORDINEA CORECTĂ."""
        logging.info("=" * 60)
        logging.info("INIȚIERE REPORNIRE SERVER ALEPH")
        logging.info("=" * 60)

        ssh_client = None

        try:
            # Blochează în fereastra de backup
            if is_backup_window():
                self.root.after(0, lambda: self.add_log("⏸ Pauză backup - repornirea este blocată (22:00-03:00)", "WARNING"))
                return False

            # 1. Conectare SSH cu credențialele CRITICE
            logging.info("Conectare SSH cu credențialele critice...")
            self.root.after(0, lambda: self.add_log(f"→ Conectare SSH la {SERVER_IP} cu {SSH_USER}...", "INFO"))

            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh_client.connect(SERVER_IP, port=SSH_PORT, username=SSH_USER, password=SSH_PASS)

            self.root.after(0, lambda: self.add_log("✓ Conectare SSH reușită cu credențialele critice", "SUCCESS"))

            # 2. Setare dată în trecut
            logging.info("Setare dată temporară...")
            self.root.after(0, lambda: self.add_log("→ Setare dată 2012...", "INFO"))

            self.execute_ssh_command(ssh_client, f'sudo date --set "{TEMP_DATE}"')
            time.sleep(2)

            # 3. Așteptare inițializare servicii
            logging.info("Așteptare inițializare (10s)...")
            self.root.after(0, lambda: self.add_log("→ Așteptare servicii (10s)...", "INFO"))
            time.sleep(30)

            # 4. PRIMA DATĂ: Accesează catalogul ONLINE în background (fără browser)
            logging.info("Acces catalog online în background...")
            self.root.after(0, lambda: self.add_log("→ Acces catalog online (HTTP)", "INFO"))

            try:
                requests.get(CATALOG_URL, timeout=15)
                time.sleep(2)
                self.root.after(0, lambda: self.add_log("✓ Catalog online accesat (fără fereastră)", "SUCCESS"))
            except Exception as e:
                logging.warning(f"Acces HTTP eșuat: {e}")
                self.root.after(0, lambda: self.add_log("⚠ Acces HTTP eșuat, se continuă", "WARNING"))

            # 5. APOI: Lansare Catalog.exe cu credențiale
            logging.info("Lansare Catalog.exe...")
            self.root.after(0, lambda: self.add_log(f"→ Lansare Catalog.exe pentru {self.catalog_user}...", "INFO"))

            self.launch_catalog_with_credentials()
            time.sleep(5)

            # 6. Revenire la data curentă
            logging.info("Revenire la data curentă...")
            self.root.after(0, lambda: self.add_log("→ Resetare dată curentă...", "INFO"))

            current_date_cmd = self.get_current_date_command()
            self.execute_ssh_command(ssh_client, current_date_cmd)
            time.sleep(2)

            # 7. Re-accesare catalog online în background (fără browser)
            logging.info("Re-accesare catalog online (HTTP)...")
            self.root.after(0, lambda: self.add_log("→ Re-accesare catalog online (HTTP)", "INFO"))

            try:
                requests.get(CATALOG_URL, timeout=15)
                time.sleep(2)
                self.root.after(0, lambda: self.add_log("✓ Catalog online re-accesat (fără fereastră)", "SUCCESS"))
            except Exception as e:
                logging.warning(f"Acces HTTP eșuat: {e}")

            # 8. Verificare finală
            self.root.after(0, lambda: self.add_log("→ Verificare finală...", "INFO"))
            time.sleep(5)

            if self.check_server_status():
                logging.info("✓✓✓ REPORNIRE REUȘITĂ")
                return True
            else:
                logging.error("✗ Server nu răspunde după repornire")
                return False

        except Exception as e:
            logging.error(f"Eroare: {e}")
            self.root.after(0, lambda: self.add_log(f"✗ Eroare: {str(e)}", "ERROR"))
            return False

        finally:
            if ssh_client:
                ssh_client.close()

    def execute_ssh_command(self, ssh_client, command):
        """Execută comandă SSH."""
        try:
            stdin, stdout, stderr = ssh_client.exec_command(command)
            output = stdout.read().decode('utf-8').strip()
            logging.info(f"SSH: {command} -> {output}")
            return output
        except Exception as e:
            logging.error(f"Eroare SSH: {e}")
            return None

    def get_current_date_command(self):
        """Generează comanda pentru data curentă."""
        now = datetime.now()
        months = {1: 'JAN', 2: 'FEB', 3: 'MART', 4: 'APR', 5: 'MAY', 6: 'JUN',
                 7: 'JUL', 8: 'AUG', 9: 'SEP', 10: 'OCT', 11: 'NOV', 12: 'DEC'}

        minute = now.minute + 1
        hour = now.hour
        if minute >= 60:
            minute = 0
            hour += 1
        if hour >= 24:
            hour = 0

        date_str = f'{now.day:02d} {months[now.month]} {now.year} {hour:02d}:{minute:02d}:{now.second:02d}'
        return f'sudo date --set "{date_str}"'

    def launch_catalog_with_credentials(self):
        """Lansează Catalog.exe fără a lua focusul sau a aduce ferestre în față.
        NU mai trimite taste globale pentru a evita interferența cu alte aplicații.
        """
        try:
            # Pornește procesul minimizat și fără activarea ferestrei
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = 7  # SW_SHOWMINNOACTIVE

            CREATE_NO_WINDOW = 0x08000000
            DETACHED_PROCESS = 0x00000008

            process = subprocess.Popen([CATALOG_EXE],
                                       startupinfo=si,
                                       creationflags=CREATE_NO_WINDOW | DETACHED_PROCESS)
            logging.info("✓ Catalog.exe lansat (minimizat, fără activare)")
            self.root.after(0, lambda: self.add_log("✓ Catalog.exe lansat în background (fără focus)", "SUCCESS"))

            # Nu trimitem credențiale prin SendKeys pentru a nu interfera cu utilizatorul.
            # Dacă aplicația suportă parametri de linie de comandă pentru auto-login,
            # îi putem adăuga aici ulterior.

        except Exception as e:
            logging.warning(f"Nu s-a putut lansa Catalog.exe: {e}")
            self.root.after(0, lambda: self.add_log(f"✗ Eroare lansare Catalog.exe: {str(e)}", "ERROR"))

    def manual_restart(self):
        """Repornire manuală."""
        self.restart_btn.config(state=tk.DISABLED)
        self.add_log("🔄 Repornire manuală inițiată...", "INFO")

        thread = threading.Thread(target=self._manual_restart_thread, daemon=True)
        thread.start()

    def _manual_restart_thread(self):
        """Thread pentru repornire manuală."""
        success = self.restart_server_sequence()
        self.root.after(0, lambda: self.restart_btn.config(state=tk.NORMAL))
        if success:
            self.root.after(0, lambda: messagebox.showinfo("Succes", "Server repornit cu succes!"))
        else:
            self.root.after(0, lambda: messagebox.showerror("Eroare", "Repornirea a eșuat!"))

    def logout(self):
        """Deconectare și oprire monitorizare."""
        if messagebox.askyesno("Confirmare", "Sigur vrei să oprești monitorizarea?"):
            self.monitoring = False
            try:
                kill_catalog_processes()
                self.add_log("⏹ Cataloage oprite (Catalog.exe + tab-uri online)", "INFO")
            except Exception as e:
                logging.warning(f"Eroare la oprirea cataloagelor: {e}")
            self.create_main_screen()

    def run(self):
        """Pornește interfața."""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

    def on_closing(self):
        """La închidere."""
        if self.monitoring:
            if messagebox.askyesno("Confirmare", "Monitorizarea este activă. Sigur vrei să închizi?"):
                self.monitoring = False
                # Oprește cataloagele și permite din nou sleep/hibernate
                try:
                    kill_catalog_processes()
                except Exception as e:
                    logging.warning(f"Eroare la oprirea cataloagelor: {e}")
                allow_sleep()
                self.root.destroy()
        else:
            # Oprește cataloagele (dacă rulează) și permite din nou sleep/hibernate
            try:
                kill_catalog_processes()
            except Exception as e:
                logging.warning(f"Eroare la oprirea cataloagelor: {e}")
            allow_sleep()
            self.root.destroy()

if __name__ == "__main__":
    app = AlephMonitorAutoLogin()
    app.run()

# ===================== UTILITĂȚI OPRIRE CATALOAGE ===================== #
def kill_catalog_processes():
    """Închide Catalog.exe și tab-urile de browser care accesează catalogul online.
    Nu închide întregul browser decât dacă tab-ul nu poate fi identificat.
    """
    try:
        # Închide Catalog.exe dacă există
        subprocess.run(["taskkill", "/IM", "Catalog.exe", "/F"], capture_output=True, text=True)
    except Exception:
        pass

    # Procese de browser posibile
    browser_names = {
        "chrome.exe",
        "msedge.exe",
        "firefox.exe",
        "opera.exe",
        "opera_browser.exe",
        "brave.exe",
        "iexplore.exe",
        "edge.exe",
    }

    targets = {CATALOG_URL, SERVER_IP, ":8991"}

    # 1) Încercare: identificare după linia de comandă
    suspect_pids: set[int] = set()
    for proc in psutil.process_iter(["name", "cmdline", "pid"]):
        try:
            name = (proc.info.get("name") or "").lower()
            if name in browser_names:
                cmd = " ".join(proc.info.get("cmdline") or [])
                if any(t in cmd for t in targets):
                    suspect_pids.add(proc.info.get("pid"))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # 2) Identificare după conexiuni active către IP:PORT
    try:
        for c in psutil.net_connections(kind="inet"):
            try:
                if c.raddr and c.raddr.ip == SERVER_IP and c.raddr.port == 8991 and c.pid:
                    suspect_pids.add(c.pid)
            except Exception:
                continue
    except Exception:
        pass

    # Închide procesele suspecte (și procesul părinte dacă e un worker de browser)
    for pid in list(suspect_pids):
        try:
            p = psutil.Process(pid)
            # Urcă la părinte dacă este un proces-sandbox/renderer
            parent = p
            for _ in range(3):
                if parent and parent.name().lower() not in browser_names:
                    parent = parent.parent()
                else:
                    break
            target = parent or p
            target.terminate()
            try:
                target.wait(timeout=3)
            except Exception:
                target.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
