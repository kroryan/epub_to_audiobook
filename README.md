# Conversor de EPUB a Audiolibro 

Este proyecto proporciona una herramienta de línea de comandos para convertir libros electrónicos EPUB en audiolibros. Ahora soporta tanto la [API de Microsoft Azure Text-to-Speech](https://learn.microsoft.com/en-us/azure/cognitive-services/speech-service/rest-text-to-speech) (alternativamente [EdgeTTS](https://github.com/rany2/edge-tts)) como la [API de OpenAI Text-to-Speech](https://platform.openai.com/docs/guides/text-to-speech) para generar el audio para cada capítulo del libro electrónico. Los archivos de audio de salida están optimizados para su uso con [Audiobookshelf](https://github.com/advplyr/audiobookshelf).


## Actualizaciones Recientes

- 2025-10-16: Agregado soporte para Coqui TTS con interfaz mejorada de selección de modelos.
- 2025-10-16: **Integración Mejorada de Kokoro TTS con Soporte Multi-idioma** - Agregada integración completa de Kokoro TTS con pestaña dedicada en la UI, selector de idiomas (español, inglés, francés, etc.), filtrado de voces, y configuración automática del entorno. Ahora soporta más de 67 voces incluyendo voces en español como `em_santa`, `ef_dora`, y `em_alex`.
- 2025-05-23: Agregada interfaz web (WebUI) al proyecto.

## Muestra de Audio

Si estás interesado en escuchar una muestra del audiolibro generado por esta herramienta, revisa los enlaces a continuación.

- [Muestra Azure TTS](https://audio.com/paudi/audio/0008-chapter-vii-agricultural-experience)
- [Muestra OpenAI TTS](https://audio.com/paudi/audio/openai-0008-chapter-vii-agricultural-experience-i-had-now-been-in)
- Muestra Edge TTS: la voz es casi la misma que Azure TTS
- [Piper TTS](https://rhasspy.github.io/piper-samples/)
- [Kokoro TTS](https://huggingface.co/spaces/hexgrad/Kokoro-TTS) (el uso de esto se hace a través de un endpoint local de OpenAI)

## Requisitos del Sistema

### Requisitos Básicos
- Python 3.6+ O ***Docker***
- **FFmpeg** (requerido para procesamiento de audio)

### Proveedores de TTS y sus Requisitos

#### **Azure TTS**
- Cuenta de Microsoft Azure con acceso a [Microsoft Cognitive Services Speech Services](https://portal.azure.com/#create/Microsoft.CognitiveServicesSpeechServices)
- Variables de entorno: `MS_TTS_KEY` y `MS_TTS_REGION`

#### **OpenAI TTS**
- [Clave API de OpenAI](https://platform.openai.com/api-keys)
- Variable de entorno: `OPENAI_API_KEY`

#### **Edge TTS**
- ✅ **No requiere clave API** (basado en la funcionalidad de lectura en voz alta de Edge)
- ✅ **Recomendado para pruebas rápidas**

#### **Piper TTS**
- Ejecutable de Piper TTS y modelos (incluidos en el proyecto en `piper_tts/`)
- ✅ **Funciona completamente offline**

#### **Coqui TTS**
- Librería TTS para *Coqui TTS*
- ✅ **Funciona completamente offline**

#### **Kokoro TTS**
- **Instalación separada requerida**: Docker para ejecutar el servidor Kokoro
- Comando para CPU: `docker run -p 8880:8880 ghcr.io/remsky/kokoro-fastapi-cpu`
- Comando para GPU: `docker run --gpus all -p 8880:8880 ghcr.io/remsky/kokoro-fastapi-gpu`
- ✅ **Excelente calidad de voz en español**
- ✅ **Soporte para múltiples idiomas**

### Instalación de FFmpeg

#### **Windows:**
```bash
# Automático (recomendado)
# El script descarga FFmpeg automáticamente en %LOCALAPPDATA%/EpubToAudiobook/ffmpeg/

# Manual usando Chocolatey
choco install ffmpeg

# Manual usando winget
winget install Gyan.FFmpeg
```

#### **macOS:**
```bash
# Usando Homebrew
brew install ffmpeg

# Usando MacPorts
sudo port install ffmpeg
```

#### **Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install ffmpeg
```

#### **Linux (CentOS/RHEL/Fedora):**
```bash
# CentOS/RHEL
sudo yum install ffmpeg

# Fedora
sudo dnf install ffmpeg
```

**Nota:** El proyecto incluye un script automático que descarga FFmpeg si no está disponible en Windows.

## Integración con Audiobookshelf

Los audiolibros generados por este proyecto están optimizados para su uso con [Audiobookshelf](https://github.com/advplyr/audiobookshelf). Cada capítulo en el archivo EPUB se convierte en un archivo MP3 separado, con el título del capítulo extraído e incluido como metadatos.

![demo](./examples/audiobookshelf.png)

### Títulos de Capítulos

El análisis y extracción de títulos de capítulos de archivos EPUB puede ser desafiante, ya que el formato y la estructura pueden variar significativamente entre diferentes libros electrónicos. El script emplea un método simple pero efectivo para extraer títulos de capítulos, que funciona para la mayoría de archivos EPUB. El método involucra analizar el archivo EPUB y buscar la etiqueta `title` en el contenido HTML de cada capítulo. Si la etiqueta title no está presente, se genera un título de respaldo usando las primeras palabras del texto del capítulo.

Ten en cuenta que este enfoque puede no funcionar perfectamente para todos los archivos EPUB, especialmente aquellos con formato complejo o inusual. Sin embargo, en la mayoría de casos, proporciona una forma confiable de extraer títulos de capítulos para usar en Audiobookshelf.

Cuando importes los archivos MP3 generados en Audiobookshelf, los títulos de capítulos se mostrarán, facilitando la navegación entre capítulos y mejorando tu experiencia de escucha.

## Instalación

1. Clona este repositorio:

    ```bash
    git clone https://git.code.sf.net/p/epub-to-audiobook/code epub_to_audiobook
    cd epub_to_audiobook
    ```
    
    Espejo alternativo en GitHub:
    ```bash
    git clone https://github.com/kroryan/epub_to_audiobook_exe.git
    cd epub_to_audiobook_exe
    ```

2. Crea un entorno virtual y actívalo:

    ```bash
    python3 -m venv venv
    source venv/bin/activate  # En Windows: venv\Scripts\activate
    ```

3. Instala las dependencias requeridas:

    ```bash
    pip install -r requirements.txt
    ```

4. Configura las siguientes variables de entorno con tus credenciales de Azure Text-to-Speech API, o tu clave API de OpenAI si estás usando OpenAI TTS:

    ```bash
    # Para Azure TTS
    export MS_TTS_KEY=<tu_clave_de_suscripcion>
    export MS_TTS_REGION=<tu_region>
    
    # Para OpenAI TTS
    export OPENAI_API_KEY=<tu_clave_api_openai>
    
    # Para Kokoro TTS (si usas un endpoint personalizado)
    export OPENAI_BASE_URL=http://localhost:8880/v1
    export OPENAI_API_KEY=fake  # Valor ficticio requerido
    ```

## Interfaz Web (WebUI)

Para usuarios que prefieren una interfaz gráfica, este proyecto incluye una UI basada en web construida con Gradio. La WebUI proporciona una forma intuitiva de configurar todas las opciones y convertir tus archivos EPUB sin usar la línea de comandos.

![WebUI Screenshot](./examples/webui.png)

### Variables de Entorno para WebUI

La WebUI respeta las mismas variables de entorno que la herramienta de línea de comandos:

```bash
export MS_TTS_KEY=<tu_clave_de_suscripcion>      # Para Azure TTS
export MS_TTS_REGION=<tu_region>                 # Para Azure TTS
export OPENAI_API_KEY=<tu_clave_api_openai>      # Para OpenAI TTS
export OPENAI_BASE_URL=<endpoint_personalizado>  # Opcional: Para endpoints compatibles con OpenAI
```

Asegúrate de configurar las variables de entorno para el servicio que estés usando antes de iniciar la WebUI.

### Iniciando la WebUI

Asegúrate de haber seguido los pasos de [Instalación](#instalación) antes de iniciar la WebUI.

Para lanzar la interfaz web, ejecuta:

```bash
python3 main_ui.py
```

Por defecto, la WebUI estará disponible en `http://127.0.0.1:7860`. Puedes personalizar el host y puerto:

```bash
python3 main_ui.py --host 127.0.0.1 --port 8080
```

Recuerda presionar `Ctrl+C` en la terminal para detener el servidor cuando hayas terminado.

### Características de la WebUI

La interfaz web proporciona:

- **Subida de Archivos**: Arrastra y suelta tu archivo EPUB directamente en el navegador
- **Selección de Proveedor TTS**: Cambio fácil entre Azure, OpenAI, Edge, Piper, Coqui y Kokoro TTS con opciones específicas del proveedor
- **Configuración de Voz**: Menús desplegables para seleccionar idiomas, voces y formatos de salida
- **Configuraciones Avanzadas**: Todas las opciones de línea de comandos disponibles a través de la interfaz web
- **Registros en Tiempo Real**: Ver el progreso de conversión y registros directamente en el navegador
- **Modo Vista Previa**: Prueba tus configuraciones sin generar audio
- **Buscar y Reemplazar**: Sube archivos de reemplazo de texto para correcciones de pronunciación

### Usando la WebUI

1. **Sube tu archivo EPUB** usando el selector de archivos
2. **Elige tu proveedor TTS** de las pestañas (OpenAI, Azure, Edge, Piper, Coqui o Kokoro)
3. **Configura ajustes específicos del proveedor**:
   - **OpenAI**: Selecciona modelo, voz, velocidad y formato
   - **Azure**: Elige idioma, voz, formato y duración de pausa
   - **Edge**: Configura idioma, voz, velocidad, volumen y tono
   - **Piper**: Configura despliegue local o Docker con opciones de voz
   - **Coqui**: Selecciona idioma y modelo con descargas automáticas, o ingresa ruta de modelo personalizado
   - **Kokoro**: Selecciona idioma y voz (requiere servidor Kokoro separado)
4. **Configura directorio de salida** o usa la carpeta con marca de tiempo por defecto
5. **Ajusta opciones avanzadas** si es necesario (rango de capítulos, procesamiento de texto, etc.)
6. **Haz clic en Iniciar** para comenzar la conversión
7. **Monitorea el progreso** a través del visor de registros integrado

Puedes seleccionar algunos capítulos para previsualizar el audio antes de iniciar la conversión completa.

### Docker con WebUI (La Forma Más Fácil Si Estás Familiarizado con Docker)

También puedes ejecutar la WebUI usando Docker. Usa el archivo `docker-compose.webui.yml` proporcionado. Asegúrate de editar el archivo con tus claves API para tu proveedor TTS.

```bash
# Edita docker-compose.webui.yml con tus claves API
docker compose -f docker-compose.webui.yml up
```

La WebUI será accesible en `http://localhost:7860` o `http://127.0.0.1:7860`.

### Consideraciones de Seguridad de la WebUI

La WebUI es una aplicación web que se ejecuta en tu máquina local. Actualmente no está diseñada para ser accesible desde internet abierto. No hay mecanismo de autorización en su lugar. Por lo tanto, no debes exponerla a internet abierto, ya que esto podría llevar a acceso no autorizado a tus proveedores TTS.

## Uso

Para convertir un libro electrónico EPUB a un audiolibro, ejecuta el siguiente comando, especificando el proveedor TTS de tu elección con la opción `--tts`:

```bash
python3 main.py <archivo_entrada> <carpeta_salida> [opciones]
```

Para verificar las últimas descripciones de opciones para este script, puedes ejecutar el siguiente comando en la terminal:

```bash
python3 main.py -h
```

```bash
usage: main.py [-h] [--tts {azure,openai,edge,piper,coqui}]
               [--log {DEBUG,INFO,WARNING,ERROR,CRITICAL}] [--preview]
               [--no_prompt] [--language LANGUAGE]
               [--newline_mode {single,double,none}]
               [--title_mode {auto,tag_text,first_few}]
               [--chapter_start CHAPTER_START] [--chapter_end CHAPTER_END]
               [--output_text] [--remove_endnotes]
               [--search_and_replace_file SEARCH_AND_REPLACE_FILE]
               [--worker_count WORKER_COUNT]
               [--voice_name VOICE_NAME] [--output_format OUTPUT_FORMAT]
               [--model_name MODEL_NAME] [--voice_rate VOICE_RATE]
               [--voice_volume VOICE_VOLUME] [--voice_pitch VOICE_PITCH]
               [--proxy PROXY] [--break_duration BREAK_DURATION]
               [--piper_path PIPER_PATH] [--piper_speaker PIPER_SPEAKER]
               [--piper_sentence_silence PIPER_SENTENCE_SILENCE]
               [--piper_length_scale PIPER_LENGTH_SCALE]
               archivo_entrada carpeta_salida

Convierte libro de texto a audiolibro

argumentos posicionales:
  archivo_entrada       Ruta al archivo EPUB
  carpeta_salida        Ruta a la carpeta de salida

opciones:
  -h, --help            muestra este mensaje de ayuda y sale
  --tts {azure,openai,edge,piper,coqui}
                        Elige proveedor TTS (predeterminado: azure). azure: Azure
                        Cognitive Services, openai: API TTS de OpenAI, edge: Edge TTS,
                        piper: Piper TTS, coqui: Coqui TTS. Cuando uses
                        azure, las variables de entorno MS_TTS_KEY y
                        MS_TTS_REGION deben estar configuradas. Cuando uses openai,
                        la variable de entorno OPENAI_API_KEY debe estar configurada.
  --log {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Nivel de registro (predeterminado: INFO), puede ser DEBUG, INFO,
                        WARNING, ERROR, CRITICAL
  --preview             Habilita modo vista previa. En modo vista previa, el script
                        no convertirá el texto a voz. En su lugar, imprimirá
                        el índice de capítulos, títulos y conteos de caracteres.
  --no_prompt           No pregunta al usuario si desea continuar después
                        de estimar el costo en la nube para TTS. Útil para
                        scripts.
  --language LANGUAGE   Idioma para el servicio de texto a voz (predeterminado: en-
                        US). Para Azure TTS (--tts=azure), verifica
                        https://learn.microsoft.com/en-us/azure/ai-
                        services/speech-service/language-
                        support?tabs=tts#text-to-speech para idiomas soportados.
                        Para OpenAI TTS (--tts=openai), su API
                        detecta el idioma automáticamente. Pero configurar esto
                        también ayudará a dividir el texto en chunks con
                        diferentes estrategias en esta herramienta, especialmente para
                        caracteres chinos. Para libros en chino, usa zh-CN, zh-
                        TW, o zh-HK.
  --newline_mode {single,double,none}
                        Elige el modo de detectar nuevos párrafos: 'single',
                        'double', o 'none'. 'single' significa un solo carácter
                        de nueva línea, mientras que 'double' significa dos caracteres
                        consecutivos de nueva línea. 'none' significa que todos los caracteres
                        de nueva línea serán reemplazados con espacios en blanco así que los párrafos
                        no serán detectados. (predeterminado: double, funciona para la mayoría
                        de libros electrónicos pero detectará menos párrafos para algunos
                        libros electrónicos)
  --title_mode {auto,tag_text,first_few}
                        Elige el modo de análisis para título de capítulo, 'tag_text'
                        busca etiquetas 'title','h1','h2','h3' para título,
                        'first_few' establece los primeros 60 caracteres como título, 'auto'
                        aplica automáticamente el mejor modo para el capítulo actual.
  --chapter_start CHAPTER_START
                        Índice de inicio de capítulo (predeterminado: 1, comenzando desde 1)
  --chapter_end CHAPTER_END
                        Índice de fin de capítulo (predeterminado: -1, significando hasta el último
                        capítulo)
  --output_text         Habilita Salida de Texto. Esto exportará un archivo de texto plano
                        para cada capítulo especificado y escribirá los archivos a la
                        carpeta de salida especificada.
  --remove_endnotes     Esto removerá números de notas al pie del final o
                        medio de oraciones. Esto es útil para libros
                        académicos.
  --search_and_replace_file SEARCH_AND_REPLACE_FILE
                        Ruta a un archivo que contiene 1 reemplazo regex por línea,
                        para ayudar con corrección de pronunciaciones, etc. El formato
                        es: <buscar>==<reemplazar> Nota que puedes tener que
                        especificar límites de palabras, para evitar reemplazar partes de
                        palabras.
  --worker_count WORKER_COUNT
                        Especifica el número de trabajadores paralelos a usar para 
                        generación de audiolibros. Incrementar este valor puede 
                        acelerar significativamente el proceso procesando 
                        múltiples capítulos simultáneamente. Nota: Los capítulos pueden 
                        no ser procesados en orden secuencial, pero esto no 
                        afectará el audiolibro final.

  --voice_name VOICE_NAME
                        Varios proveedores TTS tienen diferentes nombres de voz, busca
                        en la configuración de tu proveedor.
  --output_format OUTPUT_FORMAT
                        Formato de salida para el servicio de texto a voz.
                        El formato soportado depende del proveedor TTS seleccionado
  --model_name MODEL_NAME
                        Varios proveedores TTS tienen diferentes nombres de modelos neuronales

específico de openai:
  --speed SPEED         La velocidad del audio generado. Selecciona un valor de 0.25 a 4.0. 1.0 es el predeterminado.
  --instructions INSTRUCTIONS
                        Instrucciones para el modelo TTS. Solo soportado para el modelo 'gpt-4o-mini-tts'.

específico de edge:
  --voice_rate VOICE_RATE
                        Velocidad de habla del texto. Los valores relativos válidos van
                        desde -50%(--xxx='-50%') hasta +100%. Para valor negativo
                        usa formato --arg=value,
  --voice_volume VOICE_VOLUME
                        Nivel de volumen de la voz hablante. Los valores relativos válidos
                        van hasta -100%. Para valor negativo usa formato
                        --arg=value,
  --voice_pitch VOICE_PITCH
                        Tono base para el texto. Valores relativos válidos como
                        -80Hz,+50Hz, los cambios de tono deben estar dentro de 0.5 a 1.5
                        veces el audio original. Para valor negativo usa
                        formato --arg=value,
  --proxy PROXY         Servidor proxy para el proveedor TTS. Formato:
                        http://[username:password@]proxy.server:port

específico de azure/edge:
  --break_duration BREAK_DURATION
                        Duración de pausa en milisegundos para los diferentes
                        párrafos o secciones (predeterminado: 1250, significa 1.25 s).
                        Los valores válidos van de 0 a 5000 milisegundos para
                        Azure TTS.

específico de piper:
  --piper_path PIPER_PATH
                        Ruta al ejecutable Piper TTS
  --piper_speaker PIPER_SPEAKER
                        ID de hablante Piper, usado para modelos multi-hablante
  --piper_sentence_silence PIPER_SENTENCE_SILENCE
                        Segundos de silencio después de cada oración
  --piper_length_scale PIPER_LENGTH_SCALE
                        Duración de fonema, a.k.a. velocidad de habla
```  

**Ejemplo**:

```bash
python3 main.py examples/The_Life_and_Adventures_of_Robinson_Crusoe.epub carpeta_salida
```

Ejecutar el comando anterior generará un directorio llamado `carpeta_salida` y guardará los archivos MP3 para cada capítulo dentro de él usando el proveedor TTS y voz predeterminados. Una vez generados, puedes importar estos archivos de audio en [Audiobookshelf](https://github.com/advplyr/audiobookshelf) o reproducirlos con cualquier reproductor de audio de tu elección.

## Modo Vista Previa

Antes de convertir tu archivo epub a un audiolibro, puedes usar la opción `--preview` para obtener un resumen de cada capítulo. Esto te proporcionará el conteo de caracteres de cada capítulo y el conteo total, en lugar de convertir el texto a voz.

**Ejemplo**:

```bash
python3 main.py examples/The_Life_and_Adventures_of_Robinson_Crusoe.epub carpeta_salida --preview
```

## Buscar y Reemplazar

Puedes querer buscar y reemplazar texto, ya sea para expandir abreviaciones, o para ayudar con la pronunciación. Puedes hacer esto especificando un archivo de buscar y reemplazar, que contiene una sola búsqueda regex y reemplazo por línea, separados por '==':

**Ejemplo**:

**buscar.conf**:

```text
# esta es la estructura general
<buscar>==<reemplazar>
# esto es un comentario
# corregir abreviaciones de direcciones cardinales
N\.E\.==noreste
# ten cuidado con tus regex, ya que esto también coincidiría con Sally N. Smith
N\.==norte
# pronunciar Barbadoes como los locales
Barbadoes==Barbayduss
```

```bash
python3 main.py examples/The_Life_and_Adventures_of_Robinson_Crusoe.epub carpeta_salida --search_and_replace_file buscar.conf
```

## Usando con Docker

Esta herramienta está disponible como una imagen Docker, facilitando su ejecución sin necesidad de gestionar dependencias de Python.

Primero, asegúrate de tener Docker instalado en tu sistema.

Puedes obtener la imagen Docker del GitHub Container Registry:

```bash
docker pull ghcr.io/p0n1/epub_to_audiobook:latest
```

Luego, puedes ejecutar la herramienta con el siguiente comando:

```bash
docker run -i -t --rm -v ./:/app -e MS_TTS_KEY=$MS_TTS_KEY -e MS_TTS_REGION=$MS_TTS_REGION ghcr.io/p0n1/epub_to_audiobook tu_libro.epub salida_audiolibro --tts azure
```

Para OpenAI, puedes ejecutar:

```bash
docker run -i -t --rm -v ./:/app -e OPENAI_API_KEY=$OPENAI_API_KEY ghcr.io/p0n1/epub_to_audiobook tu_libro.epub salida_audiolibro --tts openai
```

Reemplaza `$MS_TTS_KEY` y `$MS_TTS_REGION` con tus credenciales de la API Azure Text-to-Speech. Reemplaza `$OPENAI_API_KEY` con tu clave API de OpenAI. Reemplaza `tu_libro.epub` con el nombre del archivo EPUB de entrada, y `salida_audiolibro` con el nombre del directorio donde quieres guardar los archivos de salida.

La opción `-v ./:/app` monta el directorio actual (`.`) al directorio `/app` en el contenedor Docker. Esto permite que la herramienta lea el archivo de entrada y escriba los archivos de salida a tu sistema de archivos local.

Las opciones `-i` y `-t` son requeridas para habilitar el modo interactivo y asignar un pseudo-TTY.

**También puedes verificar [este archivo de configuración de ejemplo](./docker-compose.example.yml) para el uso de docker compose.**

## Guía Amigable para Usuarios de Windows

Para usuarios de Windows, especialmente si no estás muy familiarizado con herramientas de línea de comandos, te tenemos cubierto. Entendemos los desafíos y hemos creado una guía específicamente diseñada para ti.

Revisa esta [guía paso a paso](https://gist.github.com/p0n1/cba98859cdb6331cc1aab835d62e4fba) y deja un mensaje si encuentras problemas.

## ¿Cómo Obtener tu Clave de Azure Cognitive Service?

- Suscripción de Azure - [Crea una gratis](https://azure.microsoft.com/free/cognitive-services)
- [Crea un recurso de Speech](https://portal.azure.com/#create/Microsoft.CognitiveServicesSpeechServices) en el portal de Azure.
- Obtén la clave y región del recurso Speech. Después de que tu recurso Speech sea desplegado, selecciona **Ir al recurso** para ver y gestionar claves. Para más información sobre recursos de Cognitive Services, consulta [Obtener las claves para tu recurso](https://learn.microsoft.com/en-us/azure/cognitive-services/cognitive-services-apis-create-account#get-the-keys-for-your-resource).

*Fuente: <https://learn.microsoft.com/en-us/azure/cognitive-services/speech-service/get-started-text-to-speech#prerequisites>*

## ¿Cómo Obtener tu Clave API de OpenAI?

Revisa https://platform.openai.com/docs/quickstart/account-setup. Asegúrate de revisar los detalles de [precios](https://openai.com/pricing) antes de usar.

## ✨ Acerca de Edge TTS

Edge TTS y Azure TTS son casi lo mismo, la diferencia es que Edge TTS no requiere Clave API porque está basado en la funcionalidad de lectura en voz alta de Edge, y los parámetros están un poco restringidos, como [ssml personalizado](https://github.com/rany2/edge-tts#custom-ssml).

Revisa https://gist.github.com/BettyJJ/17cbaa1de96235a7f5773b8690a20462 para voces soportadas.

**Si quieres probar este proyecto rápidamente, Edge TTS es altamente recomendado.**

## Personalización de Voz e Idioma

Puedes personalizar la voz e idioma usado para la conversión Text-to-Speech pasando las opciones `--voice_name` y `--language` al ejecutar el script.

Microsoft Azure ofrece una gama de voces e idiomas para el servicio Text-to-Speech. Para una lista de opciones disponibles, consulta la [documentación de Microsoft Azure Text-to-Speech](https://learn.microsoft.com/en-us/azure/cognitive-services/speech-service/language-support?tabs=tts#text-to-speech).

También puedes escuchar muestras de las voces disponibles en la [Galería de Voces Azure TTS](https://aka.ms/speechstudio/voicegallery) para ayudarte a elegir la mejor voz para tu audiolibro.

Por ejemplo, si quieres usar una voz femenina en inglés británico para la conversión, puedes usar el siguiente comando:

```bash
python3 main.py <archivo_entrada> <carpeta_salida> --voice_name en-GB-LibbyNeural --language en-GB
```

Para OpenAI TTS, puedes especificar las opciones de modelo, voz y formato usando `--model_name`, `--voice_name`, y `--output_format`, respectivamente.

## Más Ejemplos

Aquí hay algunos ejemplos que demuestran varias combinaciones de opciones:

### Ejemplos Usando Azure TTS

1. **Conversión básica usando Azure con configuraciones predeterminadas**  
   Este comando convertirá un archivo EPUB a un audiolibro usando las configuraciones TTS predeterminadas de Azure.

   ```sh
   python3 main.py "ruta/al/libro.epub" "ruta/a/carpeta/salida" --tts azure
   ```

2. **Conversión Azure con idioma personalizado, voz y nivel de registro**  
   Convierte un archivo EPUB a un audiolibro con una voz especificada y un nivel de registro personalizado para propósitos de depuración.

   ```sh
   python3 main.py "ruta/al/libro.epub" "ruta/a/carpeta/salida" --tts azure --language es-ES --voice_name "es-ES-ElviraNeural" --log DEBUG
   ```

3. **Conversión Azure con rango de capítulos y duración de pausa**  
   Convierte un rango específico de capítulos de un archivo EPUB a un audiolibro con duración de pausa personalizada entre párrafos.

   ```sh
   python3 main.py "ruta/al/libro.epub" "ruta/a/carpeta/salida" --tts azure --chapter_start 5 --chapter_end 10 --break_duration "1500"
   ```

### Ejemplos Usando OpenAI TTS

1. **Conversión básica usando OpenAI con configuraciones predeterminadas**  
   Este comando convertirá un archivo EPUB a un audiolibro usando las configuraciones TTS predeterminadas de OpenAI.

   ```sh
   python3 main.py "ruta/al/libro.epub" "ruta/a/carpeta/salida" --tts openai
   ```

2. **Conversión OpenAI con modelo HD y voz específica**  
   Convierte un archivo EPUB a un audiolibro usando el modelo de alta definición de OpenAI y una elección de voz específica.

   ```sh
   python3 main.py "ruta/al/libro.epub" "ruta/a/carpeta/salida" --tts openai --model_name "tts-1-hd" --voice_name "fable"
   ```

3. **Conversión OpenAI con vista previa y salida de texto**  
   Habilita el modo vista previa y salida de texto, que mostrará el índice y títulos de capítulos en lugar de convertirlos y también exportará el texto.

   ```sh
   python3 main.py "ruta/al/libro.epub" "ruta/a/carpeta/salida" --tts openai --preview --output_text
   ```

## Ejemplo usando un servicio compatible con OpenAI

Es posible usar un servicio compatible con OpenAI, como [matatonic/openedai-speech](https://github.com/matatonic/openedai-speech). En ese caso, **es requerido** configurar la variable de entorno `OPENAI_BASE_URL`, de otro modo solo usaría por defecto el servicio estándar de OpenAI. Mientras que el servicio compatible podría no requerir una clave API, el cliente OpenAI sí lo hace, así que asegúrate de configurarla a algo sin sentido.

Si tu servicio compatible con OpenAI está ejecutándose en `http://127.0.0.1:8000` y has agregado una voz personalizada llamada `skippy`, puedes usar el siguiente comando:

```shell
docker run -i -t --rm -v ./:/app -e OPENAI_BASE_URL=http://127.0.0.1:8000/v1 -e OPENAI_API_KEY=nope ghcr.io/p0n1/epub_to_audiobook tu_libro.epub salida_audiolibro --tts openai --voice_name=skippy --model_name=tts-1-hd
```

Desplázate hacia abajo al ejemplo de Kokoro TTS para ver un ejemplo más específico de esto.

### Ejemplos Usando Edge TTS

1. **Conversión básica usando Edge con configuraciones predeterminadas**  
   Este comando convertirá un archivo EPUB a un audiolibro usando las configuraciones TTS predeterminadas de Edge.

   ```sh
   python3 main.py "ruta/al/libro.epub" "ruta/a/carpeta/salida" --tts edge
   ```

2. **Conversión Edge con idioma personalizado, voz y nivel de registro**
   Convierte un archivo EPUB a un audiolibro con una voz especificada y un nivel de registro personalizado para propósitos de depuración.

   ```sh
   python3 main.py "ruta/al/libro.epub" "ruta/a/carpeta/salida" --tts edge --language es-ES --voice_name "es-ES-AlvaroNeural" --log DEBUG
   ```

3. **Conversión Edge con rango de capítulos y duración de pausa**
   Convierte un rango específico de capítulos de un archivo EPUB a un audiolibro con duración de pausa personalizada entre párrafos.

   ```sh
   python3 main.py "ruta/al/libro.epub" "ruta/a/carpeta/salida" --tts edge --chapter_start 5 --chapter_end 10 --break_duration "1500"
   ```

### Ejemplos Usando Piper TTS

*Asegúrate de tener instalado Piper TTS y tener un archivo de modelo onnx y archivo de configuración correspondiente. Revisa [Piper TTS](https://github.com/rhasspy/piper) para más detalles. Puedes seguir sus instrucciones para instalar Piper TTS, descargar los modelos y archivos de configuración, jugar con él y luego regresar para probar los ejemplos a continuación.*

Este comando convertirá un archivo EPUB a un audiolibro usando Piper TTS usando los parámetros mínimos requeridos.
Siempre necesitas especificar un archivo de modelo onnx y el ejecutable `piper` necesita estar en el $PATH actual.

```sh
python3 main.py "ruta/al/libro.epub" "ruta/a/carpeta/salida" --tts piper --model_name <ruta_a>/en_US-libritts_r-medium.onnx
```

Puedes especificar tu ruta personalizada al ejecutable piper usando el parámetro `--piper_path`.

```sh
python3 main.py "ruta/al/libro.epub" "ruta/a/carpeta/salida" --tts piper --model_name <ruta_a>/en_US-libritts_r-medium.onnx --piper_path <ruta_a>/piper
```

Algunos modelos soportan múltiples voces y eso puede ser especificado usando el parámetro voice_name.

```sh
python3 main.py "ruta/al/libro.epub" "ruta/a/carpeta/salida" --tts piper --model_name <ruta_a>/en_US-libritts_r-medium.onnx --piper_speaker 256
```

También puedes especificar velocidad (piper_length_scale) y duración de pausa (piper_sentence_silence).

```sh
python3 main.py "ruta/al/libro.epub" "ruta/a/carpeta/salida" --tts piper --model_name <ruta_a>/en_US-libritts_r-medium.onnx --piper_speaker 256 --piper_length_scale 1.5 --piper_sentence_silence 0.5
```

Piper TTS genera archivos en formato `wav` (o raw) por defecto, deberías poder especificar cualquier formato razonable a través del parámetro `--output_format`. `opus` y `mp3` son buenas opciones para tamaño y compatibilidad.

```sh
python3 main.py "ruta/al/libro.epub" "ruta/a/carpeta/salida" --tts piper --model_name <ruta_a>/en_US-libritts_r-medium.onnx --piper_speaker 256 --piper_length_scale 1.5 --piper_sentence_silence 0.5 --output_format opus
```

*Alternativamente, puedes usar el siguiente procedimiento para usar piper en un contenedor docker, que simplifica el proceso de ejecutar todo localmente.*

1. Asegúrate de tener docker desktop instalado en tu sistema. Ve a [Docker](https://www.docker.com/) para instalar (o usa la fórmula de [homebrew](https://formulae.brew.sh/formula/docker)).
2. Descarga un modelo y archivo de configuración Piper (ve el [repo de piper](https://github.com/rhasspy/piper) para detalles) y colócalos en el directorio [piper_models](./piper_models/) en el nivel superior de este proyecto.
3. Edita el [archivo docker compose](./docker-compose.piper-example.yml) para:
   - En el contenedor `piper`, configura la variable de entorno `PIPER_VOICE` al nombre del archivo de modelo que descargaste.
   - En el contenedor `piper`, mapea los `volumes` a la ubicación de los modelos piper en tu sistema (si usaste el directorio proporcionado descrito en el paso 2, puedes dejar esto como está).
   - En el contenedor `epub_to_audiobook`, actualiza el mapeo de `volumes` desde `<path/to/epub/dir/on/host>` a la ruta real al epub en tu máquina host.
4. Desde la raíz del repo, ejecuta `PATH_TO_EPUB_FILE=./Tu_archivo_epub.epub OUTPUT_DIR=$(pwd)/path/to/audiobook_output docker compose -f docker-compose.piper-example.yml up --build`, **reemplazando los valores de marcador de posición y directorios de salida con tu fuente epub deseada y salida de audio respectivamente**. (¡Deja el $(pwd)!) Nota que la configuración actual en el docker compose iniciará automáticamente el proceso, completamente en el contenedor. Si quieres ejecutar el proceso principal de python fuera del contenedor, puedes descomentar el comando `command: tail -f /dev/null`, y usar `docker exec -it epub_to_audiobook /bin/bash` para conectarte al contenedor y ejecutar el script de python manualmente (ve comentarios en el [archivo docker compose](./docker-compose.piper-example.yml) para más detalles).

### Ejemplos Usando Coqui TTS

Coqui TTS proporciona síntesis de texto a voz local de alta calidad usando varios modelos neuronales. Los modelos se descargan automáticamente en el primer uso.

1. **Conversión básica usando Coqui con configuraciones predeterminadas**  
   Este comando convertirá un archivo EPUB a un audiolibro usando el modelo inglés predeterminado de Coqui.

   ```sh
   python3 main.py "ruta/al/libro.epub" "ruta/a/carpeta/salida" --tts coqui
   ```

2. **Conversión Coqui con idioma y modelo específicos**  
   Convierte un archivo EPUB a un audiolibro usando un idioma y modelo específicos.

   ```sh
   python3 main.py "ruta/al/libro.epub" "ruta/a/carpeta/salida" --tts coqui --language en --model_name "tts_models/en/ljspeech/tacotron2-DDC_ph"
   ```

3. **Conversión Coqui con ruta de modelo personalizada**  
   Usa un archivo de modelo Coqui personalizado si lo has descargado manualmente.

   ```sh
   python3 main.py "ruta/al/libro.epub" "ruta/a/carpeta/salida" --tts coqui --model_name "/ruta/al/modelo/personalizado.pth"
   ```

4. **Conversión Coqui con parámetros personalizados**  
   Ajusta velocidad de habla, ruido y variabilidad para calidad de audio finamente ajustada.

   ```sh
   python3 main.py "ruta/al/libro.epub" "ruta/a/carpeta/salida" --tts coqui --model_name "tts_models/en/ljspeech/tacotron2-DDC" --coqui_length_scale 0.8 --coqui_noise_scale 0.5 --coqui_noise_w_scale 0.6
   ```

### Ejemplos usando Kokoro TTS

El uso documentado de Kokoro TTS con este script usa una imagen docker con endpoints que son compatibles con OpenAI. Sin embargo, ya que es un servicio "auto-hospedado", no necesitarás obtener una clave real. Esto requiere docker, así que sigue las instrucciones de instalación y configuración de docker arriba en la sección Piper si no tienes docker en tu máquina.

Para ejecutar, en una pestaña de terminal, ejecuta:

```bash
docker run -p 8880:8880 ghcr.io/remsky/kokoro-fastapi-cpu
```

O si tienes una GPU que puede ayudar con el procesamiento, ejecuta:

```bash
docker run --gpus all -p 8880:8880 ghcr.io/remsky/kokoro-fastapi-gpu
```

Luego en otra pestaña, ejecuta:

```bash
export OPENAI_BASE_URL=http://localhost:8880/v1
export OPENAI_API_KEY="fake"
python main.py ruta/al/epub directorio-salida --tts openai --voice_name "af_bella(3)+af_alloy(1)" --model_name "tts-1" #puedes reemplazar esto con cualquier otro nombre de voz. Enlace abajo.
```
Nota que pasar el parámetro `--model_name tts-1` **es requerido** ya que kokoro falla con el valor predeterminado actual de model_name.

Alternativamente, puedes hacer toda la configuración a través de docker compose usando el [archivo docker compose configurado para kokoro](./docker-compose.kokoro-example.yml).

Para hacer esto, abre el archivo con tu editor favorito y luego:

- Desde la raíz del repo, ejecuta `PATH_TO_EPUB_FILE=./Tu_archivo_epub.epub OUTPUT_DIR=$(pwd)/path/to/audiobook_output VOICE_NAME=Tu_voz_deseada docker compose -f docker-compose.kokoro-example.yml up --build`, **reemplazando los valores de marcador de posición y directorios de salida con tu fuente epub deseada y salida de audio respectivamente, y tu nombre de voz**.
  - Una lista de voces se puede encontrar [aquí](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md), y puedes escuchar cómo suenan [aquí](https://huggingface.co/spaces/hexgrad/Kokoro-TTS).
- Nota que la configuración actual en el docker compose iniciará automáticamente el proceso, completamente en el contenedor. Si quieres ejecutar el proceso principal de python fuera del contenedor, puedes descomentar el comando `command: tail -f /dev/null`, y usar `docker exec -it epub_to_audiobook /bin/bash` para conectarte al contenedor y ejecutar el script de python manualmente (ve comentarios en el [archivo docker compose](./docker-compose.kokoro-example.yml) para más detalles).

Para más información sobre la imagen usada para kokoro tts, visita este [repo](https://github.com/remsky/Kokoro-FastAPI).

## Integración Mejorada de Kokoro TTS

### 🎯 Nuevas Características

**Español:**
- **Pestaña Dedicada para Kokoro**: Pestaña específica en la UI para configuración de Kokoro TTS
- **Selector de Idiomas**: Elige entre 9 idiomas incluyendo español, inglés, francés, etc.
- **Filtrado de Voces**: Filtrado inteligente muestra voces relevantes según el idioma seleccionado
- **Más de 67 Voces Disponibles**: Acceso a todas las voces de Kokoro incluyendo españolas como `em_santa`, `ef_dora`, `em_alex`
- **Configuración Automática**: Variables de entorno configuradas automáticamente para operación sin problemas
- **Soporte para Parámetro de Idioma**: Usa peticiones HTTP directas para soportar el parámetro de idioma de Kokoro

### 🎤 Voces en Español

Las siguientes voces en español están ahora disponibles a través de la UI mejorada:

| Nombre de Voz | Descripción |
|---------------|-------------|
| `em_santa` | Voz masculina española |
| `pm_santa` | Voz masculina española alternativa |
| `am_santa` | Otra variante masculina española |
| `ef_dora` | Voz femenina española |
| `pf_dora` | Voz femenina española alternativa |
| `em_alex` | Voz masculina española |
| `pm_alex` | Voz masculina española alternativa |

### 🌍 Códigos de Idioma

| Código | Idioma |
|--------|--------|
| `a` | Inglés (EE.UU.) |
| `b` | Inglés Británico |
| `e` | Español |
| `f` | Francés |
| `h` | Hindi |
| `i` | Italiano |
| `j` | Japonés |
| `p` | Portugués |
| `z` | Chino |

### 🚀 Inicio Rápido con Voces Españolas

1. Iniciar servidor Kokoro: `docker run -p 8880:8880 ghcr.io/remsky/kokoro-fastapi-cpu`
2. Ejecutar WebUI: `python main_ui.py`
3. Abrir `http://127.0.0.1:7860` en navegador
4. Hacer clic en pestaña "Kokoro"
5. Seleccionar idioma "Spanish"
6. Elegir voz (ej: `em_santa`, `ef_dora`)
7. Subir EPUB y hacer clic en "Start"

### 🔧 Mejoras Técnicas

- **Cliente OpenAI Híbrido**: Detecta automáticamente cuándo usar peticiones HTTP directas vs SDK de OpenAI
- **Soporte para Parámetro de Idioma**: Manejo adecuado del parámetro de idioma de Kokoro no soportado por el SDK de OpenAI
- **Descubrimiento Inteligente de Voces**: Obtiene voces dinámicamente del servidor Kokoro
- **Manejo de Errores**: Recuperación elegante cuando el parámetro de idioma no es soportado
- **Auto-configuración del Entorno**: Configura automáticamente `OPENAI_BASE_URL` y `OPENAI_API_KEY`

## Solución de Problemas

### ModuleNotFoundError: No module named 'importlib_metadata'

Esto puede ser porque la versión de Python que estás usando es [menor que 3.8](https://stackoverflow.com/questions/73165636/no-module-named-importlib-metadata). Puedes intentar instalarlo manualmente con `pip3 install importlib-metadata`, o usar una versión más alta de Python.

### FileNotFoundError: [Errno 2] No such file or directory: 'ffmpeg'

Asegúrate de que el binario ffmpeg sea accesible desde tu path. Si estás en mac y usas homebrew, puedes hacer `brew install ffmpeg`, En Ubuntu puedes hacer `sudo apt install ffmpeg`

### Instalación de FFmpeg

**Windows:**
El script descarga automáticamente FFmpeg si no está disponible. También puedes instalarlo manualmente:

```bash
# Usando Chocolatey
choco install ffmpeg

# Usando winget
winget install Gyan.FFmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# CentOS/RHEL
sudo yum install ffmpeg

# Fedora
sudo dnf install ffmpeg
```

### Piper TTS

Para problemas relacionados con la instalación, por favor consulta el repositorio [Piper TTS](https://github.com/rhasspy/piper). Es importante notar que si estás instalando `piper-tts` vía pip, [solo Python 3.10](https://github.com/rhasspy/piper/issues/509) está actualmente soportado. Los usuarios de Mac pueden encontrar desafíos adicionales cuando usen el [binario](https://github.com/rhasspy/piper/issues/523) descargado. Para más información sobre problemas específicos de Mac, por favor revisa [este issue](https://github.com/rhasspy/piper/issues/395) y [este pull request](https://github.com/rhasspy/piper/pull/412).

También revisa [esto](https://github.com/p0n1/epub_to_audiobook/issues/85) si estás teniendo problemas con Piper TTS.

### Kokoro TTS

**Instalación separada requerida:**
Kokoro TTS requiere ejecutar un servidor Docker separado. No está incluido en la instalación principal.

**Pasos de instalación:**
1. Instalar Docker en tu sistema
2. Ejecutar servidor Kokoro:
   ```bash
   # Para CPU
   docker run -p 8880:8880 ghcr.io/remsky/kokoro-fastapi-cpu
   
   # Para GPU (si está disponible)
   docker run --gpus all -p 8880:8880 ghcr.io/remsky/kokoro-fastapi-gpu
   ```
3. El servidor estará disponible en `http://localhost:8880`

**Problemas comunes:**
- **Puerto 8880 ocupado**: Cambia el puerto usando `-p 8881:8880`
- **Sin Docker**: Instala Docker Desktop desde https://docker.com
- **Problemas de GPU**: Usa la versión CPU si tienes problemas con GPU

## Información del Repositorio

**Repositorio Principal:** [SourceForge](https://sourceforge.net/projects/epub-to-audiobook/)
- Repositorio Git: `https://git.code.sf.net/p/epub-to-audiobook/code`
- Clon SSH: `ssh://krory90@git.code.sf.net/p/epub-to-audiobook/code`

**Repositorio Espejo:** [GitHub](https://github.com/kroryan/epub_to_audiobook_exe)

## Proyectos Relacionados

- [Epub to Audiobook (M4B)](https://github.com/duplaja/epub-to-audiobook-hf): Epub a Audiolibro MB4, con StyleTTS2 vía API de HuggingFace Spaces.
- [Storyteller](https://storyteller-platform.gitlab.io/storyteller/): Una plataforma auto-hospedada para sincronizar automáticamente libros electrónicos y audiolibros.

## Licencia

Este proyecto está licenciado bajo la Licencia MIT. Ve el archivo [LICENSE](LICENSE) para detalles.