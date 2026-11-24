# Historial de cambios

**Español** | [English](CHANGELOG.en.md)

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
