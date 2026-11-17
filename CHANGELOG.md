# Historial de cambios

Los cambios posteriores a la version 1.0 se agrupan en `Sin publicar` hasta
asignarles una nueva version. La version mostrada por la app sigue siendo 1.0.

## Sin publicar

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
