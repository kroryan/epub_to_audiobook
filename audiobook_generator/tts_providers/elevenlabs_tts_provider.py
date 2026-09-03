"""ElevenLabs TTS provider.

The provider deliberately uses the HTTP API instead of the optional SDK.  This
keeps the application lightweight and makes it possible to use an ElevenLabs
free-plan API key without installing another large local speech engine.
"""

import io
import logging
import math
import os
import time
from typing import Dict, Iterable, List, Optional

import requests
from pydub import AudioSegment

from audiobook_generator.config.general_config import GeneralConfig
from audiobook_generator.core.audio_tags import AudioTags
from audiobook_generator.tts_providers.base_tts_provider import BaseTTSProvider
from audiobook_generator.utils.utils import set_audio_tags, split_text

logger = logging.getLogger(__name__)

ELEVENLABS_API_BASE = "https://api.elevenlabs.io"
BREAK_STRING = " @BRK#"
DEFAULT_MODEL = "eleven_multilingual_v2"
DEFAULT_OUTPUT_FORMAT = "mp3"
DEFAULT_MAX_CHARS = 4500
TRANSIENT_STATUS_CODES = {408, 409, 425, 429, 500, 502, 503, 504}


def get_elevenlabs_supported_models() -> List[str]:
    return [
        "eleven_multilingual_v2",
        "eleven_flash_v2_5",
        "eleven_turbo_v2_5",
        "eleven_v3",
    ]


def get_elevenlabs_supported_output_formats() -> List[str]:
    # The UI exports one final MP3 after merging coherent text chunks.
    return [DEFAULT_OUTPUT_FORMAT]


def _voice_languages(voice: Dict) -> List[Dict]:
    languages = voice.get("verified_languages") or []
    return [item for item in languages if isinstance(item, dict)]


def _voice_labels(voice: Dict) -> Dict:
    labels = voice.get("labels") or {}
    return labels if isinstance(labels, dict) else {}


def voice_language_codes(voice: Dict) -> List[str]:
    """Return language codes advertised by a voice."""
    result = []
    for language in _voice_languages(voice):
        code = language.get("language") or language.get("language_code")
        if code and code not in result:
            result.append(str(code))
    label_language = _voice_labels(voice).get("language")
    if label_language and label_language not in result:
        result.append(str(label_language))
    return result


def voice_accents(voice: Dict, language_code: str = "") -> List[str]:
    """Return accent metadata, optionally restricted to one language."""
    accents = []
    for language in _voice_languages(voice):
        code = language.get("language") or language.get("language_code")
        if language_code and code and code != language_code:
            continue
        accent = language.get("accent")
        if accent and accent not in accents:
            accents.append(str(accent))
    label_accent = _voice_labels(voice).get("accent")
    if label_accent and label_accent not in accents:
        accents.append(str(label_accent))
    return accents


def format_voice_choice(voice: Dict) -> str:
    """Create a readable UI label while keeping the API voice id as value."""
    voice_id = str(voice.get("voice_id") or "")
    name = str(voice.get("name") or voice_id)
    labels = _voice_labels(voice)
    details = []
    for key in ("gender", "age", "use_case"):
        if labels.get(key):
            details.append(str(labels[key]))
    accents = voice_accents(voice)
    if accents:
        details.append("/".join(accents))
    suffix = f" — {', '.join(details)}" if details else ""
    return f"{name}{suffix} [{voice_id}]"


def _voice_search_text(voice: Dict) -> str:
    labels = _voice_labels(voice)
    language_text = " ".join(voice_language_codes(voice))
    accent_text = " ".join(voice_accents(voice))
    return " ".join(
        str(value)
        for value in [
            voice.get("voice_id", ""),
            voice.get("name", ""),
            voice.get("description", ""),
            language_text,
            accent_text,
            " ".join(str(value) for value in labels.values()),
        ]
    ).lower()


def filter_elevenlabs_voices(
    voices: Iterable[Dict], language_code: str = "", accent: str = "", search: str = ""
) -> List[Dict]:
    """Filter the voice explorer without changing the downloaded voice list."""
    search = (search or "").strip().lower()
    filtered = []
    for voice in voices or []:
        if language_code and language_code not in voice_language_codes(voice):
            continue
        if accent and accent not in voice_accents(voice, language_code):
            continue
        if search and search not in _voice_search_text(voice):
            continue
        filtered.append(voice)
    return sorted(filtered, key=lambda item: str(item.get("name", "")).lower())


def fetch_elevenlabs_voices(api_key: Optional[str], page_size: int = 100) -> List[Dict]:
    """Fetch all available voices exposed by the user's ElevenLabs account."""
    key = (api_key or os.getenv("ELEVENLABS_API_KEY") or "").strip()
    if not key:
        raise ValueError(
            "Falta la API key de ElevenLabs. Escríbela en la pestaña ElevenLabs "
            "o define ELEVENLABS_API_KEY."
        )

    voices = []
    next_page_token = ""
    while True:
        params = {"page_size": min(max(int(page_size), 1), 100)}
        if next_page_token:
            params["page_token"] = next_page_token
        response = requests.get(
            f"{ELEVENLABS_API_BASE}/v2/voices",
            headers={"xi-api-key": key, "Accept": "application/json"},
            params=params,
            timeout=30,
        )
        if response.status_code != 200:
            detail = response.text[:500]
            raise RuntimeError(
                f"ElevenLabs no pudo listar las voces ({response.status_code}): {detail}"
            )
        data = response.json()
        voices.extend(item for item in data.get("voices", []) if isinstance(item, dict))
        next_page_token = data.get("pagination", {}).get("next_page_token") or data.get(
            "next_page_token", ""
        )
        if not next_page_token:
            break
    return voices


def get_elevenlabs_language_choices(voices: Iterable[Dict]):
    languages = {}
    for voice in voices or []:
        for item in _voice_languages(voice):
            code = item.get("language") or item.get("language_code")
            if code:
                name = item.get("language_name") or item.get("name") or code
                languages[str(code)] = f"{name} ({code})"
        for code in voice_language_codes(voice):
            languages.setdefault(code, code)
    return [("Todos los idiomas", "")] + sorted(
        ((label, code) for code, label in languages.items()), key=lambda item: item[0].lower()
    )


def get_elevenlabs_accent_choices(voices: Iterable[Dict], language_code: str = ""):
    accents = sorted(
        {
            accent
            for voice in voices or []
            for accent in voice_accents(voice, language_code)
        },
        key=str.lower,
    )
    return [("Todos los acentos", "")] + [(accent, accent) for accent in accents]


def get_elevenlabs_voice_choices(
    voices: Iterable[Dict], language_code: str = "", accent: str = "", search: str = ""
):
    filtered = filter_elevenlabs_voices(voices, language_code, accent, search)
    return [(format_voice_choice(voice), voice.get("voice_id")) for voice in filtered]


class ElevenLabsTTSProvider(BaseTTSProvider):
    def __init__(self, config: GeneralConfig):
        config.model_name = config.model_name or DEFAULT_MODEL
        config.voice_name = config.voice_name or os.getenv("ELEVENLABS_VOICE_ID")
        config.output_format = config.output_format or DEFAULT_OUTPUT_FORMAT
        config.speed = config.speed or 1.0
        config.elevenlabs_break_duration = getattr(config, "elevenlabs_break_duration", 1250)

        self.api_key = (
            getattr(config, "elevenlabs_api_key", None) or os.getenv("ELEVENLABS_API_KEY") or ""
        ).strip()
        self.model_id = config.model_name
        self.language_code = (
            getattr(config, "elevenlabs_language", None) or config.language or ""
        ).strip()
        self.max_chars = int(getattr(config, "elevenlabs_max_chars", DEFAULT_MAX_CHARS))
        self.break_duration = max(0, int(config.elevenlabs_break_duration or 0))
        self.price_per_1000 = 0.05 if "flash" in self.model_id or "turbo" in self.model_id else 0.10
        super().__init__(config)

    def validate_config(self):
        if not self.api_key:
            raise ValueError(
                "ElevenLabs requiere una API key. Define ELEVENLABS_API_KEY o introdúcela en la UI."
            )
        if self.config.model_name not in get_elevenlabs_supported_models():
            raise ValueError(f"ElevenLabs: modelo no soportado: {self.config.model_name}")
        if self.config.output_format not in get_elevenlabs_supported_output_formats():
            raise ValueError(f"ElevenLabs: formato no soportado: {self.config.output_format}")
        if not self.config.voice_name:
            raise ValueError("ElevenLabs requiere seleccionar una voz del explorador.")
        if not 0.5 <= float(self.config.speed) <= 2.0:
            raise ValueError("ElevenLabs: la velocidad debe estar entre 0.5 y 2.0.")

    def estimate_cost(self, total_chars):
        return math.ceil(total_chars / 1000) * self.price_per_1000

    def get_break_string(self):
        return BREAK_STRING

    def get_output_file_extension(self):
        return "mp3"

    def _sentence_language(self) -> str:
        # sentencex accepts ISO language names/codes. ElevenLabs uses the same
        # short code for Spanish and other common languages.
        return (self.language_code or "es").split("-", 1)[0]

    def _synthesize_request(self, text: str) -> AudioSegment:
        if not text.strip():
            return AudioSegment.empty()

        url = (
            f"{ELEVENLABS_API_BASE}/v1/text-to-speech/"
            f"{self.config.voice_name}?output_format=mp3_44100_128"
        )
        payload = {
            "text": text,
            "model_id": self.model_id,
            "voice_settings": {
                "stability": 0.55,
                "similarity_boost": 0.75,
                "style": 0.0,
                "use_speaker_boost": True,
                "speed": float(self.config.speed),
            },
        }
        # multilingual_v2 detects the language itself and rejects this field.
        if self.model_id != "eleven_multilingual_v2" and self.language_code:
            payload["language_code"] = self.language_code.split("-", 1)[0]

        for attempt in range(4):
            response = requests.post(
                url,
                headers={
                    "xi-api-key": self.api_key,
                    "Content-Type": "application/json",
                    "Accept": "audio/mpeg",
                },
                json=payload,
                timeout=120,
            )
            if response.status_code == 200:
                try:
                    return AudioSegment.from_file(io.BytesIO(response.content), format="mp3")
                except Exception as exc:
                    raise RuntimeError(f"ElevenLabs devolvió audio no válido: {exc}") from exc

            detail = response.text[:500]
            if response.status_code not in TRANSIENT_STATUS_CODES or attempt == 3:
                if response.status_code in (401, 403):
                    detail = "API key inválida, sin permisos o sin cuota disponible."
                raise RuntimeError(f"ElevenLabs TTS ({response.status_code}): {detail}")

            retry_after = response.headers.get("Retry-After")
            delay = min(8, float(retry_after)) if retry_after else 2**attempt
            logger.warning(
                "ElevenLabs respondió %s; reintentando en %.1fs (%s/4)",
                response.status_code,
                delay,
                attempt + 1,
            )
            time.sleep(delay)
        raise RuntimeError("ElevenLabs: se agotaron los reintentos")

    def _synthesize_coherent_parts(self, text: str, chapter_id: str) -> AudioSegment:
        parts = [part.strip() for part in text.split(BREAK_STRING) if part.strip()]
        if not parts:
            return AudioSegment.empty()

        result = AudioSegment.empty()
        chunk_number = 0
        for part_number, part in enumerate(parts, 1):
            chunks = split_text(part, self.max_chars, self._sentence_language())
            for chunk in chunks:
                chunk_number += 1
                logger.info(
                    "Processing %s_chunk_%s, length=%s (sentence-aware)",
                    chapter_id,
                    chunk_number,
                    len(chunk),
                )
                result += self._synthesize_request(chunk)
            if part_number < len(parts) and self.break_duration:
                result += AudioSegment.silent(duration=self.break_duration, frame_rate=44100)
        return result

    def text_to_speech(self, text: str, output_file: str, audio_tags: AudioTags):
        combined = self._synthesize_coherent_parts(text, f"chapter-{audio_tags.idx}_{audio_tags.title}")
        if len(combined) == 0:
            raise ValueError("ElevenLabs no recibió texto con contenido para convertir.")
        combined.export(output_file, format="mp3", bitrate="128k")
        set_audio_tags(output_file, audio_tags)

