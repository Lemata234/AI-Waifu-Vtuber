# ============================================
# ARCHIVO DE CONFIGURACIÓN
# ============================================

# Configuración de Ollama
OLLAMA_CONFIG = {
    "model": "gemma3:4b",      # Modelo a usar
    "host": "http://localhost:11434",
    "temperature": 0.8,
    "max_tokens": 150
}

# Configuración del cable virtual
CABLE_CONFIG = {
    "device_name": "CABLE Input",  # Nombre exacto del dispositivo
    "enabled": True                 # Activar/desactivar cable virtual
}

# Configuración de voz
VOICE_CONFIG = {
    "language": "es",           # Idioma de la voz
    "rate": 160,                # Velocidad de habla
    "volume": 0.9               # Volumen (0.0 a 1.0)
}

# Configuración del personaje
CHARACTER_CONFIG = {
    "name": "Mombii",
    "identity_file": "characterConfig/Pina/identity.txt"
}

# Configuración de Twitch (si se usa)
TWITCH_CONFIG = {
    "server": "irc.chat.twitch.tv",
    "port": 6667,
    "nickname": "tu_bot",
    "token": "oauth:tu_token_aqui",
    "user": "tu_usuario",
    "channel": "#tu_canal"
}

# Lista negra de usuarios (para chats)
BLACKLIST = ["Nightbot", "streamelements"]
