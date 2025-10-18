import os
import sys
import logging
import tempfile
from pathlib import Path

import requests
from zipfile import ZipFile
import shutil
from pydub import AudioSegment
from pydub.utils import which
from .resource_path import resource_path

logger = logging.getLogger(__name__)


def _embedded_ffmpeg_bin_dir() -> Path:
    # When frozen, resources live under _MEIPASS; in dev, under project root
    return resource_path("third_party/ffmpeg/bin")


def _user_ffmpeg_bin_dir() -> Path:
    """Return a writable per-user directory for FFmpeg binaries on Windows.

    Example: %LOCALAPPDATA%/EpubToAudiobook/ffmpeg/bin
    Fallback to ~/.epub_to_audiobook/ffmpeg/bin if LOCALAPPDATA is not set.
    """
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA")
        if base:
            return Path(base) / "EpubToAudiobook" / "ffmpeg" / "bin"
    # Cross-platform fallback
    return Path.home() / ".epub_to_audiobook" / "ffmpeg" / "bin"


def _set_pydub_ffmpeg(bin_dir: Path) -> None:
    ffmpeg = bin_dir / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
    ffprobe = bin_dir / ("ffprobe.exe" if os.name == "nt" else "ffprobe")
    # Prepend to PATH so subprocesses can see it
    os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")
    # Tell pydub explicitly
    AudioSegment.converter = str(ffmpeg)
    AudioSegment.ffprobe = str(ffprobe)
    logger.info(f"Using bundled FFmpeg at: {ffmpeg}")


def _try_configure_from_embedded() -> bool:
    bin_dir = _embedded_ffmpeg_bin_dir()
    ffmpeg = bin_dir / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
    ffprobe = bin_dir / ("ffprobe.exe" if os.name == "nt" else "ffprobe")
    if ffmpeg.exists() and ffprobe.exists():
        _set_pydub_ffmpeg(bin_dir)
        return True
    return False


def _download_and_install_ffmpeg() -> bool:
    """Download a Windows x64 static FFmpeg build and place ffmpeg/ffprobe into a user-writable folder.

    Returns True on success, False otherwise.
    """
    if os.name != "nt":
        return False

    url = (
        "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"
        "ffmpeg-master-latest-win64-gpl.zip"
    )

    tmp_path: Path | None = None
    try:
        logger.info("Downloading FFmpeg (Windows x64 static build)...")
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        tmp.write(chunk)
                tmp_path = Path(tmp.name)

        # Install into a user-writable location
        target_bin = _user_ffmpeg_bin_dir()
        target_bin.mkdir(parents=True, exist_ok=True)

        with ZipFile(tmp_path, 'r') as z:
            # Extract only the bin/ffmpeg.exe and bin/ffprobe.exe
            members = [
                name for name in z.namelist()
                if name.lower().endswith('/bin/ffmpeg.exe') or name.lower().endswith('/bin/ffprobe.exe')
            ]
            if members:
                # Copy only the needed binaries from the archive
                for m in members:
                    filename = Path(m).name
                    with z.open(m) as src, open(target_bin / filename, 'wb') as dst:
                        dst.write(src.read())
            else:
                # Fall back to extracting entire zip to a temp dir, then copy binaries
                extract_root = Path(tempfile.mkdtemp(prefix="ffmpeg_extract_"))
                z.extractall(extract_root)
                ffmpeg_candidates = list(extract_root.rglob("ffmpeg.exe"))
                ffprobe_candidates = list(extract_root.rglob("ffprobe.exe"))
                if not ffmpeg_candidates or not ffprobe_candidates:
                    logger.error("FFmpeg download extracted but binaries not found")
                    return False
                shutil.copyfile(ffmpeg_candidates[0], target_bin / "ffmpeg.exe")
                shutil.copyfile(ffprobe_candidates[0], target_bin / "ffprobe.exe")

        # Configure pydub to use the newly installed binaries
        _set_pydub_ffmpeg(target_bin)
        logger.info("FFmpeg installed to user directory: %s", target_bin)
        return True
    except Exception as e:
        logger.warning(f"Failed to download/install FFmpeg: {e}")
        return False
    finally:
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass


def ensure_ffmpeg_available() -> None:
    """Ensure FFmpeg/ffprobe are available to pydub.

    Order:
    1) If already on PATH, do nothing.
    2) If embedded third_party/ffmpeg/bin exists, configure pydub to use it.
    3) On Windows, try auto-download and configure.
    4) Otherwise, log instruction.
    """
    ffmpeg_path = which("ffmpeg")
    ffprobe_path = which("ffprobe")
    if ffmpeg_path and ffprobe_path:
        logger.info(f"Found FFmpeg on PATH: ffmpeg={ffmpeg_path}, ffprobe={ffprobe_path}")
        return

    if _try_configure_from_embedded():
        return

    if _download_and_install_ffmpeg():
        return

    logger.warning(
        "FFmpeg/ffprobe not found. Some conversions (e.g., MP3) require FFmpeg. "
        "Either install FFmpeg and add it to PATH, or place ffmpeg.exe and ffprobe.exe under "
        f"{_embedded_ffmpeg_bin_dir()}"
    )
