#!/usr/bin/env python3
"""
Test para verificar que XTTS-v2 aparece en los modelos de español
"""

# Fix para PyTorch 2.6+ - weights_only=False por defecto
import torch
import os
_original_torch_load = torch.load

def custom_torch_load(*args, **kwargs):
    if "weights_only" not in kwargs:
        kwargs["weights_only"] = False
    return _original_torch_load(*args, **kwargs)

torch.load = custom_torch_load
os.environ["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"] = "1"

# Import the function
from audiobook_generator.tts_providers.coqui_tts_provider import get_coqui_models_by_language

def test_spanish_models():
    """Test que XTTS-v2 aparece en los modelos de español"""
    print("🧪 Probando modelos disponibles para español...")
    
    spanish_models = get_coqui_models_by_language("es")
    
    print(f"📝 Total de modelos para español: {len(spanish_models)}")
    print("\n🎯 Modelos encontrados:")
    
    for i, model in enumerate(spanish_models[:10]):  # Show first 10
        if "xtts" in model.lower():
            print(f"  {i+1}. ✅ {model} (XTTS ENCONTRADO!)")
        elif "/es/" in model:
            print(f"  {i+1}. 🇪🇸 {model}")
        else:
            print(f"  {i+1}. 🌍 {model}")
    
    if len(spanish_models) > 10:
        print(f"     ... y {len(spanish_models) - 10} modelos más")
    
    # Check if XTTS-v2 is included
    xtts_v2_found = any("xtts_v2" in model for model in spanish_models)
    
    if xtts_v2_found:
        print("\n🎉 ¡ÉXITO! XTTS-v2 está disponible en los modelos de español")
        
        # Check if it's the first option
        if spanish_models and "xtts_v2" in spanish_models[0]:
            print("✅ XTTS-v2 está como primera opción (perfecto)")
        else:
            print(f"⚠️ XTTS-v2 está en posición: {[i for i, m in enumerate(spanish_models) if 'xtts_v2' in m][0] + 1}")
    else:
        print("\n❌ ERROR: XTTS-v2 NO encontrado en los modelos de español")
    
    return xtts_v2_found

if __name__ == "__main__":
    print("🔧 Test de disponibilidad de XTTS-v2 en español\n")
    success = test_spanish_models()
    
    if success:
        print("\n✅ Todo correcto - XTTS-v2 debería aparecer en la interfaz")
    else:
        print("\n❌ Problema - XTTS-v2 no está disponible")