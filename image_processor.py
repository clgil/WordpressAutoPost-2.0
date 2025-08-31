"""
image_processor.py
Módulo para manejar imágenes destacadas en WordPress.
"""

import logging
import os
import tempfile
import requests
from typing import Optional

from main import Config
from wordpress_api import upload_media

logger = logging.getLogger("image_processor")


def set_featured_image_from_url(image_url: str, alt_text: Optional[str] = None) -> Optional[int]:
    """
    Descarga una imagen desde una URL y la sube a WordPress como media.
    Devuelve el ID del adjunto o None si falla.
    """
    if not image_url:
        logger.warning("Se llamó a set_featured_image_from_url sin URL.")
        return None

    try:
        resp = requests.get(image_url, timeout=Config.HTTP_TIMEOUT_SECONDS)
        if resp.status_code != 200:
            logger.error("No se pudo descargar imagen (%s): %s", resp.status_code, image_url)
            return None

        # Guardar temporalmente la imagen
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(image_url)[1]) as tmp:
            tmp.write(resp.content)
            tmp_path = tmp.name

        media_id = upload_media(tmp_path, alt_text=alt_text)

        try:
            os.remove(tmp_path)
        except OSError:
            pass  # no es crítico si falla limpiar

        if media_id:
            logger.info("Imagen destacada subida correctamente: %s (id=%s)", image_url, media_id)
            return media_id
        else:
            logger.error("Fallo al subir la imagen a WP: %s", image_url)
            return None

    except Exception as e:
        logger.exception("Excepción en set_featured_image_from_url (%s): %s", image_url, e)
        return None
