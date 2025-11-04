import tkinter as tk
from tkinter import messagebox
import psutil
import subprocess

SERVER_IP = "182.16.11.44"
CATALOG_URL = f"http://{SERVER_IP}:8991/F"


def kill_catalog_processes():
    killed = []
    try:
        out = subprocess.run(["taskkill", "/IM", "Catalog.exe", "/F"], capture_output=True, text=True)
        if out.returncode == 0:
            killed.append("Catalog.exe")
    except Exception:
        pass

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
    closed = 0

    suspect_pids = set()
    for proc in psutil.process_iter(["name", "cmdline", "pid"]):
        try:
            name = (proc.info.get("name") or "").lower()
            if name in browser_names:
                cmd = " ".join(proc.info.get("cmdline") or [])
                if any(t in cmd for t in targets):
                    suspect_pids.add(proc.info.get("pid"))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # Conexiuni la IP:PORT
    try:
        for c in psutil.net_connections(kind="inet"):
            try:
                if c.raddr and c.raddr.ip == SERVER_IP and c.raddr.port == 8991 and c.pid:
                    suspect_pids.add(c.pid)
            except Exception:
                continue
    except Exception:
        pass

    for pid in list(suspect_pids):
        try:
            p = psutil.Process(pid)
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
            closed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return killed, closed


def on_stop_click(status_label):
    killed, closed = kill_catalog_processes()
    msg = "Oprit: " + ", ".join(killed) if killed else "Catalog.exe nu era pornit"
    msg2 = f"; Tab-uri browser închise: {closed}"
    status_label.config(text=msg + msg2)
    messagebox.showinfo("Oprit", msg + msg2)


def main():
    root = tk.Tk()
    root.title("Opreste Catalog Online")
    root.geometry("420x180")
    root.resizable(False, False)

    frame = tk.Frame(root, padx=20, pady=20)
    frame.pack(fill=tk.BOTH, expand=True)

    tk.Label(frame, text="Oprește Catalog OPAC și catalogul online", font=("Arial", 12, "bold")).pack(pady=5)
    tk.Label(frame, text=f"URL: {CATALOG_URL}", fg="#666").pack(pady=2)

    status = tk.Label(frame, text="Apasă butonul pentru a opri procesele.", fg="#2c3e50")
    status.pack(pady=8)

    btn = tk.Button(frame, text="⏹ Oprește acum", bg="#e74c3c", fg="white", font=("Arial", 12, "bold"),
                    padx=12, pady=8, command=lambda: on_stop_click(status))
    btn.pack(pady=6)

    tk.Button(frame, text="Ieșire", command=root.destroy).pack(pady=4)

    root.mainloop()


if __name__ == "__main__":
    main()
