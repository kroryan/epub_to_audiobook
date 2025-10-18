#!/usr/bin/env python3
"""
Test completo de XTTS-v2 con speaker
"""
import os
import tempfile

# Fix para PyTorch 2.6+ - weights_only=False por defecto
import torch
_original_torch_load = torch.load

def custom_torch_load(*args, **kwargs):
    if "weights_only" not in kwargs:
        kwargs["weights_only"] = False
    return _original_torch_load(*args, **kwargs)

torch.load = custom_torch_load
os.environ["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"] = "1"

def test_xtts_with_speaker():
    """Test XTTS-v2 con speaker específico"""
    try:
        print("🎯 Probando XTTS-v2 con speaker...")
        
        from TTS.api import TTS
        
        # Cargar modelo
        tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)
        print("✅ Modelo XTTS-v2 cargado correctamente!")
        
        # Información básica
        print(f"✅ Multilingüe: {tts.is_multi_lingual}")
        print(f"✅ Multispeaker: {tts.is_multi_speaker}")
        print(f"🌍 Idiomas: {tts.languages}")
        
        # Test de síntesis con speaker
        texto = "Hola, esto es una prueba de XTTS-v2 en español con clonación de voz."
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            output_file = tmp.name
        
        print("🗣️ Generando audio con speaker predefinido...")
        
        # Lista de speakers comunes en XTTS-v2
        test_speakers = [
            "Claribel Dervla", "Daisy Studious", "Gracie Wise", 
            "Ana Florence", "Sofia Hellen", "Tammie Ema"
        ]
        
        # Probar con el primer speaker disponible
        speaker = test_speakers[0]  # "Claribel Dervla"
        
        # Síntesis con speaker
        tts.tts_to_file(
            text=texto,
            file_path=output_file,
            language="es",
            speaker=speaker
        )
        
        # Verificar resultado
        if os.path.exists(output_file):
            size = os.path.getsize(output_file)
            print(f"✅ ¡ÉXITO! Audio generado: {size} bytes")
            print(f"🎤 Usando speaker: {speaker}")
            os.unlink(output_file)
            return True
        else:
            print("❌ No se generó el archivo")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 Test XTTS-v2 con speaker\n")
    
    success = test_xtts_with_speaker()
    
    if success:
        print("\n🎉 ¡XTTS-v2 FUNCIONA PERFECTAMENTE!")
        print("💡 El fix de PyTorch + speaker resolvió todos los problemas.")
        print("✨ XTTS-v2 está listo para usar en español!")
    else:
        print("\n❌ XTTS-v2 aún tiene problemas.")