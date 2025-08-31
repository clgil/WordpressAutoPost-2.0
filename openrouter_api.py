"""
openrouter_api.py
Cliente para obtener descripciones breves usando OpenRouter (modelos LLM).
"""

import logging
import requests
from typing import Optional

from main import Config

logger = logging.getLogger("openrouter_api")


def get_brief_description(file_name: str) -> str:
    """
    Llama a OpenRouter API para generar una breve descripción del archivo.
    Devuelve una cadena (puede ser vacía si falla).
    """
    api_key = Config.OPENROUTER_API_KEY
    if not api_key:
        logger.warning("OPENROUTER_API_KEY no configurado. Se omite descripción.")
        return ""

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://your-app.example",  # opcional, se puede personalizar
        "X-Title": "WordpressAutoPost",
    }

    data = {
        "model": "gpt-3.5-turbo",  # o cualquier modelo compatible
        "messages": [
            {
                "role": "system",
                "content": (
                    "Eres un asistente que redacta descripciones breves, claras y atractivas "
                    "para archivos técnicos de esquemas electrónicos y boardviews. "
                    "No uses más de 25 palabras."
                ),
            },
            {
                "role": "user",
                "content": f"Escribe una breve descripción para el archivo: {file_name}",
            },
        ],
        "max_tokens": 60,
        "temperature": 0.6,
    }

    try:
        resp = requests.post(url, headers=headers, json=data, timeout=Config.HTTP_TIMEOUT_SECONDS)
        if resp.status_code != 200:
            logger.error("Error de OpenRouter (%s): %s", resp.status_code, resp.text[:200])
            return ""

        payload = resp.json()
        choice = payload.get("choices", [{}])[0]
        message = choice.get("message", {})
        content = message.get("content", "")
        description = content.strip() if content else ""
        logger.debug("Descripción generada para %s: %s", file_name, description)
        return description
    except Exception as e:
        logger.exception("Excepción al llamar a OpenRouter para %s: %s", file_name, e)
        return ""
