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

def getPrompt():
    """Construye el prompt completo para el modelo"""

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

    # System prompt con la identidad y refuerzo de idioma
    system_content = (
        f"{identity}\n\n"
        "IMPORTANTE: Debes responder SIEMPRE en el idioma en el que se te habla. "
        "Mantén un tono profesional pero amable. "
        "Si no sabes algo, admítelo y ofrece ayuda alternativa."
    )
    messages.append({"role": "system", "content": system_content})

    # Agregar historial reciente (últimos 10 mensajes)
    messages.extend(conversation[-10:])

    return messages
