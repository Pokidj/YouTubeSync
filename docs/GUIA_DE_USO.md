# Guia de uso de YouTubeSync

## Que hace

YouTubeSync vigila una carpeta de Windows y sube sus videos a tu canal de
YouTube. El titulo se obtiene de la fecha y hora de creacion del archivo:
`2025-06-18 14:32:05`. Copiar archivos entre discos puede cambiar esa fecha;
revisa los titulos de la biblioteca antes de iniciar una subida masiva.

## Instalacion

Si recibes una compilacion, extrae la carpeta completa y ejecuta
`YouTubeSync.exe`. Conserva la subcarpeta `_internal` junto al ejecutable.
El codigo del repositorio se ejecuta o compila siguiendo la
[guia de desarrollo](DESARROLLO.md).

## Primera configuracion

1. Al abrir por primera vez aparece **Conectar mi canal**. Tambien puedes abrirlo
   desde Ajustes > YouTube. Si ya tienes credenciales, pulsa **Ya tengo mi JSON OAuth**.
2. El asistente te guia para crear tu proyecto de Google Cloud, activar YouTube
   Data API v3 y crear un cliente OAuth de tipo escritorio.
3. Selecciona el JSON descargado. La app lo valida y conserva una copia bajo
   `%APPDATA%\YouTubeSync\oauth`; ya no depende del original de Descargas.
4. Pulsa **Conectar con Google**. La autorizacion se abre en el navegador del
   sistema. Nunca se pide tu contrasena dentro de YouTubeSync.
5. Revisa el nombre, la imagen y el ID del canal y marca **Este es mi canal**.
   **Elegir otra cuenta** vuelve a abrir la seleccion en Google.
6. Elige carpeta, subcarpetas, privacidad y lista. Marca **Subir automaticamente**
   solo si quieres ese modo; inicialmente esta desactivado en el asistente.
7. Pulsa **Guardar y finalizar**. La app recuerda la autorizacion y las opciones.
   Si elegiste Auto, se comprueba primero el canal antes de iniciar el trabajador.

Puedes pulsar **Configurar mas tarde** sin completar la conexion ni iniciar
subidas. Cancelar tampoco sustituye la cuenta activa por una cuenta provisional.
Los usuarios con carpeta y credenciales ya configuradas mantienen el arranque
habitual, sin tener que repetir el asistente. El resto de opciones, como categoria,
extensiones, limpieza e inicio con Windows, siguen disponibles en Ajustes.

### Obtener el JSON OAuth

El asistente de la app enlaza a los pasos necesarios:

1. Crea un proyecto en [Google Cloud Console](https://console.cloud.google.com/projectcreate).
2. Habilita [YouTube Data API v3](https://console.cloud.google.com/apis/library/youtube.googleapis.com).
3. Configura la pantalla de consentimiento y el acceso de tu cuenta.
4. Crea un cliente OAuth de tipo **Aplicacion de escritorio** y descarga su JSON.
5. Selecciona ese archivo en la app y completa la autorizacion en el navegador.

Las pantallas de Google pueden cambiar. Si tu proyecto esta en modo de prueba,
comprueba en Google Cloud que tu cuenta puede autorizarlo. Nunca publiques
el JSON ni el token de acceso en GitHub.

## Controles generales

| Control | Funcion |
| --- | --- |
| ON / OFF | Activa o pausa el modo automatico. |
| Flecha hacia arriba | Solicita la subida de pendientes y activa el modo automatico. |
| Stop | Solicita cancelar la subida actual y deja el automatico en OFF. |
| Actualizar | Recarga configuracion y carpeta y comprueba la conexion a YouTube. |
| Engranaje | Abre Ajustes. |

Los botones muestran su funcion al situar el raton encima. La cancelacion
puede tardar hasta que termine la operacion de transferencia en curso.
Una cancelacion no borra automaticamente un video remoto. Antes de reintentar,
la app comprueba el canal; si YouTube sigue procesando el video, lo conserva.
Los videos dudosos pueden revisarse y eliminarse manualmente desde Canal.

## Pestana Videos

Muestra los archivos de la carpeta configurada, con titulo, tamano, fecha,
estado y ruta. Pulsa una cabecera para ordenar por esa columna.

| Estado | Significado |
| --- | --- |
| Pendiente | El archivo necesita una subida o una comprobacion adicional. |
| En curso | Se esta transfiriendo o comprobando su procesamiento. |
| Subido | Correspondencia y procesamiento confirmados; se conserva la ultima confirmacion. |
| En espera | Falta cuota para continuar, sin convertirlo en un fallo del archivo. |
| Por verificar | Faltan datos suficientes para confirmar la correspondencia con el canal. |
| Incidencia | Se ha registrado un error o una cancelacion. |

El estado local Subido no sustituye la comprobacion remota: antes de eliminar
un archivo, la limpieza consulta YouTube y comprueba el archivo local.

Selecciona un archivo y usa Subir para solicitar su subida individual.
Reintentar limpia su incidencia y vuelve a solicitar la subida. Abrir local
lo abre con el programa asociado de Windows. Actualizar carpeta fuerza un
nuevo escaneo local.

### Limpieza de archivos locales

La papelera de Videos solicita borrar el archivo local seleccionado marcado
como subido. Limpieza busca los archivos cuyo tiempo de conservacion se ha
cumplido. Ambas acciones piden confirmacion y comprueban YouTube antes del borrado.

Si no puede confirmarse la identidad o el procesamiento del video, o el archivo
local ha cambiado, se conserva el archivo y se muestra el motivo. Revisa el
resultado: un lote puede tener archivos borrados y otros conservados.

En Ajustes > Limpieza puedes activar la limpieza automatica y elegir minutos,
horas o dias desde la subida. Empieza con un plazo que te permita revisar tus videos.

## Pestana Canal

Al abrirla se solicita la carga del canal. Tambien puedes usar Cargar canal.
La carga necesita conexion y puede tardar en canales grandes.

- Busca por titulo, lista o enlace.
- Filtra por privacidad, lista o fecha. La fecha busca coincidencias en titulo
  o fecha de publicacion; puedes escribir `2026` o `2026-06`.
- Selecciona una fila para ver miniatura, duracion, privacidad, publicacion y listas.
- Arrastra el separador para cambiar el ancho del panel lateral.
- Si falta altura, desplaza el panel lateral para acceder a todos sus datos.

### Acciones del canal

| Accion | Resultado |
| --- | --- |
| Abrir / Reproducir | Abre el video seleccionado en tu navegador. |
| YouTube | Abre la pagina principal de YouTube. |
| Compartir | Tras confirmar, cambia el primer video seleccionado a Oculto y copia el enlace. |
| Privacidad | Cambia la privacidad de los videos seleccionados. |
| Mover a lista | Cambia la lista de un video seleccionado; requiere seleccion individual. |
| Duplicados | Busca grupos con huella o metadatos de archivo suficientes. |
| Borrar | Elimina de YouTube los videos seleccionados, previa confirmacion. |

Para seleccionar varios videos usa Ctrl o Mayus. Comprueba la seleccion antes
de borrar del canal. Un video privado se abre con los permisos de la sesion del
navegador; la autorizacion OAuth de la app no inicia sesion en ese navegador.

La busqueda de duplicados no considera suficiente compartir fecha o duracion.
Puede omitir videos que no tengan metadatos adecuados. Comprueba los resultados
antes de decidir que borrar. Edita un filtro para volver a la lista filtrada normal.

## Ajustes

| Pestana | Opciones |
| --- | --- |
| General | Version, carpeta, extensiones e inclusion de subcarpetas. |
| YouTube | JSON OAuth, asistente, privacidad, categoria y listas; permite crear listas. |
| Automatizacion | Auto al arrancar, inicio minimizado, cierre a bandeja, inicio con Windows, intervalo y estabilidad. |
| Limpieza | Borrado automatico y tiempo de conservacion con unidad. |

El buscador localiza secciones por palabras clave. Los cambios se aplican al
pulsar Guardar.

### Actualizaciones

En General, pulsa **Buscar actualizaciones**. Se consulta la ultima Release
estable de `Pokidj/YouTubeSync`, no los commits del repositorio. Si hay una version
posterior con paquete Windows x64, puedes ver sus notas y descargarla con progreso
y cancelacion. No utiliza el OAuth ni la cuota de YouTube.

Solo se da por terminada una descarga cuyo tamano, SHA-256 publicado por GitHub
y manifiesto de version coinciden. **Abrir carpeta** muestra el ZIP guardado.
Cierra YouTubeSync por completo antes de extraerlo y sustituir la carpeta del
programa completa, no solo el EXE. La configuracion y el registro permanecen en
AppData. No hay instalacion automatica ni reinicio forzado.

Si aun no hay ninguna Release estable publicada, la app lo indica. Las versiones
en borrador, preliminares y el Source code ZIP de GitHub no se ofrecen como paquete.

## Bandeja y cierre

El icono de la bandeja ofrece Mostrar, modo automatico, subir pendientes,
cancelar, actualizar, ajustes y Salir. Si esta activado el cierre a bandeja,
la X oculta la ventana y la app sigue abierta. Salir pide confirmacion y cierra
la aplicacion por completo. Si desactivas el cierre a bandeja, la X tambien
solicita confirmacion para salir.

## Consola y datos locales

Consola muestra los mensajes tecnicos. Limpiarla borra solo el texto mostrado;
no elimina el registro de subidas. Configuracion, autorizacion y base de datos
se guardan bajo `%APPDATA%\YouTubeSync`.

## Problemas habituales

El [protocolo de verificacion](VERIFICACION_DE_SUBIDAS.md) explica por que un
archivo que sigue en la carpeta no se vuelve a subir, que recuerda la app sin
API y que comprobaciones adicionales son obligatorias antes de borrarlo.

### Cuota de la API agotada

No es un fallo de los archivos. YouTubeSync conserva los Subidos ya confirmados
y deja En espera los intentos bloqueados por cuota. La cuenta atras indica la
proxima comprobacion prevista; no garantiza que Google conceda cuota nueva.
Si Auto sigue ON, los intentos se reanudan al terminar la pausa. OFF sigue OFF.

Actualizar ofrece Ver cuota, Solicitar ampliacion y Reintentar conexion. Esta
ultima opcion solo vuelve a consultar Google: no reinicia ni aumenta la cuota.
Google permite solicitar ampliaciones mediante su
[formulario de auditoria y ampliacion](https://support.google.com/youtube/contact/yt_api_form).

La cuota diaria se reinicia a medianoche del Pacifico. Normalmente corresponde
a las 09:00 en Espana peninsular; durante el desfase entre cambios de horario
de Estados Unidos y Europa puede ser a las 08:00. La app calcula el instante
del proximo reinicio, no una espera fija de 24 horas.
[Referencia oficial de cuotas](https://developers.google.com/youtube/data/determine_quota_cost).

Sin API puedes ver la biblioteca local, abrir enlaces en el navegador y, si
ya se cargo correctamente el canal con esta version, consultar su ultima copia
guardada. Se muestra la fecha de esa copia. No es una verificacion actual del
canal, especialmente para videos privados, y no se usa para autorizar borrados.
YouTube Studio permite revisar manualmente el canal con tu cuenta autorizada.

### Otros problemas

| Problema | Que hacer |
| --- | --- |
| No detecta un archivo | Revisa carpeta, extension y subcarpetas; pulsa Actualizar carpeta. Un archivo reciente debe cumplir la espera de estabilidad. |
| Falta conexion OAuth | Revisa el JSON y completa la autorizacion de la cuenta correcta. |
| Error o cancelacion | Lee el motivo en Consola, comprueba conexion y usa Reintentar cuando proceda. |
| Cuota o limite de subidas | Respeta la pausa indicada por YouTube. Algunas esperas son estimadas; reintentar no elimina el limite. |
| No puede borrar un archivo | Lee el motivo: puede faltar confirmacion remota, seguir procesandose o haber cambiado el archivo local. |
| Video privado no visible | Inicia sesion con una cuenta autorizada en el navegador donde se abre el video. |

Al comunicar un problema, indica version, accion y mensaje de error. Evita
compartir tokens, JSON OAuth y registros con informacion personal.
