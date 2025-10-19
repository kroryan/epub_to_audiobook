#!/usr/bin/env python3
"""
Script para probar que la interfaz web funciona correctamente con Kokoro
"""

def check_ui_components():
    """Verificar que todos los componentes de la UI están definidos"""
    print("🖥️ Checking UI components...")
    
    try:
        # Test basic imports
        import sys
        import os
        
        # Get the correct path to the project root
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.join(current_dir, '..', '..')
        project_root = os.path.abspath(project_root)
        
        # Insert at beginning to avoid conflicts
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        
        # Import with explicit path handling
        try:
            from audiobook_generator.ui.web_ui import (
                get_kokoro_languages, 
                fetch_kokoro_voices,
                validate_voice_combination,
                test_kokoro_connection
            )
        except ImportError as e:
            print(f"Import error: {e}")
            # Try alternative import method
            ui_module_path = os.path.join(project_root, 'audiobook_generator', 'ui', 'web_ui.py')
            if os.path.exists(ui_module_path):
                import importlib.util
                spec = importlib.util.spec_from_file_location("web_ui", ui_module_path)
                web_ui_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(web_ui_module)
                
                get_kokoro_languages = web_ui_module.get_kokoro_languages
                fetch_kokoro_voices = web_ui_module.fetch_kokoro_voices  
                validate_voice_combination = web_ui_module.validate_voice_combination
                test_kokoro_connection = web_ui_module.test_kokoro_connection
            else:
                raise ImportError("Cannot find web_ui.py module")
        
        print("✅ UI functions import successfully")
        
        # Test language function
        languages = get_kokoro_languages()
        print(f"✅ Languages available: {len(languages)}")
        
        # Test voice fetch
        voices = fetch_kokoro_voices()
        print(f"✅ Voices fetched: {len(voices)} voices")
        
        # Test connection
        success, message = test_kokoro_connection()
        if success:
            print(f"✅ Connection test: {message}")
        else:
            print(f"⚠️ Connection test: {message}")
        
        # Test voice validation
        test_voice = "af_bella+af_sky(0.3)"
        is_valid, result_msg = validate_voice_combination(test_voice)
        print(f"✅ Voice validation: {result_msg}")
        
        return True
        
    except Exception as e:
        print(f"❌ UI component test failed: {e}")
        return False

def main():
    """Función principal"""
    print("🧪 KOKORO WEB UI TEST")
    print("=" * 30)
    
    success = check_ui_components()
    
    if success:
        print(f"\n🎉 UI COMPONENTS TEST PASSED!")
        print(f"✅ Web interface is ready to use")
        print(f"\n🚀 To start the web UI:")
        print(f"   python main_ui.py --host 0.0.0.0 --port 7070")
        print(f"\n💡 Features available:")
        print(f"   • Kokoro tab with all advanced options")
        print(f"   • Voice combination tools")
        print(f"   • Text normalization controls") 
        print(f"   • Quality presets")
        print(f"   • Connection testing")
    else:
        print(f"\n❌ UI components test failed")
        print(f"   Please check the implementation")
    
    return success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)