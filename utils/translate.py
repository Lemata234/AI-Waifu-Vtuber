import requests
import json
import sys
import time
from functools import lru_cache

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf8', buffering=1)

# ============================================
# CONFIGURACIÓN DE TRADUCCIÓN
# ============================================
DEEPLX_URL = "http://localhost:1188/translate"
USE_DEEPLX = False  # Cambiar a True si tienes DeepLx corriendo
MAX_RETRIES = 3
RETRY_DELAY = 1

# ============================================
# DEEPLX (si está disponible)
# ============================================
def translate_deeplx(text, source, target, retry=0):
    """Traduce usando DeepLx (servidor local)"""
    if not USE_DEEPLX:
        return translate_google(text, source, target)

    try:
        headers = {"Content-Type": "application/json"}

        # Mapeo de idiomas
        lang_map = {
            "ES": "ES", "EN": "EN", "FR": "FR", "DE": "DE",
            "JA": "JA", "ZH": "ZH", "KO": "KO", "RU": "RU"
        }

        source_lang = lang_map.get(source.upper(), source.upper())
        target_lang = lang_map.get(target.upper(), target.upper())

        params = {
            "text": text,
            "source_lang": source_lang,
            "target_lang": target_lang
        }

        payload = json.dumps(params)
        response = requests.post(DEEPLX_URL, headers=headers, data=payload, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if 'data' in data:
                return data['data']
            elif 'text' in data:
                return data['text']

        if retry < MAX_RETRIES:
            time.sleep(RETRY_DELAY)
            return translate_deeplx(text, source, target, retry + 1)
        return translate_google(text, source, target)

    except Exception:
        return translate_google(text, source, target)

# ============================================
# GOOGLE TRANSLATE (sin librería externa)
# ============================================
@lru_cache(maxsize=128)
def translate_google(text, source, target):
    """Traduce usando Google Translate (con caché)"""
    try:
        source_lang = source.lower() if source else 'auto'
        target_lang = target.lower()

        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": source_lang,
            "tl": target_lang,
            "dt": "t",
            "q": text
        }

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, params=params, headers=headers, timeout=5)

        if response.status_code == 200:
            result = response.json()
            translated_text = ''.join([part[0] for part in result[0] if part[0]])
            return translated_text
        else:
            return text

    except Exception:
        return text

# ============================================
# DETECCIÓN DE IDIOMA
# ============================================
def detect_google(text):
    """Detecta el idioma usando Google Translate"""
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": "auto",
            "tl": "en",
            "dt": "t",
            "q": text[:100]
        }

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, params=params, headers=headers, timeout=5)

        if response.status_code == 200:
            result = response.json()
            detected_lang = result[2] if len(result) > 2 else "es"
            return detected_lang.upper()
        else:
            return "ES"

    except Exception:
        return "ES"

# ============================================
# FUNCIÓN UNIFICADA
# ============================================
def translate_text(text, target_lang="ES", source_lang="auto"):
    """Función unificada para traducir texto"""
    if source_lang == "auto":
        source_lang = detect_google(text)

    if USE_DEEPLX:
        result = translate_deeplx(text, source_lang, target_lang)
        if result and result != text:
            return result

    return translate_google(text, source_lang, target_lang)

# ============================================
# WRAPPERS PARA COMPATIBILIDAD
# ============================================
def translate_google_wrapper(text, source, target):
    return translate_google(text, source, target)

def detect_google_wrapper(text):
    return detect_google(text)

# ============================================
# PRUEBAS
# ============================================
if __name__ == "__main__":
    print("=== PRUEBAS DE TRADUCCIÓN ===\n")

    textos_prueba = [
        "Hola, ¿cómo estás?",
        "Necesito ayuda con mi computadora",
        "El servidor no responde"
    ]

    for texto in textos_prueba:
        print(f"Original: {texto}")
        print(f"Detectado: {detect_google(texto)}")
        print(f"Traducido (EN): {translate_google(texto, 'auto', 'en')}")
        print("-" * 40)
