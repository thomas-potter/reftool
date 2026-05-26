# Image Viewer — Linux Install Guide

A modern GUI image viewer with timed slideshow, shuffle, rotation, and subfolder scanning.

## Requirements

- Python 3.8 or newer
- tkinter (usually bundled with Python on most Linux distros)
- Pillow and customtkinter

## 1. Download the files

Copy these files to your Linux machine (e.g., into `~/image-viewer/`):

- `image_viewer.py`
- `requirements.txt`
- `install.md`

## 2. Install dependencies

Open a terminal in the folder and run:

```bash
pip3 install -r requirements.txt
```

Or install system-wide:

```bash
sudo apt update && sudo apt install -y python3-pil python3-pil.imagetk
pip3 install customtkinter
```

> **Note:** If you get a `tkinter` error, install it first:
> ```bash
> sudo apt install -y python3-tk
> ```

## 3. Optional — Better file picker

On Linux the app will try to use **Zenity** (a GTK file chooser) for the folder browser.
If Zenity is not installed it falls back to the standard tkinter dialog.

```bash
sudo apt install -y zenity
```

## 4. Make it executable

```bash
chmod +x image_viewer.py
```

## 5. Run it

```bash
./image_viewer.py
```

Or:

```bash
python3 image_viewer.py
```

## Controls

| Key | Action |
|-----|--------|
| `Left` / `Right` arrows | Previous / next image |
| `Space` | Pause / play slideshow |
| `r` | Rotate image 90° clockwise |
| `R` (Shift+R) | Rotate image 90° counter-clockwise |
| `Escape` | Back to setup |

## Optional — Create a desktop shortcut

Create a file named `image-viewer.desktop`:

```bash
cat > ~/.local/share/applications/image-viewer.desktop << 'DESKTOP'
[Desktop Entry]
Name=Image Viewer
Exec=/usr/bin/python3 /home/YOUR_USERNAME/image-viewer/image_viewer.py
Type=Application
Terminal=false
Icon=image-viewer
Categories=Graphics;Viewer;
DESKTOP
```

Replace `YOUR_USERNAME` with your actual Linux username and update the path to `image_viewer.py`.

Then reload the desktop database:

```bash
update-desktop-database ~/.local/share/applications/
```

The app will now appear in your applications menu.
