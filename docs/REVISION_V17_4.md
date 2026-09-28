# V17.4 — correcciones de la revisión funcional

Entrega basada en V17.3, después de revisar las demos de Colab el 27/09/2026. El nuevo enlace comunicado por el usuario, `https://1983f7c202c82ac6fa.gradio.live`, todavía ejecutaba V17.3 al comprobarlo. Cambiar el código del repositorio no actualiza por sí solo el proceso de Colab.

## Ejecutar la entrega

Generar con `python scripts/export_colab.py`. El archivo autónomo es `build/ALUMINA_STUDIO_V17_4_REVISION.py`. En Colab, instalar las versiones de `requirements.txt` y ejecutar `%run ALUMINA_STUDIO_V17_4_REVISION.py`. La cabecera muestra versión de ALUMINA y Gradio para identificar qué entrega está corriendo.

Guardar antes una copia del taller y sus fotos; no restaurar DEMO sobre datos propios. La estructura operativa continúa en SQLite y los archivos en media/. No se cambia la base de datos del enlace remoto durante esta entrega.

## Cambios por hallazgo

| Informe | Entrega y límite |
|---|---|
| R01 | Las calculadoras limpian el resultado ante cambios/errores y muestran el motivo junto al cálculo. Resultados iniciales vacíos. |
| R02 | Se elimina la etiqueta de compatibilidad técnica total: se explicitan temperatura/atmósfera/pasta y diferencias de óptica, superficie y base. CIEDE2000 conserva sus pruebas. |
| R03 | Crear un ensayo tiene sección y botón propios. Agua y notas del seleccionado se editan aparte y no se copian inadvertidamente al nuevo ensayo. |
| R04 | Sigue pendiente atribuir la desconexión de Colab: hacen falta sus registros. Se conserva el enrutamiento específico y sus pruebas; se registran rechazos de operaciones en el servidor. No se afirma recuperación automática ni conservación de borradores tras caída. |
| R05 | Resultados seleccionables abren fórmula, ensayo, muestra, stock o pedido y conservan la consulta. Proyectos abre Registro con el árbol productivo; no existe aún editor individual de proyecto. |
| R06 | Una ficha activa de material controlada por un selector único; el listado paralelo de desplegables deja de mostrarse. |
| R07 | Análisis ausente se expresa como “Sin datos”; LOI puede dejarse vacío al crear material. No se inventan fichas de proveedores para completar la biblioteca DEMO. |
| R08 | La pestaña se llama Elementos; búsqueda explícita por Enter y símbolos/números exactos primero. Se mantiene el catálogo, sin presentarlo como cuadrícula periódica clásica. |
| R09 | “ADN químico” pasa a hipótesis editable, con explicación de procedencia y límites del valor inicial. |
| R10 | Selector de resultado final limitado a muestras con cocciones completas; el servidor también rechaza muestras no elegibles. Tarjetas identifican muestra y resultado. |
| R11 | Se refuerzan fondos/etiquetas claros y contraste de títulos. Selectores de Gradio son explícitamente interactivos; foco de navegación accesible por teclado. Verificación visual parcial local, no certificación de accesibilidad. |
| R12 | Agenda e Inicio distinguen fechas pasadas, hoy y próximas; no se inventa un estado de finalización de eventos antiguos. |
| R13 | Referencia oficial por cono, explicación de trabajo térmico y velocidad final. Se corrige 010 regular: 891/903/915 °C; la tabla anterior mezclaba valores Iron-Free. |
| R14 | Hipótesis de pigmento agrupada en un desplegable avanzado. La reorganización completa del formulario y una acción directa desde cada coincidencia siguen siendo mejoras posteriores. |
| R15 | Bitácora admite foto persistente y miniatura. Tipo Foto exige adjunto. |
| R16 | Registro muestra relación proyecto → serie → lotes con cantidad/estado. Aún no hay un historial completo por pieza ni edición de todos sus estados. |
| R17 | Lectura real inicialmente vacía; se rechaza la ausencia en servidor. Cambiar hornada y registrar una lectura limpia el campo para evitar reutilización inadvertida. |
| R18 | Acciones del horno se habilitan según el estado seleccionado; los datos históricos incompletos se identifican sin inventar fechas. |
| R19 | Consumo y reversión seleccionan registros por nombre/ID; historial traduce tipos y muestra unidades, fecha y saldo disponible. Actualizar movimientos refresca las opciones. |
| R20 | Recepción explicita cantidades acumuladas, unidad del material y precio por presentación; moneda desconocida se marca como no registrada. Vista previa de diferencias de stock sin guardar. No se añade un motor de conversiones monetarias. |
| R21 | Destinos incompletos marcados como pendientes/parciales antes de entrar. No se simula Profe AI, Comunidad, biblioteca editorial ni balance de costos. |
| R22 | Respaldo explica entidades + media; ZIP incorpora manifiesto con fecha, versión y esquema. Importación acepta manifiesto y copias previas. Resumen interactivo de importación y fecha del último respaldo todavía pendientes. |

## Validación

Suite específica del motor/UI más regresiones del informe: 56 pruebas aprobadas: 55 en la suite y la prueba del observador del tema ejecutada por separado con Node explícito. Se incluyen transacciones, conflictos, corrección de recepción, idempotencia, reversión, medios fuera del temporal original y recuperación ZIP, normalización no destructiva, referencias CIEDE2000 y navegación. No equivale a un ensayo de varias instancias SQLite sincronizadas por Drive.

El archivo autónomo pasa sus 13 autocomprobaciones. Prueba visual local inicial: búsqueda `caolin` → ficha de stock correcta, conservación de consulta y vista a 390 × 844. El contraste de etiquetas se ajustó adicionalmente tras esa inspección. No se midieron percentiles de rendimiento ni se ensayó una caída real de Colab con esta entrega.

Fuentes de conos consultadas: [010 regular](https://www.ortonceramic.com/product-page/010-self-supporting-25-box), [06 regular](https://www.ortonceramic.com/product-page/06-self-supporting-25-box), [04 regular](https://www.ortonceramic.com/product-page/04-self-supporting-25-box), [02 regular](https://www.ortonceramic.com/product-page/02-self-supporting-25-box), [6 regular](https://www.ortonceramic.com/product-page/6-self-supporting-25-box), [explicación del trabajo térmico](https://www.ortonceramic.com/pyrometric-cones).

La revisión detectó tanto defectos como funciones aún no desarrolladas. Esta entrega corrige defectos y mejora los recorridos existentes; no declara terminados los 22 puntos en toda su amplitud.
