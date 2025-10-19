"""
Text normalizer for TTS providers, specifically designed for Spanish text normalization
to improve pronunciation quality for models like Coqui TTS that require pre-normalized text.

This module converts numbers, dates, times, currencies, percentages, and common abbreviations
into their spoken form in Spanish.
"""

import re
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Spanish months mapping
SPANISH_MONTHS = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio",
    7: "julio", 8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
}

# Spanish abbreviations mapping
SPANISH_ABBREVIATIONS = {
    "Dr.": "doctor", "Dra.": "doctora", "Sr.": "señor", "Sra.": "señora", 
    "Srta.": "señorita", "Prof.": "profesor", "Profa.": "profesora",
    "Ing.": "ingeniero", "Inga.": "ingeniera", "Lic.": "licenciado", "Lica.": "licenciada",
    "etc.": "etcétera", "p.ej.": "por ejemplo", "vs.": "versus", 
    "c/": "con", "s/": "sin", "km": "kilómetros", "m": "metros", "cm": "centímetros",
    "kg": "kilogramos", "g": "gramos", "l": "litros", "ml": "mililitros",
    "h": "horas", "min": "minutos", "seg": "segundos", "°C": "grados Celsius",
    "°F": "grados Fahrenheit", "Av.": "avenida", "Ave.": "avenida", "Blvd.": "bulevar",
    "Calle": "calle", "Col.": "colonia", "Frac.": "fraccionamiento"
}

# Spanish ordinal numbers (1st to 31st for dates)
SPANISH_ORDINALS = {
    1: "primero", 2: "segundo", 3: "tercero", 4: "cuarto", 5: "quinto",
    6: "sexto", 7: "séptimo", 8: "octavo", 9: "noveno", 10: "décimo",
    11: "undécimo", 12: "duodécimo", 13: "decimotercero", 14: "decimocuarto", 15: "decimoquinto",
    16: "decimosexto", 17: "decimoséptimo", 18: "decimoctavo", 19: "decimonoveno", 20: "vigésimo",
    21: "vigésimo primero", 22: "vigésimo segundo", 23: "vigésimo tercero", 24: "vigésimo cuarto", 25: "vigésimo quinto",
    26: "vigésimo sexto", 27: "vigésimo séptimo", 28: "vigésimo octavo", 29: "vigésimo noveno", 30: "trigésimo",
    31: "trigésimo primero"
}


def _convert_number_to_language(num: int, lang: str = 'es') -> str:
    """Convert integer to text in specified language using num2words with fallback."""
    try:
        from num2words import num2words
        # Map language variants to base languages supported by num2words
        lang_mapping = {
            'es-ES': 'es', 'es-MX': 'es', 'es-AR': 'es',
            'en-US': 'en', 'en-GB': 'en', 'en-CA': 'en',
            'pt-BR': 'pt', 'pt-PT': 'pt',
            'zh-cn': 'zh', 'zh-CN': 'zh'
        }
        
        # Use mapped language or original
        target_lang = lang_mapping.get(lang, lang)
        
        return num2words(num, lang=target_lang)
    except ImportError:
        logger.warning("num2words not available, using basic number conversion")
        return _basic_number_conversion(num, lang)
    except Exception as e:
        logger.warning(f"Error converting number {num} to {lang}: {e}, using fallback")
        return _basic_number_conversion(num, lang)


def _convert_number_to_spanish(num: int) -> str:
    """Convert integer to Spanish text using num2words with fallback."""
    return _convert_number_to_language(num, 'es')


def _basic_number_conversion(num: int, lang: str = 'es') -> str:
    """Basic number conversion with language support (fallback when num2words is not available)."""
    if lang == 'es':
        return _basic_number_to_spanish(num)
    elif lang == 'en':
        return _basic_number_to_english(num)
    else:
        # For unsupported languages, just return the number as string
        return str(num)


def _basic_number_to_spanish(num: int) -> str:
    """Basic number conversion for Spanish (fallback when num2words is not available)."""
    if num == 0:
        return "cero"
    
    # Basic mappings for common numbers
    ones = ["", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve"]
    teens = ["diez", "once", "doce", "trece", "catorce", "quince", "dieciséis", "diecisiete", "dieciocho", "diecinueve"]
    tens = ["", "", "veinte", "treinta", "cuarenta", "cincuenta", "sesenta", "setenta", "ochenta", "noventa"]
    hundreds = ["", "ciento", "doscientos", "trescientos", "cuatrocientos", "quinientos", "seiscientos", "setecientos", "ochocientos", "novecientos"]
    
    if num < 0:
        return f"menos {_basic_number_to_spanish(-num)}"
    
    if num < 10:
        return ones[num]
    elif num < 20:
        return teens[num - 10]
    elif num < 100:
        tens_digit = num // 10
        ones_digit = num % 10
        if num == 20:
            return "veinte"
        elif num < 30 and ones_digit > 0:
            return f"veinti{ones[ones_digit]}"
        elif ones_digit == 0:
            return tens[tens_digit]
        else:
            return f"{tens[tens_digit]} y {ones[ones_digit]}"
    elif num == 100:
        return "cien"
    elif num < 1000:
        hundreds_digit = num // 100
        remainder = num % 100
        if remainder == 0:
            return hundreds[hundreds_digit] if hundreds_digit != 1 else "cien"
        else:
            return f"{hundreds[hundreds_digit]} {_basic_number_to_spanish(remainder)}"
    elif num == 1000:
        return "mil"
    elif num < 1000000:
        thousands = num // 1000
        remainder = num % 1000
        thousands_text = "mil" if thousands == 1 else f"{_basic_number_to_spanish(thousands)} mil"
        if remainder == 0:
            return thousands_text
        else:
            return f"{thousands_text} {_basic_number_to_spanish(remainder)}"
    else:
        # For larger numbers, use a simplified approach
        return str(num)  # Fallback to digits for very large numbers


def _basic_number_to_english(num: int) -> str:
    """Basic number conversion for English (fallback when num2words is not available)."""
    if num == 0:
        return "zero"
    
    ones = ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
    teens = ["ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
    tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
    
    if num < 0:
        return f"negative {_basic_number_to_english(-num)}"
    
    if num < 10:
        return ones[num]
    elif num < 20:
        return teens[num - 10]
    elif num < 100:
        tens_digit = num // 10
        ones_digit = num % 10
        if ones_digit == 0:
            return tens[tens_digit]
        else:
            return f"{tens[tens_digit]}-{ones[ones_digit]}"
    elif num == 100:
        return "one hundred"
    elif num < 1000:
        hundreds_digit = num // 100
        remainder = num % 100
        if remainder == 0:
            return f"{ones[hundreds_digit]} hundred"
        else:
            return f"{ones[hundreds_digit]} hundred {_basic_number_to_english(remainder)}"
    elif num == 1000:
        return "one thousand"
    elif num < 1000000:
        thousands = num // 1000
        remainder = num % 1000
        thousands_text = "one thousand" if thousands == 1 else f"{_basic_number_to_english(thousands)} thousand"
        if remainder == 0:
            return thousands_text
        else:
            return f"{thousands_text} {_basic_number_to_english(remainder)}"
    else:
        # For larger numbers, use a simplified approach
        return str(num)  # Fallback to digits for very large numbers


def _normalize_numbers(text: str, language: str = 'es') -> str:
    """Normalize standalone numbers in text."""
    # Pattern for standalone numbers (not part of dates, times, currencies, etc.)
    # Use negative lookahead and lookbehind to avoid numbers in dates, times, and currencies
    number_pattern = r'(?<![\/\-\.\:$€£])\b(\d{1,6})\b(?![\/\-\.\:$€£%])'
    
    def replace_number(match):
        num_str = match.group(1)
        try:
            num = int(num_str)
            # Skip very large numbers to avoid performance issues
            if num > 999999:
                return num_str
            return _convert_number_to_language(num, language)
        except ValueError:
            return num_str
    
    return re.sub(number_pattern, replace_number, text)


def _normalize_dates(text: str, language: str = 'es') -> str:
    """Normalize dates in DD/MM/YYYY, DD-MM-YYYY, and DD.MM.YYYY formats."""
    # Only apply date normalization for supported languages
    if language not in ['es', 'en']:
        return text
        
    # Pattern for dates: DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY
    date_patterns = [
        r'\b(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})\b',  # DD/MM/YYYY
        r'\b(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{2})\b'    # DD/MM/YY
    ]
    
    def replace_date(match):
        try:
            day = int(match.group(1))
            month = int(match.group(2))
            year = int(match.group(3))
            
            # Handle 2-digit years
            if year < 100:
                year = 2000 + year if year < 50 else 1900 + year
            
            # Validate month
            if month < 1 or month > 12:
                return match.group(0)  # Return original if invalid
            
            # Validate day (basic check)
            if day < 1 or day > 31:
                return match.group(0)  # Return original if invalid
            
            if language == 'es':
                # Spanish date formatting
                day_text = "primero" if day == 1 else _convert_number_to_language(day, language)
                month_text = SPANISH_MONTHS[month]
                year_text = _convert_number_to_language(year, language)
                return f"{day_text} de {month_text} de {year_text}"
            elif language == 'en':
                # English date formatting
                english_months = {
                    1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
                    7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December"
                }
                ordinals = {
                    1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth", 
                    21: "twenty-first", 22: "twenty-second", 23: "twenty-third", 31: "thirty-first"
                }
                day_text = ordinals.get(day, f"{_convert_number_to_language(day, language)}")
                if day_text == _convert_number_to_language(day, language) and not day_text.endswith('th'):
                    day_text += "th"
                month_text = english_months[month]
                year_text = _convert_number_to_language(year, language)
                return f"{month_text} {day_text}, {year_text}"
            
        except (ValueError, KeyError):
            return match.group(0)  # Return original on error
    
    result = text
    for pattern in date_patterns:
        result = re.sub(pattern, replace_date, result)
    
    return result


def _normalize_times(text: str, language: str = 'es') -> str:
    """Normalize time expressions like 3:30, 15:45, etc."""
    # Pattern for time: HH:MM (with optional AM/PM)
    time_pattern = r'\b(\d{1,2}):(\d{2})(?:\s*(AM|PM|am|pm))?\b'
    
    def replace_time(match):
        try:
            hours = int(match.group(1))
            minutes = int(match.group(2))
            am_pm = match.group(3)
            
            # Validate time
            if hours > 23 or minutes > 59:
                return match.group(0)  # Return original if invalid
            
            # Convert hours
            if am_pm:
                # 12-hour format
                if am_pm.upper() == 'AM':
                    if hours == 12:
                        hours_text = "doce" if language == 'es' else "twelve"
                    else:
                        hours_text = _convert_number_to_language(hours, language)
                    period = "de la mañana" if language == 'es' else "AM"
                else:  # PM
                    if hours == 12:
                        hours_text = "doce" if language == 'es' else "twelve"
                    else:
                        hours_text = _convert_number_to_language(hours, language)
                    period = "de la tarde" if language == 'es' else "PM"
            else:
                # 24-hour format OR ambiguous time - infer from context and hour
                hours_text = _convert_number_to_language(hours, language)
                
                # If hours are 1-11 without AM/PM, assume afternoon/evening context for times like "las 3:30"
                if hours >= 1 and hours <= 11:
                    # Context clue: if preceded by "las", likely afternoon
                    full_match = match.group(0)
                    text_before = match.string[:match.start()]
                    if "las" in text_before[-10:]:  # Check last 10 chars before match
                        period = "de la tarde"
                    else:
                        period = "de la mañana"
                elif hours == 12:
                    period = "del mediodía"
                elif hours < 6:
                    period = "de la madrugada"
                elif hours < 12:
                    period = "de la mañana"
                elif hours < 19:
                    period = "de la tarde"
                else:
                    period = "de la noche"
            
            # Convert minutes
            if minutes == 0:
                return f"{hours_text} en punto {period}"
            elif minutes == 15:
                return f"{hours_text} y cuarto {period}"
            elif minutes == 30:
                return f"{hours_text} y media {period}"
            elif minutes == 45:
                next_hour = (hours + 1) % 24
                next_hour_text = _convert_number_to_language(next_hour, language)
                return f"cuarto para las {next_hour_text} {period}"
            else:
                minutes_text = _convert_number_to_language(minutes, language)
                return f"{hours_text} y {minutes_text} {period}"
                
        except ValueError:
            return match.group(0)  # Return original on error
    
    return re.sub(time_pattern, replace_time, text)


def _normalize_currencies(text: str, language: str = 'es') -> str:
    """Normalize currency expressions like $150, €20, £30, etc."""
    # Patterns for different currencies
    currency_patterns = [
        (r'\$(\d+)(?:\.(\d{1,2}))?', 'dólares', 'centavos'),
        (r'€(\d+)(?:\.(\d{1,2}))?', 'euros', 'céntimos'),
        (r'£(\d+)(?:\.(\d{1,2}))?', 'libras', 'peniques'),
        (r'(\d+)\s*USD', 'dólares estadounidenses', 'centavos'),
        (r'(\d+)\s*EUR', 'euros', 'céntimos'),
        (r'(\d+)\s*MXN', 'pesos mexicanos', 'centavos'),
        (r'(\d+)\s*pesos?', 'pesos', 'centavos'),
    ]
    
    def replace_currency(match, main_unit, sub_unit):
        try:
            main_amount = int(match.group(1))
            sub_amount = int(match.group(2)) if match.lastindex >= 2 and match.group(2) else None
            
            main_text = _convert_number_to_language(main_amount, language)
            
            # Handle singular/plural for main unit
            if main_amount == 1:
                # Special cases for currency units
                if main_unit == 'dólares':
                    main_unit_text = 'dólar'
                elif main_unit == 'euros':
                    main_unit_text = 'euro'
                elif main_unit == 'libras':
                    main_unit_text = 'libra'
                elif main_unit == 'pesos':
                    main_unit_text = 'peso'
                else:
                    main_unit_text = main_unit[:-1] if main_unit.endswith('s') else main_unit  # Remove 's' for singular
            else:
                main_unit_text = main_unit
            
            result = f"{main_text} {main_unit_text}"
            
            # Add sub-amount if present
            if sub_amount is not None and sub_amount > 0:
                sub_text = _convert_number_to_language(sub_amount, language)
                if sub_amount == 1:
                    sub_unit_text = sub_unit[:-1] if sub_unit.endswith('s') else sub_unit
                else:
                    sub_unit_text = sub_unit
                result += f" con {sub_text} {sub_unit_text}"
            
            return result
        except ValueError:
            return match.group(0)  # Return original on error
    
    result = text
    for pattern, main_unit, sub_unit in currency_patterns:
        result = re.sub(pattern, lambda m: replace_currency(m, main_unit, sub_unit), result)
    
    return result


def _normalize_percentages(text: str, language: str = 'es') -> str:
    """Normalize percentage expressions like 15%, 3.5%, etc."""
    # Pattern for percentages
    percentage_pattern = r'\b(\d+(?:\.\d+)?)\s*%'
    
    def replace_percentage(match):
        try:
            percentage_str = match.group(1)
            
            if '.' in percentage_str:
                # Handle decimal percentages
                parts = percentage_str.split('.')
                whole = int(parts[0])
                decimal = int(parts[1])
                
                whole_text = _convert_number_to_language(whole, language)
                decimal_text = _convert_number_to_language(decimal, language)
                
                return f"{whole_text} coma {decimal_text} por ciento"
            else:
                # Handle whole number percentages
                percentage = int(percentage_str)
                percentage_text = _convert_number_to_language(percentage, language)
                return f"{percentage_text} por ciento"
                
        except ValueError:
            return match.group(0)  # Return original on error
    
    return re.sub(percentage_pattern, replace_percentage, text)


def _normalize_abbreviations(text: str, language: str = 'es') -> str:
    """Normalize common Spanish abbreviations."""
    result = text
    
    # Sort by length (longest first) to handle overlapping abbreviations correctly
    sorted_abbrevs = sorted(SPANISH_ABBREVIATIONS.items(), key=lambda x: len(x[0]), reverse=True)
    
    for abbrev, expansion in sorted_abbrevs:
        # Special handling for abbreviations with periods
        if abbrev.endswith('.'):
            # Match the abbreviation with the period as literal
            pattern = re.escape(abbrev)
        else:
            # Use word boundaries for abbreviations without periods
            pattern = r'\b' + re.escape(abbrev) + r'\b'
        
        result = re.sub(pattern, expansion, result, flags=re.IGNORECASE)
    
    return result


def normalize_text_for_tts(text: str, language: str = "es") -> str:
    """
    Normalize text for TTS by converting numbers, dates, times, currencies,
    percentages, and abbreviations to their spoken form.
    
    Supports multiple languages with dynamic num2words integration.
    
    Args:
        text (str): The input text to normalize
        language (str): Language code (e.g., 'es', 'en', 'fr', 'de', etc.)
    
    Returns:
        str: Normalized text ready for TTS
    
    Examples:
        >>> normalize_text_for_tts("Tengo 25 años", "es")
        'Tengo veinticinco años'
        
        >>> normalize_text_for_tts("I have 25 years", "en")
        'I have twenty-five years'
        
        >>> normalize_text_for_tts("Cuesta $150.50", "es")
        'Cuesta ciento cincuenta dólares con cincuenta centavos'
    """
    
    # Get base language (remove variants like es-ES -> es)
    base_lang = language.lower().split('-')[0]
    
    # Supported languages for num2words (based on our testing)
    supported_languages = ['en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'nl', 'pl', 'ar', 'ja', 'ko', 'tr', 'hu']
    
    # If language not supported, only basic normalization
    if base_lang not in supported_languages:
        logger.debug(f"Language '{base_lang}' not supported for full normalization, applying basic processing")
        # For unsupported languages, we can still do basic cleanup but no number conversion
        return text
    
    logger.debug(f"Normalizing text for {base_lang.upper()} TTS: '{text[:50]}...'")
    
    try:
        # Apply normalizations in order of specificity (most specific first)
        normalized = text
        
        # 1. Normalize dates (before numbers to avoid conflicts)
        normalized = _normalize_dates(normalized, base_lang)
        
        # 2. Normalize times (before numbers to avoid conflicts) - only for Spanish and English
        if base_lang in ['es', 'en']:
            normalized = _normalize_times(normalized, base_lang)
        
        # 3. Normalize currencies (before numbers to avoid conflicts) - only for Spanish and English
        if base_lang in ['es', 'en']:
            normalized = _normalize_currencies(normalized, base_lang)
        
        # 4. Normalize percentages (before numbers to avoid conflicts)
        normalized = _normalize_percentages(normalized, base_lang)
        
        # 5. Normalize standalone numbers
        normalized = _normalize_numbers(normalized, base_lang)
        
        # 6. Normalize abbreviations (last, as they might contain numbers) - only for Spanish
        if base_lang == 'es':
            normalized = _normalize_abbreviations(normalized, base_lang)
        
        # Log what was normalized if there were changes
        if normalized != text:
            logger.debug(f"Text normalized from: '{text}' to: '{normalized}'")
        
        return normalized
        
    except Exception as e:
        logger.error(f"Error during text normalization: {e}")
        # Return original text if normalization fails
        return text


def is_normalization_needed(text: str, language: str = "es") -> bool:
    """
    Check if text contains elements that would benefit from normalization.
    
    This can be used to optimize performance by skipping normalization
    for text that doesn't need it.
    
    Args:
        text (str): The input text to check
        language (str): Language code
        
    Returns:
        bool: True if normalization would modify the text
    """
    # Get base language
    base_lang = language.lower().split('-')[0]
    
    # Supported languages for num2words
    supported_languages = ['en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'nl', 'pl', 'ar', 'ja', 'ko', 'tr', 'hu']
    
    if base_lang not in supported_languages:
        return False
    
    # Check for patterns that would be normalized
    patterns_to_check = [
        r'\b\d+\b',  # Numbers
        r'\b\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}\b',  # Dates
        r'\b\d{1,2}:\d{2}\b',  # Times
        r'[\$€£]\d+',  # Currencies
        r'\b\d+(?:\.\d+)?\s*%',  # Percentages
    ]
    
    # Check abbreviations (use word boundaries for better matching)
    for abbrev in SPANISH_ABBREVIATIONS.keys():
        if abbrev.endswith('.'):
            # For abbreviations with periods, match exactly
            if abbrev in text:
                return True
        else:
            # For abbreviations without periods, use word boundaries
            pattern = r'\b' + re.escape(abbrev) + r'\b'
            if re.search(pattern, text, re.IGNORECASE):
                return True
    
    # Check numeric patterns
    for pattern in patterns_to_check:
        if re.search(pattern, text):
            return True
    
    return False


# For backward compatibility and easier imports
__all__ = ['normalize_text_for_tts', 'is_normalization_needed']
