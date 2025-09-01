"""
openrouter_api.py
Cliente para obtener descripciones breves usando OpenRouter (modelos LLM).
"""

import logging
import requests
from typing import Optional

from main import Config

logger = logging.getLogger("openrouter_api")


def get_brief_description(file_name):
    prompt = (
        f"Eres un experto en hardware y electrónica. A partir del nombre de un archivo de diagrama esquemático "
        f"'{file_name}' de una placa madre, laptop o tarjeta gráfica, genera una descripción, precisa y clara "
        "del equipo al que pertenece. Incluye:\n"
        "- Tipo de dispositivo (PC, laptop, GPU)\n"
        "- Marca\n"
        "- Modelo\n"
        "- Una característica destacada si aplica\n\n"
        "La descripción debe ser entendible para alguien que busque información rápida sobre hardware, "
        "y debe ocupar una sola frase o formato de ficha muy breve. No agregues información irrelevante."
    )
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {Config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "openai/gpt-3.5-turbo",  # Puedes cambiar el modelo si tienes acceso a otro
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Error consultando OpenRouter.ai: {e}")
        return ""