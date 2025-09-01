"""
google_drive.py
Interfaz para listar archivos en Google Drive usando una Service Account.
"""

import logging
from typing import Optional, List, Dict, Any
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account
from main import Config
from main import init_google_drive_service

service = init_google_drive_service()

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


    """
    Devuelve un dict con la metadata de un archivo en Google Drive.
    
    En el dict se incluyen los siguientes campos:
        - size: tamaño del archivo en MB (string)
        - mimeType: tipo MIME del archivo (string)
    
    Si ocurre un error, devuelve un dict con los campos 'size' y 'mimeType' ambos con valor 'N/A'.
    """

def get_file_metadata(file_id):
    """
    Recupera la metadata de un archivo en Google Drive (solo size y mimeType).
    
    Si ocurre un error, devuelve un dict con los campos 'size' y 'mimeType' ambos con valor 'N/A'.
    """
    metadata = {'size': 'N/A', 'mimeType': 'N/A'}

    # Si el servicio no ha sido inicializado, devuelve un dict vac o
    if not service:
        return metadata

    try:
        # Intenta recuperar la metadata de un archivo en Google Drive
        file = service.files().get(
            fileId=file_id,
            fields="size,mimeType"
        ).execute()

        # Recupera el tama o del archivo en bytes y lo convierte a MB
        size_bytes = file.get('size', '0')
        if size_bytes.isdigit():
            size_mb = round(int(size_bytes) / (1024 * 1024), 2)
        else:
            size_mb = 'N/A'

        # Actualiza el dict con la metadata
        metadata['size'] = size_mb
        metadata['mimeType'] = file.get('mimeType', 'application/octet-stream')
    except HttpError as e:
        # Si ocurre un error en la API de Google, lo imprime
        print(f"Google API error: {str(e)}")
    except Exception as e:
        # Si ocurre un error general, lo imprime
        print(f"General error: {str(e)}")

    # Devuelve el dict con la metadata
    return metadata
