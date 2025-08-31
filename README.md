# WordpressAutoPost

Automatiza la publicación de archivos (ej. esquemáticos y boardviews) en WordPress a partir de archivos en Google Drive.

Incluye:
- Interfaz gráfica (Tkinter).
- Modo CLI/Batch sin interfaz.
- Generación automática de descripciones (OpenRouter API).
- Enlaces acortados con exe.io.
- Asignación de imágenes destacadas según la marca.
- Base de datos SQLite para evitar publicaciones duplicadas.

---

## 🚀 Requisitos

- Python 3.10 o superior
- Acceso a un sitio WordPress con REST API habilitada
- Credenciales de usuario de WordPress con permisos de publicación
- Una cuenta de servicio de Google Drive con permisos de lectura en la carpeta de archivos
- (Opcional) API key de [OpenRouter](https://openrouter.ai/) para descripciones automáticas
- (Opcional) API key de [exe.io](https://exe.io/) para acortar enlaces

---

## 📦 Instalación

1. Clona el repositorio:

   ```bash
   git clone https://github.com/clgil89/wordpress-autopost.git
   cd wordpress-autopost
