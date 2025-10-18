import argparse

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not installed, skip loading .env file
    pass

from audiobook_generator.config.ui_config import UiConfig
from audiobook_generator.ui.web_ui import host_ui
from audiobook_generator.utils.ffmpeg_setup import ensure_ffmpeg_available


def handle_args():
    parser = argparse.ArgumentParser(description="WebUI for Epub to Audiobook convertor")
    parser.add_argument("--host", default="127.0.0.1", help="Host address")
    parser.add_argument("--port", default=7860, type=int, help="Port number")

    ui_args = parser.parse_args()
    return UiConfig(ui_args)

def main():
    config = handle_args()
    # Ensure FFmpeg is available for pydub conversions
    ensure_ffmpeg_available()
    host_ui(config)

if __name__ == "__main__":
    main()


