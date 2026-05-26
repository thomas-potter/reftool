# Image Viewer – Linux Install Guide

A simple GUI image viewer with timed slideshow, shuffle, and subfolder scanning.

## Requirements

- Python 3.8 or newer
- tkinter (usually bundled with Python on most Linux distros)
- Pillow (Python Imaging Library)

## 1. Download the files

Copy these three files to your Linux machine (e.g., into `~/image-viewer/`):

- `image_viewer.py`
- `requirements.txt`
- `INSTALL.md`

## 2. Install Pillow

Open a terminal in the folder and run:

```bash
pip3 install -r requirements.txt
```

Or, if you prefer to install system-wide:

```bash
sudo apt update && sudo apt install -y python3-pil python3-pil.imagetk
```

> **Note:** If you get a `tkinter` error, install it first:
> ```bash
> sudo apt install -y python3-tk
> ```

## 3. Make it executable

```bash
chmod +x image_viewer.py
```

## 4. Run it

```bash
./image_viewer.py
```

Or:

```bash
python3 image_viewer.py
```

## Optional – Create a desktop shortcut

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
