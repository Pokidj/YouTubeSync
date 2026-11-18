# Historial de cambios

Los cambios posteriores a la version 1.0 se agrupan en `Sin publicar` hasta
asignarles una nueva version. La version mostrada por la app sigue siendo 1.0.

## Sin publicar

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
