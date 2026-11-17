# Desarrollo y mantenimiento

## Requisitos

- Windows y Python 3.12.
- Dependencias de `outputs/youtube-sync-modern/requirements.txt`.
- JSON OAuth propio y conexion solo para probar operaciones reales con YouTube.

## Ejecutar desde un clon

```powershell
git clone https://github.com/Pokidj/YouTubeSync.git
cd YouTubeSync
python -m venv outputs/youtube-sync-modern/.venv
./outputs/youtube-sync-modern/.venv/Scripts/python.exe -m pip install -r outputs/youtube-sync-modern/requirements.txt
./outputs/youtube-sync-modern/.venv/Scripts/python.exe outputs/youtube-sync-modern/src/youtube_sync_modern.py
```

El directorio interno `youtube-sync-modern` se conserva por compatibilidad;
el nombre visible del producto es YouTubeSync.

## Arquitectura

| Ruta | Responsabilidad |
| --- | --- |
| `outputs/youtube-sync-modern/src/youtube_sync_modern.py` | Ventana Qt, ajustes, tablas, canal, miniaturas, bandeja y acciones. |
| `outputs/youtube-sync-modern/src/youtube_sync_engine.py` | Motor independiente: configuracion, SQLite, OAuth, cliente YouTube y sincronizacion. |
| `outputs/youtube-sync-modern/assets` | Icono y logo de la interfaz actual. |
| `outputs/youtube-sync-modern/build_exe.ps1` | Empaquetado Windows con PyInstaller. |
| `tests/test_layout.py` | Pruebas de la disposicion sin operaciones reales sobre YouTube. |

La interfaz importa directamente `youtube_sync_engine` desde su propio proyecto.
No hay carga dinamica de archivos de la aplicacion anterior. `archive` conserva
la copia historica y no forma parte de la compilacion ni de las pruebas activas.
El proyecto moderno no necesita Tkinter, Pillow ni pystray.

Las operaciones de red se delegan a hilos y devuelven resultados a la interfaz
mediante senales o la cola de eventos. La tabla del canal se rellena por lotes.
Las miniaturas se conservan en memoria y el panel lateral repinta la imagen
sin decodificarla durante cada redimensionado.

## Pruebas

```powershell
./outputs/youtube-sync-modern/.venv/Scripts/python.exe -m unittest discover -s tests -v
./outputs/youtube-sync-modern/.venv/Scripts/python.exe -m py_compile outputs/youtube-sync-modern/src/youtube_sync_modern.py outputs/youtube-sync-modern/src/youtube_sync_engine.py
git diff --check
```

Las pruebas usan Qt offscreen y sustituyen el almacen y las acciones de carga.
Comprueban tres tamanos de ventana, proporcion de miniaturas, contenido largo,
acceso al boton Reproducir y redistribucion al cambiar el separador.
No validan OAuth, subidas, borrado remoto ni el instalable ejecutandose.

Las pruebas de la interfaz Tk quedaron archivadas con su version. Las pruebas
activas se centran exclusivamente en Qt y su motor. La extraccion del motor
conserva la ruta de datos y los formatos de configuracion, token y SQLite.

Para validar esas operaciones, utiliza archivos y videos de prueba y verifica
los resultados en YouTube y en disco. Revisa especialmente cancelacion,
reintento, persistencia al reiniciar y conservacion de archivos ante discrepancias.

## Compilar y distribuir

```powershell
powershell -ExecutionPolicy Bypass -File build_exe.ps1
```

El script prepara las dependencias y genera:

Los scripts cargan `outputs/youtube-sync-modern/build_hooks/hook-ssl.py`. Este hook
incluye el archivo de confianza auxiliar si el runtime de Python lo requiere.
Si se invoca PyInstaller directamente, hay que conservar `--additional-hooks-dir`
con esa carpeta: una compilacion correcta no garantiza que HTTPS funcione si
faltan los datos auxiliares del runtime.

```text
outputs/youtube-sync-modern/dist/YouTubeSync/
  YouTubeSync.exe
  _internal/
```

Las pruebas OAuth utilizan credenciales simuladas y verifican concurrencia,
conservacion del token ante fallos de red y renovacion tras revocacion. No
autorizan cuentas reales ni realizan subidas.

Distribuye la carpeta completa en un ZIP. El repositorio guarda fuentes y
recursos, y excluye las compilaciones generadas. Estas pueden publicarse como
archivos adjuntos de una release cuando exista una version verificada.

La interfaz Qt se compila con `outputs/youtube-sync-modern/packaging/YouTubeSync.spec`.
Esta especificacion excluye la `icuuc.dll` que otras herramientas pueden anadir
a PATH; Qt debe usar la API ICU de Windows. No sustituyas la compilacion por
un comando generico de PyInstaller que pierda esta exclusion.

Despues de compilar, comprueba el ejecutable real desde su carpeta `dist`:

```powershell
./outputs/youtube-sync-modern/dist/YouTubeSync/YouTubeSync.exe --self-test ./qt-startup.json
```

El comando genera un informe con `ok: true` al terminar correctamente. Este
modo no carga la base de datos ni inicia OAuth. Los ejecutables de `build` son
intermedios y no pueden ejecutarse por separado. Los lanzadores
`Abrir-YouTubeSync.cmd` de la raiz apunta a la unica distribucion activa.

Puedes comprobar la distribucion Qt y sus archivos auxiliares con:

```powershell
./outputs/youtube-sync-modern/.venv/Scripts/python.exe scripts/check_distribution.py
```

## Datos y credenciales

La app utiliza `%APPDATA%\YouTubeSync` para sus datos persistentes.
El `.gitignore` permite los directorios del proyecto y excluye entornos,
compilaciones, JSON, tokens, bases de datos y registros. No anadas credenciales
a los ejemplos ni a las pruebas. Revisa `git diff --cached` antes de publicar.

## Versiones y actualizador futuro

`APP_VERSION` en la interfaz define la version mostrada en Ajustes.
La version actual es 1.0. Las mejoras posteriores permanecen en la seccion
Sin publicar de [CHANGELOG.md](../CHANGELOG.md) hasta preparar otra version.

El boton de actualizaciones actual esta deshabilitado. Todavia no hay consulta
de releases, descarga, verificacion ni instalacion automatica. Una futura
implementacion debe definir el origen de las versiones, comprobar integridad,
gestionar el cierre y la sustitucion del ejecutable y preservar los datos del usuario.

## Convenciones

- Guarda el codigo y la documentacion como UTF-8.
- Evita reescribir archivos desde PowerShell sin especificar la codificacion.
- Manten las operaciones de YouTube fuera del hilo de la interfaz.
- Distingue registro local, transferencia y procesamiento remoto en estados y mensajes.
- Documenta cambios de comportamiento y limitaciones comprobadas en el changelog.

## Identidad y conciliacion

`remote_video_state` normaliza `uploadStatus` y `processingStatus`; recibir el
archivo no equivale a procesarlo. `reconcile_local_uploads` actualiza el registro
sin iniciar subidas ni borrar archivos y omite la transferencia activa. Un fallo
de red no se interpreta como ausencia del video. La interfaz ejecuta este trabajo
fuera del hilo Qt, incluso cuando Auto esta desactivado.

Las nuevas subidas escriben `YouTubeSync-Fingerprint: sha256:<huella>` en la
descripcion. Es una huella calculada por la app antes de transferir, no un checksum
independiente proporcionado por YouTube. Los marcadores antiguos son muestreados:
se contrastan tambien con nombre original y tamano. Titulo, fecha y duracion
iguales nunca bastan para confirmar una correspondencia. Un video sin evidencia
suficiente requiere revision en Canal; no se confirma ni se borra automaticamente.

La conciliacion completa se hace al abrir o actualizar. La periodica consulta solo
IDs pendientes de resolver en lotes de 50. Las huellas se calculan en bloques y se
cachean por ruta, tamano y marcas de tiempo para no releer clips sin cambios.
