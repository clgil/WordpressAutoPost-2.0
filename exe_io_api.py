"""
exe_io_api.py
Cliente para acortar URLs usando el servicio exe.io.
"""

import logging
import requests
from typing import Optional

from main import Config

logger = logging.getLogger("exe_io_api")


def shorten_url(long_url: str) -> str:
    """
    Acorta una URL usando exe.io API.
    Si falla, devuelve la URL original.
    """
    api_key = Config.EXE_IO_API_KEY
    if not api_key:
        logger.warning("EXE_IO_API_KEY no configurado. Se devuelve URL original.")
        return long_url

    endpoint = "https://exe.io/api"
    params = {"api": api_key, "url": long_url}

    try:
        resp = requests.get(endpoint, params=params, timeout=Config.HTTP_TIMEOUT_SECONDS)
        if resp.status_code != 200:
            logger.error("Error exe.io (%s): %s", resp.status_code, resp.text[:200])
            return long_url

        data = resp.json()
        short = data.get("shortenedUrl") or data.get("short") or ""
        if short:
            logger.debug("URL acortada: %s -> %s", long_url, short)
            return short
        else:
            logger.error("Respuesta exe.io inválida: %s", data)
            return long_url
    except Exception as e:
        logger.exception("Excepción al acortar URL %s: %s", long_url, e)
        return long_url
