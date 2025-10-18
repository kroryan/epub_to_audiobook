import threading
import subprocess
import sys
import time
import os
from pathlib import Path
import webbrowser

import pystray
from pystray import MenuItem as item
from PIL import Image

import tkinter as tk
from tkinter.scrolledtext import ScrolledText

from audiobook_generator.utils.log_handler import generate_unique_log_path
from audiobook_generator.utils.ffmpeg_setup import ensure_ffmpeg_available
from audiobook_generator.utils.resource_path import resource_path


class LogWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Epub2Audiobook Logs")
        self.text = ScrolledText(self.root, wrap=tk.WORD, height=30, width=120)
        self.text.pack(fill=tk.BOTH, expand=True)
        self._running = True
        self._last_size = 0
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self._poll()

    def _find_latest_log(self) -> Path | None:
        # Logs are written relative to current working directory
        logs_dir = Path.cwd() / "logs"
        if not logs_dir.exists():
            return None
        logs = sorted(logs_dir.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
        return logs[0] if logs else None

    def _poll(self):
        if not self._running:
            return
        try:
            log_file = self._find_latest_log()
            if log_file and log_file.exists():
                # If log file changed (new run), reset offset
                if getattr(self, "_current_log", None) != log_file:
                    self._current_log = log_file
                    self._last_size = 0
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    f.seek(self._last_size)
                    data = f.read()
                    if data:
                        self.text.insert(tk.END, data)
                        self.text.see(tk.END)
                        self._last_size = f.tell()
        except Exception:
            pass
        self.root.after(500, self._poll)

    def close(self):
        self._running = False
        self.root.destroy()

    def run(self):
        self.root.mainloop()


class ServerManager:
    def __init__(self):
        self.proc = None

    def start(self):
        if self.proc and self.proc.poll() is None:
            return
        ensure_ffmpeg_available()
        # Run this same executable in "webui" mode so we can stop it reliably
        if getattr(sys, 'frozen', False):
            # Running as bundled exe
            exe_path = sys.argv[0]
            cmd = [exe_path, "--webui"]
        else:
            # Dev mode: run main_ui via Python
            cmd = [sys.executable, "main_ui.py"]
        self.proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def stop(self):
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=5)
            except Exception:
                self.proc.kill()
        self.proc = None


def create_image() -> Image.Image:
    # Simple 16x16 icon
    img = Image.new('RGB', (64, 64), color=(40, 100, 160))
    return img


def main():
    manager = ServerManager()

    def on_start():
        manager.start()

    def on_stop():
        manager.stop()

    def on_show_logs(icon, item):
        win = LogWindow()
        t = threading.Thread(target=win.run, daemon=True)
        t.start()

    icon = pystray.Icon(
        "Epub2Audiobook",
        create_image(),
        menu=pystray.Menu(
            item("Start Server", lambda: on_start()),
            item("Stop Server", lambda: on_stop()),
            item("Show Logs", on_show_logs),
            item("Quit", lambda: (on_stop(), icon.stop()))
        )
    )
    # Auto-start the server so the UI opens in the browser on launch
    on_start()
    icon.run()


if __name__ == "__main__":
    # Support a child "webui" mode when invoked as single EXE
    if "--webui" in sys.argv:
        from main_ui import main as run_ui
        ensure_ffmpeg_available()
        run_ui()
    else:
        main()
