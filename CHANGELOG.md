# Historial de cambios

**Español** | [English](CHANGELOG.en.md)

## 1.1 - 2026-11-26

### Navegación y avisos

- «Vídeos» y «Canal» pasan a llamarse **En mi equipo** y **En YouTube**.
- Las pestañas se sitúan por encima del contenido. El perfil y los avisos solo
  aparecen en En mi equipo, sin ocupar espacio en la biblioteca remota.
- Conexión y configuración se reúnen en un perfil: conexión y canal destacados,
  ruta y privacidad, categoría y lista, sin un título redundante.
- «Ahora» pasa a **Avisos**. Sus flechas permiten recorrer los mensajes sin que
  una actualización de fondo vuelva al primero.
- Avisos no duplica acciones: las específicas están en el vídeo seleccionado y
  las generales en la barra o en «?», entre ON/OFF y Ajustes, sin flecha de menú.

### Bibliotecas y ajustes

- Tablas configurables con controles equivalentes para columnas, orden,
  restauración y color de selección, independientes para cada pestaña.
- En YouTube ofrece 14 columnas: miniatura, título, duración, privacidad, listas,
  publicado, enlace, ID, archivo original, tamaño, resolución, FPS, calidad y
  procesamiento. Mostrar columnas no añade consultas por columna.
- Selección verde por defecto y colores alternativos. Búsqueda de ajustes sin
  distinción de tildes, conservación de la pestaña coincidente y estado sin resultados.
- Los plazos de conservación se desactivan visualmente al apagar la limpieza
  automática, sin perder los valores admitidos de revisión y estabilidad.
- Logo propio «S», original vectorial con márgenes seguros, PNG transparente
  e icono Windows en ocho tamaños. La compilación genera los recursos desde el SVG.

### Vistas previas y reproductores

- Laterales redimensionables que aparecen al seleccionar una fila. La flecha
  permite ocultarlos sin perder selección y conserva su ancho y preferencia
  por separado durante la sesión. Ocultarlos detiene la reproducción.
- Diseño común: nombre, ruta o URL, vídeo, controles y fichas con iconos.
  Las acciones del vídeo quedan dentro del marco, fijas abajo.
- Vista local con miniatura, estado, tamaño, creación y duración obtenida sin API;
  posición, pausa, saltos de diez segundos, volumen, silencio y reproductor externo.
- En YouTube reproduce en el lateral con controles siempre visibles. Play inicia
  la carga; se elimina el botón Reproducir duplicado. Posición y sonido se activan
  con datos reales, no con una estimación.
- Privados con la sesión independiente de Ajustes > Reproducción. OAuth no se
  entrega al reproductor ni inicia esa sesión. Si falla el acceso, se ofrece Ajustes.
- Controles propios sin segunda barra de YouTube y subtítulos desactivados al
  iniciar, con botón para activarlos en el panel y en pantalla completa.
- Pantalla completa desde los controles de ambos reproductores, sin barra de
  título ni ventana intermedia. Escape o Volver al panel conserva la reproducción.
- La vista local de pantalla completa comparte archivo y audio con el panel;
  mantiene posición, fotograma y volumen. Cerrar esa ventana detiene el vídeo.
- Cambiar de archivo, de pestaña o cerrar el panel libera la reproducción.
  Actualizar un archivo sin cambios no lo reinicia; borrar libera antes el archivo.
- Alojamiento del navegador corregido para el escalado de Windows, sin recortar
  controles. Windows recibe el estado de pantalla completa para ocultar la barra de tareas.

### En YouTube

- Imagen, nombre e identidad del canal y resumen de públicos, privados y ocultos
  calculado sobre el catálogo completo, no sobre el filtro.
- Las referencias sin metadatos se muestran aparte y no inflan el total ni la tabla,
  incluso al recuperar una copia anterior, sin consultas extra para sumar el resumen.
- Compartir conserva la confirmación para pasar a **Oculto** y copiar el enlace.
  «Iniciar en…» es una casilla opcional con la posición real capturada.
- Cambiar lista de un vídeo desde el lateral o de varios con el icono junto al candado.
  Se elimina el selector permanente de destino.
- Cambio de lista por lotes con confirmación e informe de resultados parciales:
  se añade el destino antes de quitar las listas anteriores y se detiene al agotarse cuota.
- Se mantienen búsqueda, filtros, privacidad por lotes, duplicados conservadores,
  borrado remoto confirmado y apertura en el navegador.

### En mi equipo y seguridad

- Subir pendientes, cancelar la cola, abrir carpeta, actualizar y limpiar se agrupan
  sobre la tabla; subir uno, reintentar, revisar, comprobar, localizar y borrar, en su lateral.
- La carpeta abre siempre la raíz elegida en Ajustes. Localizar resalta el archivo
  seleccionado en el Explorador, sin reproducirlo.
- Actualizar carpeta es local; su menú permite comprobar expresamente con YouTube.
  Stop solo está disponible con cola o transferencia activa.
- Los pendientes no ofrecen comprobación guiada. Se conserva donde corresponde
  verificar un candidato o revisar una confirmación manual.
- Colores suaves y coherentes: verde para subir/reproducir/confirmar, rojo para
  borrar/detener, azul para consultar/abrir y ámbar para revisión/limpieza; ayudas al pasar el ratón.
- Persisten las protecciones de 1.0: recibos por identidad, ausencia de reintentos
  automáticos repetidos, comprobación antes de borrar y marcas manuales que no
  autorizan limpieza automática. Una falta de cuota no equivale a un vídeo ausente.

### Instalación y compatibilidad

- Instalador completo para Windows x64, actualización desde 1.0 mediante Ajustes,
  comprobación SHA-256 y validación de producto y versión.
- Se conservan ajustes, autorización, sesión de reproducción y registro de subidas.
- Documentación de uso y desarrollo, notas de publicación e historial en español e inglés.
- Siguen vigentes las cuotas de YouTube, los permisos de los privados y la dependencia
  de los códecs de Windows. El instalador no tiene firma Authenticode propia.

## 1.0

Primera publicación completa de YouTubeSync para Windows.

- Instalador que incluye la aplicación y sus dependencias, acceso desde Inicio
  y desinstalación sin eliminar los datos del usuario.
- Actualizaciones desde GitHub dentro de Ajustes: descarga con SHA-256,
  validación del producto y versión, confirmación, cierre e instalación coordinados.
- Interfaz en español e inglés, con ayudas en los controles, ajustes por pestañas
  y búsqueda de opciones.
- Asistente de conexión con credenciales propias, autorización en Google y
  confirmación del canal antes de guardar.
- Biblioteca configurable, vigilancia de carpeta, subida manual/automática,
  progreso, cancelación y reintentos expresos sin bucles de transferencias.
- Recibos e identidad local persistentes para no repetir archivos confirmados;
  transferencia y procesamiento remoto tratados como pasos distintos.
- Comparación guiada local/YouTube, sesión de reproducción independiente y marca
  manual separada de la verificación técnica.
- Canal con miniaturas, búsqueda, filtros, listas, privacidad, enlaces compartidos,
  búsqueda conservadora de duplicados y borrado remoto confirmado.
- Limpieza local verificada, conservación configurable, borrado manual advertido
  y revisión de vídeos cortos antes de subir o eliminar.
- Pausas de cuota compartidas, cachés y consultas por lotes para reducir peticiones.
- Bandeja del sistema, inicio configurable, avisos accionables y consola de diagnóstico.
- Repositorio con una única aplicación, documentación para usuarios y desarrollo
  separadas, sin credenciales ni datos privados.

### Límites conocidos

- YouTube sigue imponiendo sus cuotas y límites del canal; algunos tiempos de
  reintento son estimaciones, no garantías.
- Ver privados requiere una cuenta autorizada en la sesión de reproducción;
  OAuth no inicia esa sesión. La compatibilidad de inserción depende de YouTube.
- Una coincidencia manual es una decisión humana y no permite limpieza automática.
- Los formatos y metadatos locales disponibles dependen de los códecs de Windows.
- El instalador todavía no tiene certificado propio de firma Authenticode.
