# Instrucciones de Instalación - EPUB to Audiobook

Este documento contiene las instrucciones completas para instalar y ejecutar el proyecto EPUB to Audiobook en cualquier PC Windows.

## Requisitos Previos

- Windows 10/11
- Python 3.8 o superior
- Git (opcional, para clonar el repositorio)
- Conexión a internet (para descargar dependencias y modelos)

## Instalación Paso a Paso

### 1. Descargar el Proyecto

#### Opción A: Clonar con Git
```powershell
git clone https://github.com/kroryan/epub_to_audiobook.git
cd epub_to_audiobook
```

#### Opción B: Descargar ZIP
1. Ve a https://github.com/kroryan/epub_to_audiobook
2. Haz clic en "Code" > "Download ZIP"
3. Extrae el archivo en una carpeta de tu elección
4. Abre PowerShell en esa carpeta

### 2. Crear Entorno Virtual

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Nota**: Si aparece error de ejecución de scripts, ejecuta:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 3. Instalar Dependencias de Python

```powershell
pip install -r requirements.txt
```

### 4. Descargar FFmpeg

Ejecuta el script automático:
```powershell
.\scripts\install_ffmpeg.ps1
```

### 5. Instalar Piper TTS Completo

```powershell
.\scripts\install_piper_complete.ps1
```

Este script descarga e instala automáticamente:
- Binarios de Piper TTS (ejecutables, librerías)
- Modelos de voz en español e inglés (~400MB total)
- Archivos de configuración necesarios

**Alternativa rápida** (solo modelos, si ya tienes Piper):
```powershell
.\scripts\download_piper_models.ps1
```

### 6. Verificar Instalación

Prueba que todo funciona correctamente:
```powershell
python main.py --help
```

## Formas de Ejecutar la Aplicación

### 1. Interfaz Web (Recomendado)
```powershell
python main_ui.py
```
Abre tu navegador en `http://localhost:7860`

### 2. Línea de Comandos
```powershell
python main.py --input "ruta/al/libro.epub" --output "carpeta/salida"
```

### 3. Aplicación de Bandeja del Sistema
```powershell
python tray_app.py
```

## Configuración de Proveedores TTS

### Edge TTS (Gratis, incluido)
- No requiere configuración adicional
- Calidad buena
- Límites de uso razonables

### OpenAI TTS (Pago)
1. Obtén una API key en https://platform.openai.com/
2. Crea un archivo `.env` en la carpeta raíz:
```
OPENAI_API_KEY=tu_api_key_aqui
```

### Azure TTS (Pago)
1. Crea una cuenta en Azure Cognitive Services
2. Agrega al archivo `.env`:
```
AZURE_TTS_KEY=tu_key_aqui
AZURE_TTS_REGION=tu_region
```

### Coqui TTS (Local, gratis)
- Se instala automáticamente con requirements.txt
- Requiere más recursos de CPU/GPU

## Estructura del Proyecto

```
epub_to_audiobook/
├── main.py                 # Aplicación principal línea de comandos
├── main_ui.py             # Interfaz web Gradio
├── tray_app.py           # Aplicación de bandeja
├── requirements.txt       # Dependencias Python
├── .env                  # Variables de entorno (crear manualmente)
├── audiobook_generator/   # Código principal
├── scripts/              # Scripts de instalación
│   ├── install_ffmpeg.ps1
│   └── download_piper_models.ps1
├── examples/             # Libros de ejemplo
└── piper_tts/           # Modelos TTS (se descargan automáticamente)
```

## Solución de Problemas Comunes

### Error: "No se puede ejecutar scripts"
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Error: "FFmpeg no encontrado"
Ejecuta manualmente el script:
```powershell
.\scripts\install_ffmpeg.ps1
```

### Error: "Piper TTS no encontrado" o "Modelos no encontrados"
```powershell
# Reinstalar Piper completo
.\scripts\install_piper_complete.ps1 -Force

# O solo los modelos
.\scripts\download_piper_models.ps1
```

### Error: "tar no encontrado" al instalar Piper
1. Instala Git para Windows (incluye tar): https://git-scm.com/download/win
2. O extrae manualmente el archivo .tar.gz descargado en `piper_tts/`

### Error de memoria con archivos grandes
- Usa archivos EPUB más pequeños
- Cierra otras aplicaciones
- Considera usar Coqui TTS en lugar de otros proveedores

### Calidad de audio baja
1. Verifica que FFmpeg esté instalado correctamente
2. Usa proveedores TTS de mayor calidad (OpenAI, Azure)
3. Ajusta la configuración de audio en la interfaz

## Uso del Ejemplo Incluido

El proyecto incluye "Robinson Crusoe" como ejemplo:
```powershell
python main.py --input "examples/The_Life_and_Adventures_of_Robinson_Crusoe.epub" --output "mi_audiolibro"
```

## Actualización del Proyecto

Para obtener las últimas mejoras:
```powershell
git pull origin main
pip install -r requirements.txt --upgrade
```

## Notas Importantes

1. **Primera ejecución**: La primera vez tardará más por la descarga de modelos
2. **Espacio en disco**: Reserva ~2GB para modelos y dependencias
3. **Internet**: Se requiere conexión para descargar modelos inicialmente
4. **Rendimiento**: Los archivos grandes pueden tardar horas en procesarse

## Soporte

- **Issues**: https://github.com/kroryan/epub_to_audiobook/issues
- **Documentación**: Revisa los README específicos en el repositorio
- **Ejemplos**: Usa los archivos en la carpeta `examples/`

## Licencia

Ver archivo `LICENSE` en el repositorio.