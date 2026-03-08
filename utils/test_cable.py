import sounddevice as sd
import soundfile as sf
import numpy as np

# Cargar o generar un tono de prueba
duration = 2  # segundos
fs = 44100
t = np.linspace(0, duration, int(fs * duration))
test_signal = 0.5 * np.sin(2 * np.pi * 440 * t)  # tono de 440 Hz

# Reproducir en CABLE Input
sd.play(test_signal, fs, device="CABLE Input")
sd.wait()
print("Tono reproducido. ¿Se escucha en VTube Studio?")