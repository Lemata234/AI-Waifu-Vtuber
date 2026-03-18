import socket
import threading
import wave

import keyboard
import ollama
import pyaudio
import pytchat
import winsound
from emoji import demojize

from utils.TTS import *
from utils.promptMaker import *
from utils.subtitle import *
from utils.translate import *
from utils.twitch_config import *

# ESTE ES EL LINK DE DRIVE PARA EL ARCHIVO MODEL.PT QUE PESA 54 MB:
# https://drive.google.com/drive/folders/1uQ8XTQyBSxrwD7qRdGUeUIxTDaBD4Sfe?hl=es

# ANTES DE USAR ESTA VERSIÓN, YA QUE JODIMOS EL ENTORNO VIRTUAL, USA ESTE COMANDO LA PRIMERA VEZ QUE VAYAS
# A USAR EL POWER SHELL: .\.venv\Scripts\Activate.ps1
# CON ESE COMANDO SI TE VA A ADMITIR ESCRIBIR PYTHON RUN.PY
# id de stream yt:
# id de stream twitch:

# Configurar consola para UTF-8
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf8', buffering=1)

# ============================================
# CONFIGURACIÓN GLOBAL
# ============================================
conversation = []
history = {"history": conversation}

mode = 0
total_characters = 0
chat = ""
chat_now = ""
chat_prev = ""
is_Speaking = False
owner_name = "Usuario"
blacklist = ["Nightbot", "streamelements"]

# Modelo de Ollama (cambiar si es necesario)
OLLAMA_MODEL = "gemma3:4b"

# Nombre del dispositivo de cable virtual (VB-Audio Virtual Cable)
CABLE_DEVICE_NAME = "CABLE Input"

# NUEVO: Variable global para almacenar el último idioma detectado
current_language = "es"

# ============================================
# FUNCIÓN: Grabar audio desde micrófono
# ============================================
def record_audio():
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100
    WAVE_OUTPUT_FILENAME = "input.wav"

    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    frames = []
    print("🎤 Grabando... (mantén M)")
    while keyboard.is_pressed('M'):
        data = stream.read(CHUNK)
        frames.append(data)

    print("⏹️ Grabación detenida.")
    stream.stop_stream()
    stream.close()
    p.terminate()

    wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

    transcribe_audio("input.wav")

# ============================================
# FUNCIÓN: Transcribir audio a texto (detección automática de idioma)
# ============================================
def transcribe_audio(file):
    global chat_now, current_language  # NUEVO

    try:
        import speech_recognition as sr
        recognizer = sr.Recognizer()

        with sr.AudioFile(file) as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.record(source)


        # NUEVO: Usar detección automática de idioma de Google Speech
        try:
            chat_now = recognizer.recognize_google(audio)  # sin parámetro language, usa auto-detect  # sin language, usa auto-detect.  # None = detección automática
            print(f"🗣️ Tú: {chat_now}")
        except sr.UnknownValueError:
            print("❌ No se pudo entender el audio")
            return
        except sr.RequestError:
            print("❌ Error con el servicio de reconocimiento")
            return

        # NUEVO: Detectar el idioma del texto transcrito
        from utils.translate import detect_google
        current_language = detect_google(chat_now)
        print(f"🌐 Idioma detectado: {current_language}")

    except Exception as e:
        print(f"❌ Error transcribiendo audio: {e}")
        return

    result = owner_name + " dijo: " + chat_now
    conversation.append({'role': 'user', 'content': result})
    ollama_answer()

# ============================================
# FUNCIÓN: Obtener respuesta de Ollama
# ============================================
def ollama_answer():
    global total_characters, conversation

    # Limitar historial para no saturar memoria
    total_characters = sum(len(d['content']) for d in conversation)
    while total_characters > 4000:
        try:
            conversation.pop(2)
            total_characters = sum(len(d['content']) for d in conversation)
        except Exception as e:
            print(f"Error limpiando historial: {e}")

    # Guardar conversación
    with open("conversation.json", "w", encoding="utf-8") as f:
        json.dump(history, f, indent=4)

    # NUEVO: Obtener prompt pasando el idioma actual
    prompt = getPrompt(current_language)

    # Llamar a Ollama
    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=prompt,
            options={
                "num_predict": 150,
                "temperature": 0.8,
                "top_p": 0.9
            }
        )
        message = response['message']['content']
    except Exception as e:
        print(f"❌ Error llamando a Ollama: {e}")
        message = "Lo siento, tuve un problema. ¿Puedes repetir la pregunta?"

    conversation.append({'role': 'assistant', 'content': message})
    translate_text(message)

# ============================================
# FUNCIÓN: Generar voz y enviar a cable virtual (multilingüe)
# ============================================
def translate_text(text):
    global is_Speaking, chat_now, current_language  # NUEVO: usar current_language

    # Mostrar respuesta
    print(f"\n🤖 Mombii ({current_language}): {text}")

    # Generar subtítulo
    generate_subtitle(chat_now, text)

    is_Speaking = True

    # NUEVO: Usar función multilingüe de TTS
    try:
        from utils.TTS import hablar_en_idioma
        hablar_en_idioma(text, current_language, CABLE_DEVICE_NAME)
    except Exception as e:
        print(f"❌ Error generando voz: {e}")
        winsound.Beep(500, 500)

    is_Speaking = False

    # Limpiar archivos
    time.sleep(1)
    for archivo in ["output.txt", "chat.txt"]:
        try:
            with open(archivo, "w", encoding="utf-8") as f:
                f.truncate(0)
        except:
            pass

# ============================================
# FUNCIÓN: Capturar chat de YouTube (con detección de idioma)
# ============================================
def yt_livechat(video_id):
    global chat, current_language  # NUEVO
    live = pytchat.create(video_id=video_id)
    while live.is_alive():
        try:
            for c in live.get().sync_items():
                if c.author.name in blacklist:
                    continue
                if not c.message.startswith("!"):
                    chat_raw = re.sub(r':[^\s]+:', '', c.message)
                    chat_raw = chat_raw.replace('#', '')

                    # NUEVO: Detectar idioma del mensaje
                    from utils.translate import detect_google
                    idioma_msg = detect_google(chat_raw)
                    current_language = idioma_msg
                    print(f"🌐 Idioma del chat: {idioma_msg}")

                    chat = c.author.name + ' dijo: ' + chat_raw
                    print(chat)
                time.sleep(1)
        except Exception as e:
            print(f"Error en chat de YT: {e}")

# ============================================
# FUNCIÓN: Capturar chat de Twitch (con detección de idioma)
# ============================================
def twitch_livechat():
    global chat, current_language
    sock = socket.socket()
    sock.connect((server, port))

    # Enviar autenticación
    sock.send(f"PASS {token}\n".encode('utf-8'))
    sock.send(f"NICK {nickname}\n".encode('utf-8'))
    sock.send(f"JOIN {channel}\n".encode('utf-8'))

    # Pequeña espera para que el servidor procese
    time.sleep(1)

    regex = r":(\w+)!\w+@\w+\.tmi\.twitch\.tv PRIVMSG #\w+ :(.+)"

    while True:
        try:
            resp = sock.recv(2048).decode('utf-8', errors='ignore')

            # Mostrar todo lo que llega (para depuración)
            print(f"[DEBUG RAW] {repr(resp)}")

            # Responder a PING para mantener la conexión viva
            if resp.startswith('PING'):
                sock.send("PONG\n".encode('utf-8'))
                continue

            # Procesar solo líneas que contengan PRIVMSG
            if 'PRIVMSG' in resp:
                # Limpiar y procesar
                resp = demojize(resp)
                match = re.match(regex, resp)

                if match:
                    username = match.group(1)
                    message = match.group(2)

                    # Opcional: ignorar mensajes del propio bot para no crear un loop
                    # if username.lower() == nickname.lower():
                    #    continue

                    if username in blacklist:
                        continue

                    # Detectar idioma
                    from utils.translate import detect_google
                    idioma_msg = detect_google(message)
                    current_language = idioma_msg
                    print(f"🌐 Idioma del chat: {idioma_msg}")

                    # Asignar a la variable global chat para que el hilo preparation lo tome
                    chat = username + ' dijo: ' + message
                    print(chat)
                else:
                    print(f"⚠️ Línea PRIVMSG no coincide con regex: {resp.strip()}")
            else:
                # Líneas de bienvenida o de otro tipo, solo ignorar
                pass

        except Exception as e:
            print(f"Error en chat de Twitch: {e}")
            time.sleep(1)  # Evitar saturar en caso de error continuo

            # ============================================
# FUNCIÓN: Chat por texto (modo 4)
# ============================================
def chat_texto():
    global chat, current_language, is_Speaking
    print("\n" + "="*50)
    print("   MODO CHAT POR TEXTO")
    print("   Escribe tu mensaje y presiona ENTER")
    print("   Escribe 'salir' para volver al menú")
    print("="*50 + "\n")

    while True:
        try:
            # Mostrar prompt y leer mensaje
            mensaje = input("Tú: ").strip()

            if mensaje.lower() == 'salir':
                print("\n👋 Saliendo del modo chat...")
                break

            if mensaje:
                # Detectar idioma del mensaje
                from utils.translate import detect_google
                current_language = detect_google(mensaje)

                # Asignar a la variable global que vigila preparation()
                chat = "Usuario dijo: " + mensaje
                print(f"🌐 Idioma detectado: {current_language}")

                # --- NUEVO: Esperar a que Mombii termine de hablar ---
                # Esto evita que el siguiente prompt se muestre antes de la respuesta
                while is_Speaking:
                    time.sleep(0.1)
                # También esperar un poco más para asegurar que la respuesta se ha mostrado
                time.sleep(0.5)

        except KeyboardInterrupt:
            print("\n👋 Saliendo del modo chat...")
            break
        except Exception as e:
            print(f"❌ Error en chat de texto: {e}")
            time.sleep(1)






# ============================================
# FUNCIÓN: Preparación (hilo principal)
# ============================================
def preparation():
    global conversation, chat_now, chat, chat_prev
    while True:
        chat_now = chat
        if not is_Speaking and chat_now and chat_now != chat_prev:
            conversation.append({'role': 'user', 'content': chat_now})
            chat_prev = chat_now
            ollama_answer()
        time.sleep(1)

# ============================================
# MAIN
# ============================================
if __name__ == "__main__":
    try:
        print("=" * 50)
        print("   ASISTENTE MOMBII - MODO MULTILINGÜE")
        print("   Responde en el mismo idioma en que le hablen")
        print("=" * 50)
        print("Modos disponibles:")
        print("1 - Micrófono (habla con MOMBII)")
        print("2 - YouTube Live")
        print("3 - Twitch Live")
        print("4 - Chat por texto")  # <--- NUEVA OPCIÓN

        mode = input("Selecciona modo (1, 2, 3 o 4): ")

        if mode == "1":
            print("\n🎤 Modo MICRÓFONO")
            print("Mantén presionada la tecla M para hablar")
            print("Suelta la tecla para que MOMBII procese tu mensaje\n")
            while True:
                if keyboard.is_pressed('M'):
                    record_audio()

        elif mode == "2":
            live_id = input("ID del live de YouTube: ")
            t = threading.Thread(target=preparation)
            t.start()
            yt_livechat(live_id)

        elif mode == "3":
            print("Usando configuración de Twitch...")
            t = threading.Thread(target=preparation)
            t.start()
            twitch_livechat()

        elif mode == "4":  # <--- NUEVO MODO
            t = threading.Thread(target=preparation)
            t.start()
            chat_texto()

    except KeyboardInterrupt:
        print("\n👋 Programa terminado.")
        try:
            t.join()
        except:
            pass
