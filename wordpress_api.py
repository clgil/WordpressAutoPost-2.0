"""
wordpress_api.py
Módulo para interactuar con el API REST de WordPress.
"""

import logging
import os
import requests
from typing import Optional, Dict, Any

from main import Config, format_date_for_wp

logger = logging.getLogger("wordpress_api")

# --- Helpers internos ---
def _wp_auth() -> Optional[tuple[str, str]]:
    if not Config.WP_USER or not Config.WP_PASSWORD:
        logger.error("Credenciales de WordPress no configuradas (WP_USER/WP_PASSWORD).")
        return None
    return (Config.WP_USER, Config.WP_PASSWORD)

def _wp_url(path: str) -> str:
    if not Config.WP_API_BASE:
        logger.error("WP_SITE_URL no configurado.")
        return ""
    return f"{Config.WP_API_BASE.rstrip('/')}/{path.lstrip('/')}"

def _post(endpoint: str, data: Dict[str, Any], files=None) -> Optional[Dict[str, Any]]:
    url = _wp_url(endpoint)
    if not url:
        return None
    try:
        resp = requests.post(
            url,
            auth=_wp_auth(),
            json=data if files is None else None,
            files=files,
            timeout=Config.HTTP_TIMEOUT_SECONDS,
        )
        if resp.status_code in (200, 201):
            return resp.json()
        else:
            logger.error("Error en POST %s: %s %s", url, resp.status_code, resp.text[:300])
            return None
    except Exception as e:
        logger.exception("Excepción al hacer POST a %s: %s", url, e)
        return None

def _get(endpoint: str, params=None) -> Optional[Dict[str, Any]]:
    url = _wp_url(endpoint)
    if not url:
        return None
    try:
        resp = requests.get(
            url,
            auth=_wp_auth(),
            params=params,
            timeout=Config.HTTP_TIMEOUT_SECONDS,
        )
        if resp.status_code == 200:
            return resp.json()
        else:
            logger.error("Error en GET %s: %s %s", url, resp.status_code, resp.text[:300])
            return None
    except Exception as e:
        logger.exception("Excepción al hacer GET a %s: %s", url, e)
        return None

# --- Funciones públicas ---

def create_post(
    title: str,
    content: str,
    categories: Optional[list[int]] = None,
    tags: Optional[list[int]] = None,
    featured_media: Optional[int] = None,
    publish_date=None,
    status: str = "publish",
) -> Optional[Dict[str, Any]]:
    """
    Crea un post en WordPress. 
    - Si publish_date está en el futuro, se usará date_gmt y status=future.
    - categories/tags son listas de IDs.
    - featured_media es el ID de imagen destacada.
    """
    post_data = {
        "title": title,
        "content": content,
        "status": status,
    }
    if categories:
        post_data["categories"] = categories
    if tags:
        post_data["tags"] = tags
    if featured_media:
        post_data["featured_media"] = featured_media
    if publish_date:
        post_data.update(format_date_for_wp(publish_date))

    return _post("posts", post_data)

def upload_media(file_path: str, alt_text: Optional[str] = None) -> Optional[int]:
    """
    Sube un archivo multimedia a WordPress (normalmente imagen).
    Devuelve el ID del adjunto o None si falla.
    """
    if not os.path.exists(file_path):
        logger.error("No existe el archivo a subir: %s", file_path)
        return None

    url = _wp_url("media")
    if not url:
        return None

    try:
        with open(file_path, "rb") as f:
            headers = {"Content-Disposition": f"attachment; filename={os.path.basename(file_path)}"}
            resp = requests.post(
                url,
                headers=headers,
                auth=_wp_auth(),
                files={"file": f},
                timeout=Config.HTTP_TIMEOUT_SECONDS,
            )
        if resp.status_code in (200, 201):
            media = resp.json()
            media_id = media.get("id")
            logger.info("Subida de media correcta: %s -> id=%s", file_path, media_id)
            if alt_text and media_id:
                update_media(media_id, {"alt_text": alt_text})
            return media_id
        else:
            logger.error("Error al subir media %s: %s %s", file_path, resp.status_code, resp.text[:200])
            return None
    except Exception as e:
        logger.exception("Excepción al subir media %s: %s", file_path, e)
        return None

def update_media(media_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Actualiza metadatos de un media (ej. alt_text).
    """
    url = _wp_url(f"media/{media_id}")
    if not url:
        return None
    try:
        resp = requests.post(
            url,
            auth=_wp_auth(),
            json=data,
            timeout=Config.HTTP_TIMEOUT_SECONDS,
        )
        if resp.status_code in (200, 201):
            return resp.json()
        else:
            logger.error("Error al actualizar media %s: %s %s", media_id, resp.status_code, resp.text[:200])
            return None
    except Exception as e:
        logger.exception("Excepción al actualizar media %s: %s", media_id, e)
        return None
