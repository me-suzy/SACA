import psutil
import subprocess
import sys

SERVER_IP = "182.16.11.44"
CATALOG_URL = f"http://{SERVER_IP}:8991/F"


def kill_catalog_processes():
    try:
        subprocess.run(["taskkill", "/IM", "Catalog.exe", "/F"], capture_output=True, text=True)
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

    for proc in psutil.process_iter(["name", "cmdline"]):
        try:
            name = (proc.info.get("name") or "").lower()
            if name in browser_names:
                cmd = " ".join(proc.info.get("cmdline") or [])
                if any(t in cmd for t in targets):
                    proc.terminate()
                    try:
                        proc.wait(timeout=3)
                    except Exception:
                        proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue


if __name__ == "__main__":
    kill_catalog_processes()
    print("Cataloage oprite.")
