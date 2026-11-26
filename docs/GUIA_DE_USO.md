# Guia de uso de YouTubeSync

**Español** | [English](USER_GUIDE.en.md)

## Idioma

En **Ajustes > General > Idioma** elige **Español** (predeterminado) o **English**.
Pulsa Guardar y vuelve a abrir YouTubeSync para aplicarlo. Si cierras a la bandeja,
sal primero desde Salir. El idioma no cambia tus vídeos, listas, rutas, conexión
OAuth ni confirmaciones. Los mensajes técnicos originales de Google pueden
mantener su idioma de origen.

## Que hace

YouTubeSync vigila una carpeta de Windows y sube sus videos a tu canal de
YouTube. El titulo se obtiene de la fecha y hora de creacion del archivo:
`2025-06-18 14:32:05`. Copiar archivos entre discos puede cambiar esa fecha;
revisa los titulos de la biblioteca antes de iniciar una subida masiva.

## Instalacion

Descarga el archivo `YouTubeSync-…-windows-x64-setup.exe` de la
[última publicación](https://github.com/Pokidj/YouTubeSync/releases/latest),
ejecútalo y abre YouTubeSync desde Inicio. Incluye todas las dependencias;
no necesitas Python. Los archivos Source code son para desarrollo.
El instalador conserva los datos de la app en AppData, también al desinstalar.
La compilación del código se explica en la [guía de desarrollo](DESARROLLO.md).

## Primera configuracion

1. Al abrir por primera vez aparece **Conectar mi canal**. Tambien puedes abrirlo
   desde Ajustes > Conexión. Si ya tienes credenciales, pulsa **Ya tengo mi JSON OAuth**.
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
| ? | Abre las opciones generales y la lista de avisos; el menú no necesita una flecha aparte. |
| Subir pendientes, sobre la tabla local | Solicita la cola de pendientes y activa el modo automático. |
| Stop, sobre la tabla local | Cancela la cola o subida activa y deja el automático en OFF. |
| Actualizar carpeta | Relee la carpeta local sin API. Su menú permite comprobar con YouTube expresamente. |
| Engranaje | Abre Ajustes. |

Los botones muestran su funcion al situar el raton encima. La cancelacion
puede tardar hasta que termine la operacion de transferencia en curso.
Una cancelacion no borra automaticamente un video remoto. Antes de reintentar,
la app comprueba el canal; si YouTube sigue procesando el video, lo conserva.
Los videos dudosos pueden revisarse y eliminarse manualmente desde En YouTube.

## Pestaña En mi equipo

El perfil de conexión y el recuadro Avisos pertenecen a esta pestaña. Avisos solo
incluye sus flechas de navegación: las acciones generales están arriba y las
específicas del archivo están en su lateral. Elegir otro aviso no se deshace al
actualizar la información en segundo plano.

Muestra los archivos de la carpeta configurada. Por defecto aparecen Archivo,
Tamaño, Creado y Estado, con iconos en las cabeceras y en cada estado.
Pulsa una cabecera para ordenar por esa columna; los tamaños se comparan en bytes.

En **Ajustes > En mi equipo** puedes marcar las columnas que quieres ver y cambiar
su orden arrastrandolas o con las flechas. **Predeterminadas** recupera la vista
inicial. Pulsa **Guardar** para aplicar los cambios; se recuerdan al reiniciar.
Titulo y Ruta siguen disponibles aunque no se muestren inicialmente.

Tambien puedes activar Miniatura, Resolución, Duración y FPS. La resolución
muestra las dimensiones reales en pixeles, no una estimacion de calidad.
Estos datos se leen del proveedor del Explorador de Windows en segundo plano,
solo cuando son necesarios y con cache, sin consumir cuota de YouTube. Al ordenar
por resolución, duración o FPS, se leen tambien los datos restantes para ordenar
la biblioteca completa. Los
formatos sin controlador o codec compatible muestran Sin miniatura o No disponible.
Estos datos no se usan como prueba de que un archivo esta subido.

| Estado | Significado |
| --- | --- |
| Pendiente | El archivo necesita una subida o una comprobacion adicional. |
| Revisar | Video corto o de duracion desconocida: necesita autorizacion antes de subir. |
| En curso | Se esta transfiriendo o comprobando su procesamiento. |
| Subido | Correspondencia y procesamiento confirmados; se conserva la ultima confirmacion. |
| Subido (manual) | Correspondencia declarada por ti, sin verificacion automatica ni permiso de limpieza automatica. |
| En espera | Falta cuota para continuar, sin convertirlo en un fallo del archivo. |
| Por verificar | Faltan datos suficientes para confirmar la correspondencia con el canal. |
| Incidencia | Se ha registrado un error o una cancelacion. |

El estado local Subido no sustituye la comprobacion remota: la limpieza por
antiguedad y Comprobar y borrar consultan YouTube antes de eliminar la copia local.
El borrado manual sin comprobar requiere aceptar expresamente su advertencia.

Selecciona un archivo y usa Subir para solicitar su subida individual.
Reintentar, en el lateral del archivo, limpia su incidencia y vuelve a solicitar la subida. Abrir local
lo abre con el programa asociado de Windows. Actualizar carpeta fuerza un
nuevo escaneo local.

La cabecera contiene **ON/OFF**, la interrogación de **Opciones generales** y **Ajustes**. Sobre la tabla,
**Subir pendientes** actúa sobre la cola; la subida individual está en el lateral.
El icono Stop cancela la cola o transferencia activa. El botón de actualizar relee
la carpeta sin API; su menú **Comprobar con YouTube** permite revisar la conexión
remota respetando las pausas de cuota. Los iconos muestran una ayuda al pasar el ratón.

Las pestañas están encima del perfil y Avisos. Al seleccionar un archivo aparece
su vista previa lateral: ruta bajo el nombre, miniatura local y recuadros de estado,
tamaño, fecha y duración. La duración usa los datos locales disponibles; si todavía
no se puede leer, aparece «-». Puedes ampliar
el panel arrastrando el separador. Reproducir carga el archivo local, con posición,
saltos de diez segundos, volumen y apertura en el reproductor externo. Cambiar de
archivo o pestaña detiene la reproducción; actualizar no reinicia un archivo sin cambios.
El icono de pantalla en los controles abre pantalla completa con pausa, posición,
saltos y volumen. Escape o Volver al panel conserva el punto de reproducción.
Cerrar la ventana de pantalla completa o cambiar de archivo detiene la reproducción.
El panel permite abrir su enlace de YouTube, si existe, e iniciar la comparación
manual cuando corresponde, sin confirmar automáticamente la coincidencia.
Los archivos en estado Pendiente no ofrecen la comprobación guiada.
El botón de carpeta sobre la tabla abre siempre la ruta configurada en Ajustes,
independientemente de la selección. **Localizar**, en el lateral, abre el Explorador y resalta el
archivo seleccionado; sin selección está desactivado. Ninguno reproduce el vídeo.

En ambas pestañas, el panel lateral solo aparece con una fila seleccionada.
La flecha **Ocultar panel / Mostrar panel**, sobre la tabla,
permite cerrarlo o recuperarlo sin perder la selección. Ocultar detiene la
reproducción y devuelve todo el ancho a la tabla. Cada pestaña recuerda por separado
esta elección y el ancho del panel mientras la app siga abierta; cambiar de fila,
recargar o volver a la pestaña no deshace una ocultación manual. Sin selección,
el botón está desactivado.

Ambos laterales tienen las acciones dentro de su marco, fijas abajo aunque desplaces
los datos. La posición, pausa, saltos y volumen están justo debajo del vídeo en
ambas pestañas, antes de las fichas con iconos. En YouTube conserva además subtítulos,
compartir y pantalla completa. Los botones usan colores suaves por función: verde para subir, reproducir
o confirmar; rojo para borrar o detener; azul para consultar o abrir; ámbar para revisión
y limpieza. Se mantienen las ayudas al pasar el ratón y las confirmaciones de seguridad.

Antes de iniciar una subida nueva se lee la duracion local, sin consultar YouTube.
Los videos de **menos de 30 segundos** quedan en **Revisar**; si Windows no puede
leer su duracion tambien se pide revision. Al pulsar Revisar o Subir en el lateral puedes
elegir **Autorizar y subir**, **Abrir local**, **Borrar local** o **Más tarde**.
El borrado pide una confirmacion independiente. No se borran ni se suben por
si solos. La autorizacion se recuerda al reiniciar, pero no se aplica a un archivo
modificado. Los videos ya confirmados no vuelven a subirse ni necesitan esta revision.

### Avisos y Acciones

Avisos muestra información y conserva solo las flechas anterior/siguiente dentro del recuadro.
También puedes elegir un aviso desde **Opciones generales > Avisos** en la cabecera.
La interrogación ofrece conexión, cuota, revisión de pendientes y diagnóstico.
Las acciones específicas están en la parte inferior fija del lateral del archivo:
Subir, Reintentar, Revisar, Comparar, Comprobar, Localizar y Borrar local, según su estado.
Siempre actúan sobre el archivo mostrado, aunque Avisos esté enseñando otro problema.

En **Por verificar** puedes abrir **YouTube**, **Ver local**, **Confirmar coincidencia**,
**Comprobar este video**. **Consola** está en Opciones generales o Ajustes.
Si no hay enlace, **Comparar** permite
pegarlo. La comprobacion individual consulta ese ID, no todo el canal, y solo
cambia a Subido cuando obtiene las pruebas tecnicas y el procesamiento completo.
Un error de cuota no convierte el archivo en una incidencia ni en un video confirmado.

La comparacion manual se hace en tres pasos. Primero se reproduce el archivo
local dentro de la ventana, con pausa, sonido y desplazamiento. **Siguiente: YouTube**
pausa esa reproduccion y carga el candidato de YouTube en la misma ventana.
Puedes corregir su enlace y recargarlo. Cuando empiece la reproduccion se habilita
**Ya lo he revisado**; al pulsarlo eliges **Si, corresponde** o **No, es otro video**.
Para preparar privados, abre **Ajustes > Reproduccion > Gestionar sesion**.
Se abre Chrome (o Edge) con un perfil exclusivo de YouTubeSync. Inicia sesion
con la cuenta que tiene acceso al video y cierra esa ventana cuando termines.
Al volver a la comparacion, el navegador alojado dentro del asistente usa ese
mismo perfil. La app no lee contraseñas ni copia cookies de tu navegador personal.
Si cambias de cuenta, hazlo desde ese mismo acceso de Ajustes.
La sesion de reproduccion no sustituye OAuth ni cambia la privacidad del video.
No se muestra una cuenta como conectada sin comprobarla en el navegador.
El boton del navegador mantiene una alternativa expresa si YouTube restringe
la insercion. Sin Chrome o Edge se conserva el reproductor integrado anterior.
Auto se pausa para comparar. Si confirmas, el guardado espera a que termine la
operacion de subida activa, calcula una huella local en segundo plano y muestra
**Subido (manual)**, sin consultar la API.
La marca se recuerda al reiniciar y evita otra subida mientras el archivo no cambie.
Puedes editar el enlace desde ese aviso. Un mismo enlace no se asigna a dos
archivos presentes de contenido distinto; copias identicas si pueden compartirlo.

Si no corresponde, puedes **Guardar sin subir** para dejarlo pendiente con Auto
OFF, o solicitar **Subir como video nuevo**. Se recuerda el candidato descartado
para no vincularlo otra vez a ese archivo. Nunca se elimina el video de YouTube.
La subida nueva consume cuota y solo autoriza un intento, no reintentos continuos.
Cancelar no guarda una decision. Cerrar el asistente detiene las reproducciones
integradas; volver o avanzar tambien retira YouTube para evitar sonido detras.
Cerrar la comparacion solo cierra su ventana de reproduccion, no otras ventanas
del navegador. Si el servidor local deja de responder, el documento intenta
detener el video. La sesion del perfil exclusivo se conserva entre arranques.
Todos los botones muestran una descripcion al mantener el raton encima.

La confirmacion manual no demuestra por si sola el estado actual de YouTube y
no autoriza el borrado automatico. No crea un recibo de transferencia ficticio.
La papelera manual mantiene su advertencia y Comprobar con API puede conseguir
una verificacion tecnica posterior si existen las pruebas necesarias.

En **Limite de subidas del canal**, **YouTube Studio** y **Limites del canal** dan
acceso a la gestion y a la explicacion oficial; **Cuota API** abre Google Cloud
seleccionando el proyecto del JSON cuando consta su ID. Son limites diferentes:
YouTube no expone un contador exacto de subidas restantes del canal. La consola
de Cloud muestra los datos oficiales del proyecto, que pueden tener retraso;
la app no los sustituye por una estimacion ni garantiza un desbloqueo a una hora.

Referencias: [limite del canal](https://support.google.com/youtube/answer/10383400?hl=es),
[cuota API](https://developers.google.com/youtube/data/getting-started),
[latencia de metricas](https://docs.cloud.google.com/monitoring/api/v3/latency-n-retention).

### Limpieza de archivos locales

La papelera de En mi equipo permite borrar el archivo local seleccionado en cualquier
estado. Si no esta confirmado como subido, advierte que podrias perder la unica
copia y exige pulsar **Borrar de todos modos**; **Cancelar** es la opcion inicial.
Si figura como Subido, puedes elegir **Comprobar y borrar**, que verifica YouTube,
o **Borrar de todos modos**, que no usa la API. Este ultimo borra permanentemente
solo el archivo local, deja Auto OFF y espera a que termine la transferencia activa.
Un archivo modificado desde la seleccion o todavia reciente se conserva.

La limpieza automatica y por tiempo de conservacion mantienen la comprobacion
obligatoria de YouTube. El borrado manual no cambia sus reglas ni borra videos del canal.

El boton **Limpieza** tiene dos opciones: **Según tiempo de conservación** mantiene
la limpieza habitual con comprobacion de YouTube; **Vídeos de menos de 30 segundos**
revisa todos los archivos locales en segundo plano, incluidos los pendientes.
Muestra el numero, tamaño, estado y listado antes de pedir confirmacion, y avisa
si podrias perder la unica copia de algun archivo. Al confirmar **Borrar archivos
locales**, Auto queda OFF: se espera a que termine la transferencia activa antes
de borrar. El archivo y su duracion se comprueban de nuevo antes de eliminarlo.
Los videos de 30 segundos exactos, recientes, sin duración legible o modificados
se conservan. Esta limpieza por duracion no usa la API ni borra nada del canal;
es manual e independiente de la limpieza automatica.

Si no puede confirmarse la identidad o el procesamiento del video, o el archivo
local ha cambiado, se conserva el archivo y se muestra el motivo. Revisa el
resultado: un lote puede tener archivos borrados y otros conservados.

En Ajustes > Limpieza puedes activar la limpieza automatica y elegir minutos,
horas o dias desde la subida. Empieza con un plazo que te permita revisar tus videos.

## Pestaña En YouTube

Al abrirla se solicita la carga del canal. Tambien puedes usar Cargar canal.
La carga necesita conexion y puede tardar en canales grandes.

La cabecera muestra la imagen y el nombre del canal vinculado, el total cargado
y sus vídeos públicos, privados y ocultos. Los filtros no cambian esos totales.
Las referencias para las que no hay metadatos quedan fuera del total y de la
tabla y se indican aparte. Esto no confirma que se hayan eliminado de YouTube
ni cambia la verificación de tus archivos locales.
La fecha indica la última consulta; «Copia guardada» identifica datos anteriores
cuando no se ha podido consultar YouTube. El resumen no añade consultas API.
El perfil de conexión y «Avisos» pertenecen únicamente a la pestaña En mi equipo.

- Busca por titulo, lista o enlace.
- Filtra por privacidad, lista o fecha. La fecha busca coincidencias en titulo
  o fecha de publicacion; puedes escribir `2026` o `2026-06`.
- Selecciona una fila para ver miniatura, duracion, privacidad, publicacion y listas.
- Arrastra el separador para cambiar el ancho del panel lateral.
- Si falta altura, desplaza el panel lateral para acceder a todos sus datos.

En **Ajustes > En YouTube** puedes elegir las columnas, arrastrarlas o usar las flechas
para ordenar y cambiar el color de selección. Verde es el predeterminado. Los
campos técnicos usan datos ya consultados; `-` indica que no están disponibles
en la copia del canal. No cambian las pruebas de correspondencia de tus archivos.

### Acciones del canal

| Accion | Resultado |
| --- | --- |
| Play | Triángulo siempre visible bajo el vídeo. Inicia la reproducción en el panel usando la sesión de Ajustes > Reproducción; no hay un botón Reproducir aparte. Los controles de posición y sonido se activan cuando llegan datos reales. |
| Flechas izquierda/derecha del reproductor | Retrocede o avanza diez segundos. |
| Barra de posición | Salta a otro momento del vídeo cuando se conoce su duración. |
| Altavoz y volumen | Silencia o ajusta solo el sonido de este vídeo. |
| Subtítulos | Activa o desactiva los disponibles para el vídeo. Empiezan desactivados en «En YouTube». |
| Reproducir a pantalla completa | Mueve el mismo reproductor a pantalla completa con controles. Solo este botón cambia la vista; Reproducir mantiene el panel. Escape, salir de pantalla completa o Volver al panel devuelve el vídeo directamente al lateral, sin ventana intermedia. |
| Revisar acceso en Ajustes | Aparece si falla un privado y abre Ajustes > Reproducción para revisar la sesión. |
| Stop del reproductor | Detiene el vídeo. También se detiene al cerrar la ventana, cambiar de vídeo o salir de «En YouTube». |
| Abrir / Abrir en YouTube | Abre el vídeo seleccionado en tu navegador habitual. |
| YouTube | Abre la pagina principal de YouTube. |
| Compartir | Tras confirmar, cambia el primer video seleccionado a Oculto y copia el enlace. |
| Compartir desde aquí (icono del reproductor) | Puedes marcar «Iniciar en 1:23» para añadir `?t=83`; sin marcar, se copia el enlace normal. Se confirma el cambio a Oculto y solo se copia tras el éxito de la API. |
| Privacidad | Cambia la privacidad de los videos seleccionados. |
| Cambiar lista | Icono pequeño en el lateral para un vídeo; junto al candado permite cambiar la lista de todos los seleccionados, con confirmación. |
| Duplicados | Busca grupos con huella o metadatos de archivo suficientes. |
| Borrar | Elimina de YouTube los videos seleccionados, previa confirmacion. |

Para seleccionar varios videos usa Ctrl o Mayus. Comprueba la seleccion antes
de borrar del canal. Un video privado se abre con los permisos de la sesion del
navegador; la autorizacion OAuth de la app no inicia sesion en ese navegador.
Gestiona la cuenta desde Ajustes > Reproducción, no desde el reproductor.

Los privados se cargan directamente en YouTube para que reconozca la sesión de
reproducción. Esa cuenta debe tener permiso para ver el vídeo; la app no evita
restricciones de YouTube. Los controles propios esperan datos reales y no
simulan progreso cuando la carga o la autorización falla. Tras instalar esta
mejora, cierra las ventanas de la sesión de reproducción anterior y ábrela de
nuevo desde Ajustes si se solicita; la cuenta guardada se conserva.

La busqueda de duplicados no considera suficiente compartir fecha o duracion.
Puede omitir videos que no tengan metadatos adecuados. Comprueba los resultados
antes de decidir que borrar. Edita un filtro para volver a la lista filtrada normal.

## Ajustes

| Pestana | Opciones |
| --- | --- |
| General | Version, idioma, actualizaciones, consola, carpeta, extensiones e inclusion de subcarpetas. |
| Conexión | JSON OAuth, asistente, privacidad, categoria y listas; permite crear listas. |
| Reproducción | Gestionar la sesión de Chrome o Edge para ver privados durante la comparación. |
| Automatizacion | Auto al arrancar, inicio minimizado, cierre a bandeja, inicio con Windows, intervalo y estabilidad. |
| Limpieza | Borrado automatico y tiempo de conservacion con unidad. |
| En mi equipo | Columnas, orden, restauración y color de selección de los archivos locales. |
| En YouTube | Columnas, orden, restauración y color de selección de los vídeos del canal. |

En mi equipo y En YouTube usan el mismo editor: casillas de columnas, arrastrar o flechas
para ordenar, restauración y color de selección. Cada tabla conserva su propia
configuración. Cambiar estas opciones no consulta YouTube ni altera sus vídeos.

El buscador localiza secciones por palabras clave. Los cambios se aplican al
pulsar Guardar.

### Actualizaciones

En General, pulsa **Buscar actualizaciones**. Se consulta la ultima Release
estable de `Pokidj/YouTubeSync`, no los commits del repositorio. Si hay una version
posterior con paquete Windows x64, puedes ver sus notas y descargarla con progreso
y cancelacion. No utiliza el OAuth ni la cuota de YouTube.

Solo se conserva una descarga cuyo tamaño, SHA-256, producto y versión coinciden.
Pulsa **Instalar actualización** y confirma: la app se cerrará, el instalador
esperará al proceso, actualizará el programa y volverá a abrirlo. Finaliza o
cancela primero cualquier operación activa. No se reinicia Windows ni se fuerza
el cierre de otras aplicaciones. Se mantienen configuración, autorización,
sesión y registro. No hace falta desinstalar ni extraer archivos manualmente.

Si aun no hay ninguna Release estable publicada, la app lo indica. Las versiones
en borrador, preliminares y el Source code ZIP de GitHub no se ofrecen como paquete.

## Bandeja y cierre

El icono de la bandeja ofrece Mostrar, modo automatico, subir pendientes,
cancelar, actualizar, ajustes y Salir. Si esta activado el cierre a bandeja,
la X oculta la ventana y la app sigue abierta. Salir pide confirmacion y cierra
la aplicacion por completo. Si desactivas el cierre a bandeja, la X tambien
solicita confirmacion para salir.

## Consola y datos locales

Consola se abre desde Ajustes / General / Consola en una ventana independiente.
Los avisos tambien pueden abrirla directamente. Recoge mensajes de la sesion
aunque su ventana este cerrada, con hora, nivel y origen. Los problemas de subida
incluyen operacion, archivo y detalle tecnico cuando estan disponibles.

Permite buscar y filtrar por origen o gravedad, copiar avisos y errores, copiar
el informe completo o exportarlo como archivo `.log` UTF-8. Los tokens, secretos
OAuth y otros campos reconocibles de autorizacion se ocultan antes de mostrarlos
y copiarlos. Revisa siempre el informe antes de compartirlo: puede incluir rutas,
nombres de archivos y enlaces de tus videos.

El registro es temporal y conserva hasta 2.000 entradas. Limpiarlo no elimina
el registro de subidas. Configuracion, autorizacion y base de datos
se guardan bajo `%APPDATA%\YouTubeSync`.

## Problemas habituales

El perfil destaca conexión y canal en la primera fila; debajo aparecen ruta y
privacidad, seguidas de categoría y lista, con iconos y ayudas sin etiquetas repetidas.
El panel Avisos muestra la operacion en curso o el problema que necesita atencion,
con flechas de navegación pero sin acciones sobre archivos. Si hay varios avisos, las flechas permiten recorrerlos
y mantiene tu eleccion mientras ese aviso siga vigente. Las comprobaciones y la
cuenta atras no reinician la seleccion. Los mensajes rutinarios no se incluyen
en la rotacion cuando hay problemas pendientes.
Una pausa de cuota tiene prioridad sobre los mensajes de actividad; actualizar
la tabla no borra la explicacion del problema.

Selecciona un video con incidencia o Por verificar para ver una accion dirigida
a ese archivo. Reintentar sigue autorizando un unico intento y no desactiva las
protecciones contra subidas repetidas. Consola conserva el mensaje tecnico.
La transferencia aparece en una franja debajo de los dos bloques principales,
solo mientras haya trabajo activo, en pausa o pendiente de procesamiento. Al
terminar o detener la cola se oculta. Un aviso de cuota sin subidas no la muestra.
Procesando no significa Subido y no presenta un porcentaje de procesamiento
inventado. El perfil conserva los detalles completos en los iconos y tooltips.

El [protocolo de verificacion](VERIFICACION_DE_SUBIDAS.md) explica por que un
archivo que sigue en la carpeta no se vuelve a subir, que recuerda la app sin
API y que comprobaciones adicionales son obligatorias antes de borrarlo.

### Cuota de la API agotada

No es un fallo de los archivos. YouTubeSync conserva los Subidos ya confirmados
y deja En espera los intentos bloqueados por cuota. La cuenta atras indica la
proxima comprobacion prevista; no garantiza que Google conceda cuota nueva.
Si Auto sigue ON, los intentos se reanudan al terminar la pausa. OFF sigue OFF.

Limite temporal API no significa cuota diaria agotada: la app respeta Retry-After
si Google lo proporciona y aumenta la espera si se repite una restriccion temporal.
Si Google especifica un limite por dia, aunque el motivo sea rateLimitExceeded,
se programa el siguiente reinicio diario. El fin de la pausa permite reintentar;
no se anuncia cuota restaurada sin una nueva respuesta del servidor.

Los archivos Subidos confirmados conservan su marca sin consultas periodicas.
Los casos Por verificar necesitan revision o reintento manual y no consumen
consultas repetidas del modo automatico. No borres la base de datos para solucionar
un problema de cuota: contiene las correspondencias que evitan repetir subidas.

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

Si una transferencia falla, se cancela o la app se cierra sin confirmacion,
ese archivo no inicia otra transferencia por si solo. Revisa el canal y utiliza
Reintentar para permitir un unico intento nuevo. Actualizar la carpeta, reiniciar
o activar Auto no eliminan esa proteccion. Si YouTube confirma el contenido,
la app puede reconocerlo como Subido sin volver a transferirlo.

La cuota Video Uploads per day es distinta de Queries per day. Tener pocos
archivos en la carpeta no demuestra cuantos intentos se han iniciado durante
el dia: puede haber intentos fallidos, otras carpetas o aplicaciones del proyecto.
El historial local de intentos tampoco equivale al contador oficial de Google.

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
