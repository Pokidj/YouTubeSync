# Archivo historico

**Español** | [English](README.en.md)

`youtube-sync-legacy` conserva la aplicacion anterior por referencia historica.
No forma parte del desarrollo activo ni de las compilaciones de YouTubeSync.

El unico proyecto activo esta en `outputs/youtube-sync-modern`. La aplicacion
moderna incluye su propio motor y no importa codigo de este archivo.

Para abrir la version actual utiliza `Abrir-YouTubeSync.cmd` en la raiz.

`local-data` conserva exclusivamente respaldos locales recuperados al limpiar
pruebas antiguas. Puede contener tokens o datos de un perfil de navegador: no
debe publicarse, importarse automaticamente ni confundirse con los datos activos
de `%APPDATA%\YouTubeSync`. Esta carpeta esta excluida de Git.

Se conserva la distribucion historica de `youtube-sync-legacy`; su entorno Python
y sus caches de compilacion pueden regenerarse con su script de build.
