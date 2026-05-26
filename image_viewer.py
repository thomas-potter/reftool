#!/usr/bin/env python3
"""Modern image viewer GUI for Linux with timed slideshow, shuffle, and rotation.

Uses customtkinter for a clean SaaS aesthetic and loads images in
background threads so the UI never freezes.
"""

import os
import platform
import random
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk
from PIL import Image, ImageTk

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

INTERVAL_MAP = {
    "5s": 5_000,
    "15s": 15_000,
    "30s": 30_000,
    "1m": 60_000,
}


class ImageViewerApp:
    IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif"}

    def __init__(self, root: ctk.CTk):
        self.root = root
        self.root.title("Image Viewer")
        self.root.geometry("1100x750")
        self.root.minsize(750, 500)

        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # State
        self.images: list[str] = []
        self.current_index: int = 0
        self.shuffle: bool = False
        self.interval_ms: int = 30_000
        self.untimed: bool = True
        self.paused: bool = False
        self.time_remaining_ms: int = 0
        self.after_id: str | None = None
        self.resize_after_id: str | None = None
        self.photo_image: ImageTk.PhotoImage | None = None
        self.subfolders: bool = True
        self._loading: bool = False
        self._image_load_counter: int = 0
        self._rotation_angle: int = 0

        # Build screens
        self._build_setup_screen()
        self._build_slideshow_screen()

        self._show_setup()

        # Keyboard shortcuts
        self.root.bind("<Escape>", lambda _e: self._show_setup())
        self.root.bind("<Left>", lambda _e: self._go_back())
        self.root.bind("<Right>", lambda _e: self._advance())
        self.root.bind("<space>", lambda _e: self._toggle_pause())
        self.root.bind("<r>", lambda _e: self._rotate_right())
        self.root.bind("<R>", lambda _e: self._rotate_left())
        self.root.bind("<Configure>", self._on_resize)

    # ------------------------------------------------------------------
    # Setup screen
    # ------------------------------------------------------------------
    def _build_setup_screen(self):
        self.setup_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.setup_frame.grid(row=0, column=0, sticky="nsew")
        self.setup_frame.grid_rowconfigure(0, weight=1)
        self.setup_frame.grid_columnconfigure(0, weight=1)

        # Card
        card = ctk.CTkFrame(self.setup_frame, corner_radius=20, border_width=0)
        card.grid(row=0, column=0, padx=60, pady=60, sticky="")

        # Title
        ctk.CTkLabel(
            card,
            text="Image Viewer",
            font=("Inter", 36, "bold"),
        ).pack(pady=(35, 5))

        ctk.CTkLabel(
            card,
            text="Pick a folder and enjoy your slideshow",
            font=("Inter", 14),
            text_color="gray60",
        ).pack(pady=(0, 25))

        # Folder selection
        folder_row = ctk.CTkFrame(card, fg_color="transparent")
        folder_row.pack(padx=35, pady=8, fill="x")

        self.folder_path_var = ctk.StringVar()
        self.folder_entry = ctk.CTkEntry(
            folder_row,
            textvariable=self.folder_path_var,
            state="readonly",
            width=420,
            height=40,
            font=("Inter", 13),
            corner_radius=10,
        )
        self.folder_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        ctk.CTkButton(
            folder_row,
            text="Browse…",
            command=self._browse_folder,
            width=100,
            height=40,
            font=("Inter", 13, "bold"),
            corner_radius=10,
        ).pack(side="right")

        # Subfolders switch
        self.subfolders_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(
            card,
            text="Include subfolders",
            variable=self.subfolders_var,
            font=("Inter", 13),
            progress_color="#6366f1",
        ).pack(pady=(20, 5), padx=35, anchor="w")

        # Interval selection
        timing_frame = ctk.CTkFrame(card, fg_color="transparent")
        timing_frame.pack(padx=35, pady=15, fill="x")

        ctk.CTkLabel(
            timing_frame,
            text="Slideshow timing",
            font=("Inter", 14, "bold"),
        ).pack(anchor="w", pady=(0, 10))

        self.interval_var = ctk.StringVar(value="Untimed")
        self.interval_seg = ctk.CTkSegmentedButton(
            timing_frame,
            values=["5s", "15s", "30s", "1m", "Untimed"],
            variable=self.interval_var,
            command=self._on_interval_change,
            height=34,
            font=("Inter", 13, "bold"),
            corner_radius=10,
        )
        self.interval_seg.pack(fill="x")

        # Start button
        ctk.CTkButton(
            card,
            text="Start Slideshow",
            command=self._start_slideshow,
            height=44,
            font=("Inter", 15, "bold"),
            fg_color="#6366f1",
            hover_color="#4f46e5",
            corner_radius=12,
        ).pack(pady=(20, 35), padx=35, fill="x")

    def _browse_folder(self):
        """Use a native Linux file picker when possible, else fall back."""
        chosen = ""
        if platform.system() == "Linux":
            try:
                result = subprocess.run(
                    ["zenity", "--file-selection", "--directory"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    chosen = result.stdout.strip()
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass

        if not chosen:
            import tkinter.filedialog as filedialog

            chosen = filedialog.askdirectory()

        if chosen:
            self.folder_path_var.set(chosen)

    def _on_interval_change(self, value: str):
        self.untimed = value == "Untimed"
        self.interval_ms = INTERVAL_MAP.get(value, 30_000)

    def _start_slideshow(self):
        folder = self.folder_path_var.get()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror("Error", "Please select a valid folder.")
            return

        self.subfolders = self.subfolders_var.get()
        self._load_images(folder)

        if not self.images:
            messagebox.showinfo(
                "No images", "No supported images found in the selected folder."
            )
            return

        self.current_index = 0
        self.paused = False
        self.time_remaining_ms = self.interval_ms
        self._rotation_angle = 0
        self._show_slideshow()
        self._show_image(0)
        if not self.untimed:
            self._schedule_tick()

    def _load_images(self, folder: str):
        self.images = []
        if self.subfolders:
            for root, _dirs, files in os.walk(folder):
                for f in files:
                    if os.path.splitext(f)[1].lower() in self.IMAGE_EXTS:
                        self.images.append(os.path.join(root, f))
        else:
            for f in os.listdir(folder):
                if os.path.splitext(f)[1].lower() in self.IMAGE_EXTS:
                    self.images.append(os.path.join(folder, f))
        self.images.sort(key=lambda p: os.path.basename(p).lower())
        if self.shuffle:
            random.shuffle(self.images)

    # ------------------------------------------------------------------
    # Slideshow screen
    # ------------------------------------------------------------------
    def _build_slideshow_screen(self):
        self.slideshow_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.slideshow_frame.grid_rowconfigure(0, weight=1)
        self.slideshow_frame.grid_columnconfigure(0, weight=1)

        # Image canvas
        self.canvas = tk.Canvas(
            self.slideshow_frame,
            bg="#0e0e0e",
            highlightthickness=0,
            bd=0,
        )
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=12, pady=(12, 0))

        # Bottom toolbar
        toolbar = ctk.CTkFrame(self.slideshow_frame, fg_color="transparent", height=70)
        toolbar.grid(row=1, column=0, sticky="ew", padx=12, pady=(8, 12))
        toolbar.grid_propagate(False)

        # Left info
        info_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        info_frame.place(rely=0.5, relx=0.02, anchor="w")

        self.filename_label = ctk.CTkLabel(
            info_frame, text="", font=("Inter", 13), text_color="gray70"
        )
        self.filename_label.pack(anchor="w")

        self.countdown_label = ctk.CTkLabel(
            info_frame, text="", font=("Inter", 13, "bold"), text_color="#6366f1"
        )
        self.countdown_label.pack(anchor="w")

        # Right controls
        ctrl_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        ctrl_frame.place(rely=0.5, relx=0.98, anchor="e")

        self.rotate_left_btn = ctk.CTkButton(
            ctrl_frame,
            text="⟲",
            command=self._rotate_left,
            width=40,
            height=34,
            font=("Inter", 16),
            corner_radius=10,
            fg_color="transparent",
            border_width=1,
            text_color="gray80",
            hover_color="#2a2a2a",
        )
        self.rotate_left_btn.pack(side="left", padx=4)

        self.rotate_right_btn = ctk.CTkButton(
            ctrl_frame,
            text="⟳",
            command=self._rotate_right,
            width=40,
            height=34,
            font=("Inter", 16),
            corner_radius=10,
            fg_color="transparent",
            border_width=1,
            text_color="gray80",
            hover_color="#2a2a2a",
        )
        self.rotate_right_btn.pack(side="left", padx=4)

        self.shuffle_btn = ctk.CTkButton(
            ctrl_frame,
            text="Shuffle: OFF",
            command=self._toggle_shuffle,
            width=110,
            height=34,
            font=("Inter", 12),
            corner_radius=10,
            fg_color="transparent",
            border_width=1,
            text_color="gray80",
            hover_color="#2a2a2a",
        )
        self.shuffle_btn.pack(side="left", padx=4)

        self.prev_btn = ctk.CTkButton(
            ctrl_frame,
            text="← Prev",
            command=self._go_back,
            width=80,
            height=34,
            font=("Inter", 12, "bold"),
            corner_radius=10,
        )
        self.prev_btn.pack(side="left", padx=4)

        self.pause_btn = ctk.CTkButton(
            ctrl_frame,
            text="Pause",
            command=self._toggle_pause,
            width=90,
            height=34,
            font=("Inter", 12, "bold"),
            corner_radius=10,
            fg_color="#6366f1",
            hover_color="#4f46e5",
        )
        self.pause_btn.pack(side="left", padx=4)

        self.next_btn = ctk.CTkButton(
            ctrl_frame,
            text="Next →",
            command=self._advance,
            width=80,
            height=34,
            font=("Inter", 12, "bold"),
            corner_radius=10,
        )
        self.next_btn.pack(side="left", padx=4)

    # ------------------------------------------------------------------
    # Image display (threaded so UI stays responsive)
    # ------------------------------------------------------------------
    def _show_image(self, index: int):
        if not self.images:
            return
        self.current_index = index % len(self.images)
        path = self.images[self.current_index]
        self.filename_label.configure(text=os.path.basename(path))

        cw = max(self.canvas.winfo_width(), 1)
        ch = max(self.canvas.winfo_height(), 1)

        # Loading state
        self._loading = True
        self.canvas.delete("all")
        self.canvas.create_text(
            cw // 2,
            ch // 2,
            text="Loading…",
            fill="#555555",
            font=("Inter", 18),
            tags="loading",
        )

        # Cancel stale loads
        self._image_load_counter += 1
        counter = self._image_load_counter

        # Load + resize in background thread
        thread = threading.Thread(
            target=self._load_image_worker,
            args=(path, cw, ch, counter, self._rotation_angle),
            daemon=True,
        )
        thread.start()

    def _load_image_worker(self, path: str, cw: int, ch: int, counter: int, angle: int):
        try:
            pil_img = Image.open(path)
            if angle:
                pil_img = pil_img.rotate(angle, expand=True)
            pil_img = self._resize_to_fit(pil_img, cw, ch)
            self.root.after(0, lambda: self._on_image_loaded(pil_img, counter))
        except Exception as exc:
            self.root.after(0, lambda e=exc: self._on_image_error(e, counter))

    def _on_image_loaded(self, pil_img: Image.Image, counter: int):
        if counter != self._image_load_counter:
            return  # stale result
        self._loading = False
        self.photo_image = ImageTk.PhotoImage(pil_img)
        self.canvas.delete("all")
        cw = max(self.canvas.winfo_width(), 1)
        ch = max(self.canvas.winfo_height(), 1)
        self.canvas.create_image(
            cw // 2, ch // 2, image=self.photo_image, anchor="center"
        )
        if not self.untimed:
            self.time_remaining_ms = self.interval_ms
            self._update_countdown_display()

    def _on_image_error(self, exc: Exception, counter: int):
        if counter != self._image_load_counter:
            return
        self._loading = False
        self.canvas.delete("all")
        cw = max(self.canvas.winfo_width(), 1)
        ch = max(self.canvas.winfo_height(), 1)
        self.canvas.create_text(
            cw // 2,
            ch // 2,
            text=f"Unable to load image:\n{exc}",
            fill="#ef4444",
            font=("Inter", 13),
            justify="center",
        )

    def _resize_to_fit(self, img: Image.Image, cw: int, ch: int) -> Image.Image:
        iw, ih = img.size
        ratio = min(cw / iw, ch / ih, 1.0)
        new_w = int(iw * ratio)
        new_h = int(ih * ratio)
        return img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    def _on_resize(self, event: tk.Event | None = None):
        if event and event.widget is not self.root:
            return
        if not self.slideshow_frame.winfo_ismapped() or not self.images or self._loading:
            return
        # Debounce rapid resize events
        if self.resize_after_id is not None:
            self.root.after_cancel(self.resize_after_id)
        self.resize_after_id = self.root.after(
            250, lambda: self._show_image(self.current_index)
        )

    # ------------------------------------------------------------------
    # Rotation
    # ------------------------------------------------------------------
    def _rotate_left(self):
        self._rotation_angle = (self._rotation_angle - 90) % 360
        self._show_image(self.current_index)

    def _rotate_right(self):
        self._rotation_angle = (self._rotation_angle + 90) % 360
        self._show_image(self.current_index)

    # ------------------------------------------------------------------
    # Navigation / controls
    # ------------------------------------------------------------------
    def _advance(self):
        if self.images:
            self._rotation_angle = 0
            self._show_image(self.current_index + 1)
            if not self.untimed and not self.paused:
                self._cancel_tick()
                self._schedule_tick()

    def _go_back(self):
        if self.images:
            self._rotation_angle = 0
            self._show_image(self.current_index - 1)
            if not self.untimed and not self.paused:
                self._cancel_tick()
                self._schedule_tick()

    def _toggle_pause(self):
        if self.untimed:
            return
        self.paused = not self.paused
        if self.paused:
            self.pause_btn.configure(text="Play", fg_color="#059669", hover_color="#047857")
            self._cancel_tick()
        else:
            self.pause_btn.configure(text="Pause", fg_color="#6366f1", hover_color="#4f46e5")
            self._schedule_tick()

    def _toggle_shuffle(self):
        self.shuffle = not self.shuffle
        text = "Shuffle: ON" if self.shuffle else "Shuffle: OFF"
        self.shuffle_btn.configure(text=text)
        if self.images:
            current_path = self.images[self.current_index]
            self._load_images(self.folder_path_var.get())
            if current_path in self.images:
                self.current_index = self.images.index(current_path)
            self._show_image(self.current_index)

    # ------------------------------------------------------------------
    # Timer logic
    # ------------------------------------------------------------------
    def _schedule_tick(self):
        self._cancel_tick()
        self.after_id = self.root.after(100, self._tick)

    def _cancel_tick(self):
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None

    def _tick(self):
        if self.untimed or self.paused or not self.images:
            return
        self.time_remaining_ms -= 100
        self._update_countdown_display()
        if self.time_remaining_ms <= 0:
            self._advance()
        else:
            self.after_id = self.root.after(100, self._tick)

    def _update_countdown_display(self):
        if self.untimed:
            self.countdown_label.configure(text="")
            return
        seconds = max(0, self.time_remaining_ms) // 1000
        self.countdown_label.configure(text=f"{seconds}s remaining")

    # ------------------------------------------------------------------
    # Screen switching
    # ------------------------------------------------------------------
    def _show_setup(self):
        self._cancel_tick()
        self.slideshow_frame.grid_forget()
        self.setup_frame.grid(row=0, column=0, sticky="nsew")
        self.root.title("Image Viewer")

    def _show_slideshow(self):
        self.setup_frame.grid_forget()
        self.slideshow_frame.grid(row=0, column=0, sticky="nsew")
        self.root.title("Image Viewer — Slideshow")
        # Reset pause button to default state
        self.pause_btn.configure(text="Pause", fg_color="#6366f1", hover_color="#4f46e5")


# ----------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------
def main():
    root = ctk.CTk()
    app = ImageViewerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
