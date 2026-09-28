# V17.2 — correcciones para poder evaluar la interfaz

## Fallos comprobados y correcciones

- El observador del tema claro quitaba una clase de la raíz incluso si no estaba presente. Esa operación puede emitir otra mutación y volver a invocar el mismo observador. La prueba JavaScript reproduce el ciclo con V17.1 y verifica que V17.2 se estabiliza después de retirar la clase.
- La navegación escuchaba `change`, incluyendo actualizaciones programáticas. Parámetros quitaba la selección principal; esa actualización podía activar la navegación con valor vacío y ocultar todos los módulos. Los controles de navegación ahora escuchan sólo entrada del usuario y sus rutas directas actualizan todos los ancestros.
- La navegación funciona fuera de la cola de operaciones. Al cambiar de módulo se cierra Herramientas, evitando que su panel anterior tape el destino. El encabezado deja de superponerse a controles al desplazar la página.
- Las filas de materiales con flecha eran decorativas. Ahora son desplegables HTML nativos con su ficha completa; no necesitan una petición para abrirse. El selector tiene un valor inicial y el botón + abre el formulario. Filtrar actualiza lista, selección y ficha juntos.
- Los callbacks de consulta no abren una transacción de escritura del taller. La persistencia transaccional de comandos se conserva.

## Herramientas disponibles

Moles ↔ gramos (masa molar de óxidos o ingresada), UMF desde análisis en masa de óxidos, contracción lineal, absorción, escalado proporcional y relación agua/yeso. Se explican unidades, fórmula y límites, y se rechazan datos ausentes o divisiones por cero. Calcular no cambia datos ni descuenta stock.

UMF declara los óxidos incluidos en su base de fundentes; boro y colorantes quedan fuera de esa base. No convierte automáticamente una receta por temperatura. Cargar un material sin análisis genera un aviso y no inventa su composición.

La referencia de elementos incluye los 118 nombres, símbolos y números atómicos, búsqueda y fichas desplegables. Es un catálogo ordenado, todavía no una cuadrícula clásica por grupos y períodos. Hay masas de cálculo para los elementos usados por las calculadoras y referencias a sus óxidos; las fichas cerámicas ampliadas se incorporan progresivamente.

Adaptar automáticamente por temperatura continúa pendiente y se identifica como tal. La calculadora de yeso parte del peso del producto y su relación indicada por el fabricante, no del volumen del molde.

## Fuentes técnicas

- [CIAAW: pesos atómicos abreviados 2024](https://ciaaw.org/abridged-atomic-weights.htm), valores centrales redondeados para las masas de cálculo.
- [IUPAC: elementos e isótopos](https://iupac.org/iptei/).
- [Digitalfire: UMF](https://digitalfire.com/glossary/unity+formula), [sílice](https://digitalfire.com/oxide/sio2), [alúmina](https://digitalfire.com/oxide/al2o3) y [boro](https://digitalfire.com/oxide/b2o3).
- [USG No. 1 Pottery Plaster](https://www.usg.com/content/dam/USG_Marketing_Communications/united_states/product_promotional_materials/finished_assets/usg-no1-pottery-plaster-data-en-IG1366.pdf): referencia específica de proporción agua/yeso, no universal.

## Validación y límite

Pruebas del motor y navegación, simulación del ciclo de MutationObserver en JavaScript, procesamiento de transiciones a través de Gradio, desplegables y cálculos con casos conocidos/entradas inválidas; exportación y autocomprobación del archivo único. La prueba del observador usa un modelo de mutaciones DOM en Node, no un navegador real. La inspección visual de esta sesión quedó pendiente por permisos de acceso a pantalla; no se presenta como validada en Colab ni en móvil.

Usar el nuevo archivo ALUMINA_STUDIO_V17_2_NAVEGACION.py deteniendo la ejecución anterior. Conserva el formato de base SQLite de V17.1. Guardar respaldo antes de cambiar de entorno.
