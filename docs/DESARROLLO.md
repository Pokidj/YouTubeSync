# Desarrollo y mantenimiento

## Requisitos

- Windows y Python 3.12 con Tkinter.
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
| `outputs/youtube-sync/src/youtube_sync_app.py` | Motor compartido: configuracion, SQLite, OAuth, cliente YouTube y trabajador de sincronizacion. Tambien contiene la interfaz anterior. |
| `outputs/youtube-sync-modern/assets` | Icono y logo de la interfaz actual. |
| `outputs/youtube-sync-modern/build_exe.ps1` | Empaquetado Windows con PyInstaller. |
| `tests/test_layout.py` | Pruebas de la disposicion sin operaciones reales sobre YouTube. |

La interfaz carga el motor compartido desde la carpeta hermana en desarrollo
y desde el paquete generado en la compilacion. Por ello deben conservarse
ambas carpetas al clonar o distribuir el codigo fuente.

Las operaciones de red se delegan a hilos y devuelven resultados a la interfaz
mediante senales o la cola de eventos. La tabla del canal se rellena por lotes.
Las miniaturas se conservan en memoria y el panel lateral repinta la imagen
sin decodificarla durante cada redimensionado.

## Pruebas

```powershell
./outputs/youtube-sync-modern/.venv/Scripts/python.exe -m unittest discover -s tests -v
./outputs/youtube-sync-modern/.venv/Scripts/python.exe -m py_compile outputs/youtube-sync-modern/src/youtube_sync_modern.py outputs/youtube-sync/src/youtube_sync_app.py
git diff --check
```

Las pruebas usan Qt offscreen y sustituyen el almacen y las acciones de carga.
Comprueban tres tamanos de ventana, proporcion de miniaturas, contenido largo,
acceso al boton Reproducir y redistribucion al cambiar el separador.
No validan OAuth, subidas, borrado remoto ni el instalable ejecutandose.

`test_legacy_layout.py` abre ventanas Tk de prueba, con almacenamiento y
operaciones de red sustituidos, para comprobar que las tres pestanas de la
interfaz anterior mantienen las tablas visibles en modo ventana. Estas pruebas
requieren una sesion de escritorio disponible.

Para validar esas operaciones, utiliza archivos y videos de prueba y verifica
los resultados en YouTube y en disco. Revisa especialmente cancelacion,
reintento, persistencia al reiniciar y conservacion de archivos ante discrepancias.

## Compilar y distribuir

```powershell
powershell -ExecutionPolicy Bypass -File outputs/youtube-sync-modern/build_exe.ps1
```

El script prepara las dependencias y genera:

```text
outputs/youtube-sync-modern/dist/YouTubeSync/
  YouTubeSync.exe
  _internal/
```

Distribuye la carpeta completa en un ZIP. El repositorio guarda fuentes y
recursos, y excluye las compilaciones generadas. Estas pueden publicarse como
archivos adjuntos de una release cuando exista una version verificada.

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
