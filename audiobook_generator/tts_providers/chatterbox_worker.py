"""Persistent Chatterbox worker.

This file is executed with .venv_chatterbox/bin/python, never with the
application interpreter.  Requests and responses are JSON lines so the main
application can keep Edge, ElevenLabs, Coqui and Chatterbox isolated.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import tempfile
from pathlib import Path

import torch
import torchaudio
from pydub import AudioSegment

from chatterbox.mtl_tts import ChatterboxMultilingualTTS

logging.basicConfig(level=logging.INFO, format="[Chatterbox] %(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("chatterbox_worker")


def split_book_text(text: str, max_chars: int) -> list[str]:
    """Split at paragraph/sentence boundaries, preserving punctuation."""
    max_chars = max(300, int(max_chars or 900))
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]
    if not paragraphs:
        paragraphs = [text.strip()] if text.strip() else []

    chunks: list[str] = []
    sentence_re = re.compile(r"(?<=[.!?…。！？])\s+(?=[\"'¿¡«»A-ZÁÉÍÓÚÜÑ0-9])")
    for paragraph in paragraphs:
        sentences = [s.strip() for s in sentence_re.split(paragraph) if s.strip()]
        if not sentences:
            continue
        current = ""
        for sentence in sentences:
            if len(sentence) <= max_chars and len(current) + (1 if current else 0) + len(sentence) <= max_chars:
                current = f"{current} {sentence}".strip()
                continue
            if current:
                chunks.append(current)
                current = ""
            while len(sentence) > max_chars:
                cut = sentence.rfind(" ", 0, max_chars + 1)
                if cut < max_chars // 2:
                    cut = max_chars
                chunks.append(sentence[:cut].strip())
                sentence = sentence[cut:].strip()
            current = sentence
        if current:
            chunks.append(current)
    return chunks


def generate_request(model, request: dict) -> None:
    text = request["text"]
    output_file = Path(request["output_file"])
    output_file.parent.mkdir(parents=True, exist_ok=True)
    language = request.get("language", "es") or "es"
    reference = request.get("reference_audio") or None
    max_chars = int(request.get("max_chars", 900))
    chunks = split_book_text(text, max_chars)
    if not chunks:
        raise ValueError("Chatterbox recibió un capítulo vacío")

    logger.info("Generando %d fragmentos Chatterbox (%d caracteres)", len(chunks), len(text))
    merged = AudioSegment.empty()
    break_ms = max(0, int(request.get("break_duration", 1250)))
    with tempfile.TemporaryDirectory(prefix="chatterbox-") as temp_dir:
        for index, chunk in enumerate(chunks, start=1):
            logger.info("Fragmento %d/%d, %d caracteres", index, len(chunks), len(chunk))
            wav = model.generate(
                chunk,
                language_id=language,
                audio_prompt_path=reference,
                exaggeration=float(request.get("exaggeration", 0.5)),
                cfg_weight=float(request.get("cfg_weight", 0.5)),
                temperature=float(request.get("temperature", 0.8)),
                repetition_penalty=float(request.get("repetition_penalty", 1.2)),
                min_p=float(request.get("min_p", 0.05)),
                top_p=float(request.get("top_p", 1.0)),
            )
            chunk_file = Path(temp_dir) / f"{index:05d}.wav"
            torchaudio.save(str(chunk_file), wav.detach().cpu(), model.sr)
            merged += AudioSegment.from_wav(chunk_file)
            if index < len(chunks) and break_ms:
                merged += AudioSegment.silent(duration=break_ms, frame_rate=model.sr)

    output_format = output_file.suffix.lower().lstrip(".") or "mp3"
    export_kwargs = {"format": output_format}
    if output_format == "mp3":
        export_kwargs["bitrate"] = request.get("bitrate", "192k")
    merged.export(str(output_file), **export_kwargs)


def main() -> int:
    device = os.environ.get("CHATTERBOX_DEVICE", "cuda")
    model_name = os.environ.get("CHATTERBOX_MODEL", "v3")
    if device == "cuda" and not torch.cuda.is_available():
        logger.warning("CUDA no está disponible; usando CPU")
        device = "cpu"
    logger.info("Cargando Chatterbox Multilingual %s en %s", model_name.upper(), device)
    model = ChatterboxMultilingualTTS.from_pretrained(device=device, t3_model=model_name)
    logger.info("Modelo cargado; sample rate=%s", model.sr)
    sys.stdout.write(json.dumps({"ready": True, "device": device}) + "\n")
    sys.stdout.flush()

    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            request = json.loads(line)
            if request.get("command") == "stop":
                break
            generate_request(model, request)
            response = {"ok": True}
        except Exception as exc:  # protocol must always return one response
            logger.exception("Error generando audio")
            response = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
