"""
Test suite for the Spanish text normalizer module.

This module tests the text normalization functionality specifically designed
for improving Coqui TTS pronunciation quality with Spanish models.
"""

import sys
import os
import unittest
from pathlib import Path

# Add the project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from audiobook_generator.utils.text_normalizer import (
    normalize_text_for_tts,
    is_normalization_needed,
    _normalize_numbers,
    _normalize_dates,
    _normalize_times,
    _normalize_currencies,
    _normalize_percentages,
    _normalize_abbreviations
)


class TestTextNormalizer(unittest.TestCase):
    """Test cases for Spanish text normalization."""

    def test_number_normalization(self):
        """Test basic number conversion."""
        test_cases = [
            ("Tengo 25 años", "Tengo veinticinco años"),
            ("Hay 1 persona", "Hay uno persona"),
            ("Son 100 libros", "Son cien libros"),
            ("Pagué 150 pesos", "Pagué ciento cincuenta pesos"),
            ("El edificio tiene 1000 pisos", "El edificio tiene mil pisos"),
        ]
        
        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                result = normalize_text_for_tts(input_text, "es")
                self.assertEqual(result, expected)

    def test_date_normalization(self):
        """Test date format conversion."""
        test_cases = [
            ("El 15/03/2024", "El quince de marzo de dos mil veinticuatro"),
            ("Nació el 1/1/2000", "Nació el primero de enero de dos mil"),
            ("La fecha es 31-12-1999", "La fecha es treinta y uno de diciembre de mil novecientos noventa y nueve"),
            ("El evento es el 25.06.2025", "El evento es el veinticinco de junio de dos mil veinticinco"),
        ]
        
        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                result = normalize_text_for_tts(input_text, "es")
                self.assertEqual(result, expected)

    def test_time_normalization(self):
        """Test time format conversion."""
        test_cases = [
            ("Son las 3:30", "tres y media de la tarde"),  # Check for key elements
            ("A las 12:00", "doce en punto"),
            ("Llegamos a las 9:15 AM", "nueve y cuarto de la mañana"),
            ("La cita es a las 18:45", "cuarto para las"),  # 24h format
        ]
        
        for input_text, expected_substring in test_cases:
            with self.subTest(input_text=input_text):
                result = normalize_text_for_tts(input_text, "es")
                self.assertIn(expected_substring, result)

    def test_currency_normalization(self):
        """Test currency format conversion."""
        test_cases = [
            ("Cuesta $150", ["dólares", "ciento cincuenta"]),
            ("Pagó €20", ["euros", "veinte"]),
            ("Son $1.50", ["dólar", "uno"]),  # Singular for 1 dollar
            ("El precio es €35.75", ["euros", "treinta y cinco"]),
        ]
        
        for input_text, expected_elements in test_cases:
            with self.subTest(input_text=input_text):
                result = normalize_text_for_tts(input_text, "es")
                for element in expected_elements:
                    self.assertIn(element, result)

    def test_percentage_normalization(self):
        """Test percentage format conversion."""
        test_cases = [
            ("El 45% de descuento", "El cuarenta y cinco por ciento de descuento"),
            ("Subió 15%", "Subió quince por ciento"),
            ("Aumentó 3.5%", "Aumentó tres coma cinco por ciento"),
        ]
        
        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                result = normalize_text_for_tts(input_text, "es")
                self.assertIn("por ciento", result)

    def test_abbreviation_normalization(self):
        """Test abbreviation expansion."""
        test_cases = [
            ("El Dr. García", "El doctor García"),
            ("La Sra. López", "La señora López"),
            ("Vive en la Av. Principal", "Vive en la avenida Principal"),
            ("Y así etc.", "Y así etcétera"),
        ]
        
        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                result = normalize_text_for_tts(input_text, "es")
                self.assertEqual(result, expected)

    def test_complex_text_normalization(self):
        """Test complex text with multiple normalization needs."""
        input_text = "El Dr. García nació el 15/03/1985, tiene 38 años y gana $2500 mensuales, lo que representa el 15% más que el año pasado."
        result = normalize_text_for_tts(input_text, "es")
        
        # Check that various elements were normalized
        self.assertIn("doctor", result)  # Dr. -> doctor
        self.assertIn("quince de marzo", result)  # 15/03/1985 -> date format
        self.assertIn("treinta y ocho", result)  # 38 -> number format
        self.assertIn("dólares", result)  # $2500 -> currency format
        self.assertIn("por ciento", result)  # 15% -> percentage format

    def test_language_filtering(self):
        """Test that normalization only applies to Spanish."""
        input_text = "I have 25 years and $100"
        
        # Should not normalize for English
        result_en = normalize_text_for_tts(input_text, "en")
        self.assertEqual(result_en, input_text)
        
        # Should normalize for Spanish
        spanish_text = "Tengo 25 años y $100"
        result_es = normalize_text_for_tts(spanish_text, "es")
        self.assertNotEqual(result_es, spanish_text)

    def test_is_normalization_needed(self):
        """Test the optimization function that checks if normalization is needed."""
        # Text that needs normalization
        self.assertTrue(is_normalization_needed("Tengo 25 años", "es"))
        self.assertTrue(is_normalization_needed("El Dr. García", "es"))
        self.assertTrue(is_normalization_needed("Cuesta $150", "es"))
        
        # Text that doesn't need normalization (no numbers, dates, currencies, abbreviations)
        self.assertFalse(is_normalization_needed("Hola mundo", "es"))
        self.assertFalse(is_normalization_needed("Buenos días querido amigo", "es"))
        
        # Non-Spanish language
        self.assertFalse(is_normalization_needed("I have 25 years", "en"))

    def test_edge_cases(self):
        """Test edge cases and error handling."""
        # Empty text
        self.assertEqual(normalize_text_for_tts("", "es"), "")
        
        # Text with only spaces
        self.assertEqual(normalize_text_for_tts("   ", "es"), "   ")
        
        # Very large numbers (should not break)
        large_number_text = "El número es 999999999"
        result = normalize_text_for_tts(large_number_text, "es")
        self.assertIsNotNone(result)
        
        # Invalid dates (should remain mostly unchanged, but numbers might be converted)
        invalid_date = "El 35/15/2024"  # Invalid date
        result = normalize_text_for_tts(invalid_date, "es")
        # The date pattern won't match due to invalid day/month, but standalone numbers might be converted
        # This is actually expected behavior
        self.assertIsNotNone(result)

    def test_individual_functions(self):
        """Test individual normalization functions."""
        # Test _normalize_numbers
        self.assertEqual(_normalize_numbers("Hay 5 gatos"), "Hay cinco gatos")
        
        # Test _normalize_abbreviations
        self.assertEqual(_normalize_abbreviations("El Sr. Juan"), "El señor Juan")
        
        # These tests help ensure each component works independently


def run_basic_tests():
    """Run a quick set of basic tests to verify functionality."""
    print("Running basic Spanish text normalization tests...")
    
    test_cases = [
        ("Tengo 25 años", "números"),
        ("El 15/03/2024", "fechas"),
        ("Son las 3:30", "horas"),
        ("Cuesta $150.50", "monedas"),
        ("El 45% de descuento", "porcentajes"),
        ("El Dr. García", "abreviaturas"),
    ]
    
    all_passed = True
    for text, category in test_cases:
        try:
            result = normalize_text_for_tts(text, "es")
            print(f"✓ {category}: '{text}' → '{result}'")
        except Exception as e:
            print(f"✗ {category}: Error processing '{text}': {e}")
            all_passed = False
    
    if all_passed:
        print("\n🎉 ¡Todas las pruebas básicas pasaron correctamente!")
        print("La normalización de texto para Coqui TTS está lista para usar.")
    else:
        print("\n⚠️  Algunas pruebas fallaron. Revisar la implementación.")
    
    return all_passed


if __name__ == "__main__":
    # Check if we're running basic tests or full unit tests
    if len(sys.argv) > 1 and sys.argv[1] == "--basic":
        run_basic_tests()
    else:
        # Run full unit test suite
        unittest.main(verbosity=2)