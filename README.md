# YouTubeSync

Aplicacion para Windows que vigila una carpeta y sube videos a YouTube.
Interfaz en espanol con PySide6/Qt, automatizacion, verificacion de subidas,
gestion del canal y limpieza local con comprobacion previa en YouTube.

Version actual: **1.0**.

![YouTubeSync](outputs/youtube-sync-modern/assets/youtube-sync-logo.png)

## Documentacion

- [Guia de uso](docs/GUIA_DE_USO.md): instalacion, primera configuracion,
  subidas, canal, limpieza y soluciones a problemas habituales.
- [Desarrollo y arquitectura](docs/DESARROLLO.md): estructura, ejecucion,
  compilacion, pruebas y mantenimiento.
- [Historial de cambios](CHANGELOG.md).
- [Publicar actualizaciones](docs/RELEASES.md): preparar y publicar los paquetes de GitHub Releases.

## Funciones

- Vigilancia de carpetas y subidas con titulo basado en la fecha de creacion.
- Modo automatico ON/OFF, subida seleccionada, cancelacion y reintento.
- Registro local persistente y comprobaciones con YouTube.
- Canal con miniaturas, filtros, privacidad y gestion de listas.
- Reproduccion en el navegador y enlaces para compartir.
- Limpieza local con verificacion previa del video en YouTube.
- Ajustes por pestanas, bandeja del sistema e inicio con Windows configurable.
- Primera conexion guiada, confirmacion del canal y credenciales propias por usuario.

Las subidas y consultas estan sujetas a los limites de YouTube. Desde Ajustes se
pueden consultar Releases estables de GitHub y descargar paquetes verificados.
La instalacion de esos paquetes sigue siendo manual; no se sustituye el EXE en uso.

## Desarrollo

Requiere Windows y Python 3.12. La unica interfaz activa es PySide6/Qt.

```powershell
python -m venv outputs/youtube-sync-modern/.venv
./outputs/youtube-sync-modern/.venv/Scripts/python.exe -m pip install -r outputs/youtube-sync-modern/requirements.txt
./outputs/youtube-sync-modern/.venv/Scripts/python.exe outputs/youtube-sync-modern/src/youtube_sync_modern.py
```

## Compilar

```powershell
powershell -ExecutionPolicy Bypass -File build_exe.ps1
```

El ejecutable se genera en
`outputs/youtube-sync-modern/dist/YouTubeSync/YouTubeSync.exe`.
Para distribuirlo se necesita la carpeta `YouTubeSync` completa, incluido `_internal`.

## Estructura

- `outputs/youtube-sync-modern`: unico proyecto activo, con interfaz Qt y motor propio.
- `archive/youtube-sync-legacy`: copia historica, excluida de las compilaciones.
- `tests`: pruebas de Qt, OAuth y compatibilidad de datos locales.

Para abrir la app utiliza **Abrir-YouTubeSync.cmd** en la raiz del repositorio.
Este es el unico punto de entrada recomendado. La app se llama YouTubeSync;
la carpeta `modern` identifica el proyecto Qt en desarrollo.

El motor esta en `outputs/youtube-sync-modern/src/youtube_sync_engine.py`.
No depende de la aplicacion archivada. Se mantiene `%APPDATA%\YouTubeSync`
para conservar configuracion, token y registro de subidas.

## Configuracion

En la primera apertura aparece **Conectar mi canal**: proyecto propio, API,
credenciales de escritorio, autorizacion en el navegador, confirmacion del canal
y carpeta. Tambien se puede abrir desde Ajustes > YouTube. Hay un acceso directo
para quien ya tenga el JSON. La app conserva su copia y recuerda la autorizacion.
Cada usuario aporta su propio proyecto; no se distribuyen credenciales comunes
ni se alternan proyectos automaticamente para ampliar cuota.

Las credenciales, tokens, bases de datos, videos y compilaciones locales quedan
excluidos del repositorio. No se incluyen datos personales de configuracion.

## Verificar la interfaz

```powershell
./outputs/youtube-sync-modern/.venv/Scripts/python.exe -m unittest discover -s tests -v
```
