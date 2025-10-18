from multiprocessing import Process
from typing import Optional
import os
import requests
from datetime import datetime
from pathlib import Path

import gradio as gr
from gradio_log import Log
from audiobook_generator.config.general_config import GeneralConfig
from audiobook_generator.tts_providers.azure_tts_provider import get_azure_supported_languages, \
    get_azure_supported_voices, get_azure_supported_output_formats
from audiobook_generator.tts_providers.edge_tts_provider import get_edge_tts_supported_voices, \
    get_edge_tts_supported_language, get_edge_tts_supported_output_formats
from audiobook_generator.tts_providers.openai_tts_provider import get_openai_supported_models, \
    get_openai_supported_voices, get_openai_instructions_example, get_openai_supported_output_formats
from audiobook_generator.tts_providers.piper_tts_provider import get_piper_supported_languages, \
    get_piper_supported_voices, get_piper_supported_qualities, get_piper_supported_speakers
from audiobook_generator.tts_providers.coqui_tts_provider import (
    get_coqui_supported_models, get_coqui_supported_output_formats, 
    get_coqui_supported_languages, get_coqui_models_by_language,
    get_coqui_supported_voices, get_coqui_supported_languages_for_model,
    get_coqui_model_info
)
from audiobook_generator.utils.log_handler import generate_unique_log_path
from main import main

selected_tts = "Edge"
running_process: Optional[Process] = None
webui_log_file = None

def on_tab_change(evt: gr.SelectData):
    print(f"{evt.value} tab selected")
    global selected_tts
    # Mapear los nombres de las pestañas a los nombres internos
    tab_mapping = {
        "OpenAI": "OpenAI",
        "Azure": "Azure", 
        "Edge": "Edge",
        "Piper": "Piper",
        "Coqui TTS": "Coqui",  # Mapear "Coqui TTS" a "Coqui"
        "Coqui": "Coqui",
        "Kokoro": "Kokoro"
    }
    selected_tts = tab_mapping.get(evt.value, evt.value)
    print(f"Selected TTS provider: {selected_tts}")

def get_azure_voices_by_language(language):
    voices_list = [voice for voice in get_azure_supported_voices() if voice.startswith(language)]
    return gr.Dropdown(voices_list, value=voices_list[0], label="Voice", interactive=True, info="Select the voice")

def get_edge_voices_by_language(language):
    voices_list = [voice for voice in get_edge_tts_supported_voices() if voice.startswith(language)]
    return gr.Dropdown(voices_list, value=voices_list[0], label="Voice", interactive=True, info="Select the voice")

def get_piper_supported_voices_gui(language):
    voices_list = get_piper_supported_voices(language)
    return gr.Dropdown(voices_list, value=voices_list[0], label="Voice", interactive=True, info="Select the voice")

def get_piper_supported_qualities_gui(language, voice):
    qualities_list = get_piper_supported_qualities(language, voice)
    return gr.Dropdown(qualities_list, value=qualities_list[0], label="Quality", interactive=True, info="Select the quality")

def get_piper_supported_speakers_gui(language, voice, quality):
    speakers_list = get_piper_supported_speakers(language, voice, quality)
    return gr.Dropdown(speakers_list, value=speakers_list[0], label="Speaker", interactive=True, info="Select the speaker")

def get_coqui_models_by_language_gui(language):
    models_list = get_coqui_models_by_language(language)
    if not models_list:
        models_list = get_coqui_supported_models()  # Fallback to all models
    return gr.Dropdown(models_list, value=models_list[0] if models_list else "", label="Model", interactive=True, allow_custom_value=True, info="Select a model or enter a custom model name")

def get_coqui_voices_by_model_gui(model_name):
    """Get voices available for a specific Coqui model."""
    if not model_name:
        return gr.Dropdown(["Default"], value="Default", label="Voice/Speaker", interactive=True)
    
    voices = get_coqui_supported_voices(model_name)
    if not voices:
        voices = ["Default"]
    
    return gr.Dropdown(voices, value=voices[0], label="Voice/Speaker", interactive=True, 
                      allow_custom_value=True)

def get_coqui_languages_by_model_gui(model_name):
    """Get languages available for a specific Coqui model."""
    if not model_name:
        return gr.Dropdown(["en"], value="en", label="Language", interactive=True)
    
    languages = get_coqui_supported_languages_for_model(model_name)
    if not languages:
        languages = ["en"]
    
    return gr.Dropdown(languages, value=languages[0], label="Language", interactive=True)

def update_coqui_model_options(model_name):
    """Update voice and language options when model changes."""
    if not model_name:
        return (
            gr.Dropdown(["Voz por Defecto"], value="Voz por Defecto", label="🎤 Voz/Locutor", interactive=True),
            gr.Dropdown(["es"], value="es", label="🗣️ Idioma Objetivo", interactive=True),
            gr.File(visible=False),  # speaker_wav file
            gr.Markdown("**📋 Información del Modelo:** Selecciona un modelo primero")
        )
    
    # Get model information
    model_info = get_coqui_model_info(model_name)
    voices = get_coqui_supported_voices(model_name)
    languages = get_coqui_supported_languages_for_model(model_name)
    
    # Ensure Spanish is first in languages if available
    if "es" in languages and languages[0] != "es":
        languages.remove("es")
        languages.insert(0, "es")
    
    # Update voice dropdown
    voice_dropdown = gr.Dropdown(
        voices, 
        value=voices[0] if voices else "Voz por Defecto", 
        label="🎤 Voz/Locutor", 
        interactive=True,
        allow_custom_value=True
    )
    
    # Update language dropdown
    language_dropdown = gr.Dropdown(
        languages,
        value="es" if "es" in languages else (languages[0] if languages else "es"),
        label="🗣️ Idioma Objetivo",
        interactive=model_info.get("is_multi_lingual", False)
    )
    
    # Show/hide voice cloning file upload based on model capabilities
    show_speaker_wav = model_info.get("supports_voice_cloning", False)
    speaker_wav_file = gr.File(
        label="🎙️ Clonación de Voz - Sube audio de referencia",
        file_types=[".wav", ".mp3", ".flac"],
        visible=show_speaker_wav
    )
    
    # Create detailed model info text in Spanish
    info_parts = [f"**📋 {model_name}**"]
    
    if "xtts" in model_name.lower():
        info_parts.append("🌟 **MODELO PREMIUM** - Máxima calidad")
        info_parts.append(f"🎤 {len(voices)} voces predefinidas")
        info_parts.append(f"🌍 {len(languages)} idiomas soportados")
        info_parts.append("✅ Clonación de voz")
        info_parts.append("⚡ Requiere GPU para mejor rendimiento")
    elif "/es/" in model_name:
        info_parts.append("🇪🇸 **MODELO ESPECÍFICO DE ESPAÑOL**")
        info_parts.append("✅ Optimizado para español")
        info_parts.append("⚡ Funciona bien en CPU")
    else:
        if model_info.get("is_multi_speaker", False):
            info_parts.append(f"🎤 Multi-locutor ({len(voices)} voces)")
        if model_info.get("is_multi_lingual", False):
            info_parts.append(f"🌍 Multi-idioma ({len(languages)} idiomas)")
        if model_info.get("supports_voice_cloning", False):
            info_parts.append("✅ Clonación de voz")
    
    model_info_text = gr.Markdown("\n\n".join(info_parts))
    
    return voice_dropdown, language_dropdown, speaker_wav_file, model_info_text

# Funciones para los presets
def apply_audiolibro_preset():
    """Preset para audiolibros narrativos."""
    return 0.95, 0.6, 0.8  # length_scale, noise_scale, noise_w_scale

def apply_educativo_preset():
    """Preset para contenido educativo."""
    return 0.85, 0.4, 0.7  # Más rápido, menos expresivo, más claro

def apply_dramatico_preset():
    """Preset para lectura dramática."""
    return 1.0, 0.8, 0.9  # Velocidad normal, muy expresivo, muy natural

def apply_noticias_preset():
    """Preset para estilo noticiero."""
    return 0.9, 0.3, 0.6  # Ritmo de noticias, poco expresivo, timing preciso

# Funciones para presets de calidad de audio
def apply_mobile_quality_preset():
    """Preset para calidad móvil/podcast - Archivos pequeños"""
    return "22050", "128k", 1, "16", 4, True  # sample_rate, bitrate, channels, bit_depth, mp3_quality, limiter

def apply_desktop_quality_preset():
    """Preset para calidad escritorio - Balance calidad/tamaño"""
    return "44100", "192k", 1, "24", 2, True

def apply_high_quality_preset():
    """Preset para alta calidad - Recomendado"""
    return "44100", "320k", 1, "24", 0, True

def apply_max_quality_preset():
    """Preset para máxima calidad - Archivos grandes"""
    return "48000", "320k", 2, "24", 0, True

# Funciones para presets de calidad de audio OpenAI/Kokoro
def apply_openai_mobile_quality_preset():
    """Preset para calidad móvil/podcast OpenAI - Archivos pequeños"""
    return 22050, "128k", 1, 16, 4, True, True  # sample_rate, bitrate, channels, bit_depth, mp3_quality, limiter, normalize

def apply_openai_desktop_quality_preset():
    """Preset para calidad escritorio OpenAI - Balance calidad/tamaño"""
    return 44100, "192k", 1, 24, 2, True, True

def apply_openai_high_quality_preset():
    """Preset para alta calidad OpenAI - Recomendado"""
    return 44100, "320k", 1, 24, 0, True, True

def apply_openai_max_quality_preset():
    """Preset para máxima calidad OpenAI - Archivos grandes"""
    return 48000, "320k", 2, 24, 0, True, True

# Funciones para presets de calidad de audio Piper
def apply_piper_mobile_quality_preset():
    """Preset para calidad móvil/podcast Piper - Archivos pequeños"""
    return 22050, "128k", 1, 16, 4, True, True  # sample_rate, bitrate, channels, bit_depth, mp3_quality, limiter, normalize

def apply_piper_desktop_quality_preset():
    """Preset para calidad escritorio Piper - Balance calidad/tamaño"""
    return 44100, "192k", 1, 24, 2, True, True

def apply_piper_high_quality_preset():
    """Preset para alta calidad Piper - Recomendado"""
    return 44100, "320k", 1, 24, 0, True, True

def apply_piper_max_quality_preset():
    """Preset para máxima calidad Piper - Archivos grandes"""
    return 48000, "320k", 2, 24, 0, True, True

# Funciones para presets de calidad de audio Kokoro
def apply_kokoro_mobile_quality_preset():
    """Preset para calidad móvil/podcast Kokoro - Archivos pequeños"""
    return 22050, "128k", 1, 16, 4, True, True  # sample_rate, bitrate, channels, bit_depth, mp3_quality, limiter, normalize

def apply_kokoro_desktop_quality_preset():
    """Preset para calidad escritorio Kokoro - Balance calidad/tamaño"""
    return 44100, "192k", 1, 24, 2, True, True

def apply_kokoro_high_quality_preset():
    """Preset para alta calidad Kokoro - Recomendado"""
    return 44100, "320k", 1, 24, 0, True, True

def apply_kokoro_max_quality_preset():
    """Preset para máxima calidad Kokoro - Archivos grandes"""
    return 48000, "320k", 2, 24, 0, True, True


def fetch_kokoro_voices(kokoro_base_url: str = "http://localhost:8880"):
    """Fetch available voices from Kokoro server using the correct endpoint."""
    try:
        # Use the correct Kokoro voices endpoint
        url = f"{kokoro_base_url.rstrip('/')}/v1/audio/voices"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return []
        
        data = resp.json()
        
        # Extract voices from the response
        if isinstance(data, dict) and 'voices' in data:
            voices = data['voices']
        elif isinstance(data, list):
            voices = data
        else:
            return []
            
        # Ensure we return a list of strings
        voice_list = []
        for voice in voices:
            if isinstance(voice, dict):
                voice_list.append(voice.get('id', voice.get('name', str(voice))))
            elif isinstance(voice, str):
                voice_list.append(voice)
        
        return voice_list
        
    except Exception as e:
        print(f"Error fetching Kokoro voices: {e}")
        # Return default voices as fallback
        return [
            "af_bella", "af_sky", "af_heart", "af_nicole", "af_sarah", "af_emma",
            "bf_emma", "bf_sarah", "bf_nicole", "bf_sky",
            "am_adam", "am_daniel", "bm_lewis", "bm_george"
        ]

def get_kokoro_languages():
    """Get supported Kokoro languages with their full names."""
    return [
        ("", "Auto-detect"),
        ("a", "English (US)"), 
        ("b", "British English"),
        ("e", "Spanish"),
        ("f", "French"), 
        ("h", "Hindi"),
        ("i", "Italian"),
        ("p", "Portuguese"),
        ("j", "Japanese"),
        ("z", "Chinese")
    ]

def filter_voices_by_language(voices, language_code):
    """Filter voices based on language preference using Kokoro voice naming convention.
    
    Kokoro voices follow the pattern: [language][gender]_[name]
    - First letter: language (a=English, b=British, e=Spanish, f=French, etc.)
    - Second letter: gender (f=female, m=male)
    """
    if not language_code or language_code == "":
        return voices  # Return all voices for auto-detect
    
    # Filter voices that start with the language code
    filtered = []
    for voice in voices:
        voice_str = str(voice)
        if voice_str.startswith(language_code):
            filtered.append(voice)
    
    # If no voices match the language, return all voices as fallback
    return filtered if filtered else voices


def get_kokoro_voices_gui(base_url: str = None, language_code: str = ""):
    base = base_url or os.environ.get('OPENAI_BASE_URL', 'http://localhost:8880')
    all_voices = fetch_kokoro_voices(base.rstrip('/'))
    filtered_voices = filter_voices_by_language(all_voices, language_code)
    
    if not filtered_voices:
        # Default fallback voices (American English)
        filtered_voices = [v for v in all_voices if str(v).startswith('a')] or all_voices[:4]
    
    return gr.Dropdown(
        choices=filtered_voices, 
        value=filtered_voices[0] if filtered_voices else None, 
        label="Kokoro Voice", 
        interactive=True, 
        allow_custom_value=True, 
        info=f"Select a Kokoro voice ({len(filtered_voices)} available)"
    )

def update_kokoro_voices_by_language(language_code, base_url):
    """Update voice dropdown when language changes."""
    all_voices = fetch_kokoro_voices(base_url or 'http://localhost:8880')
    filtered_voices = filter_voices_by_language(all_voices, language_code)
    
    if not filtered_voices:
        # Default fallback voices (American English)
        filtered_voices = [v for v in all_voices if str(v).startswith('a')] or all_voices[:4]
    
    # Get language name for display
    lang_dict = dict(get_kokoro_languages())
    lang_name = lang_dict.get(language_code, 'selected language')
    
    return gr.Dropdown(
        choices=filtered_voices,
        value=filtered_voices[0] if filtered_voices else None,
        label="Kokoro Voice",
        interactive=True,
        allow_custom_value=True,
        info=f"Select a Kokoro voice ({len(filtered_voices)} available for {lang_name})"
    )


def process_ui_form(input_file, output_dir, worker_count, log_level, output_text, preview,
                    search_and_replace_file, title_mode, new_line_mode, chapter_start, chapter_end, remove_endnotes, remove_reference_numbers,
                    model, voices, speed, openai_output_format, instructions,
                    # OpenAI audio quality inputs
                    openai_sample_rate, openai_audio_bitrate, openai_audio_channels, openai_wav_bit_depth, openai_mp3_quality, openai_enable_limiter, openai_normalize_volume,
                    azure_language, azure_voice, azure_output_format, azure_break_duration,
                    edge_language, edge_voice, edge_output_format, proxy, edge_voice_rate, edge_volume, edge_pitch, edge_break_duration,
                    # Coqui inputs
                    coqui_model_input, coqui_speaker_input, coqui_language_input, coqui_speaker_wav_input, coqui_path_input, coqui_output_format,
                    coqui_length_scale, coqui_noise_scale, coqui_noise_w_scale, coqui_device,
                    # Coqui audio quality inputs
                    coqui_sample_rate, coqui_audio_bitrate, coqui_audio_channels, coqui_wav_bit_depth, coqui_mp3_quality, coqui_enable_limiter,
                    # Kokoro inputs
                    kokoro_base_url, kokoro_language, kokoro_model, kokoro_voice, kokoro_output_format, kokoro_speed,
                    # Kokoro audio quality inputs
                    kokoro_sample_rate_ui, kokoro_audio_bitrate_ui, kokoro_audio_channels_ui, kokoro_wav_bit_depth_ui, kokoro_mp3_quality_ui, kokoro_enable_limiter_ui, kokoro_normalize_volume_ui,
                    piper_executable_path, piper_docker_image, piper_language, piper_voice, piper_quality, piper_speaker,
                    piper_noise_scale, piper_noise_w_scale, piper_length_scale, piper_sentence_silence, piper_device,
                    # Piper audio quality inputs
                    piper_sample_rate, piper_audio_bitrate, piper_audio_channels, piper_wav_bit_depth, piper_mp3_quality, piper_enable_limiter, piper_normalize_volume):

    config = GeneralConfig(None)
    config.input_file = input_file.name if hasattr(input_file, 'name') else input_file
    config.output_folder = output_dir
    config.preview = preview
    config.output_text = output_text
    config.log = log_level
    config.worker_count = worker_count
    config.no_prompt = True

    config.title_mode = title_mode
    config.newline_mode = new_line_mode
    config.chapter_start = chapter_start
    config.chapter_end = chapter_end
    config.remove_endnotes = remove_endnotes
    config.remove_reference_numbers = remove_reference_numbers
    config.search_and_replace_file = search_and_replace_file.name if hasattr(search_and_replace_file, 'name') else search_and_replace_file

    global selected_tts
    if selected_tts == "OpenAI":
        config.tts = "openai"
        config.output_format = openai_output_format
        config.voice_name = voices
        config.model_name = model
        config.instructions = instructions
        config.speed = speed
        # OpenAI audio quality parameters (Note: no prefix because it's base OpenAI)
        config.sample_rate = int(openai_sample_rate)
        config.audio_bitrate = openai_audio_bitrate
        config.audio_channels = openai_audio_channels
        config.wav_bit_depth = int(openai_wav_bit_depth)
        config.mp3_quality = openai_mp3_quality
        config.enable_limiter = openai_enable_limiter
        config.normalize_volume = openai_normalize_volume
    elif selected_tts == "Kokoro":
        # Kokoro is OpenAI-compatible; route through OpenAI provider but use custom base URL
        config.tts = "openai"
        # Set environment variables for Kokoro
        if kokoro_base_url:
            os.environ['OPENAI_BASE_URL'] = kokoro_base_url.rstrip('/') + '/v1'
        # Kokoro needs a fake API key
        os.environ['OPENAI_API_KEY'] = 'fake-key'
        
        config.output_format = kokoro_output_format
        config.voice_name = kokoro_voice
        config.model_name = kokoro_model
        config.speed = kokoro_speed
        # Kokoro audio quality parameters
        config.kokoro_sample_rate = int(kokoro_sample_rate_ui)
        config.kokoro_audio_bitrate = kokoro_audio_bitrate_ui
        config.kokoro_audio_channels = kokoro_audio_channels_ui
        config.kokoro_wav_bit_depth = int(kokoro_wav_bit_depth_ui)
        config.kokoro_mp3_quality = kokoro_mp3_quality_ui
        config.kokoro_enable_limiter = kokoro_enable_limiter_ui
        config.kokoro_normalize_volume = kokoro_normalize_volume_ui
        
        # Convert language name back to code for Kokoro
        language_code = ""
        for code, name in get_kokoro_languages():
            if name == kokoro_language:
                language_code = code
                break
        if language_code:
            config.language = language_code
    elif selected_tts == "Azure":
        config.tts = "azure"
        config.language = azure_language
        config.voice_name = azure_voice
        config.output_format = azure_output_format
        config.break_duration = azure_break_duration
    elif selected_tts == "Edge":
        config.tts = "edge"
        config.language = edge_language
        config.voice_name = edge_voice
        config.output_format = edge_output_format
        config.proxy = proxy
        config.voice_rate = f"{edge_voice_rate:+}%"
        config.voice_volume = f"{edge_volume:+}%"
        config.voice_pitch = f"{edge_pitch:+}Hz"
        config.break_duration = edge_break_duration
    elif selected_tts == "Piper":
        config.tts = "piper"
        config.piper_path = piper_executable_path
        config.piper_docker_image = piper_docker_image
        config.model_name = f"{piper_language}-{piper_voice}-{piper_quality}"
        config.piper_speaker = piper_speaker
        config.piper_noise_scale = piper_noise_scale
        config.piper_noise_w_scale = piper_noise_w_scale
        config.piper_length_scale = piper_length_scale
        config.piper_sentence_silence = piper_sentence_silence
        config.piper_device = piper_device
        # Piper audio quality parameters
        config.piper_sample_rate = int(piper_sample_rate)
        config.piper_audio_bitrate = piper_audio_bitrate
        config.piper_audio_channels = piper_audio_channels
        config.piper_wav_bit_depth = int(piper_wav_bit_depth)
        config.piper_mp3_quality = piper_mp3_quality
        config.piper_enable_limiter = piper_enable_limiter
        config.piper_normalize_volume = piper_normalize_volume
    elif selected_tts == "Coqui":
        config.tts = "coqui"
        # coqui_model is passed from the Coqui UI dropdown/textbox
        config.coqui_model = coqui_model_input if coqui_model_input else None
        # coqui speaker/voice
        config.coqui_speaker = coqui_speaker_input if coqui_speaker_input else None
        # coqui language for multilingual models
        config.coqui_language = coqui_language_input if coqui_language_input else None
        # coqui speaker wav file for voice cloning
        config.coqui_speaker_wav = coqui_speaker_wav_input.name if hasattr(coqui_speaker_wav_input, 'name') else (coqui_speaker_wav_input if coqui_speaker_wav_input else None)
        # coqui_path is provided explicitly by the Coqui UI
        config.coqui_path = coqui_path_input if coqui_path_input else None
        # coqui output format
        config.output_format = coqui_output_format if coqui_output_format else config.output_format
        # coqui parameters
        config.coqui_length_scale = coqui_length_scale
        config.coqui_noise_scale = coqui_noise_scale
        config.coqui_noise_w_scale = coqui_noise_w_scale
        config.coqui_device = coqui_device
        # coqui audio quality parameters
        config.coqui_sample_rate = int(coqui_sample_rate)
        config.coqui_audio_bitrate = coqui_audio_bitrate
        config.coqui_audio_channels = coqui_audio_channels
        config.coqui_wav_bit_depth = int(coqui_wav_bit_depth)
        config.coqui_mp3_quality = coqui_mp3_quality
        config.coqui_enable_limiter = coqui_enable_limiter
    else:
        raise ValueError("Unsupported TTS provider selected")

    launch_audiobook_generator(config)


def launch_audiobook_generator(config):
    global running_process
    if running_process and running_process.is_alive():
        print("Audiobook generator already running")
        return

    running_process = Process(target=main, args=(config, str(webui_log_file.absolute())))
    running_process.start()


def terminate_audiobook_generator():
    global running_process
    if running_process and running_process.is_alive():
        running_process.terminate()
        running_process = None
        print("Audiobook generator terminated manually")

def host_ui(config):
    default_output_dir = os.path.join("audiobook_output", datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
    print(f"Default audiobook output directory: {default_output_dir}")
    with gr.Blocks(analytics_enabled=False, title="Epub to Audiobook Converter") as ui:
        with gr.Row(equal_height=True):
            with gr.Column():
                input_file = gr.File(label="Select the book file to process", file_types=[".epub"], 
                                    file_count="single", interactive=True)

            with gr.Column():
                output_dir = gr.Textbox(label="Set Output Directory", value=default_output_dir, interactive=True, info="Default one should be fine.")
                log_level = gr.Dropdown(["INFO", "DEBUG", "WARNING", "ERROR", "CRITICAL"], label="Log Level", value="INFO", interactive=True)

            with gr.Column():
                worker_count = gr.Slider(minimum=1, maximum=8, step=1, label="Worker Count", value=1,
                                     info="Number of workers to use for processing. More workers may speed up the process but will use more resources or cause instability. ***Only change if you know how to debug potential issues.***")

            with gr.Column():
                output_text = gr.Checkbox(label="Enable Output Text", value=False,
                                      info="Export a plain text file for each chapter.")
                preview = gr.Checkbox(label="Enable Preview Mode", value=False,
                                  info="It will not convert the to audio, only prepare chapters and cost. Recommended to toggle on when testing book parsing ***without*** audio generation.")

        gr.Markdown("---")
        with gr.Row(equal_height=True):
            with gr.Column():
                search_and_replace_file = gr.File(label="Select search and replace file (optional)", file_types=[".txt"], 
                                                 file_count="single", interactive=True)

            title_mode = gr.Dropdown(["auto", "tag_text", "first_few"], label="Title Mode", value="auto",
                                     interactive=True, info="Choose the parse mode for chapter title.")
            new_line_mode = gr.Dropdown(["single", "double", "none"], label="New Line Mode", value="double",
                                 interactive=True, info="Choose the mode of detecting new paragraphs")
            chapter_start = gr.Slider(minimum=1, maximum=100, step=1, label="Chapter Start", value=1,
                                      interactive=True, info="Select chapter start index (default: 1)")
            chapter_end = gr.Slider(minimum=-1, maximum=100, step=1, label="Chapter End", value=-1,
                                    interactive=True, info="Chapter end index (default: -1, means last chapter)")
            with gr.Column():
                remove_endnotes = gr.Checkbox(label="Remove Endnotes", value=False, info="Remove endnotes from text")

                remove_reference_numbers = gr.Checkbox(label="Remove Reference Numbers", value=False,
                                                       info="Remove reference numbers from text")


        gr.Markdown("---")
        with gr.Tabs(selected="edge_tab_id"):
            with gr.Tab("OpenAI", id="openai_tab_id") as open_ai_tab:
                gr.Markdown("It is expected that user configured: `OPENAI_API_KEY` in the environment variables. Optionally `OPENAI_API_BASE` can be set to overwrite OpenAI API endpoint.")
                with gr.Row(equal_height=True):
                    model = gr.Dropdown(get_openai_supported_models(), label="Model", interactive=True, allow_custom_value=True)
                    voices = gr.Dropdown(get_openai_supported_voices(), label="Voice", interactive=True, allow_custom_value=True)
                    speed = gr.Slider(minimum=0.25, maximum=4.0, step=0.1, label="Speed", value=1.0,
                                      info="Speed of the speech, 1.0 is normal speed")
                    openai_output_format = gr.Dropdown(get_openai_supported_output_formats(), label="Output Format", interactive=True)
                with gr.Row(equal_height=True):
                    instructions = gr.TextArea(label="Voice Instructions", interactive=True, lines=3,
                                               value=get_openai_instructions_example())
                
                # === CONTROLES DE CALIDAD DE AUDIO OPENAI/KOKORO ===
                with gr.Accordion("🎵 Control de Calidad de Audio", open=False):
                    gr.Markdown("### Presets de Calidad Rápida")
                    with gr.Row(equal_height=True):
                        openai_mobile_quality = gr.Button("📱 Móvil (Rápido)", variant="secondary")
                        openai_desktop_quality = gr.Button("🖥️ Escritorio", variant="secondary") 
                        openai_high_quality = gr.Button("🎧 Alta Calidad", variant="primary")
                        openai_max_quality = gr.Button("💎 Máxima Calidad", variant="primary")
                    
                    gr.Markdown("### Configuración Detallada")
                    with gr.Row(equal_height=True):
                        openai_sample_rate = gr.Dropdown(
                            choices=[16000, 22050, 44100, 48000], 
                            value=22050, 
                            label="Frecuencia de Muestreo (Hz)", 
                            info="Mayor = mejor calidad, archivos más grandes"
                        )
                        openai_audio_bitrate = gr.Dropdown(
                            choices=["128k", "192k", "256k", "320k"], 
                            value="192k", 
                            label="Bitrate de Audio", 
                            info="Para MP3 y formatos con pérdida"
                        )
                        openai_audio_channels = gr.Dropdown(
                            choices=[1, 2], 
                            value=1, 
                            label="Canales", 
                            info="1=Mono, 2=Estéreo"
                        )
                    
                    with gr.Row(equal_height=True):
                        openai_wav_bit_depth = gr.Dropdown(
                            choices=[16, 24, 32], 
                            value=16, 
                            label="Profundidad de Bits (WAV)", 
                            info="16=Estándar, 24/32=Audio profesional"
                        )
                        openai_mp3_quality = gr.Slider(
                            minimum=0, maximum=9, step=1, value=2, 
                            label="Calidad MP3 (0=mejor)", 
                            info="Solo para formato MP3"
                        )
                        openai_enable_limiter = gr.Checkbox(
                            value=True, 
                            label="Limitador de Audio", 
                            info="Evita distorsión y clipping"
                        )
                        openai_normalize_volume = gr.Checkbox(
                            value=True, 
                            label="Normalización de Volumen", 
                            info="Volumen consistente"
                        )
                
                open_ai_tab.select(on_tab_change, inputs=None, outputs=None)
            with gr.Tab("Azure", id="azure_tab_id") as azure_tab:
                gr.Markdown("It is expected that user configured: `MS_TTS_KEY` and `MS_TTS_REGION` in the environment variables.")
                with gr.Row(equal_height=True):
                    azure_language = gr.Dropdown(get_azure_supported_languages(), value="en-US", label="Language",
                                               interactive=True, info="Select source language")
                    azure_voice = get_azure_voices_by_language(azure_language.value)
                    azure_output_format = gr.Dropdown(get_azure_supported_output_formats(), label="Output Format", interactive=True,
                                                value="audio-24khz-48kbitrate-mono-mp3", info="Select output format")
                    azure_break_duration = gr.Slider(minimum=0, maximum=5000, step=1, label="Break Duration", value=1250,
                                               info="Break duration in milliseconds. Valid values range from 0 to 5000, default: 1250ms")
                    azure_language.change(
                        fn=get_azure_voices_by_language,
                        inputs=azure_language,
                        outputs=azure_voice,
                    )
                azure_tab.select(on_tab_change, inputs=None, outputs=None)

            with gr.Tab("Edge", id="edge_tab_id") as edge_tab:
                with gr.Row(equal_height=True):
                    edge_language = gr.Dropdown(get_edge_tts_supported_language(), value="en-US", label="Language",
                                           interactive=True, info="Select source language")
                    edge_voice = get_edge_voices_by_language(edge_language.value)
                    edge_output_format = gr.Dropdown(get_edge_tts_supported_output_formats(), label="Output Format",
                                                      interactive=True, info="Select output format")
                    proxy = gr.Textbox(label="Proxy", value="", interactive=True, info="Optional proxy server for the TTS provider")
                    edge_voice_rate = gr.Slider(minimum=-50, maximum=100, step=1, label="Voice Rate", value=0,
                                           info="Speaking rate (speed) of the text.")
                    edge_volume = gr.Slider(minimum=-100, maximum=100, step=1, label="Voice Volume", value=0,
                                            info="Volume level of the speaking voice.")
                    edge_pitch = gr.Slider(minimum=-100, maximum=100, step=1, label="Voice Pitch", value=0,
                                           info="Baseline pitch tone for the text.")
                    edge_break_duration = gr.Slider(minimum=0, maximum=5000, step=1, label="Break Duration", value=1250,
                                               info="Break duration in milliseconds. Valid values range from 0 to 5000, default: 1250ms")

                    edge_language.change(
                        fn=get_edge_voices_by_language,
                        inputs=edge_language,
                        outputs=edge_voice,
                    )
                edge_tab.select(on_tab_change, inputs=None, outputs=None)

            with gr.Tab("Piper", id="piper_tab_id") as piper_tab:
                piper_tab.select(on_tab_change, inputs=None, outputs=None)
                with gr.Row(equal_height=True):
                    piper_device = gr.Dropdown(["cpu", "cuda"], label="Device", value="cpu", interactive=True, info="Select device for Piper (cpu/gpu)")
                    with gr.Column():
                        piper_deployment = gr.Dropdown(["Docker", "Local"], label="Select Piper Deployment", 
                                                      value="Local", interactive=True)

                        local_group = gr.Group(visible=True)
                        with local_group:
                            # Set default path to local piper executable
                            try:
                                from audiobook_generator.utils.resource_path import resource_path
                                default_piper_path = str(resource_path("piper_tts/piper.exe"))
                            except Exception:
                                default_piper_path = str(Path(__file__).parent.parent.parent / "piper_tts" / "piper.exe")
                            piper_executable_path = gr.Textbox(label="Piper executable path", 
                                                             value=default_piper_path, 
                                                             interactive=True)
                            piper_file_upload = gr.File(label="Upload Piper executable", 
                                                      file_count="single", interactive=True)
                            piper_file_upload.change(
                                fn=lambda x: x.name if x else "",
                                inputs=piper_file_upload,
                                outputs=piper_executable_path
                            )

                        docker_group = gr.Row(visible=False, equal_height=True)
                        with docker_group:
                            piper_docker_image = gr.Textbox(label="Piper Docker Image", value="lscr.io/linuxserver/piper:latest", interactive=True)

                    piper_deployment.change(
                        fn=lambda x: (gr.update(visible=x == "Local"), gr.update(visible=x == "Docker")),
                        inputs=piper_deployment,
                        outputs=[local_group, docker_group]
                    )

                    with gr.Column():
                        with gr.Row(equal_height=True):
                            piper_language = gr.Dropdown(get_piper_supported_languages(), label="Language", value="en_US", interactive=True, info="Select language")
                            piper_voice = gr.Dropdown(get_piper_supported_voices(piper_language.value), label="Voice", interactive=True, info="Select voice")
                        with gr.Row(equal_height=True):
                            piper_quality = gr.Dropdown(get_piper_supported_qualities(piper_language.value, piper_voice.value), label="Quality", interactive=True, info="Select quality")
                            piper_speaker = gr.Dropdown(get_piper_supported_speakers(piper_language.value, piper_voice.value, piper_quality.value), label="Speaker", interactive=True, info="Select speaker if available")

                    piper_language.change(
                        fn=get_piper_supported_voices_gui,
                        inputs=piper_language,
                        outputs=piper_voice,
                    )

                    piper_voice.change(
                        fn=get_piper_supported_qualities_gui,
                        inputs=[piper_language, piper_voice],
                        outputs=piper_quality,
                    )

                    piper_quality.change(
                        fn=get_piper_supported_speakers_gui,
                        inputs=[piper_language, piper_voice, piper_quality],
                        outputs=piper_speaker,
                    )

                    with gr.Column():
                        with gr.Row(equal_height=True):
                            piper_noise_scale = gr.Slider(minimum=0.0, maximum=2.0, step=0.01, label="Audio Noise Scale", value=0.667)
                            piper_noise_w_scale = gr.Slider(minimum=0.0, maximum=2.0, step=0.1, label="Width Noise Scale", value=0.8)
                        with gr.Row(equal_height=True):
                            piper_length_scale = gr.Slider(minimum=0.0, maximum=5.0, step=0.1, label="Audio Length Scale", value=1.0)
                            piper_sentence_silence = gr.Slider(minimum=0.0, maximum=2.0, step=0.1, label="Sentence Silence", value=0.2)

                # === CONTROLES DE CALIDAD DE AUDIO PIPER ===
                with gr.Accordion("🎵 Control de Calidad de Audio", open=False):
                    gr.Markdown("### Presets de Calidad Rápida")
                    with gr.Row(equal_height=True):
                        piper_mobile_quality = gr.Button("📱 Móvil (Rápido)", variant="secondary")
                        piper_desktop_quality = gr.Button("🖥️ Escritorio", variant="secondary") 
                        piper_high_quality = gr.Button("🎧 Alta Calidad", variant="primary")
                        piper_max_quality = gr.Button("💎 Máxima Calidad", variant="primary")
                    
                    gr.Markdown("### Configuración Detallada")
                    with gr.Row(equal_height=True):
                        piper_sample_rate = gr.Dropdown(
                            choices=[16000, 22050, 44100, 48000], 
                            value=22050, 
                            label="Frecuencia de Muestreo (Hz)", 
                            info="Mayor = mejor calidad, archivos más grandes"
                        )
                        piper_audio_bitrate = gr.Dropdown(
                            choices=["128k", "192k", "256k", "320k"], 
                            value="192k", 
                            label="Bitrate de Audio", 
                            info="Para MP3 y formatos con pérdida"
                        )
                        piper_audio_channels = gr.Dropdown(
                            choices=[1, 2], 
                            value=1, 
                            label="Canales", 
                            info="1=Mono, 2=Estéreo"
                        )
                    
                    with gr.Row(equal_height=True):
                        piper_wav_bit_depth = gr.Dropdown(
                            choices=[16, 24, 32], 
                            value=16, 
                            label="Profundidad de Bits (WAV)", 
                            info="16=Estándar, 24/32=Audio profesional"
                        )
                        piper_mp3_quality = gr.Slider(
                            minimum=0, maximum=9, step=1, value=2, 
                            label="Calidad MP3 (0=mejor)", 
                            info="Solo para formato MP3"
                        )
                        piper_enable_limiter = gr.Checkbox(
                            value=True, 
                            label="Limitador de Audio", 
                            info="Evita distorsión y clipping"
                        )
                        piper_normalize_volume = gr.Checkbox(
                            value=True, 
                            label="Normalización de Volumen", 
                            info="Volumen consistente"
                        )

            with gr.Tab("Coqui TTS", id="coqui_tab_id") as coqui_tab:
                coqui_tab.select(on_tab_change, inputs=None, outputs=None)
                gr.Markdown("**🐸 Coqui TTS** - Síntesis de voz neuronal avanzada con soporte completo para español. Incluye XTTS-v2 para clonación de voz y modelos específicos de español.")
                
                # Selección de modelo y configuración básica
                with gr.Row(equal_height=True):
                    coqui_device = gr.Dropdown(
                        ["cpu", "cuda"], 
                        label="🔧 Dispositivo (GPU recomendada para XTTS)", 
                        value="cuda", 
                        interactive=True
                    )
                    coqui_language_filter = gr.Dropdown(
                        get_coqui_supported_languages(),
                        value="es",  # Default to Spanish
                        label="🌍 Filtro de Idioma",
                        interactive=True
                    )
                    coqui_output_format = gr.Dropdown(
                        get_coqui_supported_output_formats(),
                        label="🎵 Formato de Salida",
                        value="mp3",
                        interactive=True
                    )
                
                # Selección de modelo TTS
                with gr.Row():
                    coqui_model = gr.Dropdown(
                        get_coqui_models_by_language("es"),  # Default to Spanish models
                        label="🎯 Modelo TTS (CSS10 estable, XTTS-v2 avanzado con clonación)",
                        value="tts_models/multilingual/multi-dataset/xtts_v2",  # XTTS-v2 como default
                        interactive=True,
                        allow_custom_value=True
                    )
                
                # Información del modelo seleccionado
                coqui_model_info = gr.Markdown("**📋 Información del Modelo:** Selecciona un modelo para ver detalles")
                
                # Selección de voz y idioma (se actualiza dinámicamente según el modelo)
                with gr.Row(equal_height=True):
                    coqui_speaker = gr.Dropdown(
                        get_coqui_supported_voices("tts_models/multilingual/multi-dataset/xtts_v2"),
                        label="🎤 Voz/Locutor",
                        value="Ana Florence",  # Default Spanish-friendly voice
                        interactive=True,
                        allow_custom_value=True
                    )
                    coqui_language = gr.Dropdown(
                        ["es", "en", "fr", "de", "it", "pt"],
                        label="🗣️ Idioma Objetivo",
                        value="es",  # Default to Spanish
                        interactive=True
                    )
                
                # Subida de archivo para clonación de voz
                with gr.Row():
                    coqui_speaker_wav = gr.File(
                        label="🎙️ Clonación de Voz - Sube audio de referencia (WAV/MP3/FLAC de 5-30 segundos)",
                        file_types=[".wav", ".mp3", ".flac"],
                        visible=True
                    )
                
                # Ejemplo de texto para pruebas
                with gr.Row():
                    gr.Markdown("**💡 Ejemplo de uso:** Para clonación de voz, selecciona '🎤 Clonación de Voz' como locutor y sube un archivo de audio de referencia.")
                
                # Configuraciones de calidad específicas para español
                with gr.Accordion("⚙️ Configuración de Calidad para Español", open=False):
                    with gr.Row():
                        gr.Markdown("**Configuraciones optimizadas para audiolibros en español:**")
                    
                    with gr.Row(equal_height=True):
                        coqui_length_scale = gr.Slider(
                            minimum=0.5, maximum=2.0, step=0.05, 
                            label="⏱️ Velocidad de Lectura (0.8=rápido, 1.0=normal, 1.2=lento)", 
                            value=0.95
                        )
                        coqui_noise_scale = gr.Slider(
                            minimum=0.1, maximum=1.0, step=0.01, 
                            label="🎭 Expresividad (0.3=neutral, 0.7=expresivo)", 
                            value=0.6
                        )
                        coqui_noise_w_scale = gr.Slider(
                            minimum=0.1, maximum=1.0, step=0.05, 
                            label="🎵 Naturalidad del Timing (0.5=robótico, 0.8=natural)", 
                            value=0.8
                        )
                
                # === CONFIGURACIÓN DE CALIDAD DE AUDIO ===
                with gr.Accordion("🎚️ Configuración de Calidad de Audio", open=False):
                    gr.Markdown("**🎵 Controla la calidad del audio generado - Mayor calidad = archivos más grandes**")
                    
                    # Presets de calidad
                    with gr.Row(equal_height=True):
                        preset_quality_mobile = gr.Button("📱 Móvil/Podcast", variant="secondary", size="sm")
                        preset_quality_desktop = gr.Button("🖥️ Escritorio", variant="secondary", size="sm")
                        preset_quality_high = gr.Button("🎧 Alta Calidad", variant="primary", size="sm")
                        preset_quality_max = gr.Button("💿 Máxima Calidad", variant="secondary", size="sm")
                    
                    # Configuraciones detalladas
                    with gr.Row(equal_height=True):
                        coqui_sample_rate = gr.Dropdown(
                            choices=["22050", "44100", "48000"],
                            value="44100",
                            label="📊 Frecuencia de Muestreo (Hz)",
                            info="Mayor = mejor calidad, archivos más grandes"
                        )
                        
                        coqui_audio_bitrate = gr.Dropdown(
                            choices=["128k", "192k", "256k", "320k"],
                            value="320k", 
                            label="🎵 Bitrate MP3",
                            info="Mayor = mejor calidad MP3"
                        )
                    
                    with gr.Row(equal_height=True):
                        coqui_audio_channels = gr.Radio(
                            choices=[("Mono", 1), ("Estéreo", 2)],
                            value=1,
                            label="🔊 Canales de Audio",
                            info="Estéreo para mejor espacialidad"
                        )
                        
                        coqui_wav_bit_depth = gr.Dropdown(
                            choices=["16", "24", "32"],
                            value="24",
                            label="🎚️ Profundidad WAV (bits)",
                            info="24-bit recomendado para calidad profesional"
                        )
                    
                    with gr.Row(equal_height=True):
                        coqui_mp3_quality = gr.Slider(
                            minimum=0, maximum=9, step=1, value=0,
                            label="🎛️ Calidad MP3 (0=mejor, 9=menor)",
                            info="Solo para archivos MP3"
                        )
                        
                        coqui_enable_limiter = gr.Checkbox(
                            value=True,
                            label="🛡️ Activar Limitador",
                            info="Previene distorsión en picos altos"
                        )
                
                # Configuraciones avanzadas
                with gr.Accordion("🔧 Configuraciones Avanzadas", open=False):
                    with gr.Row():
                        coqui_path = gr.Textbox(
                            label="📁 Directorio Personalizado de Modelos (opcional)",
                            value="",
                            interactive=True,
                            placeholder="Ej: C:/modelos_coqui/"
                        )
                    
                    with gr.Row():
                        gr.Markdown("**🎯 Recomendaciones para Audiolibros en Español:**")
                    
                    with gr.Column():
                        gr.Markdown("""
                        **📚 Mejores Modelos para Español:**
                        - **XTTS-v2**: Máxima calidad, clonación de voz, 17 idiomas
                        - **tts_models/es/css10/vits**: Específico español, buena calidad
                        - **tts_models/es/mai/tacotron2-DDC**: Clásico, muy estable
                        
                        **🎤 Mejores Voces para Español:**
                        - Ana Florence, Sofia Hellen, Tanja Adelina (femeninas)
                        - Andrew Chipper, Dionisio Schuyler (masculinas)
                        
                        **⚡ GPU:** Altamente recomendada para XTTS-v2 (10x más rápido)
                        """)
                
                # Presets para diferentes tipos de contenido
                with gr.Accordion("🎭 Presets para Diferentes Estilos", open=False):
                    with gr.Row(equal_height=True):
                        preset_audiolibro = gr.Button("📖 Audiolibro Narrativo", variant="secondary")
                        preset_educativo = gr.Button("🎓 Contenido Educativo", variant="secondary")
                        preset_dramatico = gr.Button("🎭 Lectura Dramática", variant="secondary")
                        preset_noticias = gr.Button("📰 Estilo Noticiero", variant="secondary")

                # Update models when language filter changes
                coqui_language_filter.change(
                    fn=get_coqui_models_by_language_gui,
                    inputs=coqui_language_filter,
                    outputs=coqui_model,
                )
                
                # Update voice and language options when model changes
                coqui_model.change(
                    fn=update_coqui_model_options,
                    inputs=coqui_model,
                    outputs=[coqui_speaker, coqui_language, coqui_speaker_wav, coqui_model_info]
                )
                
                # Connect preset buttons
                preset_audiolibro.click(
                    fn=apply_audiolibro_preset,
                    outputs=[coqui_length_scale, coqui_noise_scale, coqui_noise_w_scale]
                )
                preset_educativo.click(
                    fn=apply_educativo_preset,
                    outputs=[coqui_length_scale, coqui_noise_scale, coqui_noise_w_scale]
                )
                preset_dramatico.click(
                    fn=apply_dramatico_preset,
                    outputs=[coqui_length_scale, coqui_noise_scale, coqui_noise_w_scale]
                )
                preset_noticias.click(
                    fn=apply_noticias_preset,
                    outputs=[coqui_length_scale, coqui_noise_scale, coqui_noise_w_scale]
                )
                
                # Connect quality preset buttons
                preset_quality_mobile.click(
                    fn=apply_mobile_quality_preset,
                    outputs=[coqui_sample_rate, coqui_audio_bitrate, coqui_audio_channels, coqui_wav_bit_depth, coqui_mp3_quality, coqui_enable_limiter]
                )
                preset_quality_desktop.click(
                    fn=apply_desktop_quality_preset,
                    outputs=[coqui_sample_rate, coqui_audio_bitrate, coqui_audio_channels, coqui_wav_bit_depth, coqui_mp3_quality, coqui_enable_limiter]
                )
                preset_quality_high.click(
                    fn=apply_high_quality_preset,
                    outputs=[coqui_sample_rate, coqui_audio_bitrate, coqui_audio_channels, coqui_wav_bit_depth, coqui_mp3_quality, coqui_enable_limiter]
                )
                preset_quality_max.click(
                    fn=apply_max_quality_preset,
                    outputs=[coqui_sample_rate, coqui_audio_bitrate, coqui_audio_channels, coqui_wav_bit_depth, coqui_mp3_quality, coqui_enable_limiter]
                )
                
                # Connect OpenAI quality preset buttons
                openai_mobile_quality.click(
                    fn=apply_openai_mobile_quality_preset,
                    outputs=[openai_sample_rate, openai_audio_bitrate, openai_audio_channels, openai_wav_bit_depth, openai_mp3_quality, openai_enable_limiter, openai_normalize_volume]
                )
                openai_desktop_quality.click(
                    fn=apply_openai_desktop_quality_preset,
                    outputs=[openai_sample_rate, openai_audio_bitrate, openai_audio_channels, openai_wav_bit_depth, openai_mp3_quality, openai_enable_limiter, openai_normalize_volume]
                )
                openai_high_quality.click(
                    fn=apply_openai_high_quality_preset,
                    outputs=[openai_sample_rate, openai_audio_bitrate, openai_audio_channels, openai_wav_bit_depth, openai_mp3_quality, openai_enable_limiter, openai_normalize_volume]
                )
                openai_max_quality.click(
                    fn=apply_openai_max_quality_preset,
                    outputs=[openai_sample_rate, openai_audio_bitrate, openai_audio_channels, openai_wav_bit_depth, openai_mp3_quality, openai_enable_limiter, openai_normalize_volume]
                )
                
                # Connect Piper quality preset buttons
                piper_mobile_quality.click(
                    fn=apply_piper_mobile_quality_preset,
                    outputs=[piper_sample_rate, piper_audio_bitrate, piper_audio_channels, piper_wav_bit_depth, piper_mp3_quality, piper_enable_limiter, piper_normalize_volume]
                )
                piper_desktop_quality.click(
                    fn=apply_piper_desktop_quality_preset,
                    outputs=[piper_sample_rate, piper_audio_bitrate, piper_audio_channels, piper_wav_bit_depth, piper_mp3_quality, piper_enable_limiter, piper_normalize_volume]
                )
                piper_high_quality.click(
                    fn=apply_piper_high_quality_preset,
                    outputs=[piper_sample_rate, piper_audio_bitrate, piper_audio_channels, piper_wav_bit_depth, piper_mp3_quality, piper_enable_limiter, piper_normalize_volume]
                )
                piper_max_quality.click(
                    fn=apply_piper_max_quality_preset,
                    outputs=[piper_sample_rate, piper_audio_bitrate, piper_audio_channels, piper_wav_bit_depth, piper_mp3_quality, piper_enable_limiter, piper_normalize_volume]
                )
                
            with gr.Tab("Kokoro", id="kokoro_tab_id") as kokoro_tab:
                kokoro_tab.select(on_tab_change, inputs=None, outputs=None)
                gr.Markdown("**Kokoro TTS** - OpenAI-compatible local server with multi-language support. Configure custom host/port if needed.")
                
                with gr.Row(equal_height=True):
                    kokoro_base_url = gr.Textbox(
                        value=os.environ.get('OPENAI_BASE_URL', 'http://localhost:8880').replace('/v1', ''), 
                        label="Kokoro Base URL", 
                        info="Base URL for Kokoro server (without /v1)"
                    )
                    kokoro_language = gr.Dropdown(
                        choices=[name for code, name in get_kokoro_languages()],
                        value="Auto-detect",
                        label="Language",
                        interactive=True,
                        info="Select language for voice filtering"
                    )
                
                with gr.Row(equal_height=True):
                    kokoro_model = gr.Dropdown(
                        choices=["kokoro"], 
                        value="kokoro", 
                        label="Model", 
                        interactive=False,
                        info="Kokoro model (fixed)"
                    )
                    kokoro_voice = get_kokoro_voices_gui(
                        os.environ.get('OPENAI_BASE_URL', 'http://localhost:8880').replace('/v1', ''), 
                        ""
                    )
                    kokoro_output_format = gr.Dropdown(
                        ["mp3", "wav", "opus", "flac"], 
                        value="mp3", 
                        label="Output Format", 
                        interactive=True
                    )
                
                with gr.Row(equal_height=True):
                    kokoro_speed = gr.Slider(
                        minimum=0.5, 
                        maximum=2.0, 
                        step=0.1, 
                        value=0.9, 
                        label="Speed", 
                        info="Speech speed"
                    )
                    gr.Button("🔄 Refresh Voices", size="sm").click(
                        fn=lambda url, lang: update_kokoro_voices_by_language(lang, url),
                        inputs=[kokoro_base_url, kokoro_language],
                        outputs=kokoro_voice
                    )
                
                # Update voices when language changes
                def handle_language_change(selected_language_name, base_url):
                    # Convert language name back to code
                    language_code = ""
                    for code, name in get_kokoro_languages():
                        if name == selected_language_name:
                            language_code = code
                            break
                    return update_kokoro_voices_by_language(language_code, base_url)
                
                kokoro_language.change(
                    fn=handle_language_change,
                    inputs=[kokoro_language, kokoro_base_url],
                    outputs=kokoro_voice
                )

                # === CONTROLES DE CALIDAD DE AUDIO KOKORO ===
                with gr.Accordion("🎵 Control de Calidad de Audio", open=False):
                    gr.Markdown("### Presets de Calidad Rápida")
                    with gr.Row(equal_height=True):
                        kokoro_mobile_quality = gr.Button("📱 Móvil (Rápido)", variant="secondary")
                        kokoro_desktop_quality = gr.Button("🖥️ Escritorio", variant="secondary") 
                        kokoro_high_quality = gr.Button("🎧 Alta Calidad", variant="primary")
                        kokoro_max_quality = gr.Button("💎 Máxima Calidad", variant="primary")
                    
                    gr.Markdown("### Configuración Detallada")
                    with gr.Row(equal_height=True):
                        kokoro_sample_rate_ui = gr.Dropdown(
                            choices=[16000, 22050, 44100, 48000], 
                            value=22050, 
                            label="Frecuencia de Muestreo (Hz)", 
                            info="Mayor = mejor calidad, archivos más grandes"
                        )
                        kokoro_audio_bitrate_ui = gr.Dropdown(
                            choices=["128k", "192k", "256k", "320k"], 
                            value="192k", 
                            label="Bitrate de Audio", 
                            info="Para MP3 y formatos con pérdida"
                        )
                        kokoro_audio_channels_ui = gr.Dropdown(
                            choices=[1, 2], 
                            value=1, 
                            label="Canales", 
                            info="1=Mono, 2=Estéreo"
                        )
                    
                    with gr.Row(equal_height=True):
                        kokoro_wav_bit_depth_ui = gr.Dropdown(
                            choices=[16, 24, 32], 
                            value=16, 
                            label="Profundidad de Bits (WAV)", 
                            info="16=Estándar, 24/32=Audio profesional"
                        )
                        kokoro_mp3_quality_ui = gr.Slider(
                            minimum=0, maximum=9, step=1, value=2, 
                            label="Calidad MP3 (0=mejor)", 
                            info="Solo para formato MP3"
                        )
                        kokoro_enable_limiter_ui = gr.Checkbox(
                            value=True, 
                            label="Limitador de Audio", 
                            info="Evita distorsión y clipping"
                        )
                        kokoro_normalize_volume_ui = gr.Checkbox(
                            value=True, 
                            label="Normalización de Volumen", 
                            info="Volumen consistente"
                        )

                # Connect Kokoro quality preset buttons
                kokoro_mobile_quality.click(
                    fn=apply_kokoro_mobile_quality_preset,
                    outputs=[kokoro_sample_rate_ui, kokoro_audio_bitrate_ui, kokoro_audio_channels_ui, kokoro_wav_bit_depth_ui, kokoro_mp3_quality_ui, kokoro_enable_limiter_ui, kokoro_normalize_volume_ui]
                )
                kokoro_desktop_quality.click(
                    fn=apply_kokoro_desktop_quality_preset,
                    outputs=[kokoro_sample_rate_ui, kokoro_audio_bitrate_ui, kokoro_audio_channels_ui, kokoro_wav_bit_depth_ui, kokoro_mp3_quality_ui, kokoro_enable_limiter_ui, kokoro_normalize_volume_ui]
                )
                kokoro_high_quality.click(
                    fn=apply_kokoro_high_quality_preset,
                    outputs=[kokoro_sample_rate_ui, kokoro_audio_bitrate_ui, kokoro_audio_channels_ui, kokoro_wav_bit_depth_ui, kokoro_mp3_quality_ui, kokoro_enable_limiter_ui, kokoro_normalize_volume_ui]
                )
                kokoro_max_quality.click(
                    fn=apply_kokoro_max_quality_preset,
                    outputs=[kokoro_sample_rate_ui, kokoro_audio_bitrate_ui, kokoro_audio_channels_ui, kokoro_wav_bit_depth_ui, kokoro_mp3_quality_ui, kokoro_enable_limiter_ui, kokoro_normalize_volume_ui]
                )

        gr.Markdown("---")
        with gr.Row(equal_height=True):
            gr.Button("Stop").click(
                fn=terminate_audiobook_generator,
                inputs=None,
                outputs=None)
            gr.Button("Start", variant="primary").click(
                fn=process_ui_form,
                inputs=[
                    input_file, output_dir, worker_count, log_level, output_text, preview,
                    search_and_replace_file, title_mode, new_line_mode, chapter_start, chapter_end, remove_endnotes, remove_reference_numbers,
                    model, voices, speed, openai_output_format, instructions,
                    # OpenAI audio quality inputs
                    openai_sample_rate, openai_audio_bitrate, openai_audio_channels, openai_wav_bit_depth, openai_mp3_quality, openai_enable_limiter, openai_normalize_volume,
                    azure_language, azure_voice, azure_output_format, azure_break_duration,
                    edge_language, edge_voice, edge_output_format, proxy, edge_voice_rate, edge_volume, edge_pitch, edge_break_duration,
                    # Coqui inputs (must appear before Piper inputs in the handler signature)
                    coqui_model, coqui_speaker, coqui_language, coqui_speaker_wav, coqui_path, coqui_output_format,
                    coqui_length_scale, coqui_noise_scale, coqui_noise_w_scale, coqui_device,
                    # Coqui audio quality inputs
                    coqui_sample_rate, coqui_audio_bitrate, coqui_audio_channels, coqui_wav_bit_depth, coqui_mp3_quality, coqui_enable_limiter,
                    # Kokoro inputs
                    kokoro_base_url, kokoro_language, kokoro_model, kokoro_voice, kokoro_output_format, kokoro_speed,
                    # Kokoro audio quality inputs
                    kokoro_sample_rate_ui, kokoro_audio_bitrate_ui, kokoro_audio_channels_ui, kokoro_wav_bit_depth_ui, kokoro_mp3_quality_ui, kokoro_enable_limiter_ui, kokoro_normalize_volume_ui,
                    piper_executable_path, piper_docker_image, piper_language, piper_voice, piper_quality, piper_speaker,
                    piper_noise_scale, piper_noise_w_scale, piper_length_scale, piper_sentence_silence, piper_device,
                    # Piper audio quality inputs
                    piper_sample_rate, piper_audio_bitrate, piper_audio_channels, piper_wav_bit_depth, piper_mp3_quality, piper_enable_limiter, piper_normalize_volume
                ],
                outputs=None)
        with gr.Row():
            global webui_log_file
            webui_log_file = generate_unique_log_path("EtA_WebUI")
            # Create the log file with UTF-8 encoding
            with open(webui_log_file, 'w', encoding='utf-8') as f:
                f.write("")  # Create empty file with UTF-8 encoding
            Log(str(webui_log_file.absolute()), dark=True, xterm_font_size=12)

    ui.launch(server_name=config.host, server_port=config.port, inbrowser=True)