# YouTubeSync

> ARCHIVADA. Esta interfaz anterior se conserva por referencia historica.
> El desarrollo activo y las compilaciones estan en `outputs/youtube-sync-modern`.
> Usa `Abrir-YouTubeSync.cmd` en la raiz del repositorio para abrir la app actual.

Aplicacion de escritorio para Windows que vigila una carpeta local de videos y los sube automaticamente a YouTube.

## Lo que hace

- Vigila una carpeta configurable.
- Sube videos nuevos o pendientes a YouTube.
- Usa como titulo la fecha y hora de creacion del archivo, por ejemplo `2025-06-18 14:32:05`.
- Guarda un historial local para no subir el mismo archivo dos veces.
- Revisa tambien los videos ya existentes en YouTube por titulo antes de subir.
- Tiene asistente de configuracion la primera vez.
- Puede quedarse funcionando en segundo plano mientras la app esta abierta.
- Permite cambiar carpeta, privacidad, extensiones, intervalo de revision y espera de estabilidad.
- Muestra si esta conectado a YouTube y a que canal subira los videos.
- Permite elegir lista de reproduccion desde los nombres de tus listas de YouTube.
- Permite elegir categoria por nombre, no por numero.
- Tiene barra de progreso para la subida actual.
- Tiene modo automatico ON/OFF. Cuando esta apagado, no escanea ni sube videos.
- Incluye boton `Subir pendientes` para activar el modo automatico y lanzar la subida de lo que falte en la carpeta.
- Al apagar el modo automatico durante una subida, solicita la cancelacion al terminar el bloque actual.
- La vista principal es `Videos`, organizada en `Pendientes`, `Ya subidos` e `Incidencias`.
- Incluye un boton `Actualizar` que comprueba YouTube y fuerza la deteccion de carpeta si el modo automatico esta activo.
- Puede borrar automaticamente los archivos locales ya subidos tras X horas configurables.
- Muestra contador de videos en carpeta, subidos, pendientes e intentos de subida realizados hoy.
- Tras cada subida correcta actualiza `Carpeta`: quita el archivo de `Pendientes` y lo muestra en `Ya subidos`.
- No impone un limite diario propio. Solo pausa si YouTube devuelve un limite real de API, proyecto o canal.
- Cuando YouTube bloquea las subidas, muestra una cuenta atras persistente y realiza un reintento al terminar la ventana calculada.
- Tiene indicador verde/rojo para saber si todo funciona o si falta algo.
- Ajustes redisenados por secciones para evitar campos descuadrados.
- Incluye asistente paso a paso para crear el JSON OAuth en Google Cloud, seleccionarlo y copiarlo automaticamente a la carpeta de la app.
- Ajustes tiene scroll para pantallas pequenas.
- Puede configurarse para iniciar automaticamente con Windows.
- `Ya subidos` se calcula desde la carpeta actual, el registro permanente y la comprobacion del canal.
- El escaneo de carpetas grandes es mas ligero: no espera archivo por archivo, solo ignora videos modificados demasiado recientemente.
- La pestana `Consola` muestra mensajes tecnicos y se puede limpiar sin alterar ningun registro interno.
- Mantiene un registro permanente invisible para no volver a subir videos ya subidos u omitidos por duplicado.
- La ventana de ajustes acepta la rueda del raton para desplazarse.

## Requisitos

1. Python 3.10 o superior.
2. Un archivo OAuth de Google Cloud llamado, por ejemplo, `client_secret.json`.
3. La API de YouTube Data v3 habilitada en el proyecto de Google Cloud.

## Configurar OAuth de YouTube

1. Entra en Google Cloud Console.
2. Crea o selecciona un proyecto.
3. Habilita `YouTube Data API v3`.
4. Crea credenciales de tipo `OAuth client ID`.
5. Tipo de aplicacion: `Desktop app`.
6. Descarga el JSON de credenciales.
7. En el primer arranque de YouTubeSync, selecciona ese archivo JSON.

## Ejecutar en modo desarrollo

```powershell
cd .\youtube-sync
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\src\youtube_sync_app.py
```

## Crear el .exe

```powershell
cd .\youtube-sync
.\build_exe.ps1
```

El ejecutable queda en:

```text
dist\YouTubeSync\YouTubeSync.exe
```

Si Windows mantiene abierto el ejecutable anterior y no deja sobrescribirlo, cierra YouTubeSync desde la bandeja del sistema y vuelve a ejecutar el build. La build final queda en `dist\YouTubeSync\YouTubeSync.exe`.

## Notas

- La app debe permanecer abierta para vigilar la carpeta.
- Si minimizas la ventana, seguira trabajando y quedara disponible desde el icono de bandeja.
- La primera autenticacion abre el navegador para autorizar el acceso a YouTube.
- Configuracion, token y base de datos se guardan en `%APPDATA%\YouTubeSync`.
- La limpieza solo borra archivos locales ya marcados como subidos. No elimina videos de YouTube.
- Antes de borrar, comprueba que el archivo local no haya cambiado y valida el video contra el canal. Si existe un ID guardado debe aparecer exactamente en el canal; si falta el ID, intenta recuperarlo por titulo.
- El borrado manual muestra primero el resultado de la comprobacion y pide confirmacion. Los archivos con discrepancias siempre se conservan.
- Si la limpieza automatica encuentra una sola discrepancia, cancela todo el lote, no borra nada y solicita revision manual.
- La Consola se puede limpiar sin borrar la memoria anti-duplicados ni los estados de los videos.
- La app usa el permiso OAuth `youtube` para subir videos, leer el canal y anadir videos a listas. Si venias de una version anterior, puede pedir autorizacion otra vez para limpiar permisos antiguos.
- En Ajustes, usa `Asistente JSON` para guiar a otro usuario paso a paso. El ultimo paso selecciona el JSON descargado, lo valida, lo copia a `%APPDATA%\YouTubeSync` y rellena el campo automaticamente.
- YouTube no ofrece mediante la API un contador de subidas restantes para el canal. La app muestra intentos locales, pero nunca los usa para bloquear.
- Si YouTube envia `Retry-After`, la app usa ese tiempo. Para cuota diaria del proyecto estima la siguiente medianoche del Pacifico; para `uploadLimitExceeded` del canal muestra una estimacion conservadora de 24 horas. La cuenta atras se identifica como estimada cuando YouTube no proporciona la hora exacta.
