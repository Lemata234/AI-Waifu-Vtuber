import os
import torch
import requests
import urllib.parse
import sounddevice as sd
import soundfile as sf
import numpy as np
import pyttsx3
import asyncio
import edge_tts  # <--- NUEVO
from utils.katakana import *

def silero_tts(tts, language, model, speaker, output_file="test.wav"):
    device = torch.device('cpu')
    torch.set_num_threads(4)
    local_file = 'model.pt'

    if not os.path.isfile(local_file):
        torch.hub.download_url_to_file(f'https://models.silero.ai/models/tts/{language}/{model}.pt',
                                       local_file)

    model = torch.package.PackageImporter(local_file).load_pickle("tts_models", "model")
    model.to(device)

    sample_rate = 48000

    # Guardar en el archivo especificado
    audio = model.apply_tts(text=tts,
                            speaker=speaker,
                            sample_rate=sample_rate)

    # Guardar como wav
    import soundfile as sf
    sf.write(output_file, audio, sample_rate)

    return output_file

def reproducir_en_cable(archivo_wav, nombre_dispositivo="CABLE Input"):
    """
    Reproduce un archivo WAV en el dispositivo de audio especificado.
    """
    # Cargar el audio
    data, samplerate = sf.read(archivo_wav, dtype='float32')

    # Buscar el dispositivo por nombre
    devices = sd.query_devices()
    dispositivo_id = None
    for i, dev in enumerate(devices):
        if nombre_dispositivo.lower() in dev['name'].lower():
            dispositivo_id = i
            print(f"✅ Dispositivo encontrado: {dev['name']} (ID: {i})")
            break

    if dispositivo_id is None:
        print(f"⚠️ No se encontró '{nombre_dispositivo}'. Usando dispositivo predeterminado.")
        dispositivo_id = sd.default.device[1]  # Salida predeterminada

    # Reproducir
    sd.play(data, samplerate, device=dispositivo_id)
    sd.wait()  # Esperar a que termine

# ============================================
# FUNCIONES PARA TTS MULTILINGÜE
# ============================================

# Mapeo de idiomas a palabras clave en nombres de voces de Windows (pyttsx3)
VOCES_POR_IDIOMA = {
    "es": ["spanish", "español", "es_", "es-"],
    "en": ["english", "inglés", "en_", "en-"],
    "fr": ["french", "francés", "fr_", "fr-"],
    "de": ["german", "alemán", "de_", "de-"],
    "it": ["italian", "italiano", "it_", "it-"],
    "pt": ["portuguese", "portugués", "pt_", "pt-"],
    "ru": ["russian", "ruso", "ru_", "ru-"],
    "ja": ["japanese", "japonés", "ja_", "ja-"],
    "zh": ["chinese", "chino", "zh_", "zh-"],
    "ko": ["korean", "coreano", "ko_", "ko-"],
}

# Mapeo de idiomas a voces de edge-tts (puedes ampliarlo)
EDGE_VOCES = {
    "ja": "ja-JP-NanamiNeural",      # Japonés femenino
    "es": "es-MX-DaliaNeural",        # Español mexicano
    "en": "en-US-JennyNeural",        # Inglés americano
    "de": "de-DE-KatjaNeural",        # Alemán
    "fr": "fr-FR-DeniseNeural",       # Francés
    "it": "it-IT-ElsaNeural",         # Italiano
    "pt": "pt-BR-FranciscaNeural",    # Portugués brasileño
    "ru": "ru-RU-SvetlanaNeural",     # Ruso
    "zh": "zh-CN-XiaoxiaoNeural",     # Chino mandarín
    "ko": "ko-KR-SunHiNeural",        # Coreano
    # Agrega más según necesites
}

def obtener_voz_para_idioma(engine, idioma):
    """Busca una voz del sistema (Windows) que coincida con el idioma."""
    voices = engine.getProperty('voices')
    idioma = idioma.lower()
    keywords = VOCES_POR_IDIOMA.get(idioma, [idioma])
    for voice in voices:
        nombre = voice.name.lower()
        for kw in keywords:
            if kw in nombre:
                return voice.id
    return None

# ============================================
# FUNCIONES PARA EDGE-TTS
# ============================================

async def generar_voz_edge(texto, idioma, archivo_salida="test.wav"):
    """Genera un archivo de audio usando edge-tts (asíncrono)."""
    voz = EDGE_VOCES.get(idioma.lower(), "ja-JP-NanamiNeural")  # Por defecto japonés si no se encuentra
    tts = edge_tts.Communicate(texto, voz)
    await tts.save(archivo_salida)
    print(f"✅ Audio generado con edge-tts (voz: {voz})")
    return archivo_salida

def hablar_con_edge(texto, idioma, cable_device="CABLE Input"):
    """Función sincrónica para generar y reproducir voz con edge-tts."""
    try:
        asyncio.run(generar_voz_edge(texto, idioma))
        reproducir_en_cable("test.wav", cable_device)
    except Exception as e:
        print(f"❌ Error en edge-tts: {e}")
        # Fallback a pyttsx3 si edge-tts falla
        print("⚠️ Usando pyttsx3 como fallback...")
        hablar_con_pyttsx3(texto, idioma, cable_device)

def hablar_con_pyttsx3(texto, idioma, cable_device="CABLE Input"):
    """Genera voz con pyttsx3 (voces de Windows)."""
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 160)
        engine.setProperty('volume', 0.9)

        voz_id = obtener_voz_para_idioma(engine, idioma)
        if voz_id:
            engine.setProperty('voice', voz_id)
            print(f"✅ Voz encontrada para '{idioma}': {voz_id}")
        else:
            print(f"⚠️ No se encontró voz para '{idioma}', usando defecto.")

        engine.save_to_file(texto, 'test.wav')
        engine.runAndWait()
        reproducir_en_cable('test.wav', cable_device)
    except Exception as e:
        print(f"❌ Error en pyttsx3: {e}")
        raise

def hablar_en_idioma(texto, idioma, cable_device="CABLE Input"):
    """
    Función principal que decide qué motor TTS usar según el idioma.
    Para japonés (JA) usa edge-tts. Para otros idiomas, intenta primero con pyttsx3
    y si no encuentra voz, usa edge-tts como fallback.
    """
    idioma = idioma.upper()  # Normalizar a mayúsculas (JA, ES, EN, etc.)

    # Si es japonés, usar edge-tts directamente (mejor calidad)
    if idioma == "JA":
        print("🗣️ Usando edge-tts para japonés...")
        hablar_con_edge(texto, idioma, cable_device)
        return

    # Para otros idiomas, intentar primero con pyttsx3
    try:
        hablar_con_pyttsx3(texto, idioma, cable_device)
    except Exception as e:
        print(f"⚠️ pyttsx3 falló para {idioma}, intentando con edge-tts...")
        hablar_con_edge(texto, idioma, cable_device)
