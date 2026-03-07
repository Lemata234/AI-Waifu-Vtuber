import ollama  # <--- AÑADIR ESTA LÍNEA (reemplaza import openai)
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
from config import *  # Ya no necesitarás api_key aquí, pero lo dejamos por si acaso
from utils.translate import *
from utils.TTS import *
from utils.subtitle import *
from utils.promptMaker import *
from utils.twitch_config import *
from config import OLLAMA_CONFIG


# to help the CLI write unicode characters to the terminal
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf8', buffering=1)

# YA NO NECESITAS ESTA LÍNEA - la comentamos o eliminamos
# openai.api_key = api_key

conversation = []
# Create a dictionary to hold the message data
history = {"history": conversation}

mode = 0
total_characters = 0
chat = ""
chat_now = ""
chat_prev = ""
is_Speaking = False
owner_name = "Mata"
blacklist = ["Nightbot", "streamelements"]


# MODELO DE OLLAMA A UTILIZAR (puedes cambiarlo por el que prefieras)
OLLAMA_MODEL = "gemma3:4b"  # o "llama3.2", "mistral", "phi3", etc.

# boludo usa este codigo en cmd para ejecutar voicevox: docker run --rm --gpus all -p 50021:50021 voicevox/voicevox_engine:nvidia-latest

# function to get the user's input audio
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
    print("Recording...")
    while keyboard.is_pressed('RIGHT_SHIFT'):
        data = stream.read(CHUNK)
        frames.append(data)
    print("Stopped recording.")
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

# function to transcribe the user's audio
def transcribe_audio(file):
    global chat_now
    try:
        audio_file = open(file, "rb")

        # PARA OLLAMA: Necesitamos un modelo de speech-to-text
        # Opción 1: Usar Whisper.cpp con Ollama (más complejo)
        # Opción 2: Usar la API de OpenAI solo para whisper (gratis por ahora?)
        # Opción 3: Usar una librería local como Vosk o SpeechRecognition

        # Por ahora, te recomiendo instalar:
        # pip install speechrecognition
        # Y usar esto:

        import speech_recognition as sr
        recognizer = sr.Recognizer()
        with sr.AudioFile(file) as source:
            audio = recognizer.record(source)

        try:
            # Intenta con Google Speech Recognition (gratis, sin API key)
            chat_now = recognizer.recognize_google(audio, language="id-ID")  # Cambia el idioma según necesites
            print(f"Question (Google Speech): {chat_now}")
        except:
            # Fallback a Sphinx (offline pero menos preciso)
            chat_now = recognizer.recognize_sphinx(audio)
            print(f"Question (Sphinx): {chat_now}")

        # Alternativa si quieres mantener Whisper (necesitas instalar openai-whisper)
        # pip install openai-whisper
        """
        import whisper
        model = whisper.load_model("base")
        result = model.transcribe(file)
        chat_now = result["text"]
        print(f"Question (Whisper): {chat_now}")
        """

    except Exception as e:
        print("Error transcribing audio: {0}".format(e))
        return

    result = owner_name + " said " + chat_now
    conversation.append({'role': 'user', 'content': result})
    ollama_answer()  # <--- CAMBIADO de openai_answer()

# function to get an answer from Ollama (ANTES era openai_answer)
def ollama_answer():  # <--- NOMBRE CAMBIADO
    global total_characters, conversation

    total_characters = sum(len(d['content']) for d in conversation)

    while total_characters > 4000:
        try:
            conversation.pop(2)
            total_characters = sum(len(d['content']) for d in conversation)
        except Exception as e:
            print("Error removing old messages: {0}".format(e))

    with open("conversation.json", "w", encoding="utf-8") as f:
        json.dump(history, f, indent=4)

    prompt = getPrompt()

    # --- NUEVO: Llamada a Ollama en lugar de OpenAI ---
    try:
        # Ollama tiene una interfaz similar a OpenAI
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=prompt,
            options={
                "num_predict": 128,  # equivalente a max_tokens
                "temperature": 1.0,
                "top_p": 0.9
            }
        )

        message = response['message']['content']

    except Exception as e:
        print(f"Error calling Ollama: {e}")
        message = "Lo siento, tuve un problema al procesar tu mensaje. ¿Puedes repetirlo?"
    # --- FIN DE LA NUEVA LLAMADA ---

    conversation.append({'role': 'assistant', 'content': message})
    translate_text(message)

# function to capture livechat from youtube
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
                    chat = c.author.name + ' berkata ' + chat_raw
                    print(chat)
                time.sleep(1)
        except Exception as e:
            print("Error receiving chat: {0}".format(e))

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
                chat = username + ' said ' + message
                print(chat)
        except Exception as e:
            print("Error receiving chat: {0}".format(e))

def translate_text(text):
    global is_Speaking
    # subtitle = translate_google(text, "ID")

    detect = detect_google(text)
    tts = translate_google(text, f"{detect}", "JA")
    # tts = translate_deeplx(text, f"{detect}", "JA")
    tts_en = translate_google(text, f"{detect}", "EN")
    try:
        print("JP Answer: " + tts)
        print("EN Answer: " + tts_en)
    except Exception as e:
        print("Error printing text: {0}".format(e))
        return

    # Japanese TTS
    # voicevox_tts(tts)

    # Silero TTS
    silero_tts(tts_en, "en", "v3_en", "en_21")

    # Generate Subtitle
    generate_subtitle(chat_now, text)

    time.sleep(1)

    is_Speaking = True
    winsound.PlaySound("test.wav", winsound.SND_FILENAME)
    is_Speaking = False

    time.sleep(1)
    with open ("output.txt", "w") as f:
        f.truncate(0)
    with open ("chat.txt", "w") as f:
        f.truncate(0)

def preparation():
    global conversation, chat_now, chat, chat_prev
    while True:
        chat_now = chat
        if is_Speaking == False and chat_now != chat_prev:
            conversation.append({'role': 'user', 'content': chat_now})
            chat_prev = chat_now
            ollama_answer()  # <--- CAMBIADO de openai_answer()
        time.sleep(1)

if __name__ == "__main__":
    try:
        mode = input("Mode (1-Mic, 2-Youtube Live, 3-Twitch Live): ")

        if mode == "1":
            print("Press and Hold Right Shift to record audio")
            while True:
                if keyboard.is_pressed('RIGHT_SHIFT'):
                    record_audio()

        elif mode == "2":
            live_id = input("Livestream ID: ")
            t = threading.Thread(target=preparation)
            t.start()
            yt_livechat(live_id)

        elif mode == "3":
            print("To use this mode, make sure to change utils/twitch_config.py to your own config")
            t = threading.Thread(target=preparation)
            t.start()
            twitch_livechat()
    except KeyboardInterrupt:
        t.join()
        print("Stopped")

        # ADICIONAL: SOLO DIOS Y DEEPSEEK SABEN COMO FUNCIONA ESTA COSA, NO ENTIENDO COMO A LA PRIMERA FUNCIONÓ XDDDD