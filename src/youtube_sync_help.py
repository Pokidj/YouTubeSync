"""Descriptive hover help, including controls created after startup."""

import re
import unicodedata

from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import QAbstractButton, QCheckBox, QMenu
from youtube_sync_i18n import source_text, t


def help_key(text: str) -> str:
    text = "".join(char for char in unicodedata.normalize("NFKD", text) if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", text.replace("&", "").replace("...", "").replace("…", "").strip().casefold())


HELP = {}


def register(names: str, description: str):
    for name in names.split("|"):
        HELP[help_key(name)] = description


register("ON|Auto ON|Automatizacion activa", "Desactiva Auto y solicita detener la transferencia actual; los archivos locales se conservan.")
register("OFF|Auto OFF|Automatizacion parada", "Activa la vigilancia de la carpeta y la subida de pendientes autorizados.")
register("Subir pendientes", "Activa Auto y solicita la subida de los archivos pendientes; los cortos requieren revisión.")
register("Subir|Subir seleccionado|Autorizar y subir", "Solicita una subida del archivo seleccionado; no borra el archivo local ni elimina vídeos del canal.")
register("Cancelar subida|Cancelar subida actual", "Solicita detener la transferencia actual y deja Auto en OFF; puede esperar al bloque en curso.")
register("Actualizar|Comprobar|Reintentar conexion|Comprobar con YouTube", "Recarga la información y comprueba la conexión con YouTube; puede consumir cuota API.")
register("Actualizar carpeta", "Vuelve a leer la carpeta local y actualiza la tabla sin consultar todo el canal.")
register("Ajustes", "Abre la configuración de carpeta, cuenta, automatización, limpieza y columnas.")
register("Carpeta|Elegir carpeta", "Abre los ajustes de la carpeta local para elegir o corregir su ubicación.")
register("Videos|Vídeos|En mi equipo", "Abre la biblioteca local y selecciona el archivo que requiere atención.")
register("Activar API", "Abre YouTube Data API en Google Cloud para habilitarla en tu proyecto.")
register("Reintentar|Reintentar video", "Autoriza un nuevo intento para este archivo, conservando las comprobaciones previas a la subida.")
register("Abrir local|Ver local", "Abre el archivo seleccionado con el reproductor asociado de Windows.")
register("Borrar archivo local|Borrar local", "Muestra las opciones de borrado local y advierte si no hay una subida confirmada.")
register("Borrar de todos modos", "Borra permanentemente la copia local sin comprobar YouTube; podrías perder la única copia.")
register("Comprobar y borrar", "Comprueba identidad y procesamiento en YouTube antes de borrar la copia local; necesita API.")
register("Borrar archivos locales", "Confirma el borrado permanente del listado local; no borra nada del canal.")
register("Limpieza|Opciones de limpieza local", "Ofrece limpieza por antigüedad y eliminación manual de vídeos de menos de 30 segundos.")
register("Según tiempo de conservación", "Busca copias locales ya subidas cuyo plazo de conservación se ha cumplido y verifica YouTube antes de borrarlas.")
register("Vídeos de menos de 30 segundos", "Revisa la duración de los archivos locales y muestra los cortos antes de pedir permiso para borrarlos.")
register("Ver YouTube|Ver en YouTube|YouTube|Abrir en YouTube", "Abre el vídeo de YouTube en el navegador; los privados necesitan una sesión con permisos.")
register("Reproducir", "Reproduce el vídeo seleccionado dentro del panel del canal con la sesión de reproducción de YouTubeSync.")
register("Abrir reproductor en ventana", "Mueve el mismo reproductor a una ventana independiente que puedes ampliar a pantalla completa.")
register("Reproducir a pantalla completa", "Abre el reproductor a pantalla completa con sus controles; reproducir en el panel no cambia de vista.")
register("Revisar acceso en Ajustes", "Abre Ajustes en Reproducción para revisar la cuenta y sus permisos de acceso al vídeo.")
register("Volver al panel", "Devuelve el reproductor al panel del canal sin iniciar una segunda reproducción.")
register("Detener reproducción", "Detiene el vídeo y cierra su reproductor, sin dejar audio reproduciéndose en segundo plano.")
register("Pantalla completa|Salir de pantalla completa", "Abre la pantalla completa; Escape o salir devuelve el vídeo al panel sin abrir una ventana pequeña.")
register("Retroceder 10 segundos", "Retrocede diez segundos dentro del vídeo que se está reproduciendo.")
register("Avanzar 10 segundos", "Avanza diez segundos dentro del vídeo que se está reproduciendo.")
register("Pausar vídeo", "Pausa el vídeo actual sin cerrar el reproductor ni perder su posición.")
register("Reanudar vídeo", "Continúa la reproducción desde la posición actual del vídeo.")
register("Silenciar vídeo", "Silencia solo este vídeo; no cambia el volumen de Windows.")
register("Activar sonido del vídeo", "Recupera el sonido del vídeo con el volumen elegido.")
register("Sesión de reproducción", "Abre la sesión de YouTubeSync para iniciar sesión con una cuenta autorizada a ver el vídeo privado.")
register("Abrir YouTube", "Abre la página de YouTube en el navegador predeterminado con tu sesión habitual.")
register("Abrir", "Abre el vídeo seleccionado de tu canal en el navegador predeterminado.")
register("Cargar canal", "Obtiene los vídeos y listas del canal; puede usar la copia guardada cuando no hay cuota.")
register("Compartir", "Prepara el enlace para compartir el vídeo; puede cambiarlo a Oculto tras la confirmación.")
register("Compartir desde aquí", "Permite elegir si el enlace empieza en la posición actual; cambia el vídeo a Oculto tras confirmar.")
register("Restaurar columnas de Canal", "Restaura las columnas iniciales de Canal sin cambiar los datos de YouTube.")
register("Restaurar columnas de esta tabla", "Restaura las columnas de esta tabla sin cambiar los vídeos ni su color de selección.")
register("Subtítulos", "Activa o desactiva los subtítulos disponibles para este vídeo.")
register("Cambiar lista", "Elige la lista de reproducción del vídeo seleccionado y confirma el cambio.")
register("Privacidad", "Permite elegir Público, Oculto o Privado para los vídeos seleccionados del canal.")
register("Duplicados", "Busca posibles duplicados del canal comparando los datos disponibles; no elimina ninguno.")
register("Borrar", "Pide confirmación para eliminar los vídeos seleccionados del canal de YouTube.")
register("Mover a lista|Cambiar lista de seleccionados", "Cambia la lista de reproducción de los vídeos seleccionados del canal.")
register("Cuota API|Ver cuota", "Abre Google Cloud con las cuotas oficiales del proyecto; no reinicia ni amplía los límites.")
register("Límites del canal", "Explica la diferencia entre el límite de subidas del canal y la cuota del proyecto API.")
register("YouTube Studio", "Abre YouTube Studio para gestionar el canal y consultar sus avisos.")
register("Solicitar ampliacion|Solicitar ampliación", "Abre la solicitud oficial de ampliación de cuota API; no cambia el límite desde la app.")
register("Ayuda oficial", "Abre la documentación de YouTube sobre el límite de subidas del canal.")
register("Confirmar coincidencia|Editar confirmación|Asignar enlace|Vincular YouTube", "Inicia la comparación guiada entre el archivo local y su candidato de YouTube.")
register("Comprobar este vídeo|Comprobar con API", "Consulta solo este ID y busca pruebas técnicas de correspondencia y procesamiento; usa cuota API.")
register("Revisar|Revisar video|Revisar videos", "Muestra el archivo que necesita una decisión y sus opciones de revisión.")
register("Aviso anterior", "Vuelve al aviso anterior sin cambiar los estados de los vídeos.")
register("Siguiente aviso", "Avanza al siguiente aviso; conserva tu elección durante las recargas.")
register("Copiar detalle", "Copia el detalle de este aviso ocultando las credenciales reconocibles.")
register("Consola", "Abre el diagnóstico con búsqueda, filtros y opciones para copiar o exportar los errores.")
register("Copiar informe|Copiar todo", "Copia el informe de diagnóstico con los secretos reconocibles ocultos.")
register("Copiar errores|Copiar avisos y errores", "Copia los avisos y errores del diagnóstico ocultando credenciales reconocibles.")
register("Exportar|Exportar informe|Guardar informe", "Guarda el diagnóstico en un archivo de texto UTF-8 con secretos reconocibles ocultos.")
register("Limpiar|Limpiar consola|Limpiar registro temporal", "Vacía la vista de diagnóstico; no borra vídeos ni confirmaciones de subida.")
register("Guardar", "Guarda los cambios de esta ventana y los aplica a la aplicación.")
register("Cancelar|Cancel|No|Más tarde", "Cancela o aplaza esta decisión sin confirmarla.")
register("Cerrar|Close", "Cierra esta ventana sin cerrar toda la aplicación.")
register("OK|Aceptar|Sí|Yes", "Confirma la acción descrita en esta ventana.")
register("Salir", "Pide confirmación para cerrar YouTubeSync por completo y detener su servicio.")
register("Mostrar", "Recupera la ventana de YouTubeSync desde la bandeja del sistema.")
register("Elegir", "Abre el selector del archivo o carpeta correspondiente a este ajuste.")
register("Predeterminadas", "Restaura las columnas Archivo, Tamaño, Creado y Estado en su orden inicial.")
register("Mover columna arriba|Mover columna abajo", "Cambia la posición de la columna seleccionada en la biblioteca.")
register("Buscar actualizaciones", "Consulta las versiones publicadas en GitHub; no instala nada automáticamente.")
register("Descargar", "Descarga la actualización seleccionada desde la publicación de GitHub.")
register("Instalar actualización", "Verifica el instalador, pide confirmación y cierra YouTubeSync para actualizar y volver a abrirlo conservando tus datos.")
register("Notas", "Abre las notas de la versión seleccionada para revisar sus cambios.")
register("Abrir carpeta", "Abre en el Explorador de Windows la carpeta correspondiente.")
register("Abrir carpeta configurada", "Abre en el Explorador la carpeta elegida en Ajustes, aunque tengas otro archivo seleccionado.")
register("Opciones generales", "Abre los avisos y las opciones generales de conexión, cuota y diagnóstico; no realiza subidas ni borra archivos por sí solo.")
register("Mostrar archivo en Windows", "Abre el Explorador y resalta el archivo seleccionado en la tabla.")
register("Mostrar vista previa", "Muestra el vídeo seleccionado y sus controles en el panel lateral, sin iniciar la reproducción.")
register("Ocultar vista previa", "Oculta el panel lateral y detiene su reproducción, conservando la fila seleccionada.")
register("GitHub", "Abre el repositorio oficial de YouTubeSync en el navegador.")
register("Conectar mi canal|Conectar canal", "Abre el asistente para importar tus credenciales y autorizar tu canal con Google.")
register("Ya tengo mi JSON OAuth|Seleccionar JSON de escritorio", "Selecciona las credenciales OAuth de escritorio de tu proyecto de Google Cloud.")
register("Elegir otra cuenta", "Vuelve a la autorización de Google para seleccionar otro canal o cuenta.")
register("Cargar listas", "Consulta las listas de reproducción del canal autorizado; puede consumir cuota API.")
register("Crear lista", "Solicita el nombre y crea una lista de reproducción en el canal autorizado.")
register("Configurar mas tarde", "Cierra el asistente sin completar la conexión ni iniciar nuevas subidas.")
register("Anterior|Volver", "Vuelve al paso anterior sin confirmar la decisión final.")
register("Siguiente|Continuar", "Avanza al siguiente paso del asistente.")
register("Conectar con Google|Autorizar con Google", "Abre la autorización oficial en el navegador; la contraseña no se escribe en YouTubeSync.")
register("Configurar carpeta", "Continúa con la carpeta local y las opciones de subida del canal que acabas de autorizar.")
register("Guardar y finalizar|Finalizar", "Guarda la conexión y las opciones elegidas al completar el asistente.")
register("Abrir Google Cloud", "Abre Google Cloud para crear o seleccionar tu proyecto personal.")
register("Abrir YouTube Data API v3", "Abre la API de YouTube en Google Cloud para habilitarla en tu proyecto.")
register("Abrir Credenciales|Audiencia y usuarios de prueba", "Abre la configuración oficial de Google Cloud para preparar el acceso OAuth.")
register("Show Details|Ver archivos", "Despliega el listado completo de archivos afectados por esta confirmación.")
register("Hide Details|Ocultar archivos", "Recoge el listado de archivos sin cambiar la decisión de borrado.")
register("Reproducir local", "Inicia o reanuda el archivo local en el reproductor integrado.")
register("Pausar local", "Pausa la reproducción local y conserva su posición.")
register("Silenciar|Activar sonido", "Activa o silencia el sonido del reproductor local.")
register("Ver local fuera", "Abre el archivo en el reproductor de Windows si la vista integrada no puede reproducirlo.")
register("Siguiente: YouTube", "Pausa el vídeo local y carga el candidato de YouTube dentro de esta ventana.")
register("Reproducir YouTube aquí", "Carga de nuevo el candidato de YouTube en el reproductor de esta ventana.")
register("Gestionar sesión|Gestionar sesión de reproducción", "Abre Chrome o Edge con el perfil exclusivo de YouTubeSync para iniciar sesión o cambiar de cuenta. No cambia la conexión OAuth ni la privacidad.")
register("Abrir YouTube en navegador", "Detiene el reproductor integrado y abre el candidato en el navegador con tu sesión y sus permisos.")
register("Ya lo he revisado", "Pasa a decidir si el vídeo de YouTube corresponde al archivo local.")
register("Sí, corresponde", "Confirma que ambos vídeos completos coinciden y son de tu canal; se guardará una marca manual.")
register("No, es otro vídeo", "Descarta esta correspondencia y ofrece conservar el archivo pendiente o solicitar una nueva subida.")
register("Subir como vídeo nuevo", "Guarda que no coinciden y solicita una nueva subida local; no elimina el candidato de YouTube.")
register("Guardar sin subir", "Recuerda que ese candidato no corresponde y conserva el archivo pendiente sin iniciar una subida.")
register("Clear|Borrar texto", "Vacía el texto de este campo.")
register("Scroll Left|Desplazar hacia la izquierda", "Desplaza las pestañas hacia la izquierda para ver las anteriores.")
register("Scroll Right|Desplazar hacia la derecha", "Desplaza las pestañas hacia la derecha para ver las siguientes.")


def describe_control(control) -> str:
    previous = control.property("automaticHelp")
    tooltip = control.property("sourceToolTip") or control.toolTip()
    name = control.property("sourceAccessibleName") or getattr(control, "accessibleName", lambda: "")()
    text = source_text(control)
    candidates = [tooltip if tooltip != previous else "", name, text]
    for candidate in candidates:
        key = help_key(candidate)
        if key in HELP:
            return HELP[key]
        if key.startswith("siguiente aviso /"):
            return HELP[help_key("Siguiente aviso")]
        if key.startswith("descargar "):
            return HELP[help_key("Descargar")]
    if tooltip and tooltip != previous:
        return tooltip
    if isinstance(control, QCheckBox) and text:
        return f"Activa o desactiva esta opción: {text}."
    return tooltip or (f"Ejecuta la acción «{text or name}» de esta ventana." if text or name else "")


class ButtonHelp(QObject):
    def apply(self, control):
        description = describe_control(control)
        if description:
            control.setToolTip(t(description))
            control.setProperty("sourceToolTip", description)
            control.setProperty("automaticHelp", description)
            if isinstance(control, QAbstractButton):
                control.setAccessibleDescription(t(description))

    def refresh(self, root):
        for button in root.findChildren(QAbstractButton):
            self.apply(button)

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.Show, QEvent.ToolTip):
            if isinstance(watched, QAbstractButton):
                self.apply(watched)
            elif isinstance(watched, QMenu):
                watched.setToolTipsVisible(True)
                for action in watched.actions():
                    if not action.isSeparator():
                        self.apply(action)
        return False


def install_button_help(app):
    helper = getattr(app, "_youtube_sync_button_help", None)
    if helper is None:
        helper = ButtonHelp(app)
        app._youtube_sync_button_help = helper
        app.installEventFilter(helper)
    return helper
