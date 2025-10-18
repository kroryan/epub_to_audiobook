#!/usr/bin/env python3
"""
Test script para probar XTTS-v2 con el fix para PyTorch 2.6+
"""
import os
import sys
import tempfile
import logging

# Fix para PyTorch 2.6+ - weights_only=False por defecto
import torch
_original_torch_load = torch.load

def custom_torch_load(*args, **kwargs):
    """Custom torch.load que fuerza weights_only=False para compatibilidad con TTS"""
    if "weights_only" not in kwargs:
        kwargs["weights_only"] = False
    return _original_torch_load(*args, **kwargs)

# Sobrescribir globalmente para TTS
torch.load = custom_torch_load

# También establecer variable de entorno como respaldo
os.environ["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"] = "1"

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_xtts_spanish_fixed():
    """Prueba XTTS-v2 con texto en español usando el fix de PyTorch"""
    try:
        print("🎯 Probando XTTS-v2 con español (con fix PyTorch)...")
        
        # Importar TTS después del fix
        from TTS.api import TTS
        
        # Crear modelo XTTS-v2
        print("📥 Cargando modelo XTTS-v2...")
        tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)
        
        # Verificar que es multilingüe
        print(f"✅ Modelo multilingüe: {tts.is_multi_lingual}")
        print(f"✅ Modelo multispeaker: {tts.is_multi_speaker}")
        
        # Mostrar idiomas soportados
        if tts.is_multi_lingual:
            print(f"🌍 Idiomas soportados: {tts.languages}")
            
            # Verificar que español está incluido
            if 'es' in tts.languages:
                print("✅ ¡Español confirmado en los idiomas soportados!")
            else:
                print("❌ Español no encontrado en idiomas soportados")
                return False
        
        # Mostrar voces disponibles
        if tts.is_multi_speaker:
            print(f"🎤 Voces disponibles: {len(tts.speakers)} voces")
            print(f"🎤 Primeras 5 voces: {tts.speakers[:5] if tts.speakers else 'Ninguna'}")
        
        # Texto de prueba en español
        texto_español = "Hola, este es un test de síntesis de voz en español usando XTTS-v2 con el fix de PyTorch. ¿Funciona correctamente ahora?"
        
        # Archivo de salida temporal
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            output_file = tmp_file.name
        
        print("🗣️ Generando audio en español...")
        
        # Parámetros para XTTS-v2 en español
        synthesis_params = {
            "text": texto_español,
            "file_path": output_file,
            "language": "es",  # ¡Importante: especificar idioma!
        }
        
        # Si hay voces disponibles, usar una
        if tts.is_multi_speaker and tts.speakers:
            # Usar una voz que suene bien para español
            spanish_voices = ["Ana Florence", "Sofia Hellen", "Gracie Wise"]
            selected_voice = None
            
            for voice in spanish_voices:
                if voice in tts.speakers:
                    selected_voice = voice
                    break
            
            if not selected_voice and tts.speakers:
                selected_voice = tts.speakers[0]  # Usar la primera voz disponible
            
            if selected_voice:
                synthesis_params["speaker"] = selected_voice
                print(f"🎤 Usando voz: {selected_voice}")
        
        # Generar el audio
        tts.tts_to_file(**synthesis_params)
        
        # Verificar que el archivo se creó
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            print(f"✅ Audio generado exitosamente: {output_file}")
            print(f"📁 Tamaño del archivo: {file_size} bytes")
            
            # Limpiar archivo temporal
            os.unlink(output_file)
            return True
        else:
            print("❌ No se pudo generar el archivo de audio")
            return False
            
    except Exception as e:
        print(f"❌ Error probando XTTS-v2: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_css10_spanish():
    """Prueba modelo CSS10 español como comparación"""
    try:
        print("\n🎯 Probando modelo CSS10 español...")
        
        from TTS.api import TTS
        
        # Crear modelo CSS10 español
        print("📥 Cargando modelo CSS10 español...")
        tts = TTS("tts_models/es/css10/vits", gpu=False)
        
        print(f"✅ Modelo multilingüe: {tts.is_multi_lingual}")
        print(f"✅ Modelo multispeaker: {tts.is_multi_speaker}")
        
        # Texto de prueba
        texto = "Esta es una prueba del modelo CSS10 en español para comparar con XTTS-v2."
        
        # Archivo temporal
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            output_file = tmp_file.name
        
        print("🗣️ Generando audio con CSS10...")
        
        # Generar audio (CSS10 no necesita parámetros de idioma)
        tts.tts_to_file(text=texto, file_path=output_file)
        
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            print(f"✅ CSS10 generado exitosamente: {file_size} bytes")
            os.unlink(output_file)
            return True
        else:
            print("❌ CSS10 falló")
            return False
            
    except Exception as e:
        print(f"❌ Error con CSS10: {e}")
        return False

def main():
    """Función principal"""
    print("🧪 Test de modelos TTS en español (con fix PyTorch)\n")
    
    # Mostrar información de PyTorch
    print(f"🔧 PyTorch version: {torch.__version__}")
    print(f"🔧 CUDA disponible: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"🔧 CUDA devices: {torch.cuda.device_count()}")
    print()
    
    # Probar XTTS-v2 con fix
    xtts_ok = test_xtts_spanish_fixed()
    
    # Probar CSS10 como comparación
    css10_ok = test_css10_spanish()
    
    print(f"\n📊 Resultados:")
    print(f"   XTTS-v2 (con fix): {'✅ OK' if xtts_ok else '❌ FAIL'}")
    print(f"   CSS10:             {'✅ OK' if css10_ok else '❌ FAIL'}")
    
    if xtts_ok:
        print("\n🎉 ¡XTTS-v2 funciona correctamente en español con el fix de PyTorch!")
        print("💡 El problema estaba en el comportamiento weights_only=True de PyTorch 2.6+.")
    elif css10_ok:
        print("\n⚠️ XTTS-v2 sigue con problemas, pero CSS10 funciona.")
        print("💡 Usar CSS10 como alternativa estable.")
    else:
        print("\n❌ Ambos modelos tienen problemas.")

if __name__ == "__main__":
    main()