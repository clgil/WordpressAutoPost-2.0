"""
google_drive.py
Interfaz para listar archivos en Google Drive usando una Service Account.
"""

import logging
from typing import Optional, List, Dict, Any

from main import Config

logger = logging.getLogger("google_drive")


def list_files_in_drive(
    drive_service,
    folder_id: Optional[str] = None,
    page_size: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Lista archivos dentro de un folder de Google Drive (no recursivo).
    
    Params:
        drive_service: cliente de Google Drive inicializado con service account.
        folder_id: ID de la carpeta (si None, usa Config.GOOGLE_DRIVE_FOLDER_ID).
        page_size: opcional, número de archivos por página (default Config.DRIVE_PAGE_SIZE).
    
    Returns:
        Lista de dicts con campos: id, name, mimeType, size.
        Si ocurre un error, devuelve [].
    """
    if drive_service is None:
        logger.error("Google Drive service no inicializado.")
        return []

    folder_id = folder_id or Config.GOOGLE_DRIVE_FOLDER_ID
    if not folder_id:
        logger.error("No se especificó GOOGLE_DRIVE_FOLDER_ID.")
        return []

    page_size = page_size or Config.DRIVE_PAGE_SIZE
    files: List[Dict[str, Any]] = []
    page_token: Optional[str] = None

    try:
        while True:
            resp = (
                drive_service.files()
                .list(
                    q=f"'{folder_id}' in parents and trashed=false",
                    fields="nextPageToken, files(id, name, mimeType, size)",
                    pageSize=page_size,
                    pageToken=page_token,
                    orderBy="createdTime desc",
                )
                .execute()
            )
            batch = resp.get("files", [])
            files.extend(batch)
            page_token = resp.get("nextPageToken")
            if not page_token:
                break

        logger.info("Listados %s archivos desde carpeta %s", len(files), folder_id)
        return files
    except Exception as e:
        logger.exception("Error al listar archivos de Drive: %s", e)
        return []
