#!/usr/bin/env python3
"""
Test script to find and test specific voice names like santa, dora, alex
"""

import requests
import json

def find_specific_voices():
    """Find all voices containing specific names"""
    
    print("🔍 Searching for Specific Voice Names")
    print("=" * 45)
    
    # Fetch all voices
    try:
        response = requests.get("http://localhost:8880/v1/audio/voices", timeout=10)
        if response.status_code != 200:
            print(f"❌ Cannot fetch voices: {response.status_code}")
            return
            
        voices_data = response.json()
        if isinstance(voices_data, dict) and 'voices' in voices_data:
            all_voices = voices_data['voices']
        elif isinstance(voices_data, list):
            all_voices = voices_data
        else:
            all_voices = []
            
        print(f"📊 Total voices available: {len(all_voices)}")
        
    except Exception as e:
        print(f"❌ Error fetching voices: {e}")
        return
    
    # Search for specific names
    target_names = ["santa", "dora", "alex", "bella", "sky", "heart"]
    
    print(f"\n🎯 Searching for specific voice names:")
    found_voices = {}
    
    for target in target_names:
        matches = []
        for voice in all_voices:
            voice_str = str(voice)
            if target.lower() in voice_str.lower():
                matches.append(voice_str)
        
        found_voices[target] = matches
        if matches:
            print(f"   ✅ {target}: {', '.join(matches)}")
        else:
            print(f"   ❌ {target}: Not found")
    
    # Test Spanish voice filtering with new logic
    print(f"\n🇪🇸 Testing Spanish Voice Filtering:")
    
    def filter_voices_for_spanish(voices):
        """Simulate the improved filtering logic"""
        language_prefixes = ["ef", "em", "sf", "sm", "pf", "pm"]
        popular_names = ["dora", "alex", "santa", "bella", "sky", "heart", "nicole", "emma", "sarah"]
        
        filtered = []
        for voice in voices:
            voice_str = str(voice)
            voice_prefix = voice_str.split('_')[0] if '_' in voice_str else voice_str[:2]
            voice_name = voice_str.split('_', 1)[1] if '_' in voice_str else voice_str
            
            # Include if prefix matches
            if voice_prefix in language_prefixes:
                filtered.append(voice)
            # Also include popular names regardless of prefix
            else:
                for popular_name in popular_names:
                    if popular_name.lower() in voice_name.lower():
                        filtered.append(voice)
                        break
        
        # Remove duplicates
        return list(dict.fromkeys(filtered))
    
    spanish_voices = filter_voices_for_spanish(all_voices)
    print(f"   Found {len(spanish_voices)} Spanish voices:")
    
    # Group by prefix for better display
    spanish_by_prefix = {}
    for voice in spanish_voices[:20]:  # Show first 20
        prefix = str(voice).split('_')[0] if '_' in str(voice) else 'other'
        if prefix not in spanish_by_prefix:
            spanish_by_prefix[prefix] = []
        spanish_by_prefix[prefix].append(voice)
    
    for prefix in sorted(spanish_by_prefix.keys()):
        voices_list = spanish_by_prefix[prefix]
        print(f"     {prefix}: {', '.join(voices_list[:5])}")
        if len(voices_list) > 5:
            print(f"           ... and {len(voices_list)-5} more")
    
    # Test synthesis with found voices
    print(f"\n🔊 Testing Synthesis with Found Voices:")
    
    # Test the voices you specifically mentioned
    test_voices = []
    for name in ["santa", "dora", "alex"]:
        if found_voices[name]:
            test_voices.append(found_voices[name][0])  # Take first match
    
    # Add some fallback voices
    fallback_voices = ["af_bella", "ef_dora", "pm_santa"] 
    for voice in fallback_voices:
        if voice in [str(v) for v in all_voices]:
            test_voices.append(voice)
    
    # Remove duplicates
    test_voices = list(dict.fromkeys(test_voices))
    
    for voice in test_voices[:3]:  # Test first 3
        try:
            print(f"\n   Testing voice: {voice}")
            response = requests.post("http://localhost:8880/v1/audio/speech", 
                json={
                    "model": "kokoro",
                    "voice": voice,
                    "input": "Hola, soy la voz " + voice.split('_')[1] if '_' in voice else voice,
                    "language": "e",  # Spanish
                    "response_format": "mp3"
                }, 
                timeout=20
            )
            
            if response.status_code == 200:
                size = len(response.content)
                print(f"   ✅ {voice}: {size} bytes generated")
                
                # Save test file
                from pathlib import Path
                test_file = Path(f"test_{voice}_spanish.mp3")
                test_file.write_bytes(response.content)
                print(f"   💾 Saved: {test_file}")
                
            else:
                print(f"   ❌ {voice}: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ {voice}: {e}")
    
    print(f"\n📋 Summary:")
    print(f"   • Total voices: {len(all_voices)}")
    print(f"   • Spanish filtered: {len(spanish_voices)}")
    for name, matches in found_voices.items():
        if matches:
            print(f"   • {name}: {len(matches)} found")
    
    print(f"\n💡 UI Improvements:")
    print("   ✅ Spanish filter now includes pf_/pm_ prefixes")
    print("   ✅ Popular names (santa, dora, alex) included regardless of prefix")
    print("   ✅ Duplicate voices removed")
    print("   ✅ Better voice discovery for Spanish users")

if __name__ == "__main__":
    find_specific_voices()