# V17.1 — saneamiento del motor

## Persistencia

- SQLite es la fuente de verdad operativa. La migración inicial lee el JSON V16 sin modificarlo; un JSON inválido detiene la migración.
- La transición es progresiva: entidades con ID único en filas SQLite, con contenido JSON y revisión por entidad. Todavía no hay tablas relacionales especializadas ni índice FTS.
- Cada comando lee datos vigentes dentro de una transacción. Se conservan cambios independientes; modificar un registro desactualizado se rechaza con aviso para recargar. `gr.State` conserva metadatos de revisión y datos de interfaz, no el taller completo.
- Fotos y documentos se copian a `media/` con UUID. Las fotos temporales antiguas que ya no existen quedan advertidas; no se pueden reconstruir.
- La copia ZIP incluye datos y medios. Importar o reiniciar exige confirmación visible y genera una copia previa. Las copias deben descargarse para sobrevivir al cierre de Colab.
- Las transacciones protegen sesiones conectadas a la misma base local; no garantizan sincronización entre entornos Colab ni sobre Drive montado.

## Stock y fórmulas

- Ajustes, recepciones y consumos generan movimientos con saldo anterior/posterior, referencia, fecha y motivo. Corregir una recepción aplica la diferencia, positiva o negativa. Repetirla sin cambios no vuelve a sumar.
- Se pueden revertir movimientos una vez. Las recepciones se corrigen desde su pedido. No se permiten saldos negativos.
- El consumo explícito exige una referencia existente. Una estimación exige aceptación; planificar no descuenta stock. El identificador de confirmación impide repetir el mismo consumo.
- Normalizar muestra una composición calculada sin alterar lo ingresado. Guardar normalización o duplicar crea una fórmula derivada enlazada a la original. Los asistentes completos de adaptación a stock/temperatura siguen pendientes.

## Proceso y horno

- Las muestras incorporan fotos de proceso y pesos húmedo, seco, bizcocho y final. Se calculan variaciones en gramos y porcentaje; peso inicial cero produce porcentaje indefinido. Estos datos no se presentan como reología.
- Fin del programa, enfriamiento, apertura, descarga y finalización son transiciones distintas. La apertura requiere temperatura ingresada expresamente y dentro del límite configurado. No es medición automática ni certificación de seguridad.
- No se usa una curva universal de enfriamiento. Con al menos tres registros comparables del mismo horno/programa se muestra el rango histórico entre fin y apertura; incluye la espera del operador y no garantiza cuándo abrir.
- Una hornada no puede completarse dos veces ni incrementar dos veces las cocciones de la muestra.
- Resultado de color usa CIEDE2000; sin objetivo no informa una diferencia cero ficticia. Los resultados anteriores conservan su identificación histórica.

## Interfaz y pendientes

Se mantiene LAB / TALLER / SABER. El refresco conserva las firmas de compatibilidad pero calcula sólo los grupos afectados y omite salidas ajenas a la acción; aún falta separar por completo los controladores de presentación. La carga de datos para lectura sigue siendo global.

No están terminados la arquitectura conceptual completa, registro general de piezas/lotes, gastos y estadísticas integrales, biblioteca espectral, enseñanza, Profe AI o Comunidad. El buscador no recibió un índice nuevo. La revisión visual/táctil en Colab queda para la devolución de Pedro.

Las pruebas cubren conflictos entre sesiones, creación simultánea, transacciones fallidas, migración, imágenes fuera de temporales, respaldo/restauración, stock, fórmulas, pesos, horno, cálculo de color y navegación. La suite R3 histórica permanece separada por sus módulos ausentes.
