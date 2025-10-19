# 🎯 GUÍA COMPLETA DE USO - KOKORO EN EPUB TO AUDIOBOOK

## 🚀 INICIO RÁPIDO

### 1. Iniciar el servidor Kokoro
```bash
cd Kokoro-FastAPI
# Para GPU:
start-gpu.ps1
# Para CPU:
start-cpu.ps1
```

### 2. Iniciar la interfaz web
```bash
cd epub_to_audiobook
python main_ui.py --host 0.0.0.0 --port 7070
```

### 3. Acceder a la interfaz
Abre tu navegador en: `http://localhost:7070`

---

## 🎛️ FUNCIONALIDADES AVANZADAS

### 🎭 MEZCLA DE VOCES
**Sintaxis disponible:**
- `voice1+voice2` - Mezcla 50/50
- `voice1+voice2(0.3)` - 70% voice1 + 30% voice2
- `voice1+voice2(0.7)+voice3(0.1)` - Múltiples voces

**Ejemplos prácticos:**
```
af_bella+af_sky(0.3)          # Voz femenina suave
en_male_cody+en_male_adam(0.4) # Voz masculina robusta
es_male_codi+af_bella(0.2)     # Mezcla español-inglés
```

### 🔧 HERRAMIENTAS EN LA WEB UI

#### 1. **Probar Conexión**
- Botón "Test Connection" verifica servidor Kokoro
- Muestra estado y número de voces disponibles

#### 2. **Validar Combinación de Voces**
- Introduce tu combinación en el campo
- Click "Validate Voice Combination"
- ✅ Muestra si es válida y las voces usadas

#### 3. **Crear Nueva Combinación**
- Selecciona voces de las listas desplegables
- Ajusta pesos con los sliders
- Click "Create Voice Combination"
- La combinación se genera automáticamente

#### 4. **Presets de Calidad**
- **Ultra High**: 48kHz, 320kbps, stereo
- **High**: 44.1kHz, 256kbps, stereo  
- **Standard**: 22kHz, 128kbps, mono
- **Fast**: 16kHz, 96kbps, mono

### 📝 NORMALIZACIÓN DE TEXTO
**Opciones disponibles:**
- ✅ URLs: `https://example.com` → "H T T P S example dot com"
- ✅ Emails: `user@domain.com` → "user at domain dot com"
- ✅ Teléfonos: `+1-555-123-4567` → "plus one five five five one two three four five six seven"
- ✅ Pluralización: `3 cats` → "three cats"
- ✅ Símbolos: `&` → "and"

### 🎚️ CONTROLES AVANZADOS

#### **Audio Quality**
- Sample Rate: 8kHz - 48kHz
- Bitrate: 32kbps - 320kbps
- Channels: Mono/Stereo
- WAV Bit Depth: 16/24/32 bits

#### **Voice Control**
- Speed: 0.5x - 2.0x
- Volume Multiplier: 0.1x - 2.0x
- Streaming: Habilitado por defecto

#### **Advanced Features**
- Return Timestamps: Para sincronización
- Download Links: Para descarga directa
- Weight Normalization: Normaliza pesos de voz

---

## 🎯 CASOS DE USO ESPECÍFICOS

### 📚 **Audiolibros Narrativos**
```
Configuración recomendada:
- Voice: en_female_bella+en_female_sky(0.3)
- Speed: 0.9x
- Quality Preset: High
- Normalization: ✅ All enabled
```

### 🎭 **Contenido Dramático**
```
Configuración recomendada:
- Voice: en_male_cody+en_female_bella(0.4)
- Speed: 1.0x
- Quality Preset: Ultra High
- Volume: 1.2x
```

### 📖 **Material Educativo**
```
Configuración recomendada:
- Voice: en_male_adam
- Speed: 0.8x
- Quality Preset: Standard
- Normalization: ✅ URLs, Emails, Phones
```

---

## 🐛 SOLUCIÓN DE PROBLEMAS

### **Error de Conexión**
```
❌ No connection to Kokoro server
```
**Solución:**
1. Verificar que Kokoro-FastAPI esté ejecutándose
2. Comprobar puerto 8880 disponible
3. Revisar firewall/antivirus

### **Error de Voz Inválida**
```
❌ Invalid voice combination
```
**Solución:**
1. Usar el validador de la web UI
2. Verificar sintaxis: `voice1+voice2(weight)`
3. Comprobar que las voces existen

### **Error de Calidad**
```
❌ Audio quality issues
```
**Solución:**
1. Usar presets de calidad
2. Verificar sample rate compatible
3. Ajustar bitrate según necesidades

---

## 🎉 VERIFICACIÓN FINAL

### ✅ Checklist de Funciones
- [ ] Servidor Kokoro ejecutándose (67 voces)
- [ ] Web UI accesible en puerto 7070
- [ ] Pestaña Kokoro visible con controles
- [ ] Validación de voces funcionando
- [ ] Presets de calidad aplicándose
- [ ] Normalización procesando texto
- [ ] Generación de audio exitosa

### 🧪 **Test Rápido**
1. Selecciona archivo EPUB
2. Ve a pestaña "Kokoro"
3. Prueba: `af_bella+af_sky(0.3)`
4. Activa normalization
5. Selecciona preset "High"
6. Click "Generate"

---

## 💡 TIPS AVANZADOS

### **Optimización de Rendimiento**
- Usa streaming para archivos grandes
- Ajusta worker count según CPU
- Monitorea memoria con voice mixing

### **Personalización de Voces**
- Experimenta con diferentes pesos
- Combina idiomas para efectos únicos
- Usa presets como punto de partida

### **Producción de Calidad**
- Ultra High para distribución final
- High para pruebas y revisión
- Standard para desarrollo rápido

---

## 🔗 RECURSOS ADICIONALES

- **Dokumentación Kokoro**: `Kokoro-FastAPI/README.md`
- **Voces Disponibles**: 67 voces en 10 idiomas
- **Ejemplos**: `examples/` folder
- **Logs**: `logs/` folder para debugging

---

¡Disfruta creando audiolibros con la máxima calidad y flexibilidad! 🎧📚