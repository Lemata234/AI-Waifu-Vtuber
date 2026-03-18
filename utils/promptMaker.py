import json
import os

def get_identity():
    """Lee la identidad del personaje desde el archivo"""
    identity_file = "characterConfig/Pina/identity.txt"
    try:
        if os.path.exists(identity_file):
            with open(identity_file, "r", encoding="utf-8") as f:
                return f.read().strip()
        else:
            # Identidad por defecto
            return """Eres Mombii, un asistente virtual amable y servicial.
                    Respondes SIEMPRE en el idioma en el que se te habla de forma clara y profesional.
                    Tu objetivo es ayudar con problemas de tecnología."""
    except Exception as e:
        print(f"Error leyendo identity.txt: {e}")
        return "Eres un asistente virtual que responde en varios idiomas."

def getPrompt(language="es"):
    """Construye el prompt completo para el modelo, forzando el idioma de respuesta."""

    # Cargar identidad
    identity = get_identity()

    # Cargar historial (si existe)
    conversation = []
    try:
        if os.path.exists("conversation.json"):
            with open("conversation.json", "r", encoding="utf-8") as f:
                history = json.load(f)
                conversation = history.get("history", [])
    except:
        pass

    # Crear mensajes
    messages = []

    # System prompt con instrucción estricta de monolingüismo
    system_content = (
        f"{identity}\n\n"
        f"IMPORTANTE: Debes responder EXCLUSIVAMENTE en el idioma '{language}'. "
        "No mezcles idiomas en tu respuesta. Si el usuario te habla en ese idioma, tú respondes únicamente en ese idioma, sin incluir frases en otros idiomas.\n"
        "Ejemplos:\n"
        "- Si el usuario te habla en japonés, respondes solo en japonés.\n"
        "- Si el usuario te habla en español, respondes solo en español.\n"
        "- Si el usuario te habla en alemán, respondes solo en alemán.\n\n"
        "Mantén un tono profesional pero amable. Si no sabes algo, admítelo. Pero recuerda: tu respuesta debe estar COMPLETAMENTE en el idioma indicado."
    )
    messages.append({"role": "system", "content": system_content})

    # Agregar historial reciente (últimos 10 mensajes)
    messages.extend(conversation[-10:])

    return messages
