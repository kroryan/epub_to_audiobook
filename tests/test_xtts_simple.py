#!/usr/bin/env python3
"""
Test simple de XTTS-v2 con el fix de PyTorch
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

def test_xtts_simple():
    """Test simple de XTTS-v2"""
    try:
        print("🎯 Probando XTTS-v2 simple...")
        
        from TTS.api import TTS
        
        # Cargar modelo
        tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)
        print("✅ Modelo XTTS-v2 cargado correctamente!")
        
        # Información básica
        print(f"✅ Multilingüe: {tts.is_multi_lingual}")
        print(f"✅ Multispeaker: {tts.is_multi_speaker}")
        
        if tts.is_multi_lingual and hasattr(tts, 'languages'):
            print(f"🌍 Idiomas: {tts.languages}")
        
        # Test de síntesis simple
        texto = "Hola, esto es una prueba de XTTS-v2 en español."
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            output_file = tmp.name
        
        print("🗣️ Generando audio...")
        
        # Síntesis básica
        tts.tts_to_file(
            text=texto,
            file_path=output_file,
            language="es"
        )
        
        # Verificar resultado
        if os.path.exists(output_file):
            size = os.path.getsize(output_file)
            print(f"✅ ¡ÉXITO! Audio generado: {size} bytes")
            os.unlink(output_file)
            return True
        else:
            print("❌ No se generó el archivo")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Test simple XTTS-v2 con fix PyTorch\n")
    
    success = test_xtts_simple()
    
    if success:
        print("\n🎉 ¡XTTS-v2 FUNCIONA CORRECTAMENTE!")
        print("💡 El fix de PyTorch resolvió el problema.")
    else:
        print("\n❌ XTTS-v2 aún tiene problemas.")