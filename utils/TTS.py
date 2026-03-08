import os
import torch
import requests
import urllib.parse
import sounddevice as sd
import soundfile as sf
import numpy as np
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
