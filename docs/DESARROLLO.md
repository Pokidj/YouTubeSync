# Desarrollo de YouTubeSync

**Español** | [English](DEVELOPMENT.en.md)

La información para instalar y utilizar la aplicación está en el [README](../README.md)
y la [guía de uso](GUIA_DE_USO.md). Esta página es para desarrollar y mantener el código.

## Entorno

Windows de 64 bits, Python 3.12 e Inno Setup 7 para generar el instalador.
No se necesitan credenciales reales para las pruebas automatizadas.

```powershell
git clone https://github.com/Pokidj/YouTubeSync.git
cd YouTubeSync
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe src/youtube_sync_app.py
```

No arranques la ventana principal sobre el perfil real para hacer pruebas:
puede tener Auto activado. Los tests sustituyen el almacén y las operaciones remotas.

## Estructura

| Ruta | Contenido |
| --- | --- |
| `src/youtube_sync_app.py` | Ventana Qt, ajustes, biblioteca, canal, avisos y bandeja. |
| `src/youtube_sync_engine.py` | SQLite, configuración, OAuth, API, identidad y trabajador. |
| `src/youtube_sync_install.py` | Identidad del instalador y cierre coordinado para actualizar. |
| `src/youtube_sync_updater.py` | Releases oficiales, descarga HTTPS y comprobación SHA-256. |
| `src/youtube_sync_update_ui.py` | Comprobación, descarga e instalación desde Ajustes. |
| `src/youtube_sync_i18n*.py`, `youtube_sync_translations.py` | Idiomas de presentación, sin cambiar estados internos. |
| `src/youtube_sync_manual*.py`, `youtube_sync_*player.py` | Comparación guiada y reproducción local/YouTube. |
| `assets` | Logo, iconos Lucide y avisos de licencia. |
| `packaging` | Especificación PyInstaller, manifiesto y script del instalador. |
| `build_hooks` | Datos auxiliares de SSL para el runtime. |
| `tests` | Pruebas sin cuentas, subidas ni borrados reales de YouTube. |
| `scripts` | Validación de la distribución y creación del instalador. |
| `.github/workflows` | Compilación, validación y publicación de versiones. |
| `docs` | Uso, arquitectura, verificación y publicación, en español e inglés. |

`.venv`, `build`, `dist`, `work`, `releases`, `.tools` y los respaldos locales no
se publican. La distribución completa de trabajo queda en `dist/YouTubeSync`;
`_internal` es imprescindible. No mezcles ejecutables de distintas compilaciones.

## Arquitectura y rendimiento

La interfaz importa su motor directamente. Red, huellas, miniaturas y análisis
de medios se ejecutan fuera del hilo Qt. Los resultados llegan mediante señales
o una cola acotada; el canal se pinta por lotes. Los cambios de tamaño se agrupan
y las imágenes se decodifican una sola vez.

Las confirmaciones se guardan por firma e identidad, no por título o duración.
Los recibos persisten al reiniciar y al limpiar Consola. Recibir bytes no equivale
a terminar el procesamiento. Los registros manuales están separados y nunca
permiten limpieza automática. [Protocolo detallado](VERIFICACION_DE_SUBIDAS.md).

Los confirmados sin cambios no se consultan en cada arranque o temporizador.
Los IDs pendientes se consultan por lotes de 50, con caché compartida de un minuto;
el catálogo completo tiene cinco minutos. Las comprobaciones de borrado omiten
la caché. Un fallo de red o cuota no se interpreta como ausencia del vídeo.
Las pausas se comparten y persisten; no se crean bucles de nuevas sesiones de subida.

La reproducción utiliza un perfil independiente sin leer contraseñas ni copiar
cookies personales. OAuth no se entrega al reproductor. El documento local de
comparación solo sirve en 127.0.0.1, con rutas aleatorias y eventos validados.

## Idiomas

`Config.language`: `es` predeterminado o `en`, aplicado al reiniciar. Los adaptadores
Qt traducen la presentación y conservan los modelos canónicos. No traduzcas nombres,
rutas, IDs ni estados persistidos. Los diagnósticos se clasifican y redactan antes
de traducir. Añade todo mensaje nuevo al catálogo y a sus pruebas.

## Pruebas y compilación

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
powershell -ExecutionPolicy Bypass -File build_exe.ps1
.\.venv\Scripts\python.exe scripts/check_distribution.py
.\.venv\Scripts\python.exe scripts/create_release.py
```

La especificación PyInstaller conserva el hook SSL y excluye una `icuuc.dll`
ajena que puede aparecer en PATH. No la sustituyas por un comando genérico. El
modo `--self-test` no carga la cuenta ni inicia subidas; comprueba recursos, SSL,
reproducción local e idiomas. La versión también se escribe en los recursos PE.

Los tests cubren persistencia, cancelaciones, HTTP 308, concurrencia OAuth,
cuota, falsos positivos de identidad, borrado, interfaz, idiomas e instalador.
No prueban permisos reales de cuentas privadas. Esa comprobación debe hacerse
con archivos y vídeos desechables y sin rebajar las protecciones automáticas.

## Datos y seguridad

Los datos activos permanecen en `%APPDATA%\YouTubeSync`. El instalador es por
usuario, conserva esa carpeta y actualiza el programa en su ubicación existente.
El actualizador valida origen, tamaño, SHA-256, cabecera PE, producto y versión;
vuelve a comprobar el archivo antes de ejecutarlo y exige confirmación.
El instalador espera al proceso, no fuerza su cierre ni reinicia Windows.

La huella de GitHub verifica integridad frente a la publicación, no sustituye
una firma Authenticode ni protege una cuenta de publicación comprometida.
No desactives TLS, protecciones de Windows ni el aislamiento del navegador.

Guarda UTF-8, evita cambios ajenos y revisa el índice Git antes de publicar.
Nunca añadas JSON OAuth, tokens, perfiles de navegador, bases de datos ni logs.
Las versiones se gestionan con `APP_VERSION` en `src/youtube_sync_version.py`.
Consulta [Publicar versiones](RELEASES.md).
