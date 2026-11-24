# Publicar versiones

**Español** | [English](RELEASES.en.md)

## Contrato de una publicación

La primera versión pública es **1.0**. Cada Release estable debe contener:

- `YouTubeSync-1.0-windows-x64-setup.exe`: instalador completo, no el EXE suelto.
- `SHA256SUMS.txt`: huella del instalador.
- Notas en español e inglés con funciones, cambios y limitaciones relevantes.

El número se adapta a cada versión. El Source code ZIP que genera GitHub no es
el instalador. No se publican entornos, perfiles, credenciales ni datos locales.

## Compilar localmente

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
powershell -ExecutionPolicy Bypass -File build_exe.ps1
.\.venv\Scripts\python.exe scripts/check_distribution.py
.\.venv\Scripts\python.exe scripts/create_release.py
```

Inno Setup 7 debe estar instalado; `ISCC` permite indicar otra ubicación de
`ISCC.exe`. El resultado queda en `releases`. El generador comprueba el arranque
y versión del EXE, rechaza datos personales, compila el instalador y valida sus
recursos de producto/versión. No permite renombrar una compilación antigua como nueva.

## Publicación automática

El flujo `.github/workflows/release.yml` valida, compila y publica cuando cambia
el código, pruebas o empaquetado en `main`, cuando se incorpora el propio flujo o
al ejecutarlo manualmente desde Actions. Si la versión ya está publicada no la
sobrescribe: para otra publicación hay que incrementar `APP_VERSION`.

Para preparar 1.1, cambia `APP_VERSION` a `1.1`, actualiza ambos changelogs y
`docs/RELEASE_NOTES.md`, y publica el código. El flujo crea la etiqueta `v1.1`
en ese commit y adjunta el instalador comprobado. Un fallo de pruebas o de
instalación impide publicar la Release. No se usan secretos de YouTube.

## Flujo del actualizador

1. El usuario busca la última Release estable desde Ajustes. Se omiten borradores
   y versiones preliminares; no se ofrecen rebajas ni reinstalaciones de la misma versión.
2. Se selecciona el instalador cuyo nombre coincide exactamente con la versión,
   URL del repositorio y huella `sha256:` publicada por GitHub.
3. La descarga HTTPS comprueba tamaño y SHA-256 antes de conservar el archivo.
   También se valida la cabecera PE, ProductName, ProductVersion y FileDescription.
4. Al pulsar Instalar actualización se pide confirmación y se vuelve a verificar
   el archivo fuera del hilo Qt. Una operación activa impide cerrar para actualizar.
5. Se inicia el instalador y se cierra la app de verdad, sin dejarla en bandeja.
   El instalador espera al PID, actualiza la ubicación previa y vuelve a abrirla.

Se instala por usuario sin elevar permisos, no se fuerza el cierre de otras
aplicaciones ni se reinicia Windows. Los datos de `%APPDATA%\YouTubeSync` se
conservan, también al desinstalar. La entrada de inicio con Windows se renueva
desde la aplicación si estaba activada. Las descargas están en
`%APPDATA%\YouTubeSync\updates`.

## Seguridad y mantenimiento

La integridad contra el digest de GitHub no sustituye Authenticode. La primera
versión no tiene certificado de firma propio; no la anuncies como firmada.
Protege la cuenta de publicación y no sobrescribas assets de versiones publicadas.
No indiques a los usuarios que desactiven las protecciones de Windows.

Referencias: [Inno Setup](https://jrsoftware.org/inno-setup/documentation/),
[parámetros de instalación](https://jrsoftware.org/inno-setup/documentation/topic_setupcmdline.htm),
[Releases de GitHub](https://docs.github.com/en/rest/releases/releases).
