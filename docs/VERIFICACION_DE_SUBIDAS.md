# Como se reconoce una subida

## Dos comprobaciones distintas

1. **Registro local:** recuerda una subida confirmada para no repetirla aunque
   el archivo siga en la carpeta. Funciona sin API.
2. **Comprobacion remota:** consulta si ese video sigue en el canal y ya termino
   de procesarse. Necesita API. Es obligatoria antes de borrar un archivo local.

Consultar el registro no significa comprobar en directo YouTube. Sin cuota se
conserva la ultima confirmacion; no se inventa una nueva ni se interpreta la
falta de conexion como un video borrado.

## Identidad del archivo

La firma local combina ruta, tamano y marcas de creacion y modificacion. Permite
consultar el registro rapidamente sin releer todo el archivo. Si no cambia, se
reconoce despues de reiniciar la aplicacion. Leer un archivo no cambia esta firma.

La identidad del contenido se comprueba aparte mediante SHA-256 del archivo
completo. Duracion, titulo y fecha iguales no bastan para demostrar que dos
clips son el mismo. Las huellas antiguas eran muestreadas y requieren tambien
metadatos originales coherentes; no equivalen a un checksum completo.

Si cambias, sustituyes, renombras o mueves un archivo, su firma puede cambiar.
No se reutiliza una confirmacion antigua solo por coincidir la ruta: se necesita
comprobar la nueva correspondencia. Esto evita atribuirle una subida de otro clip.

## Recibo persistente de las nuevas subidas

Al recibir la respuesta final con un ID de video, la app guarda de forma atomica
en SQLite un recibo con ID, firma local, SHA-256 completo, tamano y fecha. Tambien
guarda el estado Procesando. Este recibo sobrevive al reinicio y a limpiar Consola.

Todavia no se marca Subido: recibir los bytes no equivale a terminar de procesar.
Una cancelacion antes de la respuesta final no genera recibo. Si el archivo
cambia durante la transferencia, tampoco se confirma su correspondencia.

El recibo vincula el ID devuelto por esa transferencia con el contenido local.
Permite verificarlo aunque despues se edite la descripcion del video. El marcador
de la descripcion sigue siendo una ayuda para recuperar correspondencias antiguas.
YouTube no devuelve un SHA-256 independiente de los bytes originales: el checksum
es calculado por YouTubeSync, no por el servidor de YouTube.

## Comprobacion con la API

La app consulta IDs por lotes, comprueba el canal propietario y solicita estado,
procesamiento y metadatos. Solo acepta como terminado `uploadStatus=processed`
o `processingStatus=succeeded`, descartando fallidos, rechazados o terminados
con error. `uploaded` por si solo no demuestra que el procesamiento haya finalizado.

Para vincularlo al archivo necesita huella coherente o recibo persistente del
mismo ID. Un ID de otro video, un titulo repetido o una duracion parecida no bastan.
Si Google devuelve ausencia real, vuelve a Pendiente; un fallo de red o de cuota
no se confunde con esa ausencia.

Referencia de los estados de YouTube:
[Videos](https://developers.google.com/youtube/data/reference/rest/v3/videos).

## Estados y seguridad

| Estado | Significado |
| --- | --- |
| Pendiente | No hay una subida confirmada para este archivo. |
| En curso | Transferencia activa o archivo recibido que aun se procesa. |
| Subido | Correspondencia y procesamiento confirmados; se conserva en el registro. |
| En espera | Una restriccion de cuota impide el siguiente intento. No es un archivo defectuoso. |
| Por verificar | Hay un candidato, pero faltan pruebas para vincularlo con seguridad. |
| Incidencia | Hay un fallo concreto o una discrepancia que necesita revision. |

Los registros antiguos sin pruebas suficientes no se convierten automaticamente
en recibos nuevos. No es posible reconstruir retroactivamente el ID que devolvio
una transferencia si esa informacion no se guardo de forma fiable.

Antes de borrar un archivo local se vuelve a consultar YouTube, se comprueba el
contenido y el estado final y se verifica que el archivo local no haya cambiado.
La copia local del canal y el historial no sustituyen esa comprobacion de borrado.
