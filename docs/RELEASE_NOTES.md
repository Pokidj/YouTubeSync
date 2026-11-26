# YouTubeSync 1.1

## Español

Una actualización centrada en consultar y reproducir tus vídeos, con una interfaz
más clara y sin perder las protecciones de las subidas y los archivos locales.

### Novedades

- **En mi equipo / En YouTube:** nombres representativos, nuevo logo S y botones
  con iconos, ayudas y colores suaves según su función.
- **Perfil y Avisos:** conexión y configuración reunidas, avisos navegables que
  conservan tu elección y acciones sin duplicados.
- **Vistas previas laterales:** aparecen al seleccionar, se pueden ocultar con
  una flecha y conservan su ancho durante la sesión. Acciones dentro del marco,
  fijas abajo, con ruta o enlace y fichas de datos con iconos.
- **Reproductores unificados:** posición, pausa, saltos de diez segundos, volumen
  y pantalla completa con controles. Escape vuelve al panel sin reiniciar el vídeo.
  En YouTube, Play está siempre visible y sustituye el botón Reproducir aparte.
- **Vídeos privados:** reproducción con la sesión independiente de Ajustes >
  Reproducción, sin entregar al reproductor el token OAuth de la API.
- **Canal:** imagen e identidad y totales de públicos, privados y ocultos sin
  inflarlos con referencias no disponibles ni recalcularlos con el filtro.
- **Compartir:** confirmación para pasar a Oculto y casilla opcional «Iniciar en…»
  con el instante real del reproductor.
- **Listas por lotes:** icono junto a Privacidad, confirmación, resultados parciales
  y parada por cuota; primero se añade la lista destino para no perder las anteriores
  si falla esa operación.
- **Tablas y ajustes:** columnas, orden y color de selección configurables en ambas
  vistas, 14 columnas disponibles en En YouTube y búsqueda de ajustes mejorada.
- **Archivos locales:** carpeta raíz de Ajustes y Localizar en el Explorador son
  acciones distintas. Los pendientes ya no ofrecen comprobación guiada.

### Instalar o actualizar

Descarga **YouTubeSync-1.1-windows-x64-setup.exe**. Incluye el programa completo;
no necesitas Python. Desde 1.0, usa **Ajustes > General > Buscar actualizaciones**,
descarga e instala cuando no haya operaciones activas. No desinstales antes:
se conservan ajustes, autorización, sesión de reproducción y registro de subidas.

Se incluye **SHA256SUMS.txt**. El instalador no tiene firma Authenticode propia.
YouTube sigue imponiendo cuotas y permisos; no hay un contador exacto de cuota
restante ni una hora garantizada de desbloqueo. La reproducción privada depende
de que YouTube autorice la cuenta de la sesión. Los códecs disponibles dependen de
Windows. Una confirmación manual nunca autoriza limpieza automática.

[Historial completo](https://github.com/Pokidj/YouTubeSync/blob/v1.1/CHANGELOG.md) ·
[Guía de uso](https://github.com/Pokidj/YouTubeSync/blob/v1.1/docs/GUIA_DE_USO.md)

## English

A release focused on browsing and playing your videos, with a clearer interface
while keeping upload and local-file safeguards.

### What's New

- **On my computer / On YouTube:** representative tab names, new S logo and
  icon-based buttons with hover help and muted functional colors.
- **Profile and Notices:** combined connection/configuration, notice navigation
  that retains your choice and commands without duplication.
- **Preview sidebars:** appear for a selection, hide with an arrow and retain their
  widths during the session. Actions are docked inside the frame, with paths/links
  and matching icon-based details.
- **Matching players:** seeking, pause, ten-second skips, volume and full screen
  with controls. Escape returns inline without restarting. On YouTube's always-visible
  Play control replaces the separate Play button.
- **Private videos:** use the dedicated Settings > Playback session; the API OAuth
  token is never passed to the player.
- **Channel:** avatar, identity and public/private/unlisted totals, without counting
  unavailable references as videos or recalculating totals from filters.
- **Share:** confirm changing to Unlisted and optionally select Start at using the
  real captured player position.
- **Batch playlists:** icon beside Visibility, confirmation, partial results and
  quota stop; add the destination before removing old memberships.
- **Tables and Settings:** configurable columns, order and selection color for
  both views, 14 available YouTube columns and improved settings search.
- **Local files:** open the configured folder or locate the selected file in
  Explorer as separate actions. Pending files no longer offer guided matching.

### Install or Update

Download **YouTubeSync-1.1-windows-x64-setup.exe**, the complete application; no
Python installation is needed. From 1.0 use **Settings > General > Check for updates**,
download and install after completing active operations. Do not uninstall first:
settings, authorization, playback session and upload history are retained.

**SHA256SUMS.txt** is included. The installer has no publisher-owned Authenticode
signature. YouTube quotas and permissions still apply; there is no exact remaining
quota counter or guaranteed unlock time. Private playback requires an authorized
session account. Codec support depends on Windows. Manual confirmation never
authorizes automatic cleanup.

[Full changelog](https://github.com/Pokidj/YouTubeSync/blob/v1.1/CHANGELOG.en.md) ·
[User guide](https://github.com/Pokidj/YouTubeSync/blob/v1.1/docs/USER_GUIDE.en.md)
