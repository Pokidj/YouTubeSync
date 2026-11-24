# Como se reconoce una subida

**Español** | [English](UPLOAD_VERIFICATION.en.md)

## Dos comprobaciones distintas

1. **Registro local:** recuerda una subida confirmada para no repetirla aunque
   el archivo siga en la carpeta. Funciona sin API.
2. **Comprobacion remota:** consulta si ese video sigue en el canal y ya termino
   de procesarse. Necesita API. Es obligatoria para la limpieza por antiguedad y
   la opcion Comprobar y borrar, no para un descarte manual expresamente confirmado.

Consultar el registro no significa comprobar en directo YouTube. Sin cuota se
conserva la ultima confirmacion; no se inventa una nueva ni se interpreta la
falta de conexion como un video borrado.

Una vez confirmado Subido, no se vuelve a consultar por el arranque, la recarga
de carpeta o el temporizador. La marca persistente conserva el ID y la identidad
local; solo se sigue consultando el procesamiento de los intentos no confirmados.
Esto tambien significa que borrar un video desde YouTube Studio no se detecta
automaticamente para un archivo ya confirmado. La limpieza por antiguedad y
Comprobar y borrar hacen una comprobacion nueva y conservan el archivo si ya no
aparece en el canal. Borrar de todos modos es una excepcion manual, con advertencia:
no consulta YouTube y puede eliminar la unica copia del archivo.

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

## Correspondencia confirmada por el usuario

Ahora permite abrir el archivo local y el enlace de YouTube, corregir el enlace
y declarar que se ha comprobado el mismo video completo y del propio canal.
Se guarda **Subido (manual)** en una tabla independiente con firma, ID, huella
local completa, tamaño, canal declarado y fecha. No se consulta la API para esta
decision y no se afirma que Google haya comprobado la identidad o el procesamiento.

La comparacion es guiada: reproduccion local y candidato de YouTube integrados en
la misma ventana, y decision explicita Si/No. El navegador real alojado reutiliza
el perfil exclusivo abierto desde Ajustes > Reproduccion > Gestionar sesion.
El usuario debe iniciar sesion con la cuenta que tiene acceso al privado.
No se copian cookies del perfil personal ni se lee su contenido desde Python.
Hay alternativa externa si YouTube restringe la insercion.
El reproductor no recibe credenciales OAuth ni cambia la privacidad. Reproducir
no confirma automaticamente la correspondencia. Un rechazo se guarda por firma local e ID;
ese ID se excluye de las futuras asociaciones para el mismo archivo. Rechazarlo
no borra videos remotos ni crea recibos. Subir como nuevo requiere una eleccion
adicional: permite un solo intento, no un bucle, y conserva los controles de cuota.

La marca impide repetir la subida de ese archivo sin cambios, pero no genera
un recibo de transferencia y `verify_local_file` no la acepta como prueba remota.
Los registros manuales se excluyen de la limpieza automatica y por antiguedad.
Solo una comprobacion tecnica posterior con pruebas reales y estado procesado
puede convertirlos en Subido automatico. La confirmacion manual nunca rebaja una
confirmacion automatica existente ni sustituye sus recibos.

El guardado rechaza un archivo cambiado durante la comparacion o el calculo de
huella y un ID ya asignado a otro archivo presente de contenido diferente.
La asociacion manual sigue siendo una decision humana, no una comparacion de
bytes con el video remoto. El borrado local sin comprobar exige otra confirmacion.

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

Los IDs conocidos se consultan directamente por lotes de hasta 50, sin descargar
el canal entero. Se comparte una cache de 60 segundos entre interfaz y servicio;
las busquedas completas, solo necesarias para recuperar identidades desconocidas,
pueden reutilizarse durante cinco minutos. Leer la cache no prolonga su vigencia.
Las comprobaciones para borrar archivos omiten estas caches.

Los casos Por verificar no se revisan continuamente en modo automatico: necesitan
revision o un reintento explicito. Nunca se convierten en Subidos solo para ahorrar
cuota. Si no hay candidatos, el temporizador no consulta el canal.

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
| Revisar | Video corto o de duracion desconocida pendiente de autorizacion para subir. |
| En curso | Transferencia activa o archivo recibido que aun se procesa. |
| Subido | Correspondencia y procesamiento confirmados; se conserva en el registro. |
| Subido (manual) | Correspondencia declarada por el usuario; no sirve como prueba para limpieza automatica. |
| En espera | Una restriccion de cuota impide el siguiente intento. No es un archivo defectuoso. |
| Por verificar | Hay un candidato, pero faltan pruebas para vincularlo con seguridad. |
| Incidencia | Hay un fallo concreto o una discrepancia que necesita revision. |

Los registros antiguos sin pruebas suficientes no se convierten automaticamente
en recibos nuevos. No es posible reconstruir retroactivamente el ID que devolvio
una transferencia si esa informacion no se guardo de forma fiable.

## Intentos sin confirmacion

Cada transferencia reserva de forma atomica un intento antes de iniciarse. Si
falla, se cancela o se interrumpe el proceso, el registro impide empezar otra
transferencia automaticamente. Incluso si una comprobacion no encuentra el ID
remoto, no se libera esa reserva: el usuario debe revisar y pulsar Reintentar.
La autorizacion manual permite un unico intento adicional, no un bucle de intentos.
Al arrancar se conservan tambien las protecciones de intentos antiguos.

Se permiten reintentos acotados de bloques dentro de la misma sesion resumible.
Un rechazo de cuota anterior a crear la sesion puede reanudarse tras la pausa
global, pero no se aplica esa excepcion si ya habia una sesion parcial o si no
se sabe que ocurrio. Los resultados nuevos se guardan junto al intento local;
los antiguos siguen sin resultado reconstruible. No son una medida de cuota real.

En la limpieza por antiguedad y Comprobar y borrar se consulta YouTube, se comprueba
el contenido y el estado final y se verifica que el archivo local no haya cambiado.
La copia local del canal y el historial no sustituyen esa comprobacion.

La papelera permite elegir Borrar de todos modos tras aceptar el riesgo de perder
la unica copia. Esta accion y la limpieza manual de videos cortos no consultan la
API ni eliminan videos del canal. Pausan las siguientes subidas, esperan a que la
operacion activa libere el archivo y verifican su firma y estabilidad antes de borrarlo.
