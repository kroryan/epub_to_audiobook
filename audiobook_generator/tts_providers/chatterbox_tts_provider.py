"""Chatterbox Multilingual V3 provider with an isolated worker process."""

from __future__ import annotations

import json
import logging
import os
import subprocess
from pathlib import Path

from audiobook_generator.config.general_config import GeneralConfig
from audiobook_generator.core.audio_tags import AudioTags
from audiobook_generator.tts_providers.base_tts_provider import BaseTTSProvider
from audiobook_generator.utils.utils import set_audio_tags

logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGES = {
    "ar": "Arabic", "da": "Danish", "de": "German", "el": "Greek",
    "en": "English", "es": "Spanish", "fi": "Finnish", "fr": "French",
    "he": "Hebrew", "hi": "Hindi", "it": "Italian", "ja": "Japanese",
    "ko": "Korean", "ms": "Malay", "nl": "Dutch", "no": "Norwegian",
    "pl": "Polish", "pt": "Portuguese", "ru": "Russian", "sv": "Swedish",
    "sw": "Swahili", "tr": "Turkish", "zh": "Chinese",
}


class ChatterboxTTSProvider(BaseTTSProvider):
    def __init__(self, config: GeneralConfig):
        config.output_format = (config.output_format or "mp3").lower()
        config.chatterbox_model = (config.chatterbox_model or "v3").lower()
        config.chatterbox_language = (config.chatterbox_language or "es").lower()
        self._worker = None
        self._worker_log_handle = None
        self._ready = False
        super().__init__(config)

    def validate_config(self):
        if self.config.chatterbox_model not in {"v2", "v3"}:
            raise ValueError("Chatterbox: el modelo debe ser v2 o v3")
        if self.config.chatterbox_language not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Chatterbox: idioma no soportado: {self.config.chatterbox_language}")
        if self.config.output_format not in {"wav", "mp3"}:
            raise ValueError("Chatterbox: formato de salida debe ser wav o mp3")
        if self.config.chatterbox_device not in {"cpu", "cuda"}:
            raise ValueError("Chatterbox: dispositivo debe ser cpu o cuda")

    def get_break_string(self):
        return "\n\n"

    def get_output_file_extension(self):
        return self.config.output_format

    def estimate_cost(self, total_chars):
        return 0.0

    def _start_worker(self):
        if self._worker and self._worker.poll() is None and self._ready:
            return
        project_root = Path(__file__).resolve().parents[2]
        python = project_root / ".venv_chatterbox" / "bin" / "python"
        worker = Path(__file__).with_name("chatterbox_worker.py")
        if not python.exists():
            raise RuntimeError(f"No existe el entorno Chatterbox: {python}")
        env = os.environ.copy()
        cache = project_root / ".cache" / "chatterbox"
        env.setdefault("HF_HOME", str(cache / "huggingface"))
        env.setdefault("TRANSFORMERS_CACHE", str(cache / "transformers"))
        env.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
        env["CHATTERBOX_DEVICE"] = self.config.chatterbox_device
        env["CHATTERBOX_MODEL"] = self.config.chatterbox_model
        log_path = getattr(self.config, "log_file", None)
        if log_path:
            Path(log_path).parent.mkdir(parents=True, exist_ok=True)
            self._worker_log_handle = open(log_path, "a", encoding="utf-8")
        self._worker = subprocess.Popen(
            [str(python), str(worker)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self._worker_log_handle,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        ready = self._worker.stdout.readline() if self._worker.stdout else ""
        if not ready:
            return_code = self._worker.poll()
            if return_code is not None:
                raise RuntimeError(
                    "Chatterbox terminó durante el arranque "
                    f"(código {return_code}); revisa el log para ver el motivo"
                )
            raise RuntimeError("Chatterbox no devolvió estado de arranque")
        message = json.loads(ready)
        if not message.get("ready"):
            raise RuntimeError(f"Chatterbox no pudo arrancar: {message}")
        self._ready = True
        logger.info("Chatterbox %s listo en %s", self.config.chatterbox_model.upper(), message.get("device"))

    def text_to_speech(self, text: str, output_file: str, audio_tags: AudioTags):
        self._start_worker()
        reference = self.config.chatterbox_reference_audio
        if hasattr(reference, "name"):
            reference = reference.name
        request = {
            "text": text,
            "output_file": str(Path(output_file).absolute()),
            "language": self.config.chatterbox_language,
            "reference_audio": str(reference) if reference else None,
            "exaggeration": self.config.chatterbox_exaggeration,
            "cfg_weight": self.config.chatterbox_cfg_weight,
            "temperature": self.config.chatterbox_temperature,
            "repetition_penalty": self.config.chatterbox_repetition_penalty,
            "min_p": self.config.chatterbox_min_p,
            "top_p": self.config.chatterbox_top_p,
            "break_duration": self.config.chatterbox_break_duration,
            "max_chars": self.config.chatterbox_max_chars,
            "bitrate": "192k",
        }
        if not self._worker or not self._worker.stdin or not self._worker.stdout:
            raise RuntimeError("Chatterbox worker no está disponible")
        self._worker.stdin.write(json.dumps(request, ensure_ascii=False) + "\n")
        self._worker.stdin.flush()
        response = self._worker.stdout.readline()
        if not response:
            raise RuntimeError("Chatterbox terminó inesperadamente; revisa el log (posible falta de VRAM)")
        result = json.loads(response)
        if not result.get("ok"):
            raise RuntimeError(result.get("error", "Chatterbox no pudo generar el audio"))
        set_audio_tags(output_file, audio_tags)
        logger.info("Audio Chatterbox exportado: %s", output_file)

    def close(self):
        if self._worker and self._worker.poll() is None:
            try:
                self._worker.stdin.write(json.dumps({"command": "stop"}) + "\n")
                self._worker.stdin.flush()
                self._worker.wait(timeout=10)
            except Exception:
                self._worker.kill()
        self._worker = None
        self._ready = False
        if self._worker_log_handle:
            self._worker_log_handle.close()
            self._worker_log_handle = None


def get_chatterbox_supported_languages():
    return list(SUPPORTED_LANGUAGES.items())


def get_chatterbox_supported_models():
    return ["v3", "v2"]
