"""English UI catalog. Spanish source labels are the stable message identifiers."""

ENGLISH = dict(line.split("|", 1) for line in """
Reproducir a pantalla completa|Play full screen
En mi equipo|On my computer
En YouTube|On YouTube
Conexión|Connection
Archivos y subidas|Files and uploads
Columnas de archivos|Local file columns
Columnas de YouTube|YouTube columns
Selecciona al menos una columna de archivos locales.|Select at least one local file column.
Selecciona al menos una columna de YouTube.|Select at least one YouTube column.
Compartir desde aquí|Share from here
Subtítulos|Captions
Columnas de Canal|Channel columns
Color de selección|Selection color
Verde|Green
Azul|Blue
Rojo|Red
Violeta|Violet
ID del vídeo|Video ID
Archivo original|Original file
Calidad|Quality
Procesamiento|Processing
Selecciona al menos una columna para Canal.|Select at least one channel column.
Activa o desactiva los subtítulos disponibles para este vídeo.|Turn available captions on or off for this video.
Elige la lista de reproducción del vídeo seleccionado y confirma el cambio.|Choose the selected video's playlist and confirm the change.
Permite elegir si el enlace empieza en la posición actual; cambia el vídeo a Oculto tras confirmar.|Choose whether the link starts at the current position; set the video to Unlisted after confirmation.
Restaurar columnas de Canal|Restore channel columns
Restaurar columnas de esta tabla|Restore this table's columns
Restaura las columnas de esta tabla sin cambiar los vídeos ni su color de selección.|Restore this table's columns without changing videos or its selection color.
No hay ajustes que coincidan con la búsqueda.|No settings match your search.
Restaura las columnas iniciales de Canal sin cambiar los datos de YouTube.|Restore the initial channel columns without changing YouTube data.
Revisar acceso en Ajustes|Review access in Settings
Abre el reproductor a pantalla completa con sus controles; reproducir en el panel no cambia de vista.|Open the player full screen with its controls; playing in the panel does not change the view.
Abre Ajustes en Reproducción para revisar la cuenta y sus permisos de acceso al vídeo.|Open Settings on Playback to review the account and video access permissions.
Posición del vídeo|Video position
Ir a un punto del vídeo|Seek within the video
Volumen del vídeo|Video volume
Retroceder 10 segundos|Back 10 seconds
Avanzar 10 segundos|Forward 10 seconds
Reanudar vídeo|Resume video
Pausar vídeo|Pause video
Silenciar vídeo|Mute video
Activar sonido del vídeo|Unmute video
Sesión de reproducción|Playback session
Inicia sesión en YouTube y vuelve a reproducir el vídeo.|Sign in to YouTube, then play the video again.
Abriendo YouTube con la sesión de reproducción…|Opening YouTube using the playback session…
Se necesita Chrome o Microsoft Edge para reproducir los privados con tu sesión.|Chrome or Microsoft Edge is required to play private videos using your session.
Cierra las ventanas de la sesión de reproducción y vuelve a abrirla desde Ajustes > Reproducción. No cierres tu navegador habitual.|Close the playback-session windows and reopen the session from Settings > Playback. Do not close your usual browser.
YouTube no permite reproducir este vídeo con esta sesión. Revisa la cuenta en Ajustes > Reproducción.|YouTube does not allow playback with this session. Check the account in Settings > Playback.
YouTube no da acceso a este vídeo. Inicia sesión con una cuenta autorizada en Ajustes > Reproducción.|YouTube is not granting access to this video. Sign in with an authorized account in Settings > Playback.
No se pudo abrir el vídeo en la sesión de YouTube.|Could not open the video in the YouTube session.
No se pudo cargar YouTube. Comprueba la conexión y reintenta.|Could not load YouTube. Check the connection and retry.
El reproductor ha salido del vídeo seleccionado. Vuelve a cargarlo.|The player has left the selected video. Load it again.
Se ha cerrado la sesión del reproductor. Vuelve a cargar el vídeo.|The player session was closed. Load the video again.
Windows no ha permitido identificar la ventana del reproductor.|Windows could not identify the player window.
El reproductor aún no está disponible. Reintenta la carga del vídeo.|The player is not available yet. Try loading the video again.
La configuración local del reproductor no es válida.|The local player configuration is invalid.
Retrocede diez segundos dentro del vídeo que se está reproduciendo.|Go back ten seconds in the video currently playing.
Avanza diez segundos dentro del vídeo que se está reproduciendo.|Go forward ten seconds in the video currently playing.
Pausa el vídeo actual sin cerrar el reproductor ni perder su posición.|Pause the current video without closing the player or losing its position.
Continúa la reproducción desde la posición actual del vídeo.|Resume playback from the video's current position.
Silencia solo este vídeo; no cambia el volumen de Windows.|Mute this video only; Windows volume is unchanged.
Recupera el sonido del vídeo con el volumen elegido.|Unmute the video at the selected volume.
Abre la sesión de YouTubeSync para iniciar sesión con una cuenta autorizada a ver el vídeo privado.|Open the YouTubeSync session to sign in with an account authorized to watch the private video.
Tu canal de YouTube|Your YouTube channel
Canal vinculado|Linked channel
Públicos|Public
Privados|Private
Ocultos|Unlisted
Sin cargar|Not loaded
Copia guardada|Saved snapshot
Canal actualizado|Channel updated
Reproductor / YouTubeSync|Player / YouTubeSync
Abrir en YouTube|Open on YouTube
Abrir reproductor en ventana|Open player in a separate window
Volver al panel|Return to panel
Detener reproducción|Stop playback
Pantalla completa|Full screen
Salir de pantalla completa|Exit full screen
Reproduciendo en ventana|Playing in a separate window
Reproduce el vídeo seleccionado dentro del panel del canal con la sesión de reproducción de YouTubeSync.|Play the selected video in the channel panel using the YouTubeSync playback session.
Mueve el mismo reproductor a una ventana independiente que puedes ampliar a pantalla completa.|Move the same player to a separate window that can be made full screen.
Devuelve el reproductor al panel del canal sin iniciar una segunda reproducción.|Return the player to the channel panel without starting a second playback.
Detiene el vídeo y cierra su reproductor, sin dejar audio reproduciéndose en segundo plano.|Stop the video and close its player without leaving audio playing in the background.
Abre la pantalla completa; Escape o salir devuelve el vídeo al panel sin abrir una ventana pequeña.|Open full screen; Escape or exit returns the video to the panel without opening a small window.
Ahora|Now
Avisos|Notices
Opciones generales|General options
Cambiar lista de seleccionados|Change selected videos' playlist
Mover {count} vídeo(s) a '{playlist}'?|Move {count} video(s) to '{playlist}'?
Se quitarán de sus otras listas de reproducción.|They will be removed from their other playlists.
Cambiando lista de {count} vídeo(s)...|Changing playlist for {count} video(s)...
Listas: {updated} actualizado(s), {errors} error(es), {skipped} sin intentar.|Playlists: {updated} updated, {errors} error(s), {skipped} not attempted.
Comparar|Compare
Abre los avisos y las opciones generales de conexión, cuota y diagnóstico; no realiza subidas ni borra archivos por sí solo.|Open notices and general connection, quota and diagnostic options; opening this menu does not upload or delete files.
Localizar|Locate
Mostrar panel|Show panel
Ocultar panel|Hide panel
Abrir carpeta configurada|Open configured folder
Mostrar archivo en Windows|Reveal file in Windows
La carpeta configurada no está disponible.|The configured folder is not available.
Abre en el Explorador la carpeta elegida en Ajustes, aunque tengas otro archivo seleccionado.|Open the folder chosen in Settings in File Explorer, even if another file is selected.
Abre el Explorador y resalta el archivo seleccionado en la tabla.|Open File Explorer and highlight the file selected in the table.
Mostrar vista previa|Show preview
Ocultar vista previa|Hide preview
Muestra el vídeo seleccionado y sus controles en el panel lateral, sin iniciar la reproducción.|Show the selected video and its controls in the sidebar without starting playback.
Oculta el panel lateral y detiene su reproducción, conservando la fila seleccionada.|Hide the sidebar and stop its playback while keeping the selected row.
Abrir en el Explorador|Show in File Explorer
Selecciona un archivo|Select a file
Selecciona un archivo para previsualizarlo.|Select a file to preview it.
Comprobar con YouTube|Check with YouTube
Canal|Channel
Canal y carpeta|Channel and folder
Configuracion|Settings
Estado|Status
Ajustes|Settings
General|General
Aplicacion|Application
Idioma|Language
Tras reiniciar|After restart
Idioma de la aplicación|Application language
Se aplica al volver a abrir YouTubeSync.|Applies the next time you open YouTubeSync.
Biblioteca|Library
Biblioteca de videos|Video library
Canal de YouTube|YouTube channel
Videos|Videos
Carpeta|Folder
Carpeta de videos|Video folder
Carpeta de vídeos|Video folder
Categoria|Category
Lista|Playlist
Listas|Playlists
Lista de reproduccion|Playlist
Lista destino|Destination playlist
Privacidad|Visibility
Duracion|Duration
Publicado|Published
Titulo|Title
Archivo|File
Tamaño|Size
Creado|Created
Ruta|Path
Calidad|Quality
Resolución|Resolution
Miniatura|Thumbnail
Columnas de la biblioteca|Library columns
Mover columna arriba|Move column up
Mover columna abajo|Move column down
Predeterminadas|Defaults
Diagnostico|Diagnostics
Consola|Console
Guardar|Save
Cancelar|Cancel
Cerrar|Close
Salir|Exit
Mostrar|Show
Elegir|Browse
Elegir carpeta|Choose folder
Selecciona carpeta|Select folder
Selecciona JSON OAuth|Select OAuth JSON
Selecciona el JSON de Google Cloud|Select Google Cloud JSON
Extensiones|Extensions
Incluir subcarpetas|Include subfolders
Automatizacion|Automation
Arrancar con Auto ON|Start with Auto ON
Arrancar minimizada|Start minimized
Al cerrar, dejar en bandeja|Keep running in the system tray when closed
Iniciar con Windows|Start with Windows
Revisar cada (segundos)|Scan every (seconds)
Esperar estabilidad (segundos)|Wait for file stability (seconds)
Limpieza|Cleanup
Limpieza local|Local cleanup
Limpieza configurada|Scheduled cleanup
Borrar automaticamente archivos locales ya subidos|Automatically delete uploaded local files
Borrar tras|Delete after
minutos|minutes
horas|hours
dias|days
minuto|minute
hora|hour
dia|day
Reproducción|Playback
Sesión de reproducción|Playback session
Gestionar sesión|Manage session
Gestionar sesión de reproducción|Manage playback session
Se necesita Chrome o Microsoft Edge|Chrome or Microsoft Edge is required
Cuenta independiente de OAuth|Account separate from OAuth
Ventana de sesión abierta. Comprueba la cuenta con acceso a tus vídeos privados.|Session window opened. Check the account that can access your private videos.
Conectar mi canal|Connect my channel
Conectar canal|Connect channel
Conectar|Connect
Conectado|Connected
Conexion|Connection
Sin conexion|Disconnected
Sin confirmar|Unconfirmed
Canal sin confirmar|Unconfirmed channel
Canal conectado|Channel connected
Canal confirmado|Channel confirmed
Canal conectado / confirmaciones guardadas|Channel connected / confirmations saved
Preparado / confirmaciones guardadas|Ready / confirmations saved
Preparado|Ready
Listo|Ready
Pendiente|Pending
Pendientes|Pending
Subido|Uploaded
Subidos|Uploaded
Ya subidos|Uploaded
Subido (manual)|Uploaded (manual)
Incidencia|Issue
Incidencias|Issues
En curso|In progress
En espera|Waiting
En pausa|Paused
Por verificar|Needs verification
Revisar|Review
Sin revisar|Not reviewed
Subiendo|Uploading
Preparando|Preparing
Procesando|Processing
Cancelando|Cancelling
Trabajando|Working
Trabajando...|Working...
Esperando archivos|Waiting for files
Sin transferencia activa|No active upload
Transferencia en curso|Upload in progress
Archivo recibido|File received
Archivo en espera|File waiting
Subida|Upload
Subida cancelada|Upload cancelled
Subida confirmada|Upload confirmed
Subida cancelada / Auto OFF|Upload cancelled / Auto OFF
Subida de pendientes solicitada.|Pending uploads requested.
Modo automatico activo|Automatic mode enabled
Modo automatico pausado|Automatic mode paused
Automatico ON|Automatic ON
Automatico OFF|Automatic OFF
Automatizacion activa|Automation enabled
Automatizacion parada|Automation disabled
Subir|Upload
Subir pendientes|Upload pending videos
Subir seleccionado|Upload selected
Cancelar subida|Cancel upload
Cancelar subida actual|Cancel current upload
Actualizar|Refresh
Actualizar carpeta|Refresh folder
Comprobar|Check
Reintentar|Retry
Reintentar video|Retry video
Reintentar conexion|Retry connection
Abrir|Open
Abrir local|Open local file
Ver local|View local file
Ver YouTube|View on YouTube
Abrir YouTube|Open YouTube
Reproducir|Play
Compartir|Share
Compartir video|Share video
Cambiar privacidad|Change visibility
Cambiar lista|Change playlist
Mover a lista|Move to playlist
Duplicados|Duplicates
Borrar|Delete
Borrar local|Delete local file
Borrar archivo local|Delete local file
Borrar archivos locales|Delete local files
Borrado local|Local deletion
Borrar del canal|Delete from channel
Borrar de todos modos|Delete anyway
Comprobar y borrar|Verify and delete
Opciones de limpieza local|Local cleanup options
Según tiempo de conservación|By retention period
Vídeos de menos de 30 segundos|Videos under 30 seconds
Limpiar vídeos de menos de 30 segundos|Clean up videos under 30 seconds
Limpieza de vídeos cortos|Short video cleanup
Buscando vídeos cortos|Finding short videos
Vídeos cortos|Short videos
Revisar antes de subir|Review before uploading
Autorizar y subir|Approve and upload
Filtros|Filters
Buscar por titulo, lista o enlace|Search by title, playlist or link
Fecha: 2026, 2026-06...|Date: 2026, 2026-06...
Todas|All
Ninguna|None
Sin lista|No playlist
Sin titulo|Untitled
Sin fecha|No date
Sin carpeta|No folder
Sin imagen|No image
Sin miniatura|No thumbnail
Cargando miniatura...|Loading thumbnail...
Cargando...|Loading...
Cargar canal|Load channel
Cargando canal desde YouTube...|Loading channel from YouTube...
Cargar listas|Load playlists
Crear lista|Create playlist
Nombre de la lista:|Playlist name:
Lista sin nombre|Untitled playlist
Lista actualizada correctamente.|Playlist updated.
Lista creada correctamente.|Playlist created.
Privado|Private
Oculto|Unlisted
Publico|Public
Selecciona un video|Select a video
Miniatura, datos y acciones rapidas.|Thumbnail, details and quick actions.
Aqui veras la miniatura, datos y acciones rapidas.|The thumbnail, details and quick actions appear here.
Pulsa Cargar canal o abre esta pestana para consultar YouTube.|Click Load channel or open this tab to check YouTube.
Abrir el video seleccionado en el navegador|Open the selected video in your browser
Aviso anterior|Previous notice
Siguiente aviso|Next notice
Copiar detalle|Copy details
Copiar errores|Copy errors
Copiar informe|Copy report
Copiar avisos y errores|Copy warnings and errors
Guardar informe|Save report
Limpiar registro temporal|Clear temporary log
Buscar mensaje, archivo o codigo de error|Search message, file or error code
Todo|All
Avisos y errores|Warnings and errors
Solo errores|Errors only
Todos los origenes|All sources
Seguir|Follow
Guardar diagnostico|Save diagnostics
Registro (*.log)|Log (*.log)
Fecha|Date
Sistema|System
Servicio|Service
Revisión|Review
Verificación|Verification
Comprobación|Check
Confirmación manual|Manual confirmation
Confirmación manual guardada|Manual confirmation saved
Confirmado por ti|Confirmed by you
Sin confirmación automática|No automatic confirmation
Vincular YouTube|Link YouTube video
Asignar enlace|Assign link
Editar confirmación|Edit confirmation
Confirmar coincidencia|Confirm match
Comprobar con API|Check with API
Comprobar este vídeo|Check this video
Comprobando este vídeo|Checking this video
Descartando asociación|Rejecting match
Guardando confirmación manual|Saving manual confirmation
Verificación automática confirmada|Automatic verification confirmed
Ver archivos|Show files
Ocultar archivos|Hide files
Cuota API|API quota
Ver cuota|View quota
Cuota de YouTube|YouTube quota
Cuota diaria API|Daily API quota
Cuota de consultas agotada|Query quota exhausted
Cuota de subidas agotada|Upload quota exhausted
Limite temporal API|Temporary API limit
Límite de subidas del canal|Channel upload limit
Límites del canal|Channel limits
Límites del canal y cuota API|Channel limits and API quota
Solicitar ampliacion|Request more quota
Ayuda oficial|Official help
Activar API|Enable API
Activa la API de YouTube|Enable the YouTube API
Requiere atencion|Needs attention
Hay avisos pendientes|Pending notices
Fallo de conexion|Connection error
Revisa la conexion|Check your connection
Faltan permisos|Missing permissions
Revisa carpeta o archivo|Check folder or file
Falta conectar el canal|Connect your channel
Falta una carpeta disponible|Choose an available folder
Configuracion aplazada / Auto OFF|Setup postponed / Auto OFF
Proceso terminado|Process finished
Procesamiento pendiente|Processing pending
Procesamiento pendiente de confirmar.|Processing still needs confirmation.
Revisando archivos|Checking files
Comprobando YouTube|Checking YouTube
Comprobando videos con YouTube...|Checking videos with YouTube...
Video en Oculto / enlace copiado|Video set to Unlisted / link copied
Preparando enlace compartido...|Preparing sharing link...
Salir de YouTubeSync|Exit YouTubeSync
La app sigue funcionando en la bandeja.|The app is still running in the system tray.
Buscar ajuste: carpeta, columnas, privacidad, auto, limpieza...|Search settings: folder, columns, visibility, auto, cleanup...
Tamaño del archivo|File size
Miniatura del Explorador de Windows|Windows Explorer thumbnail
Miniatura del Explorador de Windows, si el formato dispone de ella.|Windows Explorer thumbnail, if available for this format.
Dimensiones reales del archivo, leidas por Windows.|Actual file dimensions reported by Windows.
Buscar actualizaciones|Check for updates
Sin comprobar|Not checked
Descargar|Download
Notas|Release notes
Abrir carpeta|Open folder
Consultando Releases de GitHub...|Checking GitHub Releases...
No hay una release estable publica disponible.|No public stable release is available.
No hay una version posterior publicada.|No newer version has been published.
Descargando desde GitHub...|Downloading from GitHub...
Descarga cancelada. Puedes reintentar.|Download cancelled. You can retry.
Reproducir local|Play local file
Pausar local|Pause local playback
Silenciar|Mute
Activar sonido|Unmute
Ver local fuera|Open local file externally
Comparar vídeo / YouTubeSync|Compare video / YouTubeSync
Enlace o ID del vídeo de YouTube|YouTube video link or ID
Reproducir YouTube aquí|Play YouTube here
Abrir YouTube en navegador|Open YouTube in browser
Candidato de YouTube|YouTube candidate
¿Es el mismo vídeo completo y de tu canal?|Is it the same complete video, on your channel?
Sí, corresponde|Yes, it matches
No, es otro vídeo|No, it is a different video
El candidato no corresponde|The candidate does not match
Subir como vídeo nuevo|Upload as a new video
Guardar sin subir|Save without uploading
Anterior|Back
Siguiente|Next
Siguiente: YouTube|Next: YouTube
Ya lo he revisado|I have reviewed it
Revisa el archivo local|Review the local file
Compara con YouTube|Compare with YouTube
Confirma la correspondencia|Confirm the match
Elige qué hacer|Choose what to do
Candidato abierto en el navegador|Candidate opened in browser
No se ha podido abrir el navegador. Vuelve a intentarlo.|Could not open the browser. Try again.
No se pudo guardar el informe completo.|Could not save the complete report.
Conectar mi canal / YouTubeSync|Connect my channel / YouTubeSync
Conecta tu canal|Connect your channel
Cuenta de Google / Proyecto propio de Google Cloud|Google account / Your own Google Cloud project
Ya tengo mi JSON OAuth|I already have my OAuth JSON
Crea tu proyecto|Create your project
Abrir Google Cloud|Open Google Cloud
Abrir YouTube Data API v3|Open YouTube Data API v3
Prepara las credenciales|Prepare your credentials
Abrir Credenciales|Open Credentials
Audiencia y usuarios de prueba|Audience and test users
Autoriza el acceso|Authorize access
Ningun JSON seleccionado|No JSON selected
Seleccionar JSON de escritorio|Select desktop JSON
Confirma tu canal|Confirm your channel
Este es mi canal|This is my channel
Elegir otra cuenta|Choose another account
Configurar mas tarde|Set up later
Conectar con Google|Connect with Google
Autorizar con Google|Authorize with Google
Configurar carpeta|Configure folder
Guardar y finalizar|Save and finish
Finalizar|Finish
Continuar|Continue
Configura tu carpeta|Configure your folder
Modo de subida|Upload mode
Manual|Manual
Automático|Automatic
Sí|Yes
No|No
Más tarde|Later
Aceptar|OK
Operacion|Operation
Total|Total
archivo|file
columnas|columns
orden|order
limpieza|cleanup
version|version
actualizacion|update
errores|errors
registro|log
copiar|copy
informe|report
extensiones|extensions
subcarpetas|subfolders
credenciales|credentials
conexion|connection
conectar|connect
asistente|wizard
inicio|startup
minimizada|minimized
estabilidad|stability
borrar|delete
eliminar|delete
locales|local
cuenta|account
sesion|session
privados|private
calidad|quality
resolucion|resolution
""".strip().splitlines())
ENGLISH.update(dict(line.split("|", 1) for line in """
Activa YouTube Data API v3 en el proyecto del JSON y vuelve a comprobar la conexion.|Enable YouTube Data API v3 in the JSON's project, then check the connection again.
Autoriza de nuevo tu canal con Google o revisa el JSON OAuth en Ajustes.|Authorize your channel with Google again or check the OAuth JSON in Settings.
Autoriza la subida o revisa el archivo local. No se subirá automáticamente.|Approve the upload or review the local file. It will not upload automatically.
Comprueba los permisos, el canal autorizado y el acceso al archivo. No se ha confirmado la operacion.|Check permissions, the authorized channel and file access. The operation has not been confirmed.
El archivo se conserva. No se iniciara otra transferencia sin tu autorizacion.|The file is kept. Another upload will not start without your approval.
Revisa Internet, VPN o proxy antes de reintentar. Los archivos se conservan.|Check your Internet connection, VPN or proxy before retrying. Files are kept.
La ruta no esta disponible. Comprueba que la unidad este conectada y que la carpeta elegida exista.|The path is unavailable. Check that the drive is connected and the selected folder exists.
Revisa el motivo en Consola. El archivo no se volvera a subir por si solo.|Check the reason in Console. The file will not upload again on its own.
Consulta el detalle en Consola y revisa los ajustes antes de repetir la accion.|Check Console for details and review Settings before repeating the action.
Consulta la cuota del proyecto antes de reintentar. Los archivos y sus confirmaciones se conservan.|Check the project quota before retrying. Files and their confirmations are kept.
Consultando solo los estados que necesitan verificacion.|Checking only states that need verification.
Consultando su ID en YouTube, sin recargar todo el canal.|Checking this ID on YouTube without reloading the entire channel.
Comprobando candidatos antes de iniciar una transferencia.|Checking candidates before starting an upload.
La transferencia termino; falta confirmar el procesamiento antes de marcarlo Subido.|The upload finished; processing must be confirmed before marking it Uploaded.
YouTube aun no ha confirmado la recepcion completa del archivo.|YouTube has not confirmed receipt of the complete file yet.
YouTube esta procesando el archivo|YouTube is processing the file
YouTube todavía no confirma el procesamiento completo.|YouTube has not confirmed complete processing yet.
YouTube no confirma el video procesado|YouTube has not confirmed the processed video
YouTube ha limitado temporalmente las peticiones.|YouTube has temporarily limited requests.
Google ha agotado la cuota diaria.|The daily Google quota is exhausted.
Google ha limitado esta operacion|Google has limited this operation
Reintentar comprueba si Google ya ha renovado o ampliado la cuota; no reinicia su contador.|Retry checks whether Google has renewed or increased the quota; it does not reset the counter.
Son dos límites diferentes.|These are two different limits.
El archivo ha cambiado desde la selección.|The file has changed since selection.
El archivo ha cambiado desde la última revisión. Actualiza la biblioteca y vuelve a seleccionarlo.|The file has changed since the last review. Refresh the library and select it again.
El archivo ha cambiado. Actualiza la biblioteca antes de compararlo.|The file has changed. Refresh the library before comparing it.
El archivo seleccionado ya no existe.|The selected file no longer exists.
El estado ha cambiado durante la consulta. Se conserva el estado más reciente.|The state changed during the request. The most recent state is kept.
Ese candidato no volverá a vincularse a este archivo. El vídeo de YouTube no se ha borrado.|This candidate will not be linked to this file again. The YouTube video has not been deleted.
Asociación descartada|Match rejected
Espera a que termine la comprobacion o la subida actual. Puedes cancelar la subida antes de cambiar la conexion.|Wait for the current check or upload to finish. You can cancel the upload before changing the connection.
Esperando a que termine la transferencia activa y comprobando los archivos locales.|Waiting for the active upload to finish and checking local files.
Esperando la operación activa y guardando la decisión, sin consultar la API.|Waiting for the active operation and saving your decision without querying the API.
Este archivo no tiene una confirmación automática de subida. Si lo borras, podrías perder su única copia.|This file has no automatic upload confirmation. Deleting it could remove the only copy.
Este archivo se está transfiriendo. Espera a que termine antes de vincularlo manualmente.|This file is being uploaded. Wait for it to finish before linking it manually.
Este video ya aparece como subido en el registro.|This video is already recorded as uploaded.
Este video ya se esta subiendo. Cancela o espera a que termine antes de reintentar.|This video is already uploading. Cancel it or wait for completion before retrying.
Elige la carpeta de videos o conecta la unidad donde esta guardada.|Choose the video folder or connect the drive where it is stored.
Figura como subido. Puedes comprobar YouTube antes de borrar la copia local. Si borras sin comprobar, podrías perder la única copia si el vídeo ya no está disponible.|It is marked as uploaded. You can check YouTube before deleting the local copy. Deleting without checking could lose the only copy if the video is no longer available.
Hay archivos que YouTube no confirma. No se ha borrado ninguno; revisalos antes de repetir la limpieza.|YouTube did not confirm some files. None were deleted; review them before repeating cleanup.
Limpieza detenida por seguridad|Cleanup stopped for safety
La coincidencia es manual. No autoriza el borrado automático del archivo.|This is a manual match. It does not authorize automatic deletion of the file.
La decisión de comparación no es válida.|The comparison decision is invalid.
La marca se conserva mientras el archivo no cambie.|The mark is kept as long as the file does not change.
La recepción y el procesamiento son pasos diferentes.|Receipt and processing are separate steps.
La restricción de cuota no cambia el archivo ni confirma una subida.|A quota restriction does not change the file or confirm an upload.
Leyendo la duración de los archivos locales...|Reading local video durations...
No hay archivos locales subidos que cumplan el tiempo configurado.|No uploaded local files meet the configured retention period.
No hay vídeos locales para revisar.|There are no local videos to review.
No se encontraron duplicados fiables en el canal cargado.|No reliable duplicate matches were found in the loaded channel.
No se han encontrado vídeos de menos de 30 segundos.|No videos under 30 seconds were found.
No se pudieron guardar los ajustes. Comprueba los permisos de la carpeta de datos.|Could not save Settings. Check data folder permissions.
No se repetirá la subida de este archivo. La limpieza automática no se basa en esta marca. Auto OFF.|This file will not be uploaded again. Automatic cleanup does not use this manual mark. Auto OFF.
No se sustituye una subida confirmada automáticamente o una transferencia en curso.|An automatically confirmed upload or active transfer cannot be replaced.
Pausa finalizada / preparado para reintentar|Pause ended / ready to retry
Se borran solo los archivos locales seleccionados por duración. Los vídeos del canal no se borran.|Only local files selected by duration are deleted. Channel videos are not deleted.
Selecciona al menos una columna para la biblioteca.|Select at least one library column.
Selecciona primero un JSON OAuth valido.|Select a valid OAuth JSON first.
Selecciona primero un video de la tabla.|Select a video in the table first.
Selecciona primero uno o varios videos del canal.|Select one or more channel videos first.
Selecciona tu JSON OAuth y autoriza el canal con Google.|Select your OAuth JSON and authorize your channel with Google.
Selecciona un solo video para moverlo de lista.|Select a single video to move it to a playlist.
Todavía no hay una subida confirmada para este archivo.|There is no confirmed upload for this file yet.
Windows no ha podido leer su duración.|Windows could not read its duration.
Configura primero el JSON OAuth.|Configure the OAuth JSON first.
Configura una carpeta valida.|Configure a valid folder.
Cancelacion solicitada. Auto queda pausado.|Cancellation requested. Auto is paused.
Compara el archivo y el vídeo de YouTube antes de confirmar que coinciden.|Compare the local file and YouTube video before confirming they match.
Configura tus subidas|Configure your uploads
Selecciona una carpeta existente|Select an existing folder
Subir automaticamente|Upload automatically
Esperando autorizacion en Google y comprobando el canal...|Waiting for Google authorization and checking the channel...
Puedes configurar mas tarde y reintentar cuando se renueve la cuota.|You can finish setup later and retry when the quota renews.
Revisa que la API este habilitada y tu correo figure como usuario de prueba si el proyecto esta en Pruebas.|Check that the API is enabled and your email is a test user if the project is in Testing.
Confirma primero el canal conectado.|Confirm the connected channel first.
Selecciona una carpeta existente para los videos.|Select an existing folder for your videos.
La autorizacion no se completo. Vuelve a conectar con Google.|Authorization did not complete. Connect with Google again.
Google no ha devuelto un canal valido.|Google did not return a valid channel.
Canal conectado. No se pudieron cargar las listas; puedes reintentarlo en Ajustes.|Channel connected. Playlists could not be loaded; you can retry in Settings.
No se pudo guardar la configuracion. Comprueba los permisos de la carpeta de datos y reintenta.|Could not save Settings. Check data folder permissions and retry.
Autorizacion en el navegador oficial de Google. No se solicita tu contrasena en esta ventana.|Authorization opens in Google's official browser page. You never enter your password in this window.
Preparando archivo local…|Preparing local file…
Desplaza la posición de reproducción del archivo local.|Seek to another position in the local video.
Ajusta el volumen de la vista previa local.|Adjust local preview volume.
El archivo local ya no está disponible.|The local file is no longer available.
Cargando vídeo local…|Loading local video…
Reproduciendo archivo local|Playing local file
Reproducción local pausada|Local playback paused
Archivo local|Local file
YouTube no permite acceder al vídeo: puede ser privado, estar eliminado o no estar disponible. Revísalo en el navegador con tu cuenta.|YouTube does not allow access to this video: it may be private, deleted or unavailable. Check it in your browser with your account.
El propietario no permite reproducir este vídeo dentro de otras aplicaciones. Ábrelo en el navegador.|The owner does not allow playback in other applications. Open it in your browser.
No se puede reproducir el formato de este vídeo aquí. Puedes verlo en el navegador.|This video format cannot be played here. You can watch it in your browser.
YouTube no ha respondido. Reintenta la carga o usa el navegador para comparar.|YouTube did not respond. Reload or compare it in your browser.
Preparando reproductor de YouTube…|Preparing YouTube player…
No se puede iniciar el reproductor integrado en este equipo. Puedes comparar el vídeo en el navegador.|The embedded player could not start on this computer. You can compare the video in your browser.
Cargando vídeo de YouTube…|Loading YouTube video…
Faltan componentes del reproductor integrado. Reintenta o abre el vídeo en el navegador.|Embedded player components are missing. Retry or open the video in your browser.
Pulsa reproducir para comparar el vídeo de YouTube.|Press Play to compare the YouTube video.
Reproduciendo vídeo de YouTube|Playing YouTube video
Vídeo de YouTube finalizado|YouTube video ended
Reproducción de YouTube pausada|YouTube playback paused
Pulsa reproducir en el vídeo para iniciar la comparación.|Press Play on the video to start the comparison.
Se necesita Chrome o Microsoft Edge para reproducir con tu sesión.|Chrome or Microsoft Edge is required for playback with your session.
Abriendo reproductor con la sesión de YouTubeSync…|Opening player with the YouTubeSync session…
YouTube no ha respondido. Revisa la conexión y vuelve a cargar el vídeo.|YouTube did not respond. Check your connection and reload the video.
Se ha cerrado la ventana de reproducción. Puedes volver a cargar el vídeo.|The playback window was closed. You can reload the video.
Windows no ha permitido alojar el reproductor.|Windows did not allow the player to be hosted.
Introduce un enlace de vídeo de YouTube o su ID de 11 caracteres.|Enter a YouTube video link or its 11-character ID.
El enlace no contiene un ID de vídeo de YouTube válido.|The link does not contain a valid YouTube video ID.
El archivo ha cambiado; se conserva.|The file has changed; it is kept.
Windows no ha podido leer la duración; se conserva.|Windows could not read the duration; the file is kept.
El archivo ha cambiado durante la lectura; se conserva.|The file changed while being read; it is kept.
El archivo ha cambiado desde la revisión; se conserva.|The file changed since review; it is kept.
El archivo se ha modificado hace poco; espera a que termine de guardarse.|The file was modified recently; wait for it to finish saving.
El archivo ha cambiado durante la comprobación; se conserva.|The file changed during verification; it is kept.
No disponible|Unavailable
Cine y animacion|Film & animation
Coches y vehiculos|Autos & vehicles
Musica|Music
Mascotas y animales|Pets & animals
Deportes|Sports
Viajes y eventos|Travel & events
Videojuegos|Gaming
Gente y blogs|People & blogs
Comedia|Comedy
Entretenimiento|Entertainment
Noticias y politica|News & politics
Consejos y estilo|How-to & style
Educacion|Education
Ciencia y tecnologia|Science & technology
ONG y activismo|Nonprofits & activism
""".strip().splitlines()))

ENGLISH.update({
    "Instalar actualización": "Install update",
    "Actualizar YouTubeSync": "Update YouTubeSync",
    "Verificando el instalador antes de actualizar...": "Verifying the installer before updating...",
    "Finaliza o cancela la operación activa antes de instalar la actualización.": "Finish or cancel the active operation before installing the update.",
    "La instalación solo está disponible en Windows.": "Installation is only available on Windows.",
    "El instalador no contiene información de versión válida.": "The installer contains no valid version information.",
    "El instalador no contiene información del producto.": "The installer contains no product information.",
    "El archivo descargado no es un instalador de Windows.": "The downloaded file is not a Windows installer.",
    "La cabecera del instalador no es válida.": "The installer header is invalid.",
    "El instalador no corresponde a YouTubeSync o a la versión solicitada.": "The installer does not match YouTubeSync or the requested version.",
    "No hay una actualización válida para instalar.": "There is no valid update to install.",
    "El instalador ha cambiado durante la comprobación.": "The installer changed during verification.",
    "La descarga no coincide con la huella publicada. Descárgala de nuevo.": "The download does not match the published digest. Download it again.",
    "El instalador ha cambiado. Descárgalo de nuevo.": "The installer changed. Download it again.",
    "Verifica el instalador, pide confirmación y cierra YouTubeSync para actualizar y volver a abrirlo conservando tus datos.": "Verify the installer, ask for confirmation and close YouTubeSync to update and reopen while keeping your data.",
    "Sin notas de version.": "No release notes.",
    "Solo se admiten versiones estables publicadas.": "Only published stable versions are supported.",
    "GitHub ha devuelto una respuesta de release no valida.": "GitHub returned an invalid release response.",
    "La release no pertenece al repositorio esperado.": "The release does not belong to the expected repository.",
    "GitHub no ha devuelto una lista valida de paquetes.": "GitHub did not return a valid package list.",
    "La release contiene paquetes duplicados con el mismo nombre.": "The release contains duplicate packages with the same name.",
    "Las notas de version no son validas.": "Invalid release notes.",
    "La release no tiene una version valida.": "The release has no valid version.",
    "La descarga redirige fuera de los servidores HTTPS de GitHub permitidos.": "The download redirects outside the allowed GitHub HTTPS servers.",
    "El paquete no esta publicado correctamente en el repositorio esperado.": "The package is not correctly published in the expected repository.",
    "El tamano del paquete no es valido.": "Invalid package size.",
    "GitHub no proporciona una huella SHA-256 valida para este paquete.": "GitHub provides no valid SHA-256 digest for this package.",
    "No se puede validar el archivo ZIP descargado.": "Cannot validate the downloaded ZIP.",
    "Esta release no incluye un paquete Windows x64 compatible.": "This release includes no compatible Windows x64 package.",
    "El nombre o la procedencia del paquete no coinciden con la release.": "Package name or origin does not match the release.",
    "GitHub ha devuelto una direccion de descarga no valida.": "GitHub returned an invalid download URL.",
    "El paquete supera los limites de seguridad de descompresion.": "The package exceeds safe extraction limits.",
    "Falta el ejecutable o su runtime. No es una distribucion completa.": "The executable or runtime is missing. This is not a complete distribution.",
    "El paquete no incluye un manifiesto de version valido.": "The package includes no valid version manifest.",
    "El contenido del paquete no corresponde a esta version de Windows.": "Package contents do not match this Windows version.",
    "No se pudo conectar con GitHub. Comprueba tu conexion e intentalo de nuevo.": "Could not connect to GitHub. Check your connection and retry.",
    "GitHub no ha devuelto metadatos de version validos.": "GitHub did not return valid version metadata.",
    "La descarga esta incompleta o no coincide con la huella SHA-256 publicada.": "Download is incomplete or does not match the published SHA-256 digest.",
    "No se pudo completar la descarga. Comprueba la conexion y el espacio disponible.": "Could not complete the download. Check your connection and available disk space.",
    "El paquete contiene rutas no permitidas.": "The package contains disallowed paths.",
    "El paquete contiene archivos duplicados.": "The package contains duplicate files.",
    "La respuesta de GitHub es demasiado grande.": "The GitHub response is too large.",
    "GitHub ha limitado las consultas. Espera unos minutos y vuelve a intentarlo.": "GitHub has limited requests. Wait a few minutes and retry.",
    "La descarga supera el tamano publicado por GitHub.": "The download exceeds GitHub's published size.",
    "Vídeo por verificar": "Video needs verification",
    "Vídeo pendiente": "Pending video",
    "principal": "primary",
    "El archivo es demasiado grande para ser un JSON OAuth de escritorio.": "The file is too large to be a desktop OAuth JSON.",
    "No se puede leer el JSON. Selecciona el archivo descargado de Google Cloud.": "Cannot read the JSON. Select the file downloaded from Google Cloud.",
    "Selecciona credenciales OAuth de tipo Aplicacion de escritorio, no web ni cuenta de servicio.": "Select Desktop app OAuth credentials, not web or service account credentials.",
    "El JSON no contiene un ID de cliente de Google valido.": "The JSON does not contain a valid Google client ID.",
    "El enlace de autorizacion del JSON no es un enlace oficial de Google.": "The JSON authorization URL is not an official Google URL.",
    "El servidor de tokens del JSON no es un servidor oficial de Google.": "The JSON token server is not an official Google server.",
    "La configuración no contiene un objeto JSON.": "Settings do not contain a JSON object.",
    "Falta el ID o la huella completa del recibo de subida": "The upload receipt ID or full fingerprint is missing",
    "No hay credenciales OAuth disponibles. Configura el JSON OAuth.": "No OAuth credentials available. Configure the OAuth JSON.",
    "Selecciona el archivo client_secret.json en Configuracion.": "Select the client_secret.json file in Settings.",
    "Faltan dependencias. Instala requirements.txt antes de ejecutar la app.": "Missing dependencies. Install requirements.txt before running the app.",
    "La cuenta conectada no devuelve ningun canal de YouTube.": "The connected account did not return a YouTube channel.",
    "Canal sin nombre": "Unnamed channel",
    "El nombre de la lista no puede estar vacio.": "Playlist name cannot be empty.",
    "Privacidad de YouTube no válida.": "Invalid YouTube visibility.",
    "No hay ID de YouTube para eliminar el video.": "No YouTube ID is available for deletion.",
    "Google solicita renovar la autorizacion del canal.": "Google requires renewed channel authorization.",
    "La autorizacion no termino correctamente. Vuelve a conectar YouTube.": "Authorization did not finish correctly. Connect YouTube again.",
    "Los permisos de YouTube cambiaron. Se pedira autorizacion de nuevo.": "YouTube permissions changed. Authorization will be requested again.",
    "OAuth omitido: no existe el JSON configurado.": "OAuth skipped: the configured JSON does not exist.",
    "Modo automatico activado.": "Automatic mode enabled.",
    "Modo automatico pausado.": "Automatic mode paused.",
    "Servicio en segundo plano iniciado.": "Background service started.",
    "Servicio detenido.": "Service stopped.",
    "No hay videos pendientes.": "No pending videos.",
    "Subida cancelada por el usuario.": "Upload cancelled by the user.",
    "Cancelacion solicitada. Se detendra al terminar el bloque actual.": "Cancellation requested. Upload will stop after the current chunk.",
    "La carpeta configurada no existe. Elige una carpeta valida.": "The configured folder does not exist. Choose a valid folder.",
    "Operación cancelada": "Operation cancelled",
    "El archivo ha cambiado antes de iniciar la transferencia.": "The file changed before the upload started.",
    "El archivo ha cambiado o la operación se ha cancelado.": "The file changed or the operation was cancelled.",
    "El archivo ha cambiado al leer su duración": "The file changed while its duration was read",
    "El archivo ha cambiado durante la comprobacion": "The file changed during verification",
    "El archivo ha cambiado. Revisa la nueva versión antes de autorizarla.": "The file changed. Review the new version before approving it.",
    "La revisión ya no corresponde al archivo actual": "The review no longer matches the current file",
    "Intento anterior sin confirmar. Revisa el canal y pulsa Reintentar.": "Previous attempt unconfirmed. Review the channel and click Retry.",
    "Cuota API agotada": "API quota exhausted",
    "Cuota diaria de YouTube Data API agotada para este proyecto de Google. No es un fallo del video: YouTube no aceptara nuevas peticiones hasta que se renueve la cuota o aumentes el limite del proyecto.": "Daily YouTube Data API quota exhausted for this Google project. This is not a video error: YouTube will not accept new requests until the quota renews or the project limit is increased.",
    "Limite temporal de peticiones de YouTube. Se reintentara sin modificar los estados de los videos.": "Temporary YouTube request limit. It will retry without changing video states.",
    "Debes confirmar que has comparado ambos vídeos completos.": "Confirm that you compared both complete videos.",
    "El archivo ha cambiado desde la comparación. No se modifica su estado.": "The file changed since comparison. Its state is not changed.",
    "El archivo ha cambiado. Vuelve a comparar su contenido antes de confirmar.": "The file changed. Compare its content again before confirming.",
    "El enlace asociado ha cambiado durante la comparación. Revisa la nueva asociación.": "The linked URL changed during comparison. Review the new match.",
    "Ese vídeo ya está asignado manualmente a otro archivo de contenido distinto. Revisa el enlace.": "This video is already manually linked to another file with different content. Check the link.",
    "ID de recepcion y huella local persistente confirmados": "Receipt ID and persistent local fingerprint confirmed",
    "huella de contenido confirmada": "content fingerprint confirmed",
    "el video no aparece en el canal": "video not found on the channel",
    "faltan metadatos para confirmar el contenido": "insufficient metadata to confirm content",
    "nombre original distinto": "different original filename",
    "el archivo local ha cambiado desde la subida": "local file changed since upload",
    "duración desconocida.": "unknown duration.",
    "indicado por YouTube": "reported by YouTube",
    "reinicio diario estimado de la cuota del proyecto": "estimated daily project quota reset",
    "reintento conservador tras limite temporal": "conservative retry after temporary limit",
    "ventana estimada de 24 h": "estimated 24-hour window",
    "Servicio de sincronizacion": "Synchronization service",
    "Verificacion previa a la subida": "Pre-upload verification",
    "Verificacion antes de borrar": "Verification before deletion",
    "Transferir video a YouTube": "Upload video to YouTube",
    "Retirar intento fallido de YouTube": "Remove failed YouTube attempt",
    "Cancelar transferencia": "Cancel upload",
    "Esto cerrara YouTubeSync por completo y detendra la vigilancia de la carpeta.\n\nQuieres salir?": "This will exit YouTubeSync and stop watching the folder.\n\nExit now?",
    "1. Inicia sesion en Google Cloud con tu cuenta.\n2. Crea un proyecto para tu uso de YouTubeSync.\n3. Selecciona ese proyecto en la barra superior.": "1. Sign in to Google Cloud with your account.\n2. Create a project for your use of YouTubeSync.\n3. Select that project in the top bar.",
    "1. Comprueba que este seleccionado tu proyecto.\n2. Abre YouTube Data API v3.\n3. Pulsa Habilitar.": "1. Check that your project is selected.\n2. Open YouTube Data API v3.\n3. Click Enable.",
    "1. Configura el nombre y los correos de contacto en Google Auth Platform.\n2. Elige la audiencia adecuada. Si tu proyecto es Externo y esta en Pruebas, anade tu correo como usuario de prueba.\n3. Crea un ID de cliente OAuth de tipo Aplicacion de escritorio.\n4. Descarga su JSON.": "1. Configure the name and contact email addresses in Google Auth Platform.\n2. Choose the appropriate audience. If your project is External and in Testing, add your email as a test user.\n3. Create an OAuth client ID of type Desktop app.\n4. Download its JSON.",
    "«Sí» guardará «Subido (manual)», sin gastar API ni autorizar limpieza automática. Con «No» podrás descartar la asociación o solicitar una subida nueva.": "Yes saves Uploaded (manual), without using API quota or authorizing automatic cleanup. No lets you reject the match or request a new upload.",
    "Se guardará la discrepancia para no volver a vincular este candidato al archivo. No se eliminará ningún vídeo de YouTube.": "The mismatch will be saved so this candidate is not linked to the file again. No YouTube video will be deleted.",
    "Subir como nuevo solicita una transferencia adicional y puede consumir cuota. Guardar sin subir deja el archivo pendiente, con Auto OFF.": "Upload as new requests an additional upload and may consume quota. Save without uploading keeps the file pending, with Auto OFF.",
    "El límite del canal afecta a sus subidas desde web, móvil y API. YouTube no ofrece un contador exacto de subidas restantes.\n\nLa cuota API pertenece al proyecto de Google Cloud. Su consola muestra los datos oficiales disponibles, que pueden tener retraso. El horario recomendado por la app no garantiza que el canal esté desbloqueado.": "The channel limit applies to uploads from the web, mobile and API. YouTube does not provide an exact remaining-upload counter.\n\nAPI quota belongs to the Google Cloud project. Its console shows the available official data, which may be delayed. The time suggested by the app does not guarantee that the channel is unblocked.",
    "\n\nEl borrado es permanente y no elimina vídeos del canal. «Borrar de todos modos» deja Auto en OFF y espera a que termine la transferencia activa.": "\n\nDeletion is permanent and does not delete channel videos. Delete anyway sets Auto to OFF and waits for the active upload to finish.",
    "No borrados:": "Not deleted:",
    "No se subirá sin tu autorización.": "It will not upload without your approval.",
    "No es una verificación automática ni autoriza limpieza automática.": "This is not automatic verification and does not authorize automatic cleanup.",
    "Se conserva aunque el archivo siga en la carpeta.": "Kept even if the file remains in the folder.",
})

TEMPLATES = [
    ("Iniciar en {time}", "Start at {time}"),
    ("Desde {time}", "From {time}"),
    ("Enlace copiado desde {time} / vídeo en Oculto", "Link copied from {time} / video set to Unlisted"),
    ("{count} referencias no disponibles (fuera del total)", "{count} unavailable references (excluded from the total)"),
    ("{count} sin clasificar", "{count} unclassified"),
    ("No se pudo actualizar el inicio con Windows: {error}", "Could not update Windows startup: {error}"),
    ("Instalar la versión {version}?\n\nYouTubeSync se cerrará y volverá a abrirse al terminar. Tus ajustes, autorización y registro se conservarán.", "Install version {version}?\n\nYouTubeSync will close and reopen when finished. Your settings, authorization and records will be kept."),
    ("GitHub no pudo consultar la release (HTTP {code}).", "GitHub could not retrieve the release (HTTP {code})."),
    ("GitHub no pudo descargar el paquete (HTTP {code}).", "GitHub could not download the package (HTTP {code})."),
    ("Comprobados {count} videos procesados en YouTube", "Checked {count} processed YouTube videos"),
    ("Anadido a la lista: {playlist}", "Added to playlist: {playlist}"),
    ("Rechazo de YouTube: {error}", "YouTube rejection: {error}"),
    ("{message} Proximo intento: {time} ({criterion}).", "{message} Next attempt: {time} ({criterion})."),
    ("Subidas manuales en cola retiradas antes del borrado local: {count}.", "Queued manual uploads removed before local deletion: {count}."),
    ("Subida manual seleccionada: {file}.", "Manual upload selected: {file}."),
    ("Limpieza automatica: {count} archivo(s) local(es) borrado(s).", "Automatic cleanup: {count} local file(s) deleted."),
    ("Omitido {file}: ya esta en el registro permanente.", "Skipped {file}: already in the permanent registry."),
    ("No se sube ni se borra {file}: {reason}.", "Not uploading or deleting {file}: {reason}."),
    ("Omitido {file}: contenido confirmado en YouTube ({reason}).", "Skipped {file}: content confirmed on YouTube ({reason})."),
    ("El titulo {title} existe, pero no corresponde a {file}: {reason}. Se subira el archivo correcto.", "Title {title} exists but does not match {file}: {reason}. The correct file will be uploaded."),
    ("YouTube aun esta procesando https://youtu.be/{id}; se conserva y se comprobara de nuevo. Puedes revisarlo en Canal.", "YouTube is still processing https://youtu.be/{id}; it is kept and will be checked again. Review it in Channel."),
    ("Se conserva {file}: el archivo ha cambiado antes de autorizar la transferencia.", "Keeping {file}: the file changed before upload approval."),
    ("Se conserva {file}: {reason}", "Keeping {file}: {reason}"),
    ("El video se subio, pero no se pudo anadir a la lista: {error}", "Video uploaded, but could not be added to playlist: {error}"),
    ("No se pudo comprobar {file}: {error}", "Could not check {file}: {error}"),
    ("Limpieza automatica cancelada: no se pudo comprobar YouTube ({error}).", "Automatic cleanup cancelled: could not check YouTube ({error})."),
    ("Limpieza automatica cancelada para {file}: {reason}.", "Automatic cleanup cancelled for {file}: {reason}."),
    ("Omitido {file}: ya no existe.", "Skipped {file}: no longer exists."),
    ("Omitido {file}: {reason}", "Skipped {file}: {reason}"),
    ("Eliminado de YouTube el intento fallido {id}; se iniciara una subida limpia.", "Removed failed YouTube attempt {id}; a clean upload will start."),
    ("Limpieza automatica: se conserva {file} porque ha cambiado durante la comprobacion.", "Automatic cleanup: keeping {file} because it changed during verification."),
    ("Limpieza automatica: no se pudo borrar {file}: {error}", "Automatic cleanup: could not delete {file}: {error}"),
    ("dura {seconds} s.", "duration {seconds} s."),
    ("YouTube indica {reason}. Revisa el video en Canal antes de reintentar.", "YouTube reports {reason}. Review the video in Channel before retrying."),
    ("no se pudo comprobar el archivo local: {error}", "could not check local file: {error}"),
    ("No puedo leer {file}: {error}", "Cannot read {file}: {error}"),
    ("No se pudo guardar el error de {file}: {error}", "Could not save error for {file}: {error}"),
    ("{context}: necesita revision", "{context}: review needed"),
    ("Siguiente aviso / {count} avisos", "Next notice / {count} notices"),
    ("AHORA / {index} DE {total}", "NOW / {index} OF {total}"),
    ("AVISOS / {index} DE {total}", "NOTICES / {index} OF {total}"),
    ("{count} en cola", "{count} queued"),
    ("Total {total} / Pendientes {pending} / Revisar {review} / En curso {active} / En espera {waiting} / Por verificar {verify} / Subidos {uploaded} / Incidencias {issues}", "Total {total} / Pending {pending} / Review {review} / In progress {active} / Waiting {waiting} / Verification {verify} / Uploaded {uploaded} / Issues {issues}"),
    ("Subida manual solicitada para {file}.", "Manual upload requested for {file}."),
    ("Borrar {count} archivo(s) local(es), {size}?", "Delete {count} local file(s), {size}?"),
    ("Borrar {file}?", "Delete {file}?"),
    ("{count} archivo(s) no están confirmados como subidos: podrías perder su única copia.", "{count} file(s) are not confirmed as uploaded: you could lose the only copy."),
    ("Se conservan {count} archivo(s) que no se han podido revisar.", "{count} file(s) that could not be reviewed are kept."),
    ("{title} / Proximo intento {time} / {remaining}", "{title} / Next attempt {time} / {remaining}"),
    ("Proximo intento {time} / {remaining}. Los estados se conservan.", "Next attempt {time} / {remaining}. States are kept."),
    ("Copia local del canal / ultima consulta {time} / sin verificacion en directo", "Saved channel copy / last checked {time} / not live verification"),
    ("Pintando canal... {count} de {total}", "Rendering channel... {count} of {total}"),
    ("{count} videos cargados del canal.", "{count} channel videos loaded."),
    ("{count} de {total} videos", "{count} of {total} videos"),
    ("Privacidad para {count} video(s):", "Visibility for {count} video(s):"),
    ("{count} videos en {groups} grupo(s) duplicado(s) fiables", "{count} videos in {groups} reliable duplicate group(s)"),
    ("No se pudo cargar el canal: {error}", "Could not load channel: {error}"),
    ("Se comprobaran {count} archivo(s) con YouTube antes de borrar localmente.\n\nContinuar?", "{count} file(s) will be checked with YouTube before local deletion.\n\nContinue?"),
    ("{count} archivo(s) sin duración verificable o modificados se han conservado. Consulta la Consola.", "{count} file(s) with unverified duration or changes were kept. Check Console."),
    ("Se pondra como Oculto y se copiara el enlace:\n\n{link}", "The video will be set to Unlisted and its link copied:\n\n{link}"),
    ("Se borraran {count} video(s) de YouTube.\n\nNo se tocara ningun archivo local.", "{count} YouTube video(s) will be permanently deleted.\n\nContinue?"),
    ("Mover este video a '{playlist}'?\n\n{title}", "Move this video to '{playlist}'?\n\n{title}"),
    ("{count} video(s) no tienen metadatos suficientes para compararlos con seguridad.", "{count} video(s) lack enough metadata for a reliable comparison."),
    ("No se pudieron cargar las listas:\n\n{error}", "Could not load playlists:\n\n{error}"),
    ("No se pudo crear la lista:\n\n{error}", "Could not create playlist:\n\n{error}"),
    ("{count} video(s) necesitan revision", "{count} video(s) need review"),
    ("{review} pendientes de revisión / {verify} por verificar / {issues} con incidencia.", "{review} need review / {verify} need verification / {issues} with issues."),
    ("{count} vídeo(s) esperan tu autorización.", "{count} video(s) await your approval."),
    ("Este vídeo dura {seconds} segundos, menos de 30.", "This video is {seconds} seconds long, under 30."),
    ("Última subida rechazada. Reintento recomendado {time} (estimación).", "Last upload rejected. Suggested retry {time} (estimate)."),
    ("No se pudo completar la revisión: {error}", "Could not complete review: {error}"),
    ("{file}: el archivo local ha cambiado desde la subida", "{file}: local file changed since upload"),
    ("{file}: el archivo ha cambiado durante la comprobacion", "{file}: file changed during verification"),
    ("Comprobacion de YouTube: {count} estado(s) actualizado(s).", "YouTube check: {count} state(s) updated."),
    ("No se pudo compartir el video: {error}", "Could not share video: {error}"),
    ("No se pudo cambiar privacidad: {error}", "Could not change visibility: {error}"),
    ("No se pudo borrar del canal: {error}", "Could not delete from channel: {error}"),
    ("No se pudo cambiar la lista: {error}", "Could not change playlist: {error}"),
    ("No se pudo comprobar YouTube: {error}", "Could not check YouTube: {error}"),
    ("{count} video(s) actualizado(s)", "{count} video(s) updated"),
    ("{count} video(s) borrado(s) del canal", "{count} video(s) deleted from channel"),
    ("{count} archivo(s) local(es) borrado(s).", "{count} local file(s) deleted."),
    ("Duración revisada: {count} de {total} archivos.", "Duration checked: {count} of {total} files."),
    ("Candidato descartado manualmente: {file} -> {id}.", "Candidate manually rejected: {file} -> {id}."),
    ("Confirmación manual guardada: {file} -> https://youtu.be/{id}. No es una verificación automática.", "Manual confirmation saved: {file} -> https://youtu.be/{id}. This is not automatic verification."),
    ("{index} de 3", "{index} of 3"),
    ("Conexion inicial / {index} de 7", "Initial setup / {index} of 7"),
    ("JSON de escritorio preparado / {file}", "Desktop JSON ready / {file}"),
    ("Descargar {version}", "Download {version}"),
    ("Version {version} publicada / falta el paquete Windows x64.", "Version {version} published / Windows x64 package missing."),
    ("Disponible {version} / {size} MB", "Available {version} / {size} MB"),
    ("Descargando / {received} de {total} MB", "Downloading / {received} of {total} MB"),
    ("Descarga verificada / {file}", "Download verified / {file}"),
    ("{visible} de {total} mensajes / {errors} errores / {warnings} avisos", "{visible} of {total} messages / {errors} errors / {warnings} warnings"),
    ("No se pudo exportar el informe: {error}", "Could not export report: {error}"),
    ("No se puede reproducir aquí: {error}. Puedes abrirlo en el reproductor externo.", "Cannot play here: {error}. You can open it in the external player."),
    ("YouTube no ha podido reproducir este vídeo (error {code}). Reintenta o ábrelo en el navegador.", "YouTube could not play this video (error {code}). Retry or open it in your browser."),
    ("YouTube ha rechazado el reproductor integrado (error {code}). Puedes comparar el vídeo en el navegador.", "YouTube rejected the embedded player (error {code}). You can compare it in your browser."),
    ("No se confirma una duración inferior a {seconds} segundos; se conserva.", "Duration under {seconds} seconds could not be confirmed; the file is kept."),
    ("Privacidad: {value}", "Visibility: {value}"),
    ("Categoria: {value}", "Category: {value}"),
    ("Lista de reproduccion: {value}", "Playlist: {value}"),
    ("Operacion: {value}", "Operation: {value}"),
    ("Ultima confirmacion: {value}", "Last confirmation: {value}"),
    ("Confirmado por ti: {value}", "Confirmed by you: {value}"),
    ("Activa o desactiva esta opción: {option}.", "Enable or disable this option: {option}."),
    ("Ejecuta la acción «{action}» de esta ventana.", "Run the {action} action in this window."),
    ("Encontrados {count} video(s) candidato(s).", "Found {count} candidate video(s)."),
    ("Autorizando credencial OAuth {slot}.", "Authorizing OAuth credential {slot}."),
    ("OAuth en espera breve tras un error: {error}", "OAuth briefly waiting after an error: {error}"),
    ("Subiendo {file} como '{title}'.", "Uploading {file} as '{title}'."),
    ("Subiendo {file}: {percent}%", "Uploading {file}: {percent}%"),
    ("Error de YouTube subiendo {file}: {error}", "YouTube error uploading {file}: {error}"),
    ("Error subiendo {file}: {error}", "Error uploading {file}: {error}"),
    ("No se pudo comprobar YouTube antes de subir: {error}", "Could not check YouTube before upload: {error}"),
    ("Archivo recibido por YouTube y pendiente de procesamiento: https://youtu.be/{id}", "File received by YouTube, awaiting processing: https://youtu.be/{id}"),
    ("YouTube aun esta procesando https://youtu.be/{id}", "YouTube is still processing https://youtu.be/{id}"),
    ("Revisión necesaria antes de subir {file}: {reason}", "Review required before uploading {file}: {reason}"),
    ("Subida manual seleccionada: {file}", "Manual upload selected: {file}"),
    ("No se puede subir el archivo seleccionado: {error}", "Cannot upload selected file: {error}"),
    ("No se pudo retirar de YouTube el intento fallido: {error}", "Could not remove failed YouTube attempt: {error}"),
    ("Eliminado de YouTube el intento fallido {id} antes de reintentar.", "Removed failed YouTube attempt {id} before retrying."),
    ("Eliminado de YouTube el intento incompleto {id} antes de reintentar.", "Removed incomplete YouTube attempt {id} before retrying."),
    ("No se pudo revisar la carpeta {folder}: {error}", "Could not scan folder {folder}: {error}"),
    ("No se encontro la ruta: {path}", "Path not found: {path}"),
    ("Subidas manuales en cola retiradas antes del borrado local: {count}", "Queued manual uploads removed before local deletion: {count}"),
    ("{file}: ya esta en el registro permanente.", "{file}: already in the permanent registry."),
    ("{file}: contenido confirmado en YouTube ({reason})", "{file}: content confirmed on YouTube ({reason})"),
    ("{file}: la huella de contenido no coincide", "{file}: content fingerprint does not match"),
    ("{file}: nombre original distinto", "{file}: different original filename"),
    ("{file}: huella declarada coincidente pero tamaño recibido distinto", "{file}: matching declared fingerprint but different received size"),
    ("{file}: el archivo ha cambiado antes de autorizar la transferencia.", "{file}: file changed before upload approval."),
    ("{file}: borrado local completado, no se pudo actualizar el registro ({error})", "{file}: local deletion completed, could not update registry ({error})"),
]

# Hover help is kept in the same catalog as labels and notices.
ENGLISH.update(dict(line.split("|", 1) for line in """
Desactiva Auto y solicita detener la transferencia actual; los archivos locales se conservan.|Disable Auto and request cancellation of the current upload; local files are kept.
Activa la vigilancia de la carpeta y la subida de pendientes autorizados.|Enable folder watching and uploading of approved pending files.
Activa Auto y solicita la subida de los archivos pendientes; los cortos requieren revisión.|Enable Auto and request pending uploads; short videos require review.
Solicita una subida del archivo seleccionado; no borra el archivo local ni elimina vídeos del canal.|Request one upload of the selected file; neither the local file nor channel videos are deleted.
Solicita detener la transferencia actual y deja Auto en OFF; puede esperar al bloque en curso.|Request cancellation of the current upload and set Auto to OFF; it may wait for the current chunk.
Recarga la información y comprueba la conexión con YouTube; puede consumir cuota API.|Refresh information and check the YouTube connection; this may use API quota.
Vuelve a leer la carpeta local y actualiza la tabla sin consultar todo el canal.|Rescan the local folder and refresh the table without querying the entire channel.
Abre la configuración de carpeta, cuenta, automatización, limpieza y columnas.|Open folder, account, automation, cleanup and column settings.
Abre los ajustes de la carpeta local para elegir o corregir su ubicación.|Open local folder settings to choose or correct its location.
Abre la biblioteca local y selecciona el archivo que requiere atención.|Open the local library and select the file that needs attention.
Abre YouTube Data API en Google Cloud para habilitarla en tu proyecto.|Open YouTube Data API in Google Cloud to enable it for your project.
Autoriza un nuevo intento para este archivo, conservando las comprobaciones previas a la subida.|Approve one new attempt for this file, keeping all pre-upload checks.
Abre el archivo seleccionado con el reproductor asociado de Windows.|Open the selected file in the associated Windows player.
Muestra las opciones de borrado local y advierte si no hay una subida confirmada.|Show local deletion options and warn if no upload is confirmed.
Borra permanentemente la copia local sin comprobar YouTube; podrías perder la única copia.|Permanently delete the local copy without checking YouTube; you could lose the only copy.
Comprueba identidad y procesamiento en YouTube antes de borrar la copia local; necesita API.|Check identity and processing on YouTube before deleting the local copy; requires the API.
Confirma el borrado permanente del listado local; no borra nada del canal.|Confirm permanent deletion of the listed local files; nothing is deleted from the channel.
Ofrece limpieza por antigüedad y eliminación manual de vídeos de menos de 30 segundos.|Offer retention-based cleanup and manual deletion of videos under 30 seconds.
Busca copias locales ya subidas cuyo plazo de conservación se ha cumplido y verifica YouTube antes de borrarlas.|Find uploaded local copies past their retention period and check YouTube before deletion.
Revisa la duración de los archivos locales y muestra los cortos antes de pedir permiso para borrarlos.|Check local file durations and show short videos before asking permission to delete them.
Abre el vídeo de YouTube en el navegador; los privados necesitan una sesión con permisos.|Open the YouTube video in your browser; private videos need an authorized session.
Abre la página de YouTube en el navegador predeterminado con tu sesión habitual.|Open YouTube in your default browser with your usual session.
Abre el vídeo seleccionado de tu canal en el navegador predeterminado.|Open the selected channel video in your default browser.
Obtiene los vídeos y listas del canal; puede usar la copia guardada cuando no hay cuota.|Load channel videos and playlists; a saved copy may be used when quota is exhausted.
Prepara el enlace para compartir el vídeo; puede cambiarlo a Oculto tras la confirmación.|Prepare a sharing link; the video may be set to Unlisted after confirmation.
Permite elegir Público, Oculto o Privado para los vídeos seleccionados del canal.|Choose Public, Unlisted or Private for the selected channel videos.
Busca posibles duplicados del canal comparando los datos disponibles; no elimina ninguno.|Find possible channel duplicates by comparing available metadata; nothing is deleted.
Pide confirmación para eliminar los vídeos seleccionados del canal de YouTube.|Ask for confirmation before deleting the selected YouTube channel videos.
Cambia la lista de reproducción de los vídeos seleccionados del canal.|Change the playlist of the selected channel videos.
Abre Google Cloud con las cuotas oficiales del proyecto; no reinicia ni amplía los límites.|Open Google Cloud's official project quotas; this does not reset or increase limits.
Explica la diferencia entre el límite de subidas del canal y la cuota del proyecto API.|Explain the difference between the channel upload limit and API project quota.
Abre YouTube Studio para gestionar el canal y consultar sus avisos.|Open YouTube Studio to manage the channel and check its notices.
Abre la solicitud oficial de ampliación de cuota API; no cambia el límite desde la app.|Open the official API quota increase request; the app cannot change the limit.
Abre la documentación de YouTube sobre el límite de subidas del canal.|Open YouTube's documentation about the channel upload limit.
Inicia la comparación guiada entre el archivo local y su candidato de YouTube.|Start a guided comparison between the local file and its YouTube candidate.
Consulta solo este ID y busca pruebas técnicas de correspondencia y procesamiento; usa cuota API.|Check only this ID for technical evidence of identity and processing; uses API quota.
Muestra el archivo que necesita una decisión y sus opciones de revisión.|Show the file that needs a decision and its review options.
Vuelve al aviso anterior sin cambiar los estados de los vídeos.|Go to the previous notice without changing video states.
Avanza al siguiente aviso; conserva tu elección durante las recargas.|Go to the next notice; your selection is kept during refreshes.
Copia el detalle de este aviso ocultando las credenciales reconocibles.|Copy this notice's details with recognizable credentials redacted.
Abre el diagnóstico con búsqueda, filtros y opciones para copiar o exportar los errores.|Open diagnostics with search, filters and options to copy or export errors.
Copia el informe de diagnóstico con los secretos reconocibles ocultos.|Copy the diagnostic report with recognizable secrets redacted.
Copia los avisos y errores del diagnóstico ocultando credenciales reconocibles.|Copy diagnostic warnings and errors with recognizable credentials redacted.
Guarda el diagnóstico en un archivo de texto UTF-8 con secretos reconocibles ocultos.|Save diagnostics as UTF-8 text with recognizable secrets redacted.
Vacía la vista de diagnóstico; no borra vídeos ni confirmaciones de subida.|Clear the diagnostic view; videos and upload confirmations are not deleted.
Guarda los cambios de esta ventana y los aplica a la aplicación.|Save this window's changes and apply them to the app.
Cancela o aplaza esta decisión sin confirmarla.|Cancel or postpone this decision without confirming it.
Cierra esta ventana sin cerrar toda la aplicación.|Close this window without exiting the app.
Confirma la acción descrita en esta ventana.|Confirm the action described in this window.
Pide confirmación para cerrar YouTubeSync por completo y detener su servicio.|Ask for confirmation before exiting YouTubeSync and stopping its service.
Recupera la ventana de YouTubeSync desde la bandeja del sistema.|Restore the YouTubeSync window from the system tray.
Abre el selector del archivo o carpeta correspondiente a este ajuste.|Open the file or folder picker for this setting.
Restaura las columnas Archivo, Tamaño, Creado y Estado en su orden inicial.|Restore File, Size, Created and Status columns in their original order.
Cambia la posición de la columna seleccionada en la biblioteca.|Change the position of the selected library column.
Consulta las versiones publicadas en GitHub; no instala nada automáticamente.|Check published GitHub versions; nothing is installed automatically.
Descarga la actualización seleccionada desde la publicación de GitHub.|Download the selected update from its GitHub release.
Abre las notas de la versión seleccionada para revisar sus cambios.|Open the selected version's release notes.
Abre en el Explorador de Windows la carpeta correspondiente.|Open the corresponding folder in Windows Explorer.
Abre el repositorio oficial de YouTubeSync en el navegador.|Open the official YouTubeSync repository in your browser.
Abre el asistente para importar tus credenciales y autorizar tu canal con Google.|Open the wizard to import your credentials and authorize your channel with Google.
Selecciona las credenciales OAuth de escritorio de tu proyecto de Google Cloud.|Select your Google Cloud project's desktop OAuth credentials.
Vuelve a la autorización de Google para seleccionar otro canal o cuenta.|Return to Google authorization to choose another channel or account.
Consulta las listas de reproducción del canal autorizado; puede consumir cuota API.|Load the authorized channel's playlists; may use API quota.
Solicita el nombre y crea una lista de reproducción en el canal autorizado.|Ask for a name and create a playlist on the authorized channel.
Cierra el asistente sin completar la conexión ni iniciar nuevas subidas.|Close the wizard without completing the connection or starting new uploads.
Vuelve al paso anterior sin confirmar la decisión final.|Return to the previous step without confirming the final decision.
Avanza al siguiente paso del asistente.|Go to the wizard's next step.
Abre la autorización oficial en el navegador; la contraseña no se escribe en YouTubeSync.|Open official authorization in your browser; your password is never entered in YouTubeSync.
Continúa con la carpeta local y las opciones de subida del canal que acabas de autorizar.|Continue with local folder and upload options for the channel you just authorized.
Guarda la conexión y las opciones elegidas al completar el asistente.|Save the connection and selected options when completing the wizard.
Abre Google Cloud para crear o seleccionar tu proyecto personal.|Open Google Cloud to create or select your personal project.
Abre la API de YouTube en Google Cloud para habilitarla en tu proyecto.|Open the YouTube API in Google Cloud to enable it for your project.
Abre la configuración oficial de Google Cloud para preparar el acceso OAuth.|Open official Google Cloud settings to prepare OAuth access.
Despliega el listado completo de archivos afectados por esta confirmación.|Show the complete list of files affected by this confirmation.
Recoge el listado de archivos sin cambiar la decisión de borrado.|Collapse the file list without changing the deletion decision.
Inicia o reanuda el archivo local en el reproductor integrado.|Start or resume the local file in the integrated player.
Abre la ubicación del archivo seleccionado en Windows; sin selección, abre la carpeta configurada.|Open the selected file's location in Windows; without a selection, open the configured folder.
La carpeta o el archivo ya no está disponible.|The folder or file is no longer available.
Pausa la reproducción local y conserva su posición.|Pause local playback and keep its position.
Activa o silencia el sonido del reproductor local.|Mute or unmute the local player.
Abre el archivo en el reproductor de Windows si la vista integrada no puede reproducirlo.|Open the file in the Windows player if the embedded preview cannot play it.
Pausa el vídeo local y carga el candidato de YouTube dentro de esta ventana.|Pause the local video and load the YouTube candidate inside this window.
Carga de nuevo el candidato de YouTube en el reproductor de esta ventana.|Reload the YouTube candidate in this window's player.
Abre Chrome o Edge con el perfil exclusivo de YouTubeSync para iniciar sesión o cambiar de cuenta. No cambia la conexión OAuth ni la privacidad.|Open Chrome or Edge with YouTubeSync's dedicated profile to sign in or switch accounts. OAuth and visibility are not changed.
Detiene el reproductor integrado y abre el candidato en el navegador con tu sesión y sus permisos.|Stop the embedded player and open the candidate in your browser with your session and permissions.
Pasa a decidir si el vídeo de YouTube corresponde al archivo local.|Continue to decide whether the YouTube video matches the local file.
Confirma que ambos vídeos completos coinciden y son de tu canal; se guardará una marca manual.|Confirm that both complete videos match and belong to your channel; a manual mark is saved.
Descarta esta correspondencia y ofrece conservar el archivo pendiente o solicitar una nueva subida.|Reject this match and offer to keep the file pending or request a new upload.
Guarda que no coinciden y solicita una nueva subida local; no elimina el candidato de YouTube.|Save the mismatch and request a new upload; the YouTube candidate is not deleted.
Recuerda que ese candidato no corresponde y conserva el archivo pendiente sin iniciar una subida.|Remember this candidate does not match and keep the file pending without starting an upload.
Vacía el texto de este campo.|Clear this field's text.
Desplaza las pestañas hacia la izquierda para ver las anteriores.|Scroll tabs left to see earlier tabs.
Desplaza las pestañas hacia la derecha para ver las siguientes.|Scroll tabs right to see later tabs.
""".strip().splitlines()))
