# Historial de cambios

**Español** | [English](CHANGELOG.en.md)

Los cambios posteriores a la version 1.0 se agrupan en `Sin publicar` hasta
asignarles una nueva version. La version mostrada por la app sigue siendo 1.0.

## Sin publicar

### Idiomas y documentación bilingüe

- Selector Español (predeterminado) / English en Ajustes > General. Se guarda
  con el perfil y se aplica al reiniciar, sin migrar ni traducir los estados internos.
- Interfaz, asistentes, avisos, ayudas y presentación de diagnósticos en inglés.
  Los nombres, rutas, enlaces, títulos y listas del usuario se conservan literalmente.
- Los filtros, la privacidad, el orden de columnas y las comprobaciones siguen
  usando los mismos identificadores; cambiar el idioma no provoca consultas API.
- README, guía de uso, desarrollo, verificación, publicación y changelog con
  versiones en español e inglés enlazadas. Datos privados excluidos de GitHub.

### Limpieza del proyecto

- Retirados prototipos, capturas, copias de distribuciones obsoletas, caches y el
  entorno de desarrollo de la version archivada. Se conserva la distribucion
  actual completa, el entorno activo, codigo, pruebas y documentacion.
- Datos locales encontrados entre las pruebas apartados en un respaldo privado,
  fuera de Git. La configuracion, OAuth y sesiones activas de AppData no cambian.
- Mapa de carpetas actualizado y ruta de ejecucion conservada para no romper
  los lanzadores ni accesos existentes. La version historica sigue archivada.

### Sesion de reproduccion dentro de la app

- Chrome o Edge reales alojados dentro de la comprobacion, con un perfil exclusivo
  de YouTubeSync compartido con Gestionar sesion en Ajustes > Reproduccion.
- Inicio de sesion en una ventana normal del navegador desde Ajustes. La app no
  lee contraseñas ni importa cookies del perfil personal. OAuth sigue independiente.
- Sin barra de titulo interior; cierre limitado a la ventana del reproductor,
  sin terminar el navegador completo ni otras ventanas de la sesion.
- Documento de reproduccion solo en 127.0.0.1, rutas aleatorias y eventos validados.
  Cambiar de paso o cerrar solicita detener el video y retira la ventana alojada.
- La confirmacion sigue siendo explicita y no se cambia la privacidad del video.
  La compatibilidad con un privado requiere probar la cuenta autorizada.
- Los ajustes de reproduccion tienen su propia pestaña; los campos de YouTube
  conservan su altura legible en ventanas pequeñas.

### Comparacion guiada y ayudas

- El paso de YouTube incluye ahora el reproductor oficial dentro de la ventana.
  No abre el navegador automaticamente. La decision se habilita al empezar la
  reproduccion o tras abrir expresamente el candidato en el navegador alternativo.
- La recarga y el navegador quedan como botones auxiliares con ayuda. Al volver
  al local, avanzar, cambiar el enlace o cerrar se retira y silencia el reproductor.
- El reproductor usa identificacion de la app, perfil aislado y no recibe tokens
  OAuth. Los privados o videos con restricciones conservan la alternativa externa.
  El arranque nativo se comprueba en un proceso separado para no cerrar la app
  si el componente web no esta disponible.
- El motor web se carga solo al comparar con YouTube, no al arrancar la app.
  Intro en el campo del enlace recarga el candidato sin cerrar la comparacion.
- La comprobacion manual reproduce el archivo local dentro del asistente, con
  pausa, volumen y desplazamiento. Al avanzar muestra el candidato de YouTube
  y pregunta explicitamente si corresponde al mismo video completo y del canal.
- No corresponde permite guardar la discrepancia sin subir o solicitar una
  subida nueva de forma separada. Se recuerda el candidato descartado para no
  asociarlo otra vez; no se borra nada de YouTube. La nueva subida sigue limitada
  a un intento y conserva los controles de cuota y seguridad.
- Cerrar, cancelar o avanzar detiene o pausa la reproduccion local para evitar
  sonido en segundo plano. Hay acceso al reproductor de Windows como alternativa.
- Ayudas descriptivas al mantener el raton sobre botones, incluidos los de solo
  icono, ventanas auxiliares y acciones de los menus.

### Acciones de Ahora y confirmacion manual

- Ahora admite hasta cinco acciones contextuales con iconos y nombres accesibles,
  y navegacion al aviso anterior y siguiente sin perder el aviso elegido.
- Los videos por verificar ofrecen YouTube, archivo local, confirmacion manual,
  comprobacion individual por ID y Consola. Si falta el enlace, puede introducirse
  en el dialogo de comparacion; no se busca todo el canal automaticamente.
- Nueva marca Subido (manual), separada de los recibos de transferencia y de la
  verificacion automatica. Requiere confirmar que ambos videos completos coinciden,
  guarda la huella local en segundo plano y evita repetir la subida sin gastar API.
- Esta marca no autoriza limpieza automatica ni se usa como prueba criptografica
  remota. No sustituye una confirmacion automatica y rechaza enlaces ya vinculados
  a archivos presentes de contenido diferente. Una comprobacion tecnica valida
  posterior puede convertirla en una confirmacion automatica.
- Limite del canal separado de cuota API: accesos a Studio, ayuda del limite y
  consola de cuota del proyecto del JSON. No se muestra un contador de restantes
  ni un reinicio garantizado que Google no proporciona.
- Acciones adicionales por estado para reintentar, abrir, borrar y copiar el
  detalle con secretos ocultos. Cancelar desde un aviso solo afecta a su archivo
  si sigue siendo la transferencia activa.

### Borrado manual desde la biblioteca

- La papelera permite borrar cualquier archivo local seleccionado, aunque este
  pendiente, en revision, procesandose o con incidencia. Advierte si no hay una
  subida confirmada y exige elegir Borrar de todos modos; Cancelar es la opcion inicial.
- Los archivos que figuran como Subidos conservan Comprobar y borrar y ofrecen
  tambien el borrado local sin comprobacion, con aviso sobre la posible perdida.
- El borrado manual sin comprobar no usa la API ni elimina videos del canal.
  Pausa Auto, espera la transferencia activa y verifica que el archivo no haya
  cambiado ni este recien modificado antes de eliminarlo.
- La revision previa a subir permite tambien borrar archivos de duracion
  desconocida, pasando por la misma confirmacion. La limpieza automatica mantiene
  todas sus comprobaciones remotas y no adopta esta excepcion manual.

### Limpieza de videos cortos

- El boton Limpieza ofrece la limpieza por tiempo de conservacion y una nueva
  opcion para cualquier archivo local que dure estrictamente menos de 30 segundos,
  este subido o pendiente. El aviso informa de los que pueden no tener otra copia.
- Analisis de duracion en segundo plano con propiedades de Windows, sin cuota
  de YouTube, con avance visible y confirmacion del numero, tamaño y listado.
- Los archivos sin duracion fiable, recientes o modificados se conservan. La
  duracion y la identidad local se vuelven a comprobar inmediatamente antes de borrar,
  sin API. La limpieza habitual mantiene su comprobacion remota; esta opcion no
  borra videos del canal ni se ejecuta automaticamente.
- Los clips cortos o de duracion desconocida requieren revision antes de subir:
  estado Revisar, aviso con acciones y decisiones Autorizar y subir, Abrir local,
  Borrar local o Mas tarde. No son incidencias.
- Autorizacion persistente por archivo, invalidada si cambia. Un intento sin
  revisar no consume una sesion de subida ni anula el bloqueo de reintentos.
- La limpieza pausa las siguientes subidas y espera a que termine la operacion
  activa antes de borrar; no se borra un archivo mientras se esta transfiriendo.

### Biblioteca configurable

- Nuevos ajustes de Biblioteca para elegir las columnas visibles, reordenarlas
  arrastrando o con flechas y recuperar la vista predeterminada.
- Vista inicial con Archivo, Tamaño, Creado y Estado. Titulo y Ruta siguen
  disponibles, junto con las columnas opcionales Miniatura, Resolución, Duración y FPS.
- Cabeceras con iconos y estados identificados por texto, color e icono.
- Miniaturas y propiedades leidas del proveedor del Explorador de Windows,
  para las filas visibles y en segundo plano, sin peticiones a YouTube.
  Ordenar por metadatos completa los datos restantes con una cola acotada.
  Cache acotada por identidad del archivo; formatos no soportados no inventan datos.
- Ordenacion numerica de tamaño, resolución, duración y FPS. Ocultar o mover
  columnas no modifica las acciones, la identidad ni las confirmaciones de subida.
- Guardar cambios exclusivos de columnas no lanza una comprobacion del canal.

### Avisos estables y transferencia compacta

- La flecha de Ahora conserva el aviso elegido durante las recargas y la cuenta
  atras. La actividad rutinaria ya no entra en la rotacion de avisos pendientes.
- La seleccion explicita de un archivo muestra su aviso y lo conserva al recargar;
  si el problema desaparece, se vuelve al aviso pendiente de mayor prioridad.
- Perfil distribuido en una cuadricula uniforme sin etiquetas redundantes; se
  conservan los iconos, valores, nombres accesibles y detalles al pasar el puntero.
- Sustituido el tercer recuadro por una franja de transferencia bajo los dos
  bloques principales. Solo aparece con trabajo activo, en pausa o procesandose.
- La cuota de una consulta sin cola de subidas no muestra una transferencia.
  La franja desaparece al cancelar, detener la cola o confirmar los archivos.
- El procesamiento usa una indicacion indeterminada, sin inventar un porcentaje
  de YouTube. El progreso de bytes y el archivo se muestran solo en la franja.

### Interfaz y consola de diagnostico

- Perfil Canal y carpeta con campos separados e iconos para canal, carpeta,
  privacidad, categoria y lista, rutas ajustadas al espacio y estado de conexion.
- Eliminada la explicacion duplicada de cuota en Subida actual: los motivos y
  las acciones permanecen en Ahora; la transferencia solo muestra su estado.
- Sustituidos los simbolos de fuentes y los iconos nativos dispares por recursos
  Lucide locales, con atribucion y licencia incluidas. Controles, filtros, tablas,
  ajustes y asistente comparten un estilo mas limpio y coherente.
- Consola retirada de las pestanas principales. Se abre como ventana reutilizable
  desde Ajustes / General o desde los avisos, sin interrumpir la captura al cerrarla.
- Registro acotado con hora y zona, nivel, origen, operacion, archivo y trazas
  cuando estan disponibles. Busqueda, filtros, copia de incidencias o informe y
  exportacion UTF-8; los campos reconocibles de credenciales se ocultan.
- Texto tecnico mostrado como texto plano, sin interpretar HTML devuelto por
  servidores. Limpiar la consola no toca la base de datos ni las confirmaciones.
- Comprobacion del paquete ampliada a SVG y diagnostico para detectar recursos
  o bibliotecas ausentes antes de entregar el ejecutable.

### Estado y orientacion en una sola vista

- Unificados Estado y Configuracion en Canal y carpeta: canal, ruta, privacidad,
  categoria y lista. La recarga local ya no sustituye Conectado por Preparado.
- Nuevo panel Ahora, visible desde todas las pestanas, con motivo del problema
  y acciones concretas para conexion, OAuth, API desactivada, permisos y cuota.
- Avisos persistentes por origen y navegacion entre avisos; una recarga o un
  mensaje de actividad no ocultan los problemas pendientes de resolver.
- Al seleccionar un video con incidencia o por verificar, se muestra el archivo
  y una accion dirigida a el, no a una seleccion anterior o distinta.
- Errores del servicio, Canal, ajustes y limpieza publicados tambien en el panel;
  los detalles tecnicos permanecen disponibles en Consola y en el aviso.
- Progreso integrado en Subida actual, que distingue transferencia y procesamiento.
  Ajustes compactos comprobados en ventanas pequenas, sin nuevas consultas API.

### Proteccion frente a subidas repetidas

- Corregido el bucle que podia devolver a Pendiente un intento sin confirmar
  e iniciar otra transferencia del mismo archivo en cada reintento automatico.
- Reserva persistente y atomica por archivo: un error, cancelacion o cierre
  inesperado no autoriza una transferencia nueva, tampoco tras reiniciar.
- Reintentar o Subir seleccionado permiten un unico intento adicional; no se
  admite encolar otra subida del archivo que ya esta transfiriendose.
- La comprobacion remota puede recuperar una confirmacion, pero no desbloquea
  por si sola un intento anterior si el video no aparece en YouTube.
- Reintentos de bloques limitados a una sesion resumible ya creada; no se
  repite automaticamente la creacion de sesion ante un fallo ambiguo.
- Un rechazo de cuota previo a crear sesion puede volver a probarse al acabar
  la pausa global. Una transferencia parcial requiere revision explicita.
- Historial local de resultado y motivo de cada intento nuevo. Los intentos
  locales no se presentan como contador de cuota ni como videos terminados.

### Menos consultas y confirmaciones permanentes

- Los archivos Subidos confirmados no se vuelven a verificar en el arranque,
  las recargas ni los controles periodicos mientras su firma local no cambie.
- Sin comprobaciones de procesamiento pendientes, el control periodico no
  consulta el canal. Los IDs conocidos se verifican por lotes sin recorrerlo entero.
- Cache breve persistente y compartida entre interfaz y trabajador; las consultas
  simultaneas se agrupan y no renuevan artificialmente su caducidad.
- Los casos Por verificar esperan una accion explicita en lugar de repetir
  continuamente una comprobacion sin pruebas nuevas.
- Separados el limite temporal y la cuota diaria, incluido rateLimitExceeded
  cuando Google especifica Video Uploads per day. Pausas caducadas descartadas,
  avisos antiguos corregidos y espera progresiva ante limites temporales repetidos.
- Borrado local sigue exigiendo una consulta nueva a YouTube, ahora solo de los
  IDs de los archivos que se pretende borrar. No utiliza la cache para autorizarlo.

### Actualizaciones desde GitHub Releases

- Activado Buscar actualizaciones en Ajustes: consulta manual de la ultima
  Release estable del repositorio publico, con comparacion numerica de versiones.
- Descarga directa del paquete Windows x64, progreso y cancelacion, sin OAuth
  de GitHub ni consumo de cuota de YouTube.
- Verificacion de origen HTTPS, tamano, SHA-256 publicado, estructura y manifiesto
  de version. No se ofrecen ZIP de codigo fuente ni paquetes parciales como app.
- Notas de version y acceso a la carpeta descargada. La instalacion sigue siendo
  manual para no sustituir binarios en uso ni tocar datos del usuario.
- Version centralizada en `youtube_sync_version.py` y comando de empaquetado que
  comprueba el EXE antes de crear el ZIP completo y su checksum.
- Documentado el procedimiento para publicar, por ejemplo, v1.1 sin crear una
  release ficticia ahora. La version actual permanece en 1.0.
- Pruebas de metadatos, versiones, integridad, rutas ZIP, cancelacion, errores,
  interfaz y generacion de paquetes sin datos personales.
### Primera conexion con credenciales propias

- Asistente integrado de siete pasos: inicio, proyecto, API, credenciales,
  autorizacion, confirmacion del canal y opciones de subida.
- Acceso directo para usuarios que ya tienen JSON; copia gestionada y validacion
  de cliente de escritorio y servidores oficiales de autorizacion y tokens.
- Migracion de autorizaciones compatibles y pausas de cuota al importar el JSON.
- Autorizacion en navegador externo con PKCE explicito y seleccion de cuenta;
  comprobacion de nombre, imagen e ID antes de guardar.
- Token provisional durante el asistente; cancelar no cambia la cuenta activa.
  Guardar confirma conexion, carpeta, privacidad, lista y modo de subida.
- Primer arranque sin subidas automaticas por defecto; Auto elegido expresamente
  espera la conciliacion del canal. Los usuarios configurados conservan su flujo.
- Sustituido el asistente JSON antiguo; entrada unica desde Ajustes y busqueda
  de ajustes corregida para encontrar la conexion en la pestana YouTube.
- Pruebas de importacion, cancelacion, fallos de guardado, confirmacion, navegacion,
  arranque nuevo/existente y conservacion de las funciones anteriores.
### Revision de persistencia y seguridad

- Recibo persistente de cada nueva transferencia completada: ID devuelto por
  YouTube, firma del archivo, huella completa, tamano y fecha, guardados con el
  estado Procesando en una transaccion. No depende de conservar la descripcion.
- Un archivo ya confirmado y sin cambios sigue reconocido aunque permanezca
  en la carpeta, se reinicie la app o se limpie Consola; no se vuelve a subir.
- Los registros sin evidencia suficiente se muestran Por verificar, no como
  archivos defectuosos. No se inventan recibos para las subidas antiguas.
- Consultas por ID verifican pertenencia al canal conectado. Eliminados los
  metodos antiguos sin uso que confirmaban videos solo por titulo.
- Borrado manual recibe el ID persistente de la seleccion; los errores locales
  posteriores no eliminan el ID remoto guardado.
- Cierre explicito del archivo de transferencia en exito, fallo y cancelacion;
  una modificacion durante la transferencia impide confirmar esa correspondencia.
- Miniaturas con seis trabajadores como maximo; el cierre definitivo detiene
  vigilancia y temporizadores sin lanzar trabajo adicional.
- Guardado atomico y validacion de ajustes; reparado el inicio minimizado y el
  comando de inicio con Windows cuando se ejecuta desde el codigo fuente.
- Explicacion del protocolo en `docs/VERIFICACION_DE_SUBIDAS.md` y pruebas de
  persistencia, contenido, canal, cancelaciones, cambios y seleccion para borrado.

### Cuota API y consulta local

- La cuota agotada es una pausa global, no una incidencia de cada archivo. Se
  conservan los estados previamente confirmados; los intentos bloqueados figuran
  En espera y muestran el proximo intento con cuenta atras.
- Bloqueo compartido y persistente de peticiones hasta el reinicio previsto de
  Google o Retry-After, sin volver a consumir peticiones fallidas en cada ciclo.
- Separadas las cuotas especificas de subidas y las restricciones del canal de
  la cuota general de lectura. La pausa API no desactiva la intencion Auto ON.
- Reutilizacion del cliente del trabajador; catalogo completo cacheado cinco
  minutos y consultas por ID durante un minuto. Los videos con ID no requieren
  recorrer todo el canal. La limpieza automatica se revisa como maximo cada cinco minutos.
- Copia persistente de la ultima galeria cargada correctamente para consultarla
  sin cuota, identificada como copia local con fecha. No confirma disponibilidad
  actual ni autoriza borrados sin una nueva comprobacion remota.
- Actualizar permite abrir las cuotas de Google, solicitar ampliacion o volver
  a probar si ya se ha concedido. Reintentar no reinicia el contador de Google.
- Pruebas de cuotas, persistencia, recuperacion, cache, estados y cambios horarios
  del Pacifico; conservada la prueba de transferencia HTTP 308.

### Verificacion de contenido y recuperacion de estados

- Normalizado el resultado remoto `succeeded` como procesamiento terminado; se
  corrigen los videos finalizados que seguian apareciendo En curso.
- Comprobacion de estados al abrir, al actualizar y cada minuto incluso con Auto
  OFF. Las comprobaciones periodicas consultan IDs en lotes de 50, en segundo plano.
- Reintentar conserva la seleccion y el ID remoto aunque se recargue la tabla.
- El modo automatico configurado al arrancar inicia realmente el trabajador.
- Las nuevas subidas incluyen SHA-256 del archivo completo, calculado en bloques
  y cacheado mientras el archivo no cambie. No se identifica contenido por duracion.
- Las huellas antiguas requieren tambien nombre original y tamano coincidentes.
  Sin pruebas suficientes queda una incidencia, no un falso Subido ni un borrado.
- Se elimina la asociacion por ruta si la firma del archivo local ha cambiado.
- Conciliacion atomica que no sobrescribe reintentos o nuevas subidas posteriores
  a la consulta; los fallos de red no se interpretan como videos ausentes.
- Los estados de error muestran su motivo al pasar el cursor; En curso tiene su
  propio contador y no se contabiliza como incidencia.
- Pruebas de procesamiento, conciliacion por ID, reintento, falsos positivos de
  metadatos iguales y diferencias fuera de los segmentos de la huella antigua.

### Subidas por bloques y procesamiento

- Transporte HTTP creado con la configuracion oficial de Google: un `308 Resume
  Incomplete` sin cabecera Location continua la subida en lugar de tratarse como
  redireccion. Se conserva el tiempo de espera de 30 segundos.
- Los videos en procesamiento se conservan aunque el intento local figure como
  error o cancelacion; esos estados locales ya no provocan su borrado automatico.
- Las cancelaciones no eliminan videos remotos por una inferencia de estado incompleto.
- El registro distingue procesamiento de subida confirmada; solo los confirmados
  pasan a Subido y pueden entrar en limpieza local.
- Actualizacion agrupada de la biblioteca ante eventos del trabajador.
- Prueba con respuestas HTTP 308 sin Location y finalizacion 201, sin conexiones
  reales, y pruebas de conservacion de videos en procesamiento y cancelacion.

### Unico proyecto activo

- El desarrollo y la compilacion se centran exclusivamente en la interfaz Qt.
- Motor extraido a `youtube_sync_engine.py` dentro del proyecto moderno, sin
  dependencia de la carpeta antigua ni importaciones de Tkinter, Pillow o pystray.
- Version anterior conservada en `archive/youtube-sync-legacy`; deja de aparecer
  como una segunda aplicacion en `outputs` y de participar en las pruebas activas.
- Lanzador y compilacion unicos en la raiz del repositorio.
- Conservadas las rutas y formatos de configuracion, token OAuth y registro SQLite.

### Arranque del ejecutable

- Corregida una colision de `icuuc.dll` que impedia importar QtCore: el paquete
  Qt utiliza ahora la biblioteca ICU de Windows y excluye la copia ajena de PATH.
- Especificacion de empaquetado Qt versionada para conservar esta correccion.
- Modo `--self-test` para comprobar el arranque de Qt/Tk y SSL sin abrir la
  configuracion del usuario, autorizar cuentas ni subir archivos.
- Lanzadores `Abrir-YouTubeSync.cmd` dirigidos a `dist`, evitando ejecutar los
  archivos intermedios incompletos de `build`.

### Conexion OAuth y HTTPS

- Corregido el empaquetado del archivo auxiliar SSL requerido por ciertos
  runtimes de Python; su ausencia impedia crear conexiones HTTPS en el ejecutable.
- Autorizacion serializada entre comprobaciones, escaneos y subidas para evitar
  abrir varios consentimientos de Google a la vez.
- Los fallos de red al renovar un token ya no descartan la autorizacion existente.
- Renovacion de consentimiento solo ante permisos cambiados o credenciales revocadas.
- Escritura atomica del token y pausa breve tras errores de autorizacion.
- Tiempos de espera limitados para consultas, renovacion y consentimiento OAuth.
- Comprobacion de conexion sin hilos duplicados y cambios ON/OFF idempotentes.

### Revision de la interfaz en modo ventana

- Corregida la altura del contenedor de la interfaz anterior para que las
  tablas permanezcan visibles en vez de quedar por debajo de la ventana.
- Cabecera, progreso y contadores mas compactos; se conservan las acciones
  especificas de pendientes, limpieza y canal.
- Contadores separados de pendientes, en curso e incidencias para evitar contar
  dos veces el mismo video en el resumen.
- Controles del canal agrupados y desplazamiento de respaldo en ventanas bajas.
- Eliminados bordes claros ajenos a la paleta oscura en la interfaz anterior.
- En Qt, tablas de solo lectura, una sola ventana de Ajustes y consola
  limitada a los ultimos 2000 bloques visibles; el registro persistente se conserva.
- Procesamiento de eventos Qt en lotes para devolver tiempo a la interfaz.
- Escaneo Qt tolerante a archivos que desaparecen durante la ordenacion.
- Pruebas ampliadas a las tres pestanas de la interfaz anterior y a la
  accesibilidad de tablas, acciones y controles en Qt.

### Corregido

- Miniatura del panel Canal con proporcion estable y escalado sin deformacion.
- Panel lateral con desplazamiento cuando falta altura, para acceder a la
  informacion y al boton Reproducir.
- Redistribucion de los datos al cambiar el ancho con el separador.
- Disposicion mas compacta en ventanas bajas.
- Columna interna de enlaces oculta sin reservar ancho innecesario.

### Mejorado

- Redimensionado de la interfaz agrupado con un temporizador breve.
- Pintado de miniaturas sin volver a decodificar la imagen en cada cambio de tamano.
- Pruebas de interfaz para ventanas pequenas y grandes, texto largo y separador.

### Documentacion

- Preparacion del repositorio Git con fuentes, recursos y exclusiones locales.
- Guia de uso, documentacion de desarrollo e historial de cambios.

## 1.0

Base funcional existente al preparar este repositorio. No se reconstruyen
fechas ni versiones historicas que no cuentan con una publicacion verificable.

### Incluido

- Interfaz de escritorio PySide6/Qt con identidad YouTubeSync.
- Vigilancia de carpeta, titulo por fecha de creacion y subida a YouTube.
- Modo automatico, subida manual, progreso, cancelacion y reintentos.
- Registro persistente y comprobaciones para reducir subidas duplicadas.
- Biblioteca local y consulta del canal con miniaturas y filtros.
- Apertura de videos en el navegador, cambio de privacidad y enlaces compartidos.
- Creacion de listas desde Ajustes y cambio de lista desde Canal.
- Borrado de videos del canal y limpieza local con comprobacion previa.
- Asistente OAuth, ajustes por pestanas y buscador de ajustes.
- Configuracion de inicio con Windows, bandeja y cierre definitivo con confirmacion.
- Version 1.0 visible en Ajustes y espacio reservado para futuras actualizaciones.

### Limitaciones conocidas

- El actualizador todavia no descarga ni instala versiones.
- La reproduccion se realiza en el navegador externo.
- La deteccion de duplicados omite videos con metadatos insuficientes.
- Los tiempos de recuperacion tras ciertos limites de YouTube son estimaciones.
