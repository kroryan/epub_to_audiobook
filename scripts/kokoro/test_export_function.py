#!/usr/bin/env python3
"""
Test script for voice configuration export function
"""

import sys
import os
import json
from datetime import datetime

# Add the parent directory to sys.path to import modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from audiobook_generator.ui.web_ui import export_voice_configuration, create_multi_voice_combination

def test_export_function():
    """Test the export_voice_configuration function"""
    
    # Create test voice configuration
    test_voices = [
        {
            "voice": "am_adam",
            "weight": 1.0,
            "index": 0
        },
        {
            "voice": "af_bella", 
            "weight": 0.5,
            "index": 1
        }
    ]
    
    voice_configs_json = json.dumps(test_voices)
    
    print(f"Testing export with voice config: {voice_configs_json}")
    
    try:
        # Test the export function
        file_path, message = export_voice_configuration(voice_configs_json)
        print(f"Export result: {message}")
        print(f"File path: {file_path}")
        
        if file_path and os.path.exists(file_path):
            print(f"✅ File created successfully at: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                content = json.load(f)
                print(f"File content: {json.dumps(content, indent=2)}")
        else:
            print("❌ File was not created")
            
    except Exception as e:
        print(f"❌ Error during export: {str(e)}")
        import traceback
        traceback.print_exc()

def test_combination_function():
    """Test the create_multi_voice_combination function"""
    
    test_voices = [
        {
            "voice": "am_adam",
            "weight": 1.0,
            "index": 0
        },
        {
            "voice": "af_bella", 
            "weight": 0.5,
            "index": 1
        }
    ]
    
    voice_configs_json = json.dumps(test_voices)
    
    print(f"\nTesting create_multi_voice_combination with: {voice_configs_json}")
    
    try:
        combination = create_multi_voice_combination(voice_configs_json)
        print(f"✅ Generated combination: {combination}")
    except Exception as e:
        print(f"❌ Error in create_multi_voice_combination: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Testing voice configuration export functions...")
    test_export_function()
    test_combination_function()
    print("\nTest completed!")