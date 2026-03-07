import requests
import json
import sys
import time
from functools import lru_cache

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf8', buffering=1)

# Configuración
DEEPLX_URL = "http://localhost:1188/translate"
USE_DEEPLX = True  # Cambiar a False si DeepLx no está disponible
MAX_RETRIES = 3
RETRY_DELAY = 1  # segundos

def translate_deeplx(text, source, target, retry=0):
    """
    Traduce usando DeepLx (servidor local)
    """
    if not USE_DEEPLX:
        return translate_google(text, source, target)

    try:
        headers = {"Content-Type": "application/json"}

        # DeepL usa códigos de idioma específicos
        # Mapeo para idiomas comunes
        lang_map = {
            "ID": "ID",  # Indonesio
            "JA": "JA",  # Japonés
            "EN": "EN",  # Inglés
            "ES": "ES",  # Español
            "FR": "FR",  # Francés
            "DE": "DE",  # Alemán
            "ZH": "ZH",  # Chino
            "KO": "KO",  # Coreano
            "RU": "RU",  # Ruso
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
            else:
                print(f"Respuesta inesperada de DeepLx: {data}")
                return translate_google(text, source, target)
        else:
            print(f"Error DeepLx ({response.status_code}): {response.text}")
            if retry < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
                return translate_deeplx(text, source, target, retry + 1)
            return translate_google(text, source, target)

    except requests.exceptions.ConnectionError:
        print("⚠️  No se pudo conectar a DeepLx. ¿Está el servidor corriendo?")
        print("   Para iniciarlo: docker run -d -p 1188:1188 ghcr.io/zu1k/deeplx")
        print("   Usando Google Translate como respaldo...\n")
        return translate_google(text, source, target)
    except Exception as e:
        print(f"Error inesperado en DeepLx: {e}")
        return translate_google(text, source, target)

@lru_cache(maxsize=128)
def translate_google(text, source, target):
    """
    Traduce usando Google Translate (sin librería externa)
    Con caché para evitar llamadas repetidas
    """
    try:
        # Google Translate usa códigos de idioma en minúsculas
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
            # La estructura es [[[translated_text, ...], ...], ...]
            translated_text = ''.join([part[0] for part in result[0] if part[0]])
            return translated_text
        else:
            print(f"Error Google Translate ({response.status_code})")
            return text  # Devuelve el texto original si falla

    except Exception as e:
        print(f"Error en Google Translate: {e}")
        return text

def detect_google(text):
    """
    Detecta el idioma usando Google Translate (sin librería externa)
    """
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": "auto",
            "tl": "en",
            "dt": "t",
            "q": text[:100]  # Solo primeros 100 caracteres para detectar
        }

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, params=params, headers=headers, timeout=5)

        if response.status_code == 200:
            result = response.json()
            # El idioma detectado está en result[2]
            detected_lang = result[2] if len(result) > 2 else "en"
            return detected_lang.upper()
        else:
            print(f"Error detectando idioma ({response.status_code})")
            return "EN"  # Valor por defecto

    except Exception as e:
        print(f"Error detectando idioma: {e}")
        return "EN"

def translate_text(text, target_lang="JA", source_lang="auto"):
    """
    Función unificada para traducir texto
    Prioriza DeepLx, fallback a Google Translate
    """
    # Detectar idioma si es auto
    if source_lang == "auto":
        source_lang = detect_google(text)

    # Intentar con DeepLx primero
    if USE_DEEPLX:
        result = translate_deeplx(text, source_lang, target_lang)
        if result and result != text:  # Si tuvo éxito y cambió el texto
            return result

    # Fallback a Google Translate
    return translate_google(text, source_lang, target_lang)

# Mantener compatibilidad con el código existente
# Estas funciones mantienen la misma interfaz que antes
def translate_google_wrapper(text, source, target):
    """Wrapper para mantener compatibilidad con código existente"""
    return translate_google(text, source, target)

def detect_google_wrapper(text):
    """Wrapper para mantener compatibilidad con código existente"""
    return detect_google(text)

if __name__ == "__main__":
    # Pruebas
    print("=== Pruebas de traducción ===\n")

    # Prueba 1: Indonesio a Japonés
    text1 = "aku tidak menyukaimu"
    print(f"Texto original: {text1}")

    # Probar DeepLx (si está disponible)
    result1 = translate_deeplx(text1, "EN", "JA")
    print(f"DeepLx (ID→JA): {result1}")

    # Probar Google Translate
    result2 = translate_google(text1, "en", "ja")
    print(f"Google (ID→JA): {result2}")

    # Probar función unificada
    result3 = translate_text(text1, "ja")
    print(f"Unificada (→JA): {result3}")

    # Prueba 2: Detección de idioma
    print(f"\nDetección de idioma:")
    print(f"'{text1}' → {detect_google(text1)}")