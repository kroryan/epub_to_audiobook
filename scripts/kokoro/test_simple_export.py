#!/usr/bin/env python3
"""
Simple test script for voice export function
"""

import json
import os
from datetime import datetime

def simple_export_test():
    """Test the core export logic"""
    
    # Test voice configuration
    voice_configs_json = '[{"voice": "am_adam", "weight": 1.0, "index": 0}, {"voice": "af_bella", "weight": 0.5, "index": 1}]'
    
    try:
        if not voice_configs_json or voice_configs_json == "[]":
            print("❌ No configuration to export")
            return
        
        voice_configs = json.loads(voice_configs_json)
        if not voice_configs:
            print("❌ No voice configuration found")
            return
        
        # Create export data
        export_data = {
            "name": f"Voice_Combination_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "created": datetime.now().isoformat(),
            "voices": voice_configs,
            "combination_string": "am_adam+af_bella(0.5)",
            "version": "1.0",
            "description": f"Combinación de {len(voice_configs)} voces"
        }
        
        # Save to voice_presets directory
        presets_dir = os.path.join('..', '..', 'voice_presets')
        presets_dir = os.path.abspath(presets_dir)
        os.makedirs(presets_dir, exist_ok=True)
        
        filename = f"voice_combination_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        file_path = os.path.join(presets_dir, filename)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Configuration saved: {filename} ({len(voice_configs)} voices)")
        print(f"File path: {file_path}")
        print(f"Export data: {json.dumps(export_data, indent=2)}")
        
    except Exception as e:
        print(f"❌ Error in export: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Testing simple export function...")
    simple_export_test()
    print("\nTest completed!")