# Normalización de Texto para Coqui TTS

## Descripción

Este módulo implementa normalización de texto en español específicamente para mejorar la calidad de pronunciación del proveedor Coqui TTS. Coqui TTS genera audio de excelente calidad, pero requiere texto pre-normalizado para pronunciar correctamente números, fechas, horas y otros elementos numéricos.

## Características

### ✅ Implementado

- **Números**: `25` → `veinticinco`
- **Fechas**: `15/03/2024` → `quince de marzo de dos mil veinticuatro`
- **Horas**: `3:30 PM` → `tres y media de la tarde`
- **Monedas**: `$150.50` → `ciento cincuenta dólares con cincuenta centavos`
- **Porcentajes**: `15%` → `quince por ciento`
- **Abreviaturas**: `Dr.` → `doctor`, `Sr.` → `señor`, `etc.` → `etcétera`

### 🎯 Características Técnicas

- **Solo para español**: La normalización se aplica únicamente a modelos Coqui con idioma español
- **Detección automática**: Detecta el idioma del modelo desde su nombre (ej: `tts_models/es/css10/vits`)
- **Optimización**: Función `is_normalization_needed()` para evitar procesamiento innecesario
- **Fallback robusto**: Si `num2words` no está disponible, usa conversión básica incorporada
- **Logging**: Registra cuando se aplica normalización para debugging

## Estructura de Archivos

```
audiobook_generator/
├── utils/
│   └── text_normalizer.py          # Módulo principal de normalización
├── tts_providers/
│   └── coqui_tts_provider.py       # Integración con Coqui TTS (MODIFICADO)
└── requirements.txt                # Dependencias actualizadas (MODIFICADO)

tests/
└── test_text_normalizer.py         # Suite completa de tests

test_integration.py                  # Script de pruebas de integración
```

## Uso

### Automático (Recomendado)

La normalización se aplica automáticamente cuando uses Coqui TTS con modelos en español:

```python
# Configurar modelo español en tu config
config.tts = "coqui"
config.coqui_model = "tts_models/es/css10/vits"

# El texto se normalizará automáticamente
provider = CoquiTTSProvider(config)
provider.text_to_speech("Tengo 25 años", "output.mp3", audio_tags)
# Internamente convierte a: "Tengo veinticinco años"
```

### Manual (Para Desarrollo/Testing)

```python
from audiobook_generator.utils.text_normalizer import normalize_text_for_tts

# Normalizar texto manualmente
texto_original = "El Dr. García nació el 15/03/1985 y tiene 38 años"
texto_normalizado = normalize_text_for_tts(texto_original, "es")

print(texto_normalizado)
# Output: "El doctor García nació el quince de marzo de mil novecientos ochenta y cinco y tiene treinta y ocho años"
```

### Verificar si se Necesita Normalización

```python
from audiobook_generator.utils.text_normalizer import is_normalization_needed

# Optimizar rendimiento
if is_normalization_needed(texto, "es"):
    texto = normalize_text_for_tts(texto, "es")
```

## Instalación

### Dependencias

Agregar a `requirements.txt`:
```
num2words==0.5.13
```

Instalar:
```bash
pip install num2words==0.5.13
```

### Verificar Instalación

```bash
# Pruebas básicas
python tests/test_text_normalizer.py --basic

# Suite completa de tests
python -m pytest tests/test_text_normalizer.py -v

# Pruebas de integración
python test_integration.py
```

## Ejemplos de Transformaciones

### Números
```
"Tengo 25 años" → "Tengo veinticinco años"
"Hay 1000 personas" → "Hay mil personas"
"El número 100" → "El número cien"
```

### Fechas
```
"El 15/03/2024" → "El quince de marzo de dos mil veinticuatro"
"Nació el 1/1/2000" → "Nació el primero de enero de dos mil"
"Fecha: 31-12-1999" → "Fecha: treinta y uno de diciembre de mil novecientos noventa y nueve"
```

### Horas
```
"Son las 3:30" → "Son las tres y media de la tarde"
"A las 12:00 PM" → "A las doce en punto de la tarde"
"Llegamos a las 9:15 AM" → "Llegamos a las nueve y cuarto de la mañana"
```

### Monedas
```
"Cuesta $150" → "Cuesta ciento cincuenta dólares"
"Pagó €20.50" → "Pagó veinte euros con cincuenta céntimos"
"Son £35" → "Son treinta y cinco libras"
```

### Porcentajes
```
"El 45% de descuento" → "El cuarenta y cinco por ciento de descuento"
"Aumentó 3.5%" → "Aumentó tres coma cinco por ciento"
```

### Abreviaturas
```
"El Dr. García" → "El doctor García"
"La Sra. López vive en la Av. Principal" → "La señora López vive en la avenida Principal"
"Mide 180 cm y pesa 75 kg" → "Mide ciento ochenta centímetros y pesa setenta y cinco kilogramos"
```

## Configuración

### Modelos Soportados

La normalización se activa automáticamente para modelos que contengan `/es/` en su nombre:

```
✅ tts_models/es/css10/vits
✅ tts_models/es/mai/tacotron2-DDC  
✅ local:mi_modelo_español
❌ tts_models/en/ljspeech/tacotron2
❌ tts_models/fr/css10/vits
```

### Variables de Entorno

No se requieren variables de entorno adicionales. La normalización usa la configuración existente del proyecto.

## Rendimiento

- **Rápido**: Optimizado con `is_normalization_needed()` para evitar procesamiento innecesario
- **Memoria eficiente**: No carga num2words hasta que se necesita
- **Compatible**: Funciona con chunks de 200-400 caracteres sin impacto significativo

## Logging

Para activar logs detallados:

```python
import logging
logging.getLogger('audiobook_generator.utils.text_normalizer').setLevel(logging.DEBUG)
logging.getLogger('audiobook_generator.tts_providers.coqui_tts_provider').setLevel(logging.INFO)
```

Ejemplo de output:
```
INFO - Applied Spanish text normalization to chunk of 156 characters
DEBUG - Text normalized from: 'Tengo 25 años' to: 'Tengo veinticinco años'
```

## Limitaciones Conocidas

1. **Solo español**: Actualmente implementado únicamente para español
2. **Números grandes**: Números > 999,999 no se normalizan por rendimiento
3. **Fechas inválidas**: Fechas como "35/15/2024" se manejan como números separados
4. **Contexto limitado**: Algunas abreviaturas podrían requerir más contexto

## Troubleshooting

### Error: "num2words not available"
```bash
pip install num2words==0.5.13
```

### Error: "Text normalizer not available"
Verificar que el archivo `text_normalizer.py` esté en `audiobook_generator/utils/`

### La normalización no se aplica
1. Verificar que el modelo contenga `/es/` en el nombre
2. Verificar que el texto contenga elementos normalizables
3. Revisar logs para mensajes de debug

### Tests fallan
```bash
# Reinstalar dependencias
pip install -r requirements.txt

# Ejecutar tests individuales
python -c "from audiobook_generator.utils.text_normalizer import normalize_text_for_tts; print(normalize_text_for_tts('Tengo 25 años', 'es'))"
```

## Desarrollo

### Agregar Nuevas Normalizaciones

1. Crear función `_normalize_nuevo_tipo(text: str) -> str` en `text_normalizer.py`
2. Agregar llamada en `normalize_text_for_tts()`
3. Agregar tests en `test_text_normalizer.py`
4. Actualizar documentación

### Agregar Soporte para Otros Idiomas

1. Crear mapeos de abreviaturas para el nuevo idioma
2. Extender `_detect_language_from_model()` 
3. Modificar la condición `language.startswith('es')` en `normalize_text_for_tts()`

## Referencias

- **num2words**: https://github.com/savoirfairelinux/num2words
- **Coqui TTS**: https://github.com/coqui-ai/TTS
- **Expresiones regulares Python**: https://docs.python.org/3/library/re.html

---

## Changelog

### v1.0.0 (2025-10-16)
- ✅ Implementación inicial de normalización para español
- ✅ Soporte para números, fechas, horas, monedas, porcentajes, abreviaturas  
- ✅ Integración automática con Coqui TTS
- ✅ Suite completa de tests
- ✅ Detección automática de idioma
- ✅ Optimización de rendimiento
- ✅ Fallback robusto sin num2words