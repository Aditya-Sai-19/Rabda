"""Tkinter GUI for the WhatsApp Status automation app."""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, W, X, filedialog, messagebox
import tkinter as tk
from tkinter.scrolledtext import ScrolledText

from .status_uploader import WhatsAppStatusUploader


@dataclass
class UiState:
    running: bool = False


class App(tk.Tk):
    """Main Tkinter application."""

    def __init__(self) -> None:
        super().__init__()
        self.title("WhatsApp Status Bot (Playwright)")
        self.geometry("820x560")
        self.minsize(760, 520)

        self._ui_state = UiState(running=False)
        self._log_queue: queue.Queue[str] = queue.Queue()

        self._build_layout()
        self._schedule_log_drain()

    def _build_layout(self) -> None:
        root = tk.Frame(self)
        root.pack(fill=BOTH, expand=True, padx=12, pady=12)

        # Image selection
        file_row = tk.Frame(root)
        file_row.pack(fill=X)

        self.btn_browse = tk.Button(file_row, text="Browse Image...", command=self.on_browse)
        self.btn_browse.pack(side=LEFT)

        self.image_path_var = tk.StringVar(value="")
        self.entry_image = tk.Entry(file_row, textvariable=self.image_path_var)
        self.entry_image.pack(side=RIGHT, fill=X, expand=True, padx=(10, 0))

        # Caption
        caption_lbl = tk.Label(root, text="Caption (optional):", anchor=W)
        caption_lbl.pack(fill=X, pady=(12, 4))

        self.txt_caption = tk.Text(root, height=4)
        self.txt_caption.pack(fill=X)

        # Post button + progress
        action_row = tk.Frame(root)
        action_row.pack(fill=X, pady=(12, 8))

        self.btn_post = tk.Button(action_row, text="Post Status", command=self.on_post)
        self.btn_post.pack(side=LEFT)

        self.progress_var = tk.StringVar(value="Idle")
        self.lbl_progress = tk.Label(action_row, textvariable=self.progress_var, anchor=W)
        self.lbl_progress.pack(side=LEFT, padx=(12, 0))

        # Logs
        log_lbl = tk.Label(root, text="Status Log:", anchor=W)
        log_lbl.pack(fill=X, pady=(12, 4))

        self.txt_log = ScrolledText(root, height=16)
        self.txt_log.pack(fill=BOTH, expand=True)
        self.txt_log.configure(state="disabled")

    def on_browse(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Select an image",
            filetypes=[
                ("Images", "*.png;*.jpg;*.jpeg;*.webp;*.bmp"),
                ("All Files", "*.*"),
            ],
        )
        if file_path:
            self.image_path_var.set(file_path)

    def _append_log(self, line: str) -> None:
        self.txt_log.configure(state="normal")
        self.txt_log.insert(END, line + "\n")
        self.txt_log.see(END)
        self.txt_log.configure(state="disabled")

    def _schedule_log_drain(self) -> None:
        self.after(120, self._drain_log_queue)

    def _drain_log_queue(self) -> None:
        try:
            while True:
                line = self._log_queue.get_nowait()
                self._append_log(line)
        except queue.Empty:
            pass
        finally:
            self._schedule_log_drain()

    def _log_callback(self, line: str) -> None:
        # Called from worker thread; push to thread-safe queue.
        self._log_queue.put(line)

    def _set_running(self, running: bool) -> None:
        self._ui_state.running = running
        self.btn_post.configure(state=("disabled" if running else "normal"))
        self.btn_browse.configure(state=("disabled" if running else "normal"))
        self.entry_image.configure(state=("disabled" if running else "normal"))
        self.txt_caption.configure(state=("disabled" if running else "normal"))
        self.progress_var.set("Running..." if running else "Idle")

    def on_post(self) -> None:
        if self._ui_state.running:
            return

        image_path = self.image_path_var.get().strip()
        caption = self.txt_caption.get("1.0", END).strip()

        if not image_path:
            messagebox.showerror("Validation Error", "Please select an image file.")
            return

        if not Path(image_path).exists():
            messagebox.showerror("Validation Error", f"Image not found:\n{image_path}")
            return

        self._set_running(True)
        self._append_log("--- Starting automation ---")

        worker = threading.Thread(
            target=self._run_automation_worker,
            args=(image_path, caption),
            daemon=True,
        )
        worker.start()

    def _run_automation_worker(self, image_path: str, caption: str) -> None:
        uploader = WhatsAppStatusUploader(log_callback=self._log_callback)
        result = uploader.post_status(image_path, caption)

        # Return result to UI thread
        self.after(0, self._on_worker_done, result.success, result.message)

    def _on_worker_done(self, success: bool, message: str) -> None:
        self._append_log("--- Automation finished ---")
        self._set_running(False)

        if success:
            messagebox.showinfo("Success", message)
        else:
            messagebox.showerror("Error", message)
