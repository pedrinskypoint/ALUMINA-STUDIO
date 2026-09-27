# V17.3 — un toque, una acción

## Presentación

Se eliminó `refresh_dynamic()`. Cada callback declara sus componentes de salida y sólo solicita los renderizadores correspondientes. Una nota devuelve contexto de sesión y bitácora; stock devuelve mensaje y vista de stock; una nueva fórmula actualiza sus selectores. No se construye una tupla universal de 27 controles ni se compara todo el taller para decidir qué pintar. Los renderizadores compartidos se ejecutan una vez por acción.

Inicio se recalcula cuando el usuario lo abre. La carga inicial y el reemplazo explícito por importación/restauración son las únicas operaciones que refrescan el conjunto de vistas. El registro de revisiones de sesión sigue detectando cambios no vistos de otras sesiones.

Recepciones, consumos y reversiones actualizan también los campos de stock afectados que estén abiertos. Los cambios indirectos de horno/resultado no autorizan que una ficha de muestra vieja los sobrescriba: el botón «Recargar ficha» actualiza sus campos y su revisión juntos. Stock incorpora la misma recarga explícita para conflictos entre sesiones.

## Lecturas y escrituras

Los callbacks usan `EntityState` y `EntityMap` de `Repository`. Acceder a una ficha lee esa fila, no todas las colecciones. Enumerar una colección solicita expresamente sus registros. El contexto de transacción conserva los JSON originales sólo de las filas leídas, compara esas filas y escribe únicamente los cambios. Se eliminaron los `copy.deepcopy(st)` del código de interfaz.

Las copias por entidad (por ejemplo, crear una fórmula derivada) se conservan. El modo completo `Snapshot` permanece para carga inicial, compatibilidad de llamadas externas y respaldo: su uso no forma parte de los callbacks ordinarios. Los registros históricos que todavía están representados como listas, incluida la bitácora, se leen como una unidad; su separación futura en filas es un límite conocido.

Las escrituras continúan dentro de `BEGIN IMMEDIATE` y se devuelve éxito sólo después del commit. Un conflicto o error provoca rollback. No se crearon tareas de escritura en background ni confirmaciones optimistas. `gr.State` contiene revisiones/contexto de interfaz, no una copia persistente del taller.

## Búsqueda y comparación

SQLite FTS5 indexa fórmulas, ensayos, muestras, stock, pedidos y proyectos. La primera apertura migra el índice existente; triggers lo mantienen en la misma transacción de cada inserción, cambio y borrado. La búsqueda usa palabras/prefijos, ignora acentos y limita a 30 resultados. No es una búsqueda por cualquier fragmento interior de palabra ni un índice propio en memoria.

Las fórmulas candidatas se filtran en SQL por vehículo, atmósfera, temperatura dentro del margen elegido, pasta y perfil si se definió. Los índices de expresiones soportan vehículo/atmósfera/temperatura y perfil. Los datos desconocidos no satisfacen un filtro seleccionado. El perfil se guarda explícitamente en nuevas fórmulas digitales; no se inventa retrospectivamente para datos antiguos. Estos filtros sirven para seleccionar candidatos, no garantizan comportamiento cerámico.

La comparación posterior usa CIEDE2000 tanto en coincidencias internas como externas. Se corrigió el defecto anterior: la búsqueda calculaba ΔE76 aunque la etiqueta decía ΔE00. Los resultados guardados ya usaban CIEDE2000 y lo conservan. Se comprueba el par de referencia con resultado 2.0425 y que los candidatos descartados no llegan al cálculo perceptual.

## WAL

WAL es opcional mediante `ALUMINA_SQLITE_WAL=1` antes de abrir una base en disco local. El modo de una base ya convertida persiste en SQLite. No se activa automáticamente sobre Drive montado o carpetas sincronizadas. Se mantiene `synchronous=FULL`; no se difieren las escrituras importantes. Los checkpoints quedan a cargo de SQLite.

Referencias: [SQLite WAL](https://sqlite.org/wal.html), [SQLite FTS5](https://sqlite.org/fts5.html). La base debe seguir respaldándose desde la app; copiar sólo el archivo SQLite mientras está en uso no sustituye el respaldo.

## Verificación

Las pruebas comprueban que una nota sólo lee la fila de bitácora, prohíben una lectura/copia global durante ese callback, verifican cambios por entidad, rollback tras fallar una escritura, actualización/borrado atómico del índice, filtros previos al color, uso del índice SQL, ΔE00 interno/externo y WAL explícito con confirmación durable. Se conservan las pruebas de navegación, herramientas, persistencia y concurrencia.

La validación visual/táctil real en Colab sigue pendiente; estas pruebas no la reemplazan. El QA histórico R3 continúa separado por módulos ausentes.
