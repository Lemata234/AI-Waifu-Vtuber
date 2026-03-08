import ollama
import winsound
import sys
import pytchat
import time
import re
import pyaudio
import keyboard
import wave
import threading
import json
import socket
from emoji import demojize
from config import *
from utils.translate import *
from utils.TTS import *
from utils.subtitle import *
from utils.promptMaker import *
from utils.twitch_config import *


# ESTE ES EL LINK DE DRIVE PARA EL ARCHIVO MODEL.PT QUE PESA 54 MB:
# https://drive.google.com/drive/folders/1uQ8XTQyBSxrwD7qRdGUeUIxTDaBD4Sfe?hl=es

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
# En VB-Audio, el dispositivo de salida se llama "CABLE Input"
CABLE_DEVICE_NAME = "CABLE Input"

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
    print("🎤 Grabando... (mantén RIGHT SHIFT)")
    while keyboard.is_pressed('RIGHT_SHIFT'):
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
# FUNCIÓN: Transcribir audio a texto (español)
# ============================================
def transcribe_audio(file):
    global chat_now
    try:
        import speech_recognition as sr
        recognizer = sr.Recognizer()

        with sr.AudioFile(file) as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.record(source)

        # Reconocimiento en español
        try:
            chat_now = recognizer.recognize_google(audio, language="es-ES")
            print(f"🗣️ Tú: {chat_now}")
        except sr.UnknownValueError:
            print("❌ No se pudo entender el audio")
            return
        except sr.RequestError:
            print("❌ Error con el servicio de reconocimiento")
            return

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

    # Obtener prompt con la personalidad
    prompt = getPrompt()

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
# FUNCIÓN: Generar voz y enviar a cable virtual
# ============================================
def translate_text(text):
    global is_Speaking, chat_now

    # Mostrar respuesta
    print(f"\n🤖 Mombii: {text}")

    # Generar subtítulo
    generate_subtitle(chat_now, text)

    # Generar voz con pyttsx3 (español)
    is_Speaking = True

    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty('rate', 160)
        engine.setProperty('volume', 0.9)

        # Buscar voz en español
        voices = engine.getProperty('voices')
        voz_es = None
        for voice in voices:
            if 'spanish' in voice.name.lower() or 'español' in voice.name.lower():
                voz_es = voice.id
                print(f"✅ Voz encontrada: {voice.name}")
                break

        if voz_es:
            engine.setProperty('voice', voz_es)
        else:
            print("⚠️ No se encontró voz en español, usando voz por defecto")

        # Guardar el audio en un archivo
        engine.save_to_file(text, 'test.wav')
        engine.runAndWait()

        # Reproducir en el cable virtual (para VTube Studio)
        try:
            from utils.TTS import reproducir_en_cable
            print(f"🔊 Enviando audio a {CABLE_DEVICE_NAME}...")
            reproducir_en_cable("test.wav", CABLE_DEVICE_NAME)
        except Exception as e:
            print(f"⚠️ Error con cable virtual: {e}")
            print("🔊 Reproduciendo por altavoz normal...")
            winsound.PlaySound("test.wav", winsound.SND_FILENAME)

    except Exception as e:
        print(f"❌ Error generando voz: {e}")
        # Fallback: Beep de emergencia
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
# FUNCIÓN: Capturar chat de YouTube
# ============================================
def yt_livechat(video_id):
    global chat
    live = pytchat.create(video_id=video_id)
    while live.is_alive():
        try:
            for c in live.get().sync_items():
                if c.author.name in blacklist:
                    continue
                if not c.message.startswith("!"):
                    chat_raw = re.sub(r':[^\s]+:', '', c.message)
                    chat_raw = chat_raw.replace('#', '')
                    chat = c.author.name + ' dijo: ' + chat_raw
                    print(chat)
                time.sleep(1)
        except Exception as e:
            print(f"Error en chat de YT: {e}")

# ============================================
# FUNCIÓN: Capturar chat de Twitch
# ============================================
def twitch_livechat():
    global chat
    sock = socket.socket()
    sock.connect((server, port))
    sock.send(f"PASS {token}\n".encode('utf-8'))
    sock.send(f"NICK {nickname}\n".encode('utf-8'))
    sock.send(f"JOIN {channel}\n".encode('utf-8'))

    regex = r":(\w+)!\w+@\w+\.tmi\.twitch\.tv PRIVMSG #\w+ :(.+)"

    while True:
        try:
            resp = sock.recv(2048).decode('utf-8')
            if resp.startswith('PING'):
                sock.send("PONG\n".encode('utf-8'))
            elif not user in resp:
                resp = demojize(resp)
                match = re.match(regex, resp)
                username = match.group(1)
                message = match.group(2)
                if username in blacklist:
                    continue
                chat = username + ' dijo: ' + message
                print(chat)
        except Exception as e:
            print(f"Error en chat de Twitch: {e}")

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
        print("   ASISTENTE MOMBII - MODO ESPAÑOL")
        print("   Con soporte para VB-Audio Virtual Cable")
        print("=" * 50)
        print("Modos disponibles:")
        print("1 - Micrófono (habla con MOMBII)")
        print("2 - YouTube Live")
        print("3 - Twitch Live")

        mode = input("Selecciona modo (1, 2 o 3): ")

        if mode == "1":
            print("\n🎤 Modo MICRÓFONO")
            print("Mantén presionada la tecla RIGHT SHIFT para hablar")
            print("Suelta la tecla para que MOMBII procese tu mensaje\n")
            while True:
                if keyboard.is_pressed('RIGHT_SHIFT'):
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

    except KeyboardInterrupt:
        print("\n👋 Programa terminado.")
        try:
            t.join()
        except:
            pass
