# Packaging to EXE (Windows)

This project includes scripts to bundle dependencies, Piper voice models, and FFmpeg, and build a single Windows EXE with a system tray icon.

## Prerequisites
- Python 3.11 on Windows
- PowerShell execution policy that allows running local scripts

## Steps

1. Install dependencies

```powershell
pip install -r requirements.txt
pip install pyinstaller
```

2. Download FFmpeg (embedded into `third_party/ffmpeg/bin`)

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install_ffmpeg.ps1
```

3. Download Piper voice models

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\download_piper_models.ps1
```

4. Build the EXE

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_exe.ps1
```

The resulting EXE will be in `dist/EpubToAudiobook.exe`.

## Alternative: Installer or Portable ZIP (Recommended)

Some environments show extraction errors with very large onefile bundles (e.g., `Cython\Compiler\Code.cp311-win_amd64.pyd: decompression resulted in return code -1`). In that case, build an installer or a portable ZIP using the onedir layout:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_installer.ps1
```

This produces either:
- `dist/EpubToAudiobook-Setup.exe` (if Inno Setup is installed: `iscc.exe` in PATH), or
- `dist/EpubToAudiobook-portable.zip` as a no-install portable folder.

## System Tray App
- Double-click the EXE to launch a tray icon.
- Right-click the tray icon to:
  - Start Server: launches the Gradio Web UI
  - Stop Server: terminates the Web UI process
  - Show Logs: opens a small window that streams the log file
  - Quit: stops the server (if running) and exits

## Voice Models Included
The `scripts/download_piper_models.ps1` script downloads these models into `piper_tts/espeak-ng-data/voices/`:
- es_ES-davefx-medium.onnx (Español España - Davefx, Medium)
- es_ES-mls_10246-low.onnx (Español España - Clara, Low)
- en_US-lessac-medium.onnx (English US - Lessac, Medium)
- en_US-amy-medium.onnx (English US - Amy, Medium)

## Packaging Notes
- FFmpeg and FFprobe are used by pydub for MP3 export. The app auto-configures to use the embedded binaries at runtime.
- Piper executable is expected at `piper_tts/piper.exe`. The UI defaults to this path, and the packaged app resolves it via a resource locator to work when frozen.
- If FFmpeg is not available, the app falls back to WAV output.
- Logs are written under `logs/` with UTF-8 encoding.
