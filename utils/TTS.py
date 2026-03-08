import os
import torch
import requests
import urllib.parse
import sounddevice as sd
import soundfile as sf
import numpy as np
import pyttsx3  # NUEVO
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
# NUEVAS FUNCIONES PARA TTS MULTILINGÜE
# ============================================

# Mapeo de idiomas a palabras clave en nombres de voces (puedes ampliarlo)
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
    # Agrega más según necesites
}

def obtener_voz_para_idioma(engine, idioma):
    """Busca una voz del sistema que coincida con el idioma."""
    voices = engine.getProperty('voices')
    idioma = idioma.lower()
    keywords = VOCES_POR_IDIOMA.get(idioma, [idioma])
    for voice in voices:
        nombre = voice.name.lower()
        for kw in keywords:
            if kw in nombre:
                return voice.id
    return None

def hablar_en_idioma(texto, idioma, cable_device="CABLE Input"):
    """Genera voz en el idioma especificado y la envía al cable virtual."""
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 160)
        engine.setProperty('volume', 0.9)

        voz_id = obtener_voz_para_idioma(engine, idioma)
        if voz_id:
            engine.setProperty('voice', voz_id)
            print(f"✅ Voz para '{idioma}': {voz_id}")
        else:
            print(f"⚠️ No se encontró voz para '{idioma}', usando defecto.")

        # Guardar audio
        engine.save_to_file(texto, 'test.wav')
        engine.runAndWait()

        # Reproducir en cable
        reproducir_en_cable('test.wav', cable_device)
    except Exception as e:
        print(f"❌ Error en TTS multilingüe: {e}")
        raise
