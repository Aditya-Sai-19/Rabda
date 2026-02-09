"""Tkinter GUI for the WhatsApp Status automation app - Premium Sleek Edition."""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, W, X, Y, filedialog, messagebox, ttk
import tkinter as tk
from tkinter.scrolledtext import ScrolledText

from .config import CONFIG
from .status_uploader import WhatsAppStatusUploader

# --- Sleek Theme Constants ---
COLOR_BG = "#0B141A"          # WhatsApp Dark BG
COLOR_SIDEBAR = "#111B21"     # WhatsApp Sidebar
COLOR_ACCENT = "#00A884"      # WhatsApp Green
COLOR_ACCENT_HOVER = "#06CF9C"
COLOR_TEXT = "#E9EDEF"        # Main text
COLOR_TEXT_DIM = "#8696A0"    # Secondary text
COLOR_ENTRY_BG = "#2A3942"    # Input fields
COLOR_ERROR = "#F15C6D"
COLOR_LOG_BG = "#111B21"

FONT_MAIN = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 10, "bold")
FONT_TITLE = ("Segoe UI", 14, "bold")
FONT_MONO = ("Consolas", 9)

@dataclass
class UiState:
    running: bool = False

class SleekButton(tk.Button):
    def __init__(self, master, **kwargs):
        bg = kwargs.pop("bg", COLOR_ACCENT)
        fg = kwargs.pop("fg", "white")
        kwargs.setdefault("activebackground", COLOR_ACCENT_HOVER)
        kwargs.setdefault("activeforeground", "white")
        kwargs.setdefault("relief", "flat")
        kwargs.setdefault("borderwidth", 0)
        kwargs.setdefault("font", FONT_BOLD)
        kwargs.setdefault("cursor", "hand2")
        kwargs.setdefault("padx", 15)
        kwargs.setdefault("pady", 8)
        super().__init__(master, bg=bg, fg=fg, **kwargs)

class App(tk.Tk):
    """Sleek WhatsApp-inspired Tkinter application."""

    def __init__(self) -> None:
        super().__init__()
        self.title("WA Status Automator Pro")
        self.geometry("860x650")
        self.minsize(800, 600)
        self.configure(bg=COLOR_BG)

        # Style configuration
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        self._ui_state = UiState(running=False)
        self._log_queue: queue.Queue[str] = queue.Queue()

        self._build_layout()
        self._schedule_log_drain()

    def _build_layout(self) -> None:
        # Main container with padding
        main_container = tk.Frame(self, bg=COLOR_BG)
        main_container.pack(fill=BOTH, expand=True, padx=25, pady=25)

        # --- Header ---
        header = tk.Frame(main_container, bg=COLOR_BG)
        header.pack(fill=X, pady=(0, 20))
        
        tk.Label(
            header, text="WhatsApp Status Automation", 
            font=FONT_TITLE, fg=COLOR_TEXT, bg=COLOR_BG
        ).pack(side=LEFT)
        
        self.status_pill = tk.Label(
            header, text="IDLE", font=("Segoe UI", 8, "bold"),
            fg="white", bg="#3B4A54", padx=8, pady=2
        )
        self.status_pill.pack(side=RIGHT)

        # --- Input Section ---
        input_card = tk.Frame(main_container, bg=COLOR_SIDEBAR, padx=20, pady=20)
        input_card.pack(fill=X, pady=(0, 20))

        # CSV Path
        csv_label_row = tk.Frame(input_card, bg=COLOR_SIDEBAR)
        csv_label_row.pack(fill=X, pady=(0, 5))
        tk.Label(csv_label_row, text="STATUS QUEUE (CSV)", font=FONT_BOLD, fg=COLOR_ACCENT, bg=COLOR_SIDEBAR).pack(side=LEFT)

        csv_entry_row = tk.Frame(input_card, bg=COLOR_SIDEBAR)
        csv_entry_row.pack(fill=X, pady=(0, 15))
        
        self.csv_path_var = tk.StringVar(value=str(CONFIG.default_csv_path))
        self.entry_csv = tk.Entry(
            csv_entry_row, textvariable=self.csv_path_var, 
            bg=COLOR_ENTRY_BG, fg=COLOR_TEXT, insertbackground=COLOR_TEXT,
            relief="flat", font=FONT_MAIN, borderwidth=10
        )
        self.entry_csv.pack(side=LEFT, fill=X, expand=True)
        
        self.btn_browse_csv = tk.Button(
            csv_entry_row, text="Browse", command=self.on_browse_csv,
            bg=COLOR_ENTRY_BG, fg=COLOR_ACCENT, relief="flat", padx=10, cursor="hand2"
        )
        self.btn_browse_csv.pack(side=RIGHT, padx=(10, 0))

        # Images Dir
        img_label_row = tk.Frame(input_card, bg=COLOR_SIDEBAR)
        img_label_row.pack(fill=X, pady=(0, 5))
        tk.Label(img_label_row, text="IMAGES FOLDER", font=FONT_BOLD, fg=COLOR_ACCENT, bg=COLOR_SIDEBAR).pack(side=LEFT)

        img_entry_row = tk.Frame(input_card, bg=COLOR_SIDEBAR)
        img_entry_row.pack(fill=X)
        
        self.img_dir_var = tk.StringVar(value=str(CONFIG.default_images_folder))
        self.entry_img = tk.Entry(
            img_entry_row, textvariable=self.img_dir_var, 
            bg=COLOR_ENTRY_BG, fg=COLOR_TEXT, insertbackground=COLOR_TEXT,
            relief="flat", font=FONT_MAIN, borderwidth=10
        )
        self.entry_img.pack(side=LEFT, fill=X, expand=True)
        
        self.btn_browse_img = tk.Button(
            img_entry_row, text="Browse", command=self.on_browse_img,
            bg=COLOR_ENTRY_BG, fg=COLOR_ACCENT, relief="flat", padx=10, cursor="hand2"
        )
        self.btn_browse_img.pack(side=RIGHT, padx=(10, 0))

        # --- Control Row ---
        control_row = tk.Frame(main_container, bg=COLOR_BG)
        control_row.pack(fill=X, pady=(0, 15))

        self.btn_start = SleekButton(control_row, text="START NEW BATCH", command=lambda: self.on_start(resume=False))
        self.btn_start.pack(side=LEFT, padx=(0, 15))

        self.btn_resume = SleekButton(
            control_row, text="RESUME PENDING", bg=COLOR_ENTRY_BG, 
            fg=COLOR_TEXT, command=lambda: self.on_start(resume=True)
        )
        self.btn_resume.pack(side=LEFT)

        self.progress_var = tk.StringVar(value="Ready to broadcast")
        self.lbl_progress = tk.Label(
            control_row, textvariable=self.progress_var, 
            font=FONT_MAIN, fg=COLOR_TEXT_DIM, bg=COLOR_BG, anchor=W
        )
        self.lbl_progress.pack(side=LEFT, padx=(20, 0), fill=X, expand=True)

        # --- Log Section ---
        log_header = tk.Frame(main_container, bg=COLOR_BG)
        log_header.pack(fill=X, pady=(10, 5))
        tk.Label(log_header, text="ACTIVITY LOG", font=FONT_BOLD, fg=COLOR_TEXT_DIM, bg=COLOR_BG).pack(side=LEFT)

        self.txt_log = ScrolledText(
            main_container, height=15, bg=COLOR_LOG_BG, fg=COLOR_TEXT,
            relief="flat", font=FONT_MONO, borderwidth=15, insertbackground=COLOR_TEXT
        )
        self.txt_log.pack(fill=BOTH, expand=True)
        self.txt_log.configure(state="disabled")

    def on_browse_csv(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Select Status CSV",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
            initialdir="data" if Path("data").exists() else "."
        )
        if file_path:
            self.csv_path_var.set(file_path)

    def on_browse_img(self) -> None:
        dir_path = filedialog.askdirectory(
            title="Select Images Folder",
            initialdir="images" if Path("images").exists() else "."
        )
        if dir_path:
            self.img_dir_var.set(dir_path)

    def _append_log(self, line: str) -> None:
        self.txt_log.configure(state="normal")
        # Add timestamp-like color if possible? Just standard for now
        self.txt_log.insert(END, f"[{line}]\n")
        self.txt_log.see(END)
        self.txt_log.configure(state="disabled")

    def _schedule_log_drain(self) -> None:
        self.after(100, self._drain_log_queue)

    def _drain_log_queue(self) -> None:
        try:
            while True:
                line = self._log_queue.get_nowait()
                self._append_log(line)
                if line.startswith("[STEP]") or "Processing" in line:
                    clean_line = line.replace("[STEP]", "").strip()
                    self.progress_var.set(clean_line[:65] + "..." if len(clean_line) > 65 else clean_line)
        except queue.Empty:
            pass
        finally:
            self._schedule_log_drain()

    def _log_callback(self, line: str) -> None:
        self._log_queue.put(line)

    def _set_running(self, running: bool) -> None:
        self._ui_state.running = running
        state = "disabled" if running else "normal"
        self.btn_start.configure(state=state)
        self.btn_resume.configure(state=state)
        self.btn_browse_csv.configure(state=state)
        self.btn_browse_img.configure(state=state)
        self.entry_csv.configure(state=("readonly" if running else "normal"))
        self.entry_img.configure(state=("readonly" if running else "normal"))
        
        if running:
            self.status_pill.configure(text="RUNNING", bg=COLOR_ACCENT)
        else:
            self.status_pill.configure(text="IDLE", bg="#3B4A54")
            self.progress_var.set("Task completed")

    def on_start(self, resume: bool) -> None:
        if self._ui_state.running:
            return

        csv_path = self.csv_path_var.get().strip()
        img_dir = self.img_dir_var.get().strip()
        
        if not Path(csv_path).exists():
            messagebox.showerror("Error", f"CSV file not found: {csv_path}")
            return

        if not Path(img_dir).exists():
            messagebox.showerror("Error", f"Images folder not found: {img_dir}")
            return

        self._set_running(True)
        mode = "RESUME" if resume else "START"
        self._append_log(f"--- BATCH INITIALIZED ({mode}) ---")

        worker = threading.Thread(
            target=self._run_batch_worker,
            args=(csv_path, img_dir, resume),
            daemon=True,
        )
        worker.start()

    def _run_batch_worker(self, csv_path: str, img_dir: str, resume: bool) -> None:
        try:
            uploader = WhatsAppStatusUploader(log_callback=self._log_callback)
            result = uploader.batch_upload(
                csv_path, img_dir, resume_mode=resume, 
                progress_callback=self._log_callback
            )
            self.after(0, self._on_worker_done, result.success, result.message)
        except Exception as e:
            self.after(0, self._on_worker_done, False, f"System Error: {str(e)}")

    def _on_worker_done(self, success: bool, message: str) -> None:
        self._append_log("--- SESSION CONCLUDED ---")
        self._set_running(False)
        if success:
            messagebox.showinfo("Batch Complete", message)
        else:
            messagebox.showerror("Operation Failed", message)
