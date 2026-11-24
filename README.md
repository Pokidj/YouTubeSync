# YouTubeSync

**Español** | [English](README.en.md)

Sube tus vídeos a YouTube desde una carpeta de Windows. Mantén a la vista qué
falta por subir, qué se está procesando y qué está confirmado, sin repetir los
archivos que ya hayas subido.

![YouTubeSync](assets/youtube-sync-logo.png)

## Descargar e instalar

**[Descargar YouTubeSync para Windows](https://github.com/Pokidj/YouTubeSync/releases/latest)**

1. En la última publicación, descarga **YouTubeSync-1.0-windows-x64-setup.exe**.
2. Ejecuta el instalador y sigue los pasos. Incluye el programa completo:
   no necesitas instalar Python ni descargar librerías aparte.
3. Abre **YouTubeSync** desde el menú Inicio o el acceso directo que hayas elegido.

Requiere Windows 10 de 64 bits (1809 o posterior) o Windows 11. Los archivos
**Source code** de GitHub son para desarrollo, no para instalar la aplicación.
El instalador aún no incorpora un certificado de firma de código propio;
Windows puede mostrar un aviso de editor desconocido. Descarga solo de este
repositorio y consulta el archivo `SHA256SUMS.txt` de la publicación.

## Conectar tu canal

1. Pulsa **Conectar mi canal**. El asistente te guía para preparar tu proyecto
   de Google Cloud y sus credenciales OAuth de escritorio.
2. Selecciona el JSON descargado y autoriza tu cuenta en el navegador de Google.
   YouTubeSync no te pide la contraseña.
3. Confirma el nombre y la imagen de tu canal.
4. Elige la carpeta de vídeos, privacidad y lista de reproducción.
5. Sube un archivo seleccionado o activa **ON** para trabajar automáticamente.

Cada usuario utiliza su propio proyecto y cuota de YouTube. La configuración
y la autorización se recuerdan. [Guía completa de conexión y uso](docs/GUIA_DE_USO.md).

## Qué puedes hacer

- **Biblioteca:** ordenar los vídeos, elegir columnas y ver sus estados, tamaño,
  duración, resolución o miniatura local.
- **Subidas:** automatizar, subir un archivo, cancelar, revisar incidencias y
  autorizar un reintento concreto.
- **Confirmación:** conservar la memoria de archivos subidos y comparar un vídeo
  local con su candidato de YouTube cuando haga falta una revisión manual.
- **Canal:** buscar, filtrar, abrir vídeos, compartir enlaces, cambiar privacidad,
  gestionar listas y revisar posibles duplicados antes de decidir qué borrar.
- **Limpieza:** borrar copias locales con comprobación previa, configurar su
  conservación o revisar los vídeos de menos de 30 segundos.
- **Ajustes:** idioma español o inglés, inicio con Windows, bandeja, columnas,
  reproducción y una consola para consultar o copiar errores.

Las confirmaciones manuales no autorizan limpieza automática. La cuota API y
el límite de subidas del canal son distintos: la app respeta sus pausas y no
inventa un contador de cuota restante ni un desbloqueo garantizado.

## Actualizar

Ve a **Ajustes > General > Buscar actualizaciones**. Cuando haya una versión
posterior, descarga el instalador y pulsa **Instalar actualización**. Tras tu
confirmación, la app se cerrará, se actualizará y volverá a abrirse. Finaliza
o cancela antes cualquier subida u operación activa.

Se conservan ajustes, autorización, sesión de reproducción y registro de subidas.
No necesitas desinstalar antes ni volver a conectar tu canal.

## Ayuda y datos

- [Guía de uso y problemas frecuentes](docs/GUIA_DE_USO.md).
- [Cómo se verifican las subidas](docs/VERIFICACION_DE_SUBIDAS.md).
- [Cambios de cada versión](CHANGELOG.md).
- [Comunicar un problema](https://github.com/Pokidj/YouTubeSync/issues): indica
  versión, acción y error; nunca adjuntes tu JSON OAuth ni tokens.

Los datos se guardan en `%APPDATA%\YouTubeSync`, separados del programa.
Desinstalar no elimina esa carpeta. Revisa los informes antes de compartirlos:
pueden contener nombres, rutas y enlaces de tus vídeos.

Para colaborar con el código: [documentación de desarrollo](docs/DESARROLLO.md).
