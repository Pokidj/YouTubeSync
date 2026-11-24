# Publicar actualizaciones en GitHub

**Español** | [English](RELEASES.en.md)

## Fuente de actualizaciones

YouTubeSync consulta exclusivamente la ultima Release estable publicada en
`Pokidj/YouTubeSync`. Un commit, un push o una etiqueta sin Release no ofrece una
actualizacion a los usuarios. Se omiten borradores y versiones preliminares.
La busqueda es manual desde Ajustes > General > Buscar actualizaciones.

La version instalada se define en
`outputs/youtube-sync-modern/src/youtube_sync_version.py`. La actual sigue siendo
1.0; este cambio no publica por si mismo una version 1.1.

## Preparar, por ejemplo, la version 1.1

1. Cambia `APP_VERSION` a `1.1` y actualiza las notas en CHANGELOG.md.
2. Ejecuta las pruebas y compila la aplicacion completa.
3. Genera el paquete desde la raiz del repositorio:

```powershell
./outputs/youtube-sync-modern/.venv/Scripts/python.exe -m unittest discover -s tests
powershell -ExecutionPolicy Bypass -File build_exe.ps1
./outputs/youtube-sync-modern/.venv/Scripts/python.exe scripts/create_release.py
```

El ultimo comando comprueba el arranque y SSL del EXE y exige que su version
coincida con el codigo. No permite renombrar una compilacion 1.0 como 1.1.
Genera en `work/releases`:

- `YouTubeSync-1.1-windows-x64.zip`
- `SHA256SUMS.txt`

El ZIP contiene la carpeta `YouTubeSync` completa, incluido `_internal` y el
manifiesto `YouTubeSync/release.json`. No distribuyas el EXE suelto ni el ZIP
automatico Source code de GitHub: ninguno sustituye el paquete compilado.
El empaquetador rechaza nombres habituales de configuracion y datos personales;
revisa igualmente el contenido antes de publicarlo.

## Crear la Release

1. Sube y guarda en Git los cambios correspondientes a la version.
2. Abre [Releases](https://github.com/Pokidj/YouTubeSync/releases) y crea una nueva.
3. Usa la etiqueta `v1.1`, el titulo `YouTubeSync 1.1` y sus notas de cambios.
4. Adjunta el ZIP generado y `SHA256SUMS.txt` como assets.
5. Publicala como version estable y marcala como ultima version. No la dejes
   como borrador ni marques Pre-release para distribuirla por este canal.

El nombre del ZIP debe coincidir exactamente con la version. GitHub debe
proporcionar `digest=sha256:...` para ese asset. La app no descarga un paquete
sin una huella publicada valida, aunque exista un archivo SHA256SUMS.txt.

## Que recibe el usuario

Al pulsar Buscar actualizaciones, se compara la version instalada con la
ultima Release. Si hay una posterior con paquete compatible, aparecen Descargar
y Notas. La descarga muestra progreso, permite cancelar y usa HTTPS sin token
de GitHub ni autorizacion de YouTube.

Antes de guardar el ZIP definitivo se comprueban tamano, SHA-256 publicado,
rutas del archivo, runtime incluido, version y plataforma del manifiesto. Los
parciales fallidos no se ofrecen como descargas terminadas. Los ZIP se guardan
en `%APPDATA%\YouTubeSync\updates`; Abrir carpeta muestra ese directorio.

Esta primera implementacion **descarga, pero no instala automaticamente**.
El usuario cierra YouTubeSync completamente, extrae el ZIP y sustituye la carpeta
de programa completa. Los ajustes, OAuth y registro siguen en AppData. La app no
sobrescribe un ejecutable que este en uso ni ejecuta el contenido descargado.

SHA-256 comprueba la integridad respecto a la huella de GitHub; no equivale a
una firma digital de Windows ni protege por si solo una cuenta de publicacion
comprometida. Una instalacion automatica futura debe incorporar firma/verificacion,
cierre coordinado, copia de seguridad y recuperacion.

## Referencias

- [API de Releases de GitHub](https://docs.github.com/en/rest/releases/releases#get-the-latest-release)
- [Assets y descarga](https://docs.github.com/en/rest/releases/assets#get-a-release-asset)
