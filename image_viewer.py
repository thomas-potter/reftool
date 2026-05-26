#!/usr/bin/env python3
"""Simple image viewer GUI for Linux with timed slideshow and shuffle."""

import os
import random
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk

# ---------------------------------------------------------------------------
# Theme colours (dark mode inverted)
# ---------------------------------------------------------------------------
BG = "#1F1E1D"          # Dark Brown-Gray (was FG, now background)
FG = "#FAF9F5"          # Warm Off-White (was BG, now foreground/text)
ACCENT = "#1C6BBB"      # Claude Blue
EMPHASIS = "#C96442"    # Terracotta Orange
DISABLED = "#A0A0A8"    # Lighter Gray for dark mode readability

CANVAS_BG = "#141312"   # Slightly darker than BG for image canvas
ENTRY_BG = "#2A2928"    # Darker input field background

BUTTON_STYLE = {
    "bg": ACCENT,
    "fg": "#FFFFFF",
    "activebackground": "#155A9E",
    "activeforeground": "#FFFFFF",
    "bd": 0,
    "padx": 14,
    "pady": 8,
    "font": ("Helvetica", 11, "bold"),
    "cursor": "hand2",
}

TOGGLE_ON_STYLE = {
    "bg": EMPHASIS,
    "fg": "#FFFFFF",
    "activebackground": "#A65338",
    "activeforeground": "#FFFFFF",
    "bd": 0,
    "padx": 14,
    "pady": 8,
    "font": ("Helvetica", 11, "bold"),
    "cursor": "hand2",
}

LABEL_STYLE = {
    "bg": BG,
    "fg": FG,
    "font": ("Helvetica", 11),
}

SMALL_LABEL_STYLE = {
    "bg": BG,
    "fg": FG,
    "font": ("Helvetica", 10),
}

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
class ImageViewerApp:
    IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif"}

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Image Viewer")
        self.root.configure(bg=BG)
        self.root.geometry("900x650")
        self.root.minsize(600, 400)

        # State
        self.images: list[str] = []
        self.current_index: int = 0
        self.shuffle: bool = False
        self.interval_ms: int = 30_000
        self.untimed: bool = True
        self.paused: bool = False
        self.time_remaining_ms: int = 0
        self.after_id: str | None = None
        self.photo_image: ImageTk.PhotoImage | None = None
        self.subfolders: bool = True

        # Build screens
        self._build_setup_screen()
        self._build_slideshow_screen()

        self._show_setup()

        # Keyboard shortcuts
        self.root.bind("<Escape>", lambda e: self._show_setup())
        self.root.bind("<Left>", lambda e: self._go_back())
        self.root.bind("<Right>", lambda e: self._advance())
        self.root.bind("<space>", lambda e: self._toggle_pause())
        self.root.bind("<Configure>", lambda e: self._on_resize())

    # -----------------------------------------------------------------------
    # Setup screen
    # -----------------------------------------------------------------------
    def _build_setup_screen(self):
        self.setup_frame = tk.Frame(self.root, bg=BG)

        # Title
        tk.Label(
            self.setup_frame,
            text="Image Viewer",
            bg=BG,
            fg=FG,
            font=("Helvetica", 28, "bold"),
        ).pack(pady=(40, 10))

        # Folder selection
        folder_frame = tk.Frame(self.setup_frame, bg=BG)
        folder_frame.pack(pady=20, padx=40, fill=tk.X)

        self.folder_path_var = tk.StringVar()
        tk.Entry(
            folder_frame,
            textvariable=self.folder_path_var,
            state="readonly",
            bg=ENTRY_BG,
            fg=FG,
            font=("Helvetica", 11),
            relief="solid",
            bd=1,
            highlightthickness=0,
            insertbackground=FG,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, padx=(0, 8))

        tk.Button(
            folder_frame,
            text="Browse…",
            command=self._browse_folder,
            **BUTTON_STYLE,
        ).pack(side=tk.RIGHT)

        # Subfolders toggle
        self.subfolders_var = tk.BooleanVar(value=True)
        sub_cb = tk.Checkbutton(
            self.setup_frame,
            text="Include subfolders",
            variable=self.subfolders_var,
            bg=BG,
            fg=FG,
            activebackground=BG,
            activeforeground=FG,
            selectcolor=ENTRY_BG,
            font=("Helvetica", 11),
            cursor="hand2",
        )
        sub_cb.pack(pady=(0, 20))

        # Interval selection
        interval_frame = tk.LabelFrame(
            self.setup_frame,
            text=" Slideshow timing ",
            bg=BG,
            fg=FG,
            font=("Helvetica", 12, "bold"),
            bd=1,
        )
        interval_frame.pack(padx=40, pady=10, fill=tk.X)

        # Untimed checkbox
        self.untimed_var = tk.BooleanVar(value=True)
        untimed_cb = tk.Checkbutton(
            interval_frame,
            text="Untimed (manual navigation only)",
            variable=self.untimed_var,
            bg=BG,
            fg=FG,
            activebackground=BG,
            activeforeground=FG,
            selectcolor=ENTRY_BG,
            font=("Helvetica", 11),
            cursor="hand2",
            command=self._on_untimed_toggle,
        )
        untimed_cb.pack(anchor=tk.W, padx=10, pady=(8, 0))

        # Slider row
        self.slider_frame = tk.Frame(interval_frame, bg=BG)
        self.slider_frame.pack(fill=tk.X, padx=10, pady=(5, 10))

        self.interval_var = tk.IntVar(value=30)
        self.interval_scale = tk.Scale(
            self.slider_frame,
            from_=30,
            to=600,
            orient=tk.HORIZONTAL,
            variable=self.interval_var,
            bg=BG,
            fg=FG,
            troughcolor="#3A3938",
            highlightthickness=0,
            activebackground=ACCENT,
            sliderlength=20,
            length=400,
            command=self._on_slider_change,
        )
        self.interval_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.interval_label = tk.Label(
            self.slider_frame,
            text="30 seconds",
            **LABEL_STYLE,
        )
        self.interval_label.pack(side=tk.RIGHT, padx=(10, 0))

        self._on_untimed_toggle()

        # Image count label
        self.count_label = tk.Label(
            self.setup_frame,
            text="No folder selected",
            **SMALL_LABEL_STYLE,
        )
        self.count_label.pack(pady=(10, 5))

        # Start button
        self.start_btn = tk.Button(
            self.setup_frame,
            text="Start Slideshow",
            command=self._start_slideshow,
            **BUTTON_STYLE,
        )
        self.start_btn.pack(pady=20)

    def _browse_folder(self):
        path = filedialog.askdirectory(title="Select Image Folder")
        if not path:
            return
        self.folder_path_var.set(path)
        self._refresh_image_count()

    def _refresh_image_count(self):
        path = self.folder_path_var.get()
        if not path:
            self.count_label.config(text="No folder selected")
            return
        self._load_images(path)
        if self.images:
            self.count_label.config(
                text=f"{len(self.images)} image(s) found",
                fg="#4CAF50",
            )
        else:
            self.count_label.config(
                text="No images found in selected folder",
                fg=EMPHASIS,
            )

    def _on_untimed_toggle(self):
        if self.untimed_var.get():
            self.interval_scale.config(state=tk.DISABLED, troughcolor="#3A3938")
            self.interval_label.config(fg=DISABLED)
        else:
            self.interval_scale.config(state=tk.NORMAL, troughcolor="#3A3938")
            self.interval_label.config(fg=FG)

    def _on_slider_change(self, value):
        seconds = int(float(value))
        self.interval_label.config(text=self._format_time(seconds))

    @staticmethod
    def _format_time(seconds: int) -> str:
        if seconds < 60:
            return f"{seconds} second{'s' if seconds != 1 else ''}"
        mins = seconds // 60
        secs = seconds % 60
        if secs == 0:
            return f"{mins} minute{'s' if mins != 1 else ''}"
        return f"{mins}m {secs}s"

    # -----------------------------------------------------------------------
    # Slideshow screen
    # -----------------------------------------------------------------------
    def _build_slideshow_screen(self):
        self.slideshow_frame = tk.Frame(self.root, bg=BG)
        self.slideshow_frame.grid_rowconfigure(0, weight=1)
        self.slideshow_frame.grid_columnconfigure(0, weight=1)

        # Canvas for image
        self.canvas = tk.Canvas(
            self.slideshow_frame,
            bg=CANVAS_BG,
            highlightthickness=0,
        )
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Bottom toolbar
        toolbar = tk.Frame(self.slideshow_frame, bg=BG, height=60)
        toolbar.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        toolbar.grid_propagate(False)

        self.prev_btn = tk.Button(
            toolbar,
            text="← Previous",
            command=self._go_back,
            **BUTTON_STYLE,
        )
        self.prev_btn.place(relx=0.05, rely=0.5, anchor="w")

        self.pause_btn = tk.Button(
            toolbar,
            text="Pause",
            command=self._toggle_pause,
            **TOGGLE_ON_STYLE,
        )
        self.pause_btn.place(relx=0.35, rely=0.5, anchor="c")

        self.countdown_label = tk.Label(
            toolbar,
            text="",
            bg=BG,
            fg=FG,
            font=("Helvetica", 12, "bold"),
        )
        self.countdown_label.place(relx=0.5, rely=0.5, anchor="c")

        self.shuffle_btn = tk.Button(
            toolbar,
            text="Shuffle: OFF",
            command=self._toggle_shuffle,
            **BUTTON_STYLE,
        )
        self.shuffle_btn.place(relx=0.65, rely=0.5, anchor="c")

        self.next_btn = tk.Button(
            toolbar,
            text="Next →",
            command=self._advance,
            **BUTTON_STYLE,
        )
        self.next_btn.place(relx=0.95, rely=0.5, anchor="e")

        # Filename label above toolbar
        self.filename_label = tk.Label(
            self.slideshow_frame,
            text="",
            bg=BG,
            fg=DISABLED,
            font=("Helvetica", 10),
        )
        self.filename_label.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 5))

    # -----------------------------------------------------------------------
    # Navigation & logic
    # -----------------------------------------------------------------------
    def _load_images(self, root_path: str):
        self.images = []
        if self.subfolders_var.get():
            for dirpath, _, filenames in os.walk(root_path):
                for name in filenames:
                    if os.path.splitext(name)[1].lower() in self.IMAGE_EXTS:
                        self.images.append(os.path.join(dirpath, name))
        else:
            for name in os.listdir(root_path):
                full = os.path.join(root_path, name)
                if os.path.isfile(full) and os.path.splitext(name)[1].lower() in self.IMAGE_EXTS:
                    self.images.append(full)
        self.images.sort()
        if self.shuffle:
            random.shuffle(self.images)

    def _start_slideshow(self):
        path = self.folder_path_var.get()
        if not path:
            messagebox.showwarning("No folder", "Please select a folder first.")
            return
        self.subfolders = self.subfolders_var.get()
        self._load_images(path)
        if not self.images:
            messagebox.showwarning("No images", "No supported images found in the selected folder.")
            return

        self.untimed = self.untimed_var.get()
        self.interval_ms = self.interval_var.get() * 1_000
        self.current_index = 0
        self.paused = False
        self.time_remaining_ms = self.interval_ms

        self._show_slideshow()
        self._show_image(0)
        if not self.untimed:
            self._schedule_tick()

    def _show_image(self, index: int):
        if not self.images:
            return
        self.current_index = index % len(self.images)
        path = self.images[self.current_index]
        self.filename_label.config(text=os.path.basename(path))

        try:
            pil_img = Image.open(path)
            pil_img = self._resize_to_fit(pil_img)
            self.photo_image = ImageTk.PhotoImage(pil_img)
        except Exception as exc:
            self.photo_image = None
            self.canvas.delete("all")
            self.canvas.create_text(
                self.canvas.winfo_width() // 2,
                self.canvas.winfo_height() // 2,
                text=f"Unable to load image:\n{exc}",
                fill=EMPHASIS,
                font=("Helvetica", 12),
                justify=tk.CENTER,
            )
            return

        self.canvas.delete("all")
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        x = cw // 2
        y = ch // 2
        self.canvas.create_image(x, y, image=self.photo_image, anchor=tk.CENTER)

        if not self.untimed:
            self.time_remaining_ms = self.interval_ms
            self._update_countdown_display()

    def _resize_to_fit(self, img: Image.Image) -> Image.Image:
        cw = max(self.canvas.winfo_width(), 1)
        ch = max(self.canvas.winfo_height(), 1)
        iw, ih = img.size
        ratio = min(cw / iw, ch / ih, 1.0)
        new_w = int(iw * ratio)
        new_h = int(ih * ratio)
        return img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    def _on_resize(self, event=None):
        if self.slideshow_frame.winfo_ismapped() and self.images:
            self._show_image(self.current_index)

    def _advance(self):
        if self.images:
            self._show_image(self.current_index + 1)
            if not self.untimed and not self.paused:
                self._cancel_tick()
                self._schedule_tick()

    def _go_back(self):
        if self.images:
            self._show_image(self.current_index - 1)
            if not self.untimed and not self.paused:
                self._cancel_tick()
                self._schedule_tick()

    def _toggle_pause(self):
        if self.untimed:
            return
        self.paused = not self.paused
        if self.paused:
            self.pause_btn.config(text="Play", **BUTTON_STYLE)
            self._cancel_tick()
        else:
            self.pause_btn.config(text="Pause", **TOGGLE_ON_STYLE)
            self._schedule_tick()

    def _toggle_shuffle(self):
        self.shuffle = not self.shuffle
        text = "Shuffle: ON" if self.shuffle else "Shuffle: OFF"
        self.shuffle_btn.config(text=text)
        if self.images:
            current_path = self.images[self.current_index]
            self._load_images(self.folder_path_var.get())
            if current_path in self.images:
                self.current_index = self.images.index(current_path)
            self._show_image(self.current_index)

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
            self.countdown_label.config(text="")
            return
        seconds = max(0, self.time_remaining_ms) // 1000
        self.countdown_label.config(text=f"{seconds}s")

    # -----------------------------------------------------------------------
    # Screen switching
    # -----------------------------------------------------------------------
    def _show_setup(self):
        self._cancel_tick()
        self.slideshow_frame.grid_forget()
        self.setup_frame.pack(fill=tk.BOTH, expand=True)
        self.root.title("Image Viewer – Setup")

    def _show_slideshow(self):
        self.setup_frame.pack_forget()
        self.slideshow_frame.grid(row=0, column=0, sticky="nsew")
        self.root.title("Image Viewer – Slideshow")
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    root = tk.Tk()
    app = ImageViewerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
