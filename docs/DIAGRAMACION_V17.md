# Diagramación V17 — versión de prueba

Base recuperada del archivo entregado por Pedro, que declara `16 DEMO FIX3`.
SHA256 de la base: `3962e6a8db4161d9ee26e6281bb4217aa11855a40d923124b46af6b1ad3f4f3c`.
Decisiones: conversación «Ajustar nueva estructura», con prioridad para los acuerdos del 26/09/2026.

## Navegación implementada

- Inicio: tablero y accesos directos.
- LAB: Color Sampler, Ensayo, Formulario.
  - Ensayo: Preparación, Muestras, Resultado, Historial.
  - Formulario: guardadas, agregar fórmula manual/importada, partir de existente.
- TALLER: Bitácora, Estante, Operaciones.
  - Bitácora: Agenda, Historial y notas, Registro de piezas/lotes, Gastos.
  - Operaciones: Horneadas, Compras, Estadísticas.
- SABER: Portada, Aprender, Profe AI, Comunidad.
- Herramientas: calculadoras existentes, referencias de conos y editor de materiales.
- Parámetros del taller: configuración existente, unidades, horno y copias de seguridad.

La barra móvil contiene cuatro accesos: Inicio y los tres espacios de trabajo.
Los accesos directos actualizan selección y visibilidad de todos los niveles en el mismo callback.
Se conserva el esquema de datos 2 y el archivo de estado V16. Los grupos reubicados utilizan los mismos objetos y callbacks.

## Alcance y límites

Este cambio reorganiza la base recibida. No implementa toda la arquitectura conceptual.
Gastos unificados, estadísticas completas, tabla periódica interactiva, biblioteca didáctica,
Profe AI y Comunidad aún no existen en esta base: sus espacios lo indican expresamente.
Quedan pendientes perfiles térmicos, Stull condicionado a alta, biblioteca espectral real,
curso opcional, consumo por saldo y otras ampliaciones acordadas. No se simulan resultados.

La base conserva limitaciones previas de demo: persistencia compartida en JSON,
refresco general de controles y algunas herramientas sólo parciales.

## Ejecución y pruebas

`python run.py` abre la aplicación recuperada.
`python scripts/export_colab.py` genera un archivo independiente idéntico al código de la app.
`pytest tests/test_navigation.py -q` prueba ocho rutas con visibilidad de ancestros,
la jerarquía principal y las 13 comprobaciones internas de la base, usando datos temporales.

La suite histórica R3 sigue referenciando módulos ausentes antes de esta recuperación.
No se eliminan sus pruebas ni se inventan dichos módulos; el workflow QA original seguirá
fallando hasta completar esa migración. La validación V17 se ejecuta por separado.
La inspección visual automatizada no pudo realizarse porque el navegador no pudo verificar
su política de acceso. La aceptación táctil final en Colab/teléfono queda pendiente.
