# ALUMINA STUDIO · MATRIZ DE PARIDAD R3 DEMO → vNext

**Base auditada:** `ALUMINA_STUDIO_V14E4_CLEAN_R3_DEMO.py` · 5.759 líneas  
**Notebook de referencia:** `ALUMINA_STUDIO_V14E4_CLEAN_R3_DEMO_COLAB.ipynb`  
**Objetivo:** reestructurar sin perder funcionalidad ni decisiones ya aprobadas.  
**Regla:** R3 DEMO sigue siendo la base funcional hasta que vNext alcance paridad validada en Colab.

## Clasificación

- **CONSERVAR**: funciona y debe sobrevivir prácticamente igual.
- **ADAPTAR**: conservar núcleo/lógica, cambiar modelo, UX o conexiones.
- **MOVER**: conservar funcionalidad, cambiar de departamento/pantalla.
- **REHACER**: el concepto actual entra en conflicto con el flujo nuevo.
- **RETIRAR**: eliminar sólo porque ya fue reemplazado explícitamente.
- **NUEVO**: no existe en R3; agregar después de asegurar paridad del bloque afectado.

## Inventario real de R3

| Activo R3 | Cantidad / estado | Decisión |
|---|---:|---|
| Tabla periódica | 118 elementos | CONSERVAR |
| Catálogo maestro de materiales | 59 materiales | CONSERVAR |
| Metadatos de inventario | 59 materiales | ADAPTAR a lotes/envases |
| Familias de pigmento | 2: Cd–S–Se y Fe–Mn–Co–Cr | CONSERVAR |
| Pastas de referencia | 4 | CONSERVAR |
| Fórmulas de pasta | 4 | CONSERVAR, reubicar |
| Programas de horno | 8 | CONSERVAR |
| Proveedores precargados | 3 | ADAPTAR |
| Calculadoras | 11 | CONSERVAR |
| Demo | taller / flujo completo / hornada lista / vacío | CONSERVAR + RECONSTRUIR |
| Repository boundary | existe | CONSERVAR + USAR |
| Persistencia real | gr.State por sesión | ADAPTAR |

## Arquitectura y navegación

| R3 actual | Decisión | vNext | Regla |
|---|---|---|---|
| 10 módulos principales en Dropdown | REHACER | 5 áreas: Inicio · LAB · Taller · Operaciones · Aprender/Comunidad | No perder funciones internas |
| Cabecera estática | ADAPTAR | cabecera fija | Buscar, alertas, menú, perfil |
| Subtabs con scroll local | CONSERVAR | subtabs contextuales | Mantener |
| CSS móvil 1 columna y botones ≥44 px | CONSERVAR | base táctil | No tirar correcciones |
| Botones Actualizar por todas partes | REHACER | refresco automático | manual sólo como fallback |
| Sin buscador global | NUEVO | buscador fijo | abre objeto original |
| Estados separados en múltiples gr.State | ADAPTAR | repositorio central | fuente única de verdad |
| next_code usa max(registros)+1 | REHACER | secuencia persistente | nunca reutilizar IDs |

## Inicio

| R3 actual | Decisión | vNext |
|---|---|---|
| Cuenta ensayos, hornadas activas y alertas stock | CONSERVAR + AMPLIAR | dashboard vivo |
| Texto fijo “Flujo maestro” | RETIRAR | próxima acción contextual |
| “Actualizar resumen” | RETIRAR como requisito | auto-refresh al volver |
| Alertas stock como número | ADAPTAR | alerta accionable |
| Sin Agenda | NUEVO | Hoy / Agenda |
| Sin pedidos llega hoy / retirar | NUEVO | Compras y logística |
| Sin próxima acción | NUEVO | una acción principal priorizada |
| Sin actividad transversal | NUEVO | actividad reciente |
| Sin accesos rápidos | NUEVO | ensayo/fórmula/pieza/horno/cámara/etc. |

## LAB · Color / Pigmento / ADN / Fórmula

| R3 actual | Decisión | Cambio |
|---|---|---|
| Selector HEX | CONSERVAR | LAB · Formular |
| Foto + toma de color por zona | CONSERVAR + ADAPTAR | cámara/galería móvil |
| CIELAB / ΔE76 | CONSERVAR | similitud visual, no identificación |
| Candidatos seleccionables | CONSERVAR | tarjetas táctiles |
| 2 familias pigmento reales | CONSERVAR | expandir después |
| CdS₁₋ₓSeₓ S↔Se 0–0,60 | CONSERVAR | perfil específico |
| Fe–Mn–Co–Cr con rangos reales | CONSERVAR | mostrar min/max junto a sliders |
| FeO+MnO₂+CoO=1 | CONSERVAR | normalización |
| Conversión pigmento 25/50/100 g | CONSERVAR | mantener advertencias |
| ADN químico | CONSERVAR + ADAPTAR | elemento tocable → ficha |
| Ficha completa de elemento | CONSERVAR + CONECTAR | reutilizar desde ADN |
| Vehículos Esmalte/Engobe/Pasta coloreada | CONSERVAR | — |
| Fórmulas base por vehículo | CONSERVAR | — |
| Base de prueba 25/50 g | CONSERVAR | no confundir con batch pigmento |
| Slider % lejos de simulación | MOVER UX | unir ajuste + vista previa |
| Base óptica/pasta/temp/atmósfera | CONSERVAR | herencia futura |
| Cálculo exacto de masa | CONSERVAR | — |
| Simulación heurística | CONSERVAR | mantener etiqueta orientativa |
| Costo estimado de borrador | CONSERVAR + ADAPTAR | estimado previo |
| Fórmula en gramos | CONSERVAR | añadir procedimiento |
| No hay “Cómo preparar” | NUEVO | agua/defloculante/orden/etc. |
| Referencias/evidencia | CONSERVAR | integrar procedencia |
| Procedencia sólo local al pigmento | ADAPTAR | transversal |
| Error UX antes de candidato | BUG / REHACER ESTADO | bloques neutros/ocultos |
| Crear ensayo con receta | CONSERVAR + ADAPTAR | guardar fórmula o continuar |
| Sin biblioteca formal de fórmulas | NUEVO | Taller · Fórmulas |
| Sin revisiones de fórmula | NUEVO | FormulaRevision |

## Herramientas químicas

**CONSERVAR las 11:** Adición %, Escalar receta, Moles↔g, UMF/Seger, Line blend, Triaxial, Contracción, Absorción, Densidad de barbotina, Humedad, LOI.  
**CONSERVAR** Tabla periódica de 118 elementos, materias primas de 59 materiales y el selector que deja una sola calculadora abierta.

## Ensayos / Preparación

| R3 actual | Decisión | vNext |
|---|---|---|
| Ensayo guarda draft completo | ADAPTAR | referencia FormulaRevision |
| Código AL-xxxx | CONSERVAR formato / REHACER contador | permanente |
| Estados mezclan preparación + muestra + horno | REHACER | separar Experiment/Preparation/Sample |
| Listado/selector Ensayo | CONSERVAR + MOVER | LAB · Ensayos |
| Gramos visibles en ficha | CONSERVAR | desde entrada |
| Confirmar pesado/descontar | REHACER UX, CONSERVAR núcleo | Iniciar preparación / cantidad real |
| Prevención doble descuento | CONSERVAR | obligatorio |
| Chequeo de faltantes | CONSERVAR | faltante → Lista |
| Material cost congelado al pesar | CONSERVAR | costo real preparación |
| Avanzar proceso genérico | RETIRAR | acciones contextuales |
| Evaluación dentro de Ensayo | MOVER | LAB · Resultados |
| Tesela nace después de cocción | REHACER | muestra existe antes de horno |

## Teselas / Resultados

| R3 actual | Decisión | vNext |
|---|---|---|
| Tesela = resultado post-cocción | REHACER | Sample/PhysicalItem pre-horno |
| ID T-xxxx | REHACER | AL-xxxx-T01 |
| Listado textual | REHACER UX | galería + ficha |
| Evaluación texto libre | REHACER | técnico + gusto + decisión + defectos + comentario |
| Sin cámara resultado | NUEVO | cámara/galería |
| Sin pesos/medidas progresivas | NUEVO | húmeda/seca/bizcocho/cocida |
| Sin mono/bicocción | NUEVO | firing_scheme |
| Sin memoria experimental | NUEVO | coincidencia exacta/similar |
| Sin descartar físico conservando registro | NUEVO | disposition |
| Sin aprobación → Fórmulas | NUEVO | promover/vincular |
| Comentario móvil inestable | BUG UX | textarea estable + guardar/siguiente |

## Taller

| R3 actual | Decisión | vNext |
|---|---|---|
| Stock dentro de Taller | MOVER | Operaciones · Stock |
| Pastas | CONSERVAR + REUBICAR | Fórmulas/Producción |
| 4 fórmulas pasta escalables | CONSERVAR | categoría Pasta |
| Preparar pasta chequea y descuenta stock | CONSERVAR + ADAPTAR | batch persistente |
| Batch pasta usa P-xxxx | REHACER | prefijo propio |
| Compras dentro de Taller | MOVER + REHACER | Operaciones · Compras |
| Proveedores | MOVER + ADAPTAR | Compras · Proveedores |
| Movimientos | MOVER | Stock · Movimientos |
| Sin Bitácora | NUEVO | Taller · Bitácora |
| Sin Producción/Piezas | NUEVO | Taller · Producción |
| Sin Lote producción | NUEVO | Producción · Lotes |
| Sin Proyecto/Serie/Trabajo | NUEVO | Producción · Proyectos |
| Sin Fórmulas biblioteca | NUEVO | Taller · Fórmulas |
| Estante | NO CREAR | Stock ya es “lo que tengo” |

**Pendiente explícito:** no perder Pastas ni sus lotes; cerrar ubicación exacta antes de tocar ese bloque.

## Operaciones · Stock / Lista / Compras

| R3 actual | Decisión | vNext |
|---|---|---|
| Stock = inicial + movimientos | CONSERVAR NÚCLEO | ledger |
| Sin lotes/envases físicos | ADAPTAR | InventoryContainer |
| Compra entra directo a Stock | CONSERVAR como recepción / REHACER flujo | Pedido→Recibido→Stock |
| Faltantes automáticos | CONSERVAR + MOVER | Lista |
| Sin Lista persistente | NUEVO | PurchaseNeed |
| Sin estados de pedido | NUEVO | ciclo completo |
| Sin comprobantes/lotes recepción | NUEVO | compra/stock |
| QR | FUTURO | no bloquear CORE |

## Operaciones · Quema

| R3 actual | Decisión | vNext |
|---|---|---|
| Perfil horno completo | CONSERVAR | Quema · Hornos |
| 8 programas con fuente | CONSERVAR | Quema · Programas |
| Estimación kWh/costo | CONSERVAR | estimado vs real |
| Hornada sólo acepta Ensayos | REHACER | PhysicalItems |
| Iniciar cambia Ensayo a En cocción | ADAPTAR | estado de objeto físico |
| Timer | CONSERVAR | seguimiento |
| Fin de tiempo → Enfriando | CONSERVAR | — |
| Temperatura manual | CONSERVAR | — |
| ≤50 °C antes de cerrar | ADAPTAR | Lista para abrir |
| Cerrar = Finalizada + Cocido | REHACER | abrir/descargar/completar separados |
| Historial | CONSERVAR | ampliar relaciones |
| Costo horno por partes iguales | ADAPTAR | configurable |
| Estado hornada anterior queda visible | BUG CRÍTICO | nueva hornada limpia |
| Horno módulo global | MOVER | Operaciones · Quema |

## Costos

| R3 actual | Decisión | vNext |
|---|---|---|
| Materiales + horno + otros | CONSERVAR + AMPLIAR | ledger integral |
| Por ensayo | CONSERVAR + AMPLIAR | proyecto/pieza/lote/hornada |
| Mano obra/Indirecto/Otro | CONSERVAR + AMPLIAR | categorías formales |
| Sin períodos | NUEVO | día/semana/mes/año/personalizado |
| Sin tarifas por vigencia | NUEVO | histórico correcto |
| Sin WorkLog | NUEVO | mano de obra directa/indirecta |
| Sin contingencia separada | NUEVO | costo técnico |
| Costos lee datos existentes | CONSERVAR PRINCIPIO | no duplicar |

## Configuración

- **CONSERVAR:** unidad preferida, envase estándar/tara, modo consumo rápido/preciso, stock calculado/verificado.
- **REVISAR:** checkbox Identificación química; no retirar sin verificar su efecto.
- **NUEVO:** horno habitual, tarifa, valor/hora, contingencia, margen, mínimos, temperaturas, etiquetas, criterios.
- **MOVER:** Configuración sale de navegación principal y va a Perfil/engranaje.

## Demo / QA

- **CONSERVAR:** Taller demo, Borrar demo, aislamiento de datos.
- **RECONSTRUIR:** Flujo completo demo usando el nuevo modelo.
- **REHACER:** “Hornada lista para cerrar” → escenarios Lista para abrir / Descargada.
- **R3 debe seguir compilando y cargando** hasta que vNext tenga paridad.

## Funcionalidades nuevas aprobadas

CORE:
- cabecera fija;
- buscador global;
- Inicio coordinador;
- agenda/tareas;
- próxima acción;
- Fórmulas lista + galería;
- Bitácora;
- Proyectos/Series/Trabajos;
- Piezas;
- Lotes producción;
- Tesela física pre-horno;
- Resultados post-descarga;
- cámara;
- captura progresiva pesos/medidas;
- mono/bicocción;
- memoria experimental;
- Lista de compra;
- ciclo de pedido;
- costos por período;
- directos/indirectos/mano obra/contingencia;
- archivo en lugar de borrado;
- procedencia transversal;
- backup/exportación antes de uso durable.

FUTURO, no bloquear CORE:
- voz contextual;
- QR;
- expansión Aprender;
- expansión Comunidad.

## Contradicciones estructurales que obligan a migrar con cuidado

1. **Tesela:** R3 la crea después de cocción; vNext la necesita antes del horno.
2. **Ensayo:** R3 mezcla preparación, muestra y cocción; vNext los separa.
3. **Horno:** R3 confunde ≤50 °C con finalizar; vNext separa enfriar/abrir/descargar/completar.
4. **Compras:** R3 compra = entrada stock; vNext necesita ciclo de pedido.
5. **Estante:** se descarta para no duplicar Stock.
6. **Fórmula:** R3 vive dentro del draft; vNext es entidad reutilizable/versionada.
7. **IDs:** R3 puede reciclar por max+1; vNext nunca reutiliza.

## Orden de migración recomendado

1. **Fase 0:** congelar R3 y tests de humo.
2. **Fase 1:** shell nuevo con cabecera/navegación, reubicando sin cambiar lógica.
3. **Fase 2:** LAB actual íntegro; corregir UX/bugs pequeños.
4. **Fase 3:** FormulaRevision + Experiment/Preparation/Sample.
5. **Fase 4:** Quema sobre PhysicalItems; nueva state machine.
6. **Fase 5:** Resultados/cámara/evaluación/memoria.
7. **Fase 6:** Operaciones Stock/Lista/Compras.
8. **Fase 7:** Taller Fórmulas/Bitácora/Producción/Proyectos; reubicar Pastas sin pérdida.
9. **Fase 8:** Costos integral.
10. **Fase 9:** Inicio vivo sobre entidades reales.
11. **Fase 10:** persistencia durable + backup.

## Checklist mínima de paridad antes de reemplazar R3

Debe seguir funcionando:
- Color picker y foto→color.
- ΔE76.
- pigmento naranja.
- pigmento negro y límites molares.
- ADN y ficha de elementos.
- vehículos y fórmulas base.
- cálculo exacto y simulación.
- referencias.
- 118 elementos.
- 59 materiales.
- 11 calculadoras.
- 4 fórmulas de pasta con 1/5/10/custom.
- preparación pasta + stock.
- prevención de doble descuento.
- compras/entradas e historial.
- perfiles de horno.
- 8 programas.
- energía/costos.
- timer/enfriamiento.
- regla ≤50 °C.
- historial hornadas.
- costos.
- Demo.
- UX móvil sin overflow global.
- legibilidad.
- R3 intacta.

Y además los cambios CORE:
- navegación fija;
- Inicio vivo;
- fórmula versionada;
- Ensayo/Preparación/Sample separados;
- tesela pre-horno;
- hornada agrupa sin fusionar;
- descarga devuelve individuos;
- Resultados;
- foto resultado;
- IDs no reutilizados;
- mono/bicocción;
- Fórmulas Lista/Galería;
- Stock/Lista/Compras;
- Costos por período;
- buscador;
- archivo histórico.

## Veredicto técnico

**No hay que empezar ALUMINA de cero.**

R3 ya contiene mucho producto: motor químico, datos, calculadoras, inventario, pastas, horno, costos, demo y correcciones móviles.

La parte a preservar con mayor cuidado es:
**Color → Pigmento → ADN / Perfil molar → Fórmula + Herramientas químicas.**

La parte que requiere rediseño estructural es:
**Ensayo → Tesela/Muestra → Hornada → Resultado.**

Quema se trata como:
**motor existente a conservar + state machine a rehacer**.
