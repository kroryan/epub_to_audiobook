from multiprocessing import Process
from typing import Optional
import json
import os
import requests
from datetime import datetime
from pathlib import Path

import gradio as gr
from gradio_log import Log

# Disable Gradio analytics to prevent postMessage errors
os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"
gr.analytics.track = lambda *args, **kwargs: None
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
            gr.Dropdown(["Default Voice"], value="Default Voice", label="🎤 Voice/Speaker", interactive=True),
            gr.Dropdown(["es"], value="es", label="🗣️ Target Language", interactive=True),
            gr.File(visible=False),  # speaker_wav file
            gr.Markdown("**📋 Model Information:** Select a model first")
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
        value=voices[0] if voices else "Default Voice", 
        label="🎤 Voice/Speaker", 
        interactive=True,
        allow_custom_value=True
    )
    
    # Update language dropdown
    language_dropdown = gr.Dropdown(
        languages,
        value="es" if "es" in languages else (languages[0] if languages else "es"),
        label="🗣️ Target Language",
        interactive=model_info.get("is_multi_lingual", False)
    )
    
    # Show/hide voice cloning file upload based on model capabilities
    show_speaker_wav = model_info.get("supports_voice_cloning", False)
    speaker_wav_file = gr.File(
        label="🎙️ Voice Cloning - Upload reference audio",
        file_types=[".wav", ".mp3", ".flac"],
        visible=show_speaker_wav
    )
    
    # Create detailed model info text
    info_parts = [f"**📋 {model_name}**"]
    
    if "xtts" in model_name.lower():
        info_parts.append("🌟 **PREMIUM MODEL** - Maximum quality")
        info_parts.append(f"🎤 {len(voices)} predefined voices")
        info_parts.append(f"🌍 {len(languages)} supported languages")
        info_parts.append("✅ Voice cloning")
        info_parts.append("⚡ Requires GPU for best performance")
    elif "/es/" in model_name:
        info_parts.append("🇪🇸 **SPANISH-SPECIFIC MODEL**")
        info_parts.append("✅ Optimized for Spanish")
        info_parts.append("⚡ Works well on CPU")
    else:
        if model_info.get("is_multi_speaker", False):
            info_parts.append(f"🎤 Multi-speaker ({len(voices)} voices)")
        if model_info.get("is_multi_lingual", False):
            info_parts.append(f"🌍 Multi-language ({len(languages)} languages)")
        if model_info.get("supports_voice_cloning", False):
            info_parts.append("✅ Voice cloning")
    
    model_info_text = gr.Markdown("\n\n".join(info_parts))
    
    return voice_dropdown, language_dropdown, speaker_wav_file, model_info_text

# Functions for presets
def apply_audiolibro_preset():
    """Preset for narrative audiobooks."""
    return 0.95, 0.6, 0.8  # length_scale, noise_scale, noise_w_scale

def apply_educativo_preset():
    """Preset for educational content."""
    return 0.85, 0.4, 0.7  # Faster, less expressive, clearer

def apply_dramatico_preset():
    """Preset for dramatic reading."""
    return 1.0, 0.8, 0.9  # Normal speed, very expressive, very natural

def apply_noticias_preset():
    """Preset for news style."""
    return 0.9, 0.3, 0.6  # News pace, less expressive, precise timing

# Functions for audio quality presets
def apply_mobile_quality_preset():
    """Preset for mobile/podcast quality - Small files"""
    return "22050", "128k", 1, "16", 4, True  # sample_rate, bitrate, channels, bit_depth, mp3_quality, limiter

def apply_desktop_quality_preset():
    """Preset for desktop quality - Balance quality/size"""
    return "44100", "192k", 1, "24", 2, True

def apply_high_quality_preset():
    """Preset for high quality - Recommended"""
    return "44100", "320k", 1, "24", 0, True

def apply_max_quality_preset():
    """Preset for maximum quality - Large files"""
    return "48000", "320k", 2, "24", 0, True

# Functions for OpenAI/Kokoro audio quality presets
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

# Functions for Piper audio quality presets
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

# Functions for Kokoro audio quality presets
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


# Advanced Kokoro Functions
def validate_voice_combination(voice_spec: str, base_url: str = "http://localhost:8880"):
    """
    Validate voice combination syntax and check if voices exist
    
    Args:
        voice_spec: Voice combination string (e.g., "voice1+voice2(0.5)")
        base_url: Kokoro server base URL
        
    Returns:
        Tuple of (is_valid: bool, message: str)
    """
    try:
        # Import the provider to use its validation logic
        from audiobook_generator.tts_providers.kokoro_tts_provider import KokoroTTSProvider
        from audiobook_generator.config.general_config import GeneralConfig
        
        # Create a temporary config with all required fields
        config = GeneralConfig(None)
        config.kokoro_base_url = base_url
        config.tts = "kokoro"
        config.model_name = "kokoro"
        config.voice_name = voice_spec
        config.output_format = "mp3"  # Set default format to avoid error
        config.speed = 1.0
        
        provider = KokoroTTSProvider(config)
        
        # Try to validate the combination
        validated = provider.validate_voice_combination(voice_spec)
        return True, f"✅ Valid combination: {validated}"
        
    except Exception as e:
        return False, f"❌ Error: {str(e)}"


def create_voice_combination(voice_spec: str, base_url: str = "http://localhost:8880"):
    """
    Create a combined voice and return download info
    
    Args:
        voice_spec: Voice combination string
        base_url: Kokoro server base URL
        
    Returns:
        Tuple of (success: bool, message: str, file_path: str)
    """
    try:
        # Check if the server allows voice combination creation
        response = requests.post(
            f"{base_url.rstrip('/')}/v1/audio/voices/combine",
            json=voice_spec,
            headers={"Authorization": "Bearer fake-key", "Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 403:
            return False, "⚠️ Voice combination creation is disabled on the server. You can still use voice combinations in the voice field directly (e.g., 'voice1+voice2(0.5)').", ""
        elif response.status_code == 200:
            return True, f"✅ Combined voice created successfully", ""
        else:
            return False, f"❌ Server error: {response.status_code} - {response.text}", ""
        
    except Exception as e:
        return False, f"❌ Failed to create combination: {str(e)}", ""


def test_kokoro_connection(base_url: str = "http://localhost:8880"):
    """Test connection to Kokoro server"""
    try:
        response = requests.get(f"{base_url.rstrip('/')}/v1/models", timeout=5)
        if response.status_code == 200:
            return True, f"✅ Connected to Kokoro server at {base_url}"
        else:
            return False, f"❌ Server responded with status {response.status_code}"
    except Exception as e:
        return False, f"❌ Connection failed: {str(e)}"


def get_kokoro_voice_samples():
    """Get sample text for different languages to test voices"""
    return {
        "": "Hello, this is a test of the selected voice.",
        "a": "Hello, this is a test of the American English voice.",
        "b": "Hello, this is a test of the British English voice.",
        "e": "Hola, esta es una prueba de la voz en español.",
        "f": "Bonjour, ceci est un test de la voix française.",
        "h": "नमस्ते, यह चयनित आवाज़ का परीक्षण है।",
        "i": "Ciao, questo è un test della voce italiana.",
        "p": "Olá, este é um teste da voz portuguesa.",
        "j": "こんにちは、これは選択された音声のテストです。",
        "z": "你好，这是所选语音的测试。"
    }


# Voice Preset Management Functions
def save_voice_preset(preset_name: str, voice_combinations: str, preset_dir: str = "voice_presets"):
    """Save a voice combination preset to JSON file"""
    import json
    import os
    from datetime import datetime
    
    try:
        # Create presets directory if it doesn't exist
        if not os.path.exists(preset_dir):
            os.makedirs(preset_dir)
        
        # Parse voice combinations into structured data
        preset_data = {
            "name": preset_name,
            "voices": parse_voice_combination_to_dict(voice_combinations),
            "created": datetime.now().isoformat(),
            "combination_string": voice_combinations
        }
        
        # Save to JSON file
        filename = f"{preset_name.replace(' ', '_').lower()}.json"
        filepath = os.path.join(preset_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(preset_data, f, indent=2, ensure_ascii=False)
        
        return True, f"✅ Preset '{preset_name}' guardado en {filepath}"
        
    except Exception as e:
        return False, f"❌ Error guardando preset: {str(e)}"


def load_voice_presets(preset_dir: str = "voice_presets"):
    """Load all available voice presets from JSON files"""
    import json
    import os
    
    try:
        if not os.path.exists(preset_dir):
            return {}
        
        presets = {}
        for filename in os.listdir(preset_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(preset_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        preset_data = json.load(f)
                        presets[preset_data['name']] = preset_data
                except Exception as e:
                    print(f"Error loading preset {filename}: {e}")
        
        return presets
        
    except Exception as e:
        print(f"Error loading presets: {e}")
        return {}


def parse_voice_combination_to_dict(voice_combination: str):
    """Parse voice combination string into structured dictionary"""
    try:
        if not voice_combination or voice_combination.strip() == "":
            return []
        
        # Handle simple single voice
        if "+" not in voice_combination and "-" not in voice_combination:
            return [{"voice": voice_combination.strip(), "weight": 1.0, "operation": "base"}]
        
        # Parse complex combinations
        voices = []
        # Split by + and - while keeping the operators
        import re
        parts = re.split(r'([+-])', voice_combination)
        
        current_voice = None
        current_operation = "base"
        
        for i, part in enumerate(parts):
            part = part.strip()
            if not part:
                continue
                
            if part in ['+', '-']:
                current_operation = "add" if part == '+' else "subtract"
            else:
                # Parse voice and weight
                if '(' in part and ')' in part:
                    voice_name = part.split('(')[0].strip()
                    weight_str = part.split('(')[1].split(')')[0].strip()
                    try:
                        weight = float(weight_str)
                    except:
                        weight = 1.0
                else:
                    voice_name = part.strip()
                    weight = 1.0
                
                voices.append({
                    "voice": voice_name,
                    "weight": weight,
                    "operation": current_operation
                })
                current_operation = "add"  # Reset to add for next voices
        
        return voices
        
    except Exception as e:
        print(f"Error parsing voice combination: {e}")
        return []


def format_voice_combination_from_dict(voices_list):
    """Convert structured voice list back to combination string"""
    if not voices_list:
        return ""
    
    result = []
    for i, voice_data in enumerate(voices_list):
        voice_name = voice_data['voice']
        weight = voice_data.get('weight', 1.0)
        operation = voice_data.get('operation', 'base')
        
        voice_str = voice_name
        if weight != 1.0:
            voice_str = f"{voice_name}({weight})"
        
        if i == 0:
            # First voice (base)
            result.append(voice_str)
        else:
            # Subsequent voices with operators
            op_symbol = "+" if operation == "add" else "-"
            result.append(f"{op_symbol}{voice_str}")
    
    return "".join(result)


def create_multi_voice_combination(selected_voices_json: str):
    """Create voice combination string from JSON of selected voices with weights"""
    import json
    
    try:
        selected_voices = json.loads(selected_voices_json) if selected_voices_json else []
        
        if not selected_voices:
            return ""
        
        # Convert to combination string
        parts = []
        for i, voice_data in enumerate(selected_voices):
            voice_name = voice_data['voice']
            weight = voice_data.get('weight', 1.0)
            
            if weight != 1.0:
                voice_str = f"{voice_name}({weight})"
            else:
                voice_str = voice_name
            
            if i == 0:
                parts.append(voice_str)
            else:
                parts.append(f"+{voice_str}")
        
        return "".join(parts)
        
    except Exception as e:
        print(f"Error creating multi-voice combination: {e}")
        return ""


def filter_voices_by_search(search_term, base_url="http://localhost:8880"):
    """Filter available voices based on search term"""
    try:
        all_voices = fetch_kokoro_voices(base_url)
        
        if not search_term or search_term.strip() == "":
            return gr.CheckboxGroup(
                choices=all_voices,
                label="Voces Disponibles",
                info="Selecciona múltiples voces para mezclar",
                interactive=True
            )
        
        # Filter voices that contain the search term (case insensitive)
        search_lower = search_term.lower()
        filtered_voices = [voice for voice in all_voices if search_lower in voice.lower()]
        
        return gr.CheckboxGroup(
            choices=filtered_voices,
            label=f"Voces Disponibles ({len(filtered_voices)} encontradas)",
            info=f"Búsqueda: '{search_term}' - Selecciona múltiples voces para mezclar",
            interactive=True
        )
        
    except Exception as e:
        print(f"Error filtering voices: {e}")
        return gr.CheckboxGroup(
            choices=[],
            label="Voces Disponibles (Error)",
            info="Error al filtrar voces",
            interactive=True
        )


def clear_voice_selection():
    """Clear all selected voices"""
    return [], "<p style='color: #666; font-style: italic;'>No hay voces seleccionadas para mezclar</p>", "[]", ""


def apply_voice_mix_to_main(voice_config_json, main_voice_field):
    """Apply the mixed voice combination to the main voice field"""
    try:
        if not voice_config_json or voice_config_json == "[]":
            return main_voice_field, "❌ No hay voces seleccionadas para aplicar"
        
        voice_configs = json.loads(voice_config_json)
        if not voice_configs:
            return main_voice_field, "❌ No hay voces seleccionadas para aplicar"
        
        # Create combination string
        combination = create_multi_voice_combination(voice_config_json)
        
        return combination, f"✅ Mezcla aplicada: {combination}"
        
    except Exception as e:
        return main_voice_field, f"❌ Error aplicando mezcla: {str(e)}"


def update_selected_voices_display(selected_voices):
    """Update the display of selected voices with weight controls"""
    if not selected_voices:
        return "<p style='color: #666; font-style: italic;'>No hay voces seleccionadas para mezclar</p>", "[]"
    
    # Create HTML for selected voices with weight sliders
    html_parts = ["<div style='display: flex; flex-direction: column; gap: 10px;'>"]
    
    voice_configs = []
    
    for i, voice in enumerate(selected_voices):
        default_weight = 1.0 if i == 0 else 0.5  # First voice at full strength, others at 50%
        
        voice_config = {
            "voice": voice,
            "weight": default_weight,
            "index": i
        }
        voice_configs.append(voice_config)
        
        # Create HTML for this voice
        html_parts.append(f"""
            <div style='background: #f8f9fa; padding: 12px; border-radius: 8px; border-left: 4px solid #007acc; margin-bottom: 8px;'>
                <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;'>
                    <strong style='color: #333; font-size: 0.95em;'>{voice}</strong>
                    <span style='color: #666; font-size: 0.85em; background: #e9ecef; padding: 2px 8px; border-radius: 4px;'>Peso: {default_weight}</span>
                </div>
                <div style='display: flex; align-items: center; gap: 8px;'>
                    <span style='font-size: 0.75em; color: #6c757d; min-width: 25px;'>0.1</span>
                    <input type='range' min='0.1' max='3.0' step='0.1' value='{default_weight}' 
                           style='flex: 1; height: 4px; background: #ddd; border-radius: 2px; outline: none; cursor: pointer;'/>
                    <span style='font-size: 0.75em; color: #6c757d; min-width: 25px;'>3.0</span>
                </div>
                <div style='margin-top: 5px; font-size: 0.75em; color: #6c757d;'>
                    Desliza para ajustar el peso de esta voz en la mezcla
                </div>
            </div>
        """)
    
    html_parts.append("</div>")
    
    # Add information about the combination
    if len(selected_voices) > 1:
        html_parts.append(f"""
            <div style='margin-top: 10px; padding: 8px; background: #d1ecf1; border-radius: 4px; border-left: 4px solid #17a2b8;'>
                <strong style='color: #0c5460; font-size: 0.9em;'>🎛️ Mezcla de {len(selected_voices)} voces</strong>
                <div style='font-size: 0.8em; color: #0c5460; margin-top: 2px;'>
                    Usa el botón "Aplicar Mezcla" para usar esta combinación
                </div>
            </div>
        """)
    
    html_content = "".join(html_parts)
    voice_configs_json = json.dumps(voice_configs)
    
    return html_content, voice_configs_json


def load_preset_combination(preset_name, presets_dict):
    """Load a preset and return the combination string"""
    try:
        if not preset_name or preset_name not in presets_dict:
            return "", "No hay presets seleccionados"
        
        preset_data = presets_dict[preset_name]
        combination = preset_data.get('combination_string', '')
        
        return combination, f"✅ Preset '{preset_name}' cargado: {combination}"
        
    except Exception as e:
        return "", f"❌ Error cargando preset: {str(e)}"


def save_current_preset(preset_name, combination_string):
    """Save current voice combination as a preset"""
    try:
        if not preset_name or not preset_name.strip():
            return "❌ Nombre del preset requerido"
        
        if not combination_string or not combination_string.strip():
            return "❌ No hay combinación de voces para guardar"
        
        success, message = save_voice_preset(preset_name.strip(), combination_string)
        return message
        
    except Exception as e:
        return f"❌ Error guardando preset: {str(e)}"


def update_test_voice_weights_display(selected_test_voices):
    """Update weight controls for test voices with sliders"""
    if not selected_test_voices:
        return ("<p style='color: #666; font-style: italic;'>Select voices above to adjust their weights</p>", 
                "[]", "")
    
    # Create HTML with weight controls (dark theme)
    html_parts = ["""
        <div style='display: flex; flex-direction: column; gap: 12px; padding: 15px; background: #1f2937; border-radius: 8px; border: 1px solid #374151;'>
        <h4 style='margin: 0 0 10px 0; color: #f9fafb; font-size: 1.1em;'>🎚️ Voice Weight Controls</h4>
    """]
    
    voice_configs = []
    
    for i, voice in enumerate(selected_test_voices):
        default_weight = 1.0 if i == 0 else 0.5
        
        voice_config = {
            "voice": voice,
            "weight": default_weight,
            "index": i
        }
        voice_configs.append(voice_config)
        
        # Create slider control for each voice (dark theme)
        html_parts.append(f"""
            <div style='background: #374151; padding: 12px; border-radius: 6px; border: 1px solid #4b5563;'>
                <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;'>
                    <strong style='color: #f9fafb; font-size: 0.95em;'>{voice}</strong>
                    <span id='weight-display-{i}' style='background: #4b5563; padding: 4px 8px; border-radius: 4px; font-size: 0.85em; color: #d1d5db; min-width: 60px; text-align: center;'>{default_weight}</span>
                </div>
                <div style='display: flex; align-items: center; gap: 10px;'>
                    <span style='font-size: 0.8em; color: #9ca3af; min-width: 30px;'>0.1</span>
                    <input 
                        type='range' 
                        id='weight-slider-{i}' 
                        min='0.1' 
                        max='3.0' 
                        step='0.1' 
                        value='{default_weight}'
                        style='flex: 1; height: 6px; background: #6b7280; border-radius: 3px; outline: none; cursor: pointer; accent-color: #3b82f6;'
                        oninput='updateTestVoiceWeight({i}, this.value, "{voice}")'
                    />
                    <span style='font-size: 0.8em; color: #9ca3af; min-width: 30px;'>3.0</span>
                </div>
            </div>
        """)
    
    html_parts.append("</div>")
    
    # Add JavaScript for real-time updates
    html_parts.append(f"""
        <script>
        function updateTestVoiceWeight(index, weight, voiceName) {{
            // Update display
            const display = document.getElementById('weight-display-' + index);
            if (display) {{
                display.textContent = parseFloat(weight).toFixed(1);
            }}
            
            // Trigger Gradio update (this will be handled by the event listener)
            console.log('Updated', voiceName, 'weight to', weight);
        }}
        </script>
    """)
    
    html_content = "".join(html_parts)
    voice_configs_json = json.dumps(voice_configs)
    
    # Generate combination string
    combination_parts = []
    for i, config in enumerate(voice_configs):
        voice = config["voice"]
        weight = config["weight"]
        
        if i == 0:
            if weight != 1.0:
                combination_parts.append(f"{voice}({weight})")
            else:
                combination_parts.append(voice)
        else:
            if weight != 1.0:
                combination_parts.append(f"+{voice}({weight})")
            else:
                combination_parts.append(f"+{voice}")
    
    combination_string = "".join(combination_parts)
    
    return html_content, voice_configs_json, combination_string


def export_voice_configuration(voice_configs_json):
    """Export voice configuration to JSON file"""
    from datetime import datetime

    try:
        if voice_configs_json is None or voice_configs_json == "[]":
            return None, "❌ No configuration to export"

        if isinstance(voice_configs_json, str):
            voice_configs = json.loads(voice_configs_json)
        elif isinstance(voice_configs_json, list):
            voice_configs = voice_configs_json
        else:
            return None, "❌ Unsupported configuration format"

        if not voice_configs:
            return None, "❌ No configuration to export"

        # Generate combination string directly
        combination_parts = []
        for i, voice_config in enumerate(voice_configs):
            voice_name = voice_config.get('voice')
            weight_value = voice_config.get('weight', 1.0)

            try:
                weight = float(weight_value)
            except (TypeError, ValueError):
                weight = 1.0

            if weight != 1.0:
                voice_str = f"{voice_name}({weight})"
            else:
                voice_str = voice_name

            if i == 0:
                combination_parts.append(voice_str)
            else:
                combination_parts.append(f"+{voice_str}")

        combination_string = "".join(combination_parts)

        # Create export data
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        export_data = {
            "name": f"Voice_Combination_{timestamp}",
            "created": datetime.now().isoformat(),
            "voices": voice_configs,
            "combination_string": combination_string,
            "version": "1.0",
            "description": f"Combinación de {len(voice_configs)} voces"
        }

        # Save to voice_presets directory
        presets_dir = Path(__file__).resolve().parents[2] / 'voice_presets'
        presets_dir.mkdir(parents=True, exist_ok=True)

        filename = f"voice_combination_{timestamp}.json"
        file_path = presets_dir / filename

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        return str(file_path), f"✅ Configuration saved successfully!\n📁 File: {filename}\n📂 Location: voice_presets/ folder\n🎤 Voices: {len(voice_configs)}\n\nYou can find this file in the voice_presets directory of your project."

    except Exception as e:
        return None, f"❌ Error exporting configuration: {str(e)}"


def import_voice_configuration(config_file):
    """Import voice configuration from JSON file"""
    try:
        if config_file is None:
            return [], "<p style='color: #666;'>No hay archivo seleccionado</p>", "[]", ""
        
        # Read JSON file
        with open(config_file.name, 'r', encoding='utf-8') as f:
            import_data = json.load(f)
        
        if 'voices' not in import_data:
            return [], "<p style='color: #dc3545;'>❌ Invalid JSON file: missing 'voices'</p>", "[]", ""
        
        voices = import_data['voices']
        if not voices:
            return [], "<p style='color: #dc3545;'>❌ No hay voces en el archivo</p>", "[]", ""
        
        # Extract voice names for checkbox selection
        voice_names = [v['voice'] for v in voices]
        
        # Create display and combination
        html_display, json_config, combination = update_test_voice_weights_display(voice_names)
        
        return voice_names, html_display, json.dumps(voices), combination
        
    except Exception as e:
        return [], f"<p style='color: #dc3545;'>❌ Error importando: {str(e)}</p>", "[]", ""


def preview_voice_combination(voice_spec: str, language_code: str, base_url: str = "http://localhost:8880"):
    """
    Generate a preview audio sample with the voice combination
    
    Args:
        voice_spec: Voice combination string
        language_code: Language code for sample text
        base_url: Kokoro server base URL
        
    Returns:
        Tuple of (success: bool, message: str, audio_file: str)
    """
    try:
        # Get sample text for the language
        sample_texts = get_kokoro_voice_samples()
        sample_text = sample_texts.get(language_code, sample_texts[""])
        
        # Make request to Kokoro
        url = f"{base_url.rstrip('/')}/v1/audio/speech"
        payload = {
            "model": "kokoro",
            "voice": voice_spec,
            "input": sample_text,
            "speed": 1.0,
            "response_format": "mp3",
            "stream": False,
            "lang_code": language_code
        }
        
        headers = {
            "Authorization": "Bearer fake-key",
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            # Save to temporary file
            import tempfile
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            temp_file.write(response.content)
            temp_file.close()
            
            return True, f"✅ Preview generated: '{sample_text}'", temp_file.name
        else:
            return False, f"❌ Generation failed: {response.status_code} - {response.text}", ""
            
    except Exception as e:
        return False, f"❌ Preview failed: {str(e)}", ""


def preview_voice_with_language(voice_spec: str, language_name: str, custom_text: str = "", base_url: str = "http://localhost:8880"):
    """
    Generate preview with language name conversion
    
    Args:
        voice_spec: Voice combination string  
        language_name: Language full name (e.g., "Spanish")
        custom_text: Custom text for preview (optional)
        base_url: Kokoro server base URL
        
    Returns:
        Tuple of (success: bool, message: str, audio_file: str)
    """
    # Convert language name to code
    language_code = ""
    for code, name in get_kokoro_languages():
        if name == language_name:
            language_code = code
            break
    
    return preview_voice_combination_with_text(voice_spec, language_code, custom_text, base_url)


def preview_voice_combination_with_text(voice_spec: str, language_code: str, custom_text: str = "", base_url: str = "http://localhost:8880"):
    """
    Generate a preview audio sample with custom text or default sample
    
    Args:
        voice_spec: Voice combination string
        language_code: Language code for sample text
        custom_text: Custom text to synthesize (optional)
        base_url: Kokoro server base URL
        
    Returns:
        Tuple of (success: bool, message: str, audio_file: str)
    """
    try:
        # Use custom text or get default sample text
        if custom_text.strip():
            sample_text = custom_text.strip()
        else:
            # Auto-detect language from voice if not provided
            if not language_code and voice_spec:
                # Extract language from voice prefix (e.g., "em_" -> "e" for Spanish)
                voice_prefix = voice_spec.split('_')[0] if '_' in voice_spec else ''
                if voice_prefix in ['af', 'am']:
                    language_code = 'a'  # English
                elif voice_prefix in ['em', 'ef']:
                    language_code = 'e'  # Spanish
                elif voice_prefix in ['fm', 'ff']:
                    language_code = 'f'  # French
                else:
                    language_code = 'a'  # Default to English
            
            sample_texts = get_kokoro_voice_samples()
            sample_text = sample_texts.get(language_code, sample_texts[""])
        
        # Make request to Kokoro
        url = f"{base_url.rstrip('/')}/v1/audio/speech"
        payload = {
            "model": "kokoro",
            "voice": voice_spec,
            "input": sample_text,
            "speed": 1.0,
            "response_format": "mp3",
            "stream": False,
            "lang_code": language_code
        }
        
        headers = {
            "Authorization": "Bearer fake-key",
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            # Save to temporary file
            import tempfile
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            temp_file.write(response.content)
            temp_file.close()
            
            preview_msg = f"✅ Preview generado con voz: {voice_spec}"
            if custom_text.strip():
                preview_msg += f"\n📝 Texto personalizado: '{sample_text[:50]}...'" if len(sample_text) > 50 else f"\n📝 Texto personalizado: '{sample_text}'"
            else:
                preview_msg += f"\n📝 Texto de ejemplo: '{sample_text}'"
            
            return True, preview_msg, temp_file.name
        else:
            return False, f"❌ Error al generar preview: {response.status_code} - {response.text}", ""
            
    except Exception as e:
        return False, f"❌ Error en preview: {str(e)}", ""


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
                    # Kokoro advanced features (adding missing parameters)
                    kokoro_volume_multiplier=1.0, kokoro_stream=True, kokoro_return_timestamps=False, kokoro_return_download_link=False,
                    # Kokoro normalization options (adding missing parameters)
                    kokoro_normalize=True, kokoro_unit_normalization=False, kokoro_url_normalization=True, kokoro_email_normalization=True, 
                    kokoro_pluralization_normalization=True, kokoro_phone_normalization=True, kokoro_replace_symbols=True,
                    # Kokoro voice mixing (adding missing parameter)
                    kokoro_voice_weight_normalization=True,
                    piper_executable_path=None, piper_docker_image=None, piper_language=None, piper_voice=None, piper_quality=None, piper_speaker=None,
                    piper_noise_scale=None, piper_noise_w_scale=None, piper_length_scale=None, piper_sentence_silence=None, piper_device=None,
                    # Piper audio quality inputs
                    piper_sample_rate=None, piper_audio_bitrate=None, piper_audio_channels=None, piper_wav_bit_depth=None, piper_mp3_quality=None, piper_enable_limiter=None, piper_normalize_volume=None):

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
        # Use dedicated Kokoro TTS provider with all advanced features
        config.tts = "kokoro"
        
        # Basic Kokoro settings
        config.output_format = kokoro_output_format
        config.voice_name = kokoro_voice

        config.model_name = kokoro_model
        config.speed = kokoro_speed
        
        # Kokoro-specific settings
        config.kokoro_base_url = kokoro_base_url or "http://localhost:8880"
        config.kokoro_volume_multiplier = kokoro_volume_multiplier
        config.kokoro_stream = kokoro_stream
        config.kokoro_return_timestamps = kokoro_return_timestamps
        config.kokoro_return_download_link = kokoro_return_download_link
        
        # Advanced normalization options
        config.kokoro_normalize = kokoro_normalize
        config.kokoro_unit_normalization = kokoro_unit_normalization
        config.kokoro_url_normalization = kokoro_url_normalization
        config.kokoro_email_normalization = kokoro_email_normalization
        config.kokoro_pluralization_normalization = kokoro_pluralization_normalization
        config.kokoro_phone_normalization = kokoro_phone_normalization
        config.kokoro_replace_symbols = kokoro_replace_symbols
        
        # Voice mixing settings
        config.kokoro_voice_weight_normalization = kokoro_voice_weight_normalization
        
        # Audio quality parameters
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
                
                # === OPENAI/KOKORO AUDIO QUALITY CONTROLS ===
                with gr.Accordion("🎵 Audio Quality Control", open=False):
                    gr.Markdown("### Presets de Calidad Rápida")
                    with gr.Row(equal_height=True):
                        openai_mobile_quality = gr.Button("📱 Mobile (Fast)", variant="secondary")
                        openai_desktop_quality = gr.Button("🖥️ Desktop", variant="secondary") 
                        openai_high_quality = gr.Button("🎧 High Quality", variant="primary")
                        openai_max_quality = gr.Button("💎 Maximum Quality", variant="primary")
                    
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

                # === PIPER AUDIO QUALITY CONTROLS ===
                with gr.Accordion("🎵 Audio Quality Control", open=False):
                    gr.Markdown("### Presets de Calidad Rápida")
                    with gr.Row(equal_height=True):
                        piper_mobile_quality = gr.Button("📱 Mobile (Fast)", variant="secondary")
                        piper_desktop_quality = gr.Button("🖥️ Desktop", variant="secondary") 
                        piper_high_quality = gr.Button("🎧 High Quality", variant="primary")
                        piper_max_quality = gr.Button("💎 Maximum Quality", variant="primary")
                    
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
                coqui_model_info = gr.Markdown("**📋 Model Information:** Select a model to see details")
                
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
                        gr.Markdown("**Optimized settings for audiobooks:**")
                    
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
                
                # === AUDIO QUALITY CONTROLS ===
                with gr.Accordion("🎚️ Audio Quality Configuration", open=False):
                    gr.Markdown("**🎵 Control the generated audio quality - Higher quality = larger files**")
                    
                    # Presets de calidad
                    with gr.Row(equal_height=True):
                        preset_quality_mobile = gr.Button("📱 Mobile/Podcast", variant="secondary", size="sm")
                        preset_quality_desktop = gr.Button("🖥️ Desktop", variant="secondary", size="sm")
                        preset_quality_high = gr.Button("🎧 High Quality", variant="primary", size="sm")
                        preset_quality_max = gr.Button("💿 Maximum Quality", variant="secondary", size="sm")
                    
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
                            label="🛡️ Enable Limiter",
                            info="Prevents distortion at high peaks"
                        )
                
                # Advanced settings
                with gr.Accordion("🔧 Advanced Settings", open=False):
                    with gr.Row():
                        coqui_path = gr.Textbox(
                            label="📁 Custom Models Directory (optional)",
                            value="",
                            interactive=True,
                            placeholder="Ej: C:/modelos_coqui/"
                        )
                    
                    with gr.Row():
                        gr.Markdown("**🎯 Recommendations for Audiobooks:**")
                    
                    with gr.Column():
                        gr.Markdown("""
                        **📚 Best Models:**
                        - **XTTS-v2**: Maximum quality, voice cloning, 17 languages
                        - **tts_models/es/css10/vits**: Spanish specific, good quality
                        - **tts_models/es/mai/tacotron2-DDC**: Classic, very stable
                        
                        **🎤 Best Voices:**
                        - Ana Florence, Sofia Hellen, Tanja Adelina (female)
                        - Andrew Chipper, Dionisio Schuyler (male)
                        
                        **⚡ GPU:** Highly recommended for XTTS-v2 (10x faster)
                        """)
                
                # Presets for different content types
                with gr.Accordion("🎭 Presets for Different Styles", open=False):
                    with gr.Row(equal_height=True):
                        preset_audiolibro = gr.Button("📖 Narrative Audiobook", variant="secondary")
                        preset_educativo = gr.Button("🎓 Educational Content", variant="secondary")
                        preset_dramatico = gr.Button("🎭 Dramatic Reading", variant="secondary")
                        preset_noticias = gr.Button("📰 News Style", variant="secondary")

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
                    # Standard voice selector (restored original)
                    kokoro_voice = get_kokoro_voices_gui(
                        os.environ.get('OPENAI_BASE_URL', 'http://localhost:8880').replace('/v1', ''), 
                        ""
                    )
                    
                    # Advanced Voice Mixer (collapsible section)
                    with gr.Accordion("�️ Mezclador Avanzado de Voces", open=False):
                        gr.Markdown("**Mezcla múltiples voces para crear sonidos únicos**")
                        
                        with gr.Row():
                            with gr.Column(scale=3):
                                # Search and multi-select interface
                                voice_search_input = gr.Textbox(
                                    label="Buscar Voces",
                                    placeholder="Escribe para buscar voces...",
                                    interactive=True
                                )
                                
                                available_voices_for_mixing = gr.CheckboxGroup(
                                    choices=fetch_kokoro_voices(),
                                    label="Voces Disponibles",
                                    info="Selecciona múltiples voces para mezclar",
                                    interactive=True,
                                    visible=True
                                )
                            
                            with gr.Column(scale=2):
                                gr.Markdown("**Presets Guardados**")
                                preset_dropdown = gr.Dropdown(
                                    choices=list(load_voice_presets().keys()),
                                    label="Cargar Preset",
                                    interactive=True,
                                    allow_custom_value=False
                                )
                                
                                with gr.Row():
                                    load_preset_btn = gr.Button("📁 Cargar", size="sm")
                                    clear_selection_btn = gr.Button("🗑️ Limpiar", size="sm")
                                
                                gr.Markdown("**Guardar Combinación**")
                                preset_name_input = gr.Textbox(
                                    label="Nombre",
                                    placeholder="Ej: Narrador Épico",
                                    lines=1
                                )
                                save_preset_btn = gr.Button("💾 Guardar", size="sm")
                        
                        # Selected voices display with weight controls
                        selected_voices_display = gr.HTML(
                            value="<p style='color: #666; font-style: italic;'>No hay voces seleccionadas para mezclar</p>",
                            label="Voces Seleccionadas para Mezcla"
                        )
                        
                        # Apply mixed voice button
                        with gr.Row():
                            apply_mix_btn = gr.Button("🔀 Aplicar Mezcla al Campo Principal", size="sm", variant="primary")
                            mix_status = gr.Textbox(
                                label="Estado",
                                interactive=False,
                                visible=True,
                                max_lines=1
                            )
                    
                    # Hidden JSON for voice configuration
                    voice_weights_config = gr.JSON(
                        value=[],
                        visible=False
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

                # === KOKORO AUDIO QUALITY CONTROLS ===
                with gr.Accordion("🎵 Audio Quality Control", open=False):
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

                # === FUNCIONALIDADES AVANZADAS KOKORO ===
                with gr.Accordion("🚀 Funcionalidades Avanzadas", open=False):
                    gr.Markdown("### Control de Audio")
                    with gr.Row(equal_height=True):
                        kokoro_volume_multiplier = gr.Slider(
                            minimum=0.1,
                            maximum=2.0,
                            step=0.1,
                            value=1.0,
                            label="Multiplicador de Volumen",
                            info="Ajustar volumen de salida (1.0 = normal)"
                        )
                        kokoro_stream = gr.Checkbox(
                            value=True,
                            label="Modo Streaming",
                            info="Generar audio en tiempo real (más rápido)"
                        )
                        
                    with gr.Row(equal_height=True):
                        kokoro_return_timestamps = gr.Checkbox(
                            value=False,
                            label="Incluir Timestamps",
                            info="Generar marcas de tiempo por palabras"
                        )
                        kokoro_return_download_link = gr.Checkbox(
                            value=False,
                            label="Enlace de Descarga",
                            info="Crear enlace de descarga adicional"
                        )
                    
                    gr.Markdown("### Text Normalization")
                    with gr.Row(equal_height=True):
                        kokoro_normalize = gr.Checkbox(
                            value=True,
                            label="General Normalization",
                            info="Process text for better pronunciation"
                        )
                        kokoro_unit_normalization = gr.Checkbox(
                            value=False,
                            label="Unit Normalization",
                            info="10KB → 10 kilobytes"
                        )
                        kokoro_url_normalization = gr.Checkbox(
                            value=True,
                            label="URL Normalization",
                            info="Make URLs pronounceable"
                        )
                    
                    with gr.Row(equal_height=True):
                        kokoro_email_normalization = gr.Checkbox(
                            value=True,
                            label="Email Normalization",
                            info="Make emails pronounceable"
                        )
                        kokoro_pluralization_normalization = gr.Checkbox(
                            value=True,
                            label="Plural Normalization",
                            info="(s) → s for better pronunciation"
                        )
                        kokoro_phone_normalization = gr.Checkbox(
                            value=True,
                            label="Phone Normalization",
                            info="Make phone numbers pronounceable"
                        )
                    
                    with gr.Row(equal_height=True):
                        kokoro_replace_symbols = gr.Checkbox(
                            value=True,
                            label="Replace Symbols",
                            info="Convert remaining symbols to words"
                        )
                    
                    gr.Markdown("### Voice Mixing")
                    with gr.Row(equal_height=True):
                        kokoro_voice_weight_normalization = gr.Checkbox(
                            value=True,
                            label="Weight Normalization",
                            info="Automatically normalize weights of combined voices"
                        )
                    
                    gr.Markdown("### 🎛️ Voice Combination Tester")
                    gr.Markdown("**Select multiple voices and adjust their weights to create unique combinations**")
                    
                    with gr.Row():
                        with gr.Column(scale=2):
                            # Multi-voice selector for testing
                            test_voices_selector = gr.CheckboxGroup(
                                choices=fetch_kokoro_voices(),
                                label="Select Voices to Test",
                                info="Choose multiple voices (up to 6 recommended)",
                                interactive=True
                            )
                        
                        with gr.Column(scale=1):
                            gr.Markdown("**JSON Configuration**")
                            with gr.Row():
                                export_config_btn = gr.Button("📤 Export Config", size="sm")
                                import_config_btn = gr.Button("📥 Import Config", size="sm")
                            
                            config_file_input = gr.File(
                                label="Configuration File",
                                file_types=[".json"],
                                visible=False
                            )
                            
                            config_status = gr.Textbox(
                                label="Export Status",
                                value="",
                                visible=False,
                                interactive=False
                            )
                    
                    # Dynamic weight controls for selected test voices
                    test_voice_weights_display = gr.HTML(
                        value="<p style='color: #666; font-style: italic;'>Select voices above to adjust their weights</p>",
                        label="Weight Controls"
                    )
                    
                    # Generated combination preview
                    with gr.Row(equal_height=True):
                        generated_combination = gr.Textbox(
                            label="Generated Combination",
                            interactive=False,
                            info="Automatically generated based on selected voices and weights"
                        )
                        validate_combination_btn = gr.Button("✅ Validate", size="sm")
                        apply_combination_btn = gr.Button("📋 Apply to Voice Field", size="sm")
                    
                    combination_result = gr.Textbox(
                        label="Validation Result",
                        interactive=False,
                        max_lines=3
                    )
                    
                    # Hidden JSON for test voice weights
                    test_voice_weights_json = gr.JSON(
                        value=[],
                        visible=False
                    )
                    
                    gr.Markdown("### Connection Test & Preview")
                    with gr.Row(equal_height=True):
                        test_connection_btn = gr.Button("🔗 Test Connection", size="sm")
                        preview_voice_btn = gr.Button("🎧 Preview Voice", size="sm")
                    
                    # Custom text input for voice preview
                    preview_text_input = gr.Textbox(
                        label="Preview Text (optional)",
                        placeholder="Write the text you want to hear with the selected voice...",
                        lines=2,
                        max_lines=3
                    )
                    
                    connection_status = gr.Textbox(
                        label="Connection Status",
                        interactive=False,
                        max_lines=2
                    )
                    
                    # Audio output for voice preview
                    preview_audio_output = gr.Audio(
                        label="Preview de Voz",
                        interactive=False,
                        visible=True
                    )

                # Test voice selector events
                test_voices_selector.change(
                    fn=update_test_voice_weights_display,
                    inputs=[test_voices_selector],
                    outputs=[test_voice_weights_display, test_voice_weights_json, generated_combination]
                )
                
                # Configuration import/export
                def handle_export_config(voice_configs_json):
                    """Handle export configuration - saves to voice_presets folder"""
                    try:
                        print(f"DEBUG: Received voice_configs_json: {voice_configs_json}")

                        if not voice_configs_json:
                            return "❌ No configuration to export"

                        if isinstance(voice_configs_json, str):
                            payload = voice_configs_json
                        else:
                            payload = json.dumps(voice_configs_json)

                        file_path, message = export_voice_configuration(payload)
                        print(f"DEBUG: Export result - file_path: {file_path}, message: {message}")

                        return message
                    except Exception as e:
                        error_msg = f"❌ Error in handle_export_config: {str(e)}"
                        print(f"DEBUG: {error_msg}")
                        return error_msg
                
                export_config_btn.click(
                    fn=handle_export_config,
                    inputs=[test_voice_weights_json],
                    outputs=[combination_result]
                )
                
                import_config_btn.click(
                    fn=lambda: gr.File(visible=True),
                    outputs=[config_file_input]
                )
                
                config_file_input.change(
                    fn=import_voice_configuration,
                    inputs=[config_file_input],
                    outputs=[test_voices_selector, test_voice_weights_display, test_voice_weights_json, generated_combination]
                )
                
                # Connect advanced Kokoro functions
                validate_combination_btn.click(
                    fn=lambda combo, url: validate_voice_combination(combo, url)[1],
                    inputs=[generated_combination, kokoro_base_url],
                    outputs=combination_result
                )
                
                def apply_voice_combination(combo):
                    """Apply validated combination to main voice field"""
                    if not combo or combo.strip() == "":
                        return gr.update(), "❌ No hay combinación para aplicar"
                    
                    is_valid, message = validate_voice_combination(combo, "http://localhost:8880")
                    if is_valid:
                        return combo, f"✅ Applied: {combo}"
                    else:
                        return gr.update(), f"❌ Invalid combination: {message}"
                
                apply_combination_btn.click(
                    fn=apply_voice_combination,
                    inputs=[generated_combination],
                    outputs=[kokoro_voice, combination_result]
                )
                
                test_connection_btn.click(
                    fn=lambda url: test_kokoro_connection(url)[1],
                    inputs=[kokoro_base_url],
                    outputs=connection_status
                )
                
                def handle_voice_preview(voice, lang_name, custom_text, url):
                    success, message, audio_file = preview_voice_with_language(voice, lang_name, custom_text, url)
                    return message, audio_file if success else None
                
                preview_voice_btn.click(
                    fn=handle_voice_preview,
                    inputs=[kokoro_voice, kokoro_language, preview_text_input, kokoro_base_url],
                    outputs=[connection_status, preview_audio_output]
                )
                
                # Voice search filtering
                voice_search_input.change(
                    fn=filter_voices_by_search,
                    inputs=[voice_search_input],
                    outputs=[available_voices_for_mixing]
                )
                
                # Advanced Voice Mixer Events
                available_voices_for_mixing.change(
                    fn=update_selected_voices_display,
                    inputs=[available_voices_for_mixing],
                    outputs=[selected_voices_display, voice_weights_config]
                )
                
                # Clear selection
                clear_selection_btn.click(
                    fn=clear_voice_selection,
                    outputs=[available_voices_for_mixing, selected_voices_display, voice_weights_config, mix_status]
                )
                
                # Apply mix to main voice field
                apply_mix_btn.click(
                    fn=apply_voice_mix_to_main,
                    inputs=[voice_weights_config, kokoro_voice],
                    outputs=[kokoro_voice, mix_status]
                )
                
                # Load preset functionality
                load_preset_btn.click(
                    fn=lambda preset_name: load_preset_combination(preset_name, load_voice_presets()),
                    inputs=[preset_dropdown],
                    outputs=[kokoro_voice, mix_status]
                )
                
                # Save preset functionality
                save_preset_btn.click(
                    fn=save_current_preset,
                    inputs=[preset_name_input, kokoro_voice],
                    outputs=[mix_status]
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
                    # Kokoro advanced features
                    kokoro_volume_multiplier, kokoro_stream, kokoro_return_timestamps, kokoro_return_download_link,
                    # Kokoro normalization options
                    kokoro_normalize, kokoro_unit_normalization, kokoro_url_normalization, kokoro_email_normalization, 
                    kokoro_pluralization_normalization, kokoro_phone_normalization, kokoro_replace_symbols,
                    # Kokoro voice mixing
                    kokoro_voice_weight_normalization,
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

    ui.launch(
        server_name=config.host, 
        server_port=config.port, 
        inbrowser=True,
        show_error=True,
        quiet=False,
        share=False
    )