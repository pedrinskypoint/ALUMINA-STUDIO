# ALUMINA STUDIO · MODELO DE DATOS VNEXT

Estado: especificación de dominio para implementar después de congelar Arquitectura y Navegación.

Objetivo central:
**cada dato existe una sola vez; los departamentos muestran vistas distintas sobre los mismos objetos.**

---

# 1. REGLAS GLOBALES

## 1.1 Identidad

Cada entidad persistente tendrá dos identificadores:

- `id`: UUID interno, nunca visible como identificador principal.
- `code`: código humano estable e inmutable.

Ejemplos:
- Fórmula: `F-0014`
- Ensayo: `AL-0032`
- Tesela derivada: `AL-0032-T01`
- Pieza: `P-0101`
- Proyecto: `PR-0004`
- Lote de producción: `L-0018`
- Hornada: `H-0021`
- Pedido: `PO-0008`

Reglas:
- códigos nunca se reutilizan;
- eliminar/archivar un registro no libera su código;
- los contadores sólo avanzan;
- los códigos son inmutables.

## 1.2 Archivo en lugar de borrado

Campos comunes:
- `created_at`
- `updated_at`
- `archived_at`
- `created_by`

Regla:
- archivar es la operación normal;
- borrado definitivo sólo como operación administrativa explícita.

## 1.3 Fuente única de verdad

No copiar objetos al pasar entre módulos.

Ejemplo:
- `F-014` vive una sola vez;
- LAB la referencia;
- un Ensayo la referencia;
- una Tesela la referencia indirectamente por el Ensayo;
- Resultados vincula evidencia;
- Costos consulta los movimientos relacionados.

---

# 2. ENTIDADES TRANSVERSALES

## 2.1 WorkshopProfile

Representa el taller.

Campos principales:
- id
- name
- default_units
- locale
- timezone

No guarda hornos, fórmulas ni proveedores embebidos.

## 2.2 UserProfile

Preferencias personales:
- display_name
- language
- unit_preferences
- appearance
- notifications
- accessibility_preferences

## 2.3 WorkshopSettings

Sólo defaults y políticas:
- default_kiln_id
- default_supplier_id
- default_energy_tariff_id
- default_hourly_rate
- default_contingency_pct
- default_margin_pct
- default_low_stock_threshold
- default_firing_scheme
- common_temperatures
- label_format
- costing_method

Regla:
- referencia entidades reales;
- no duplica datos maestros.

## 2.4 SequenceCounter

Contadores persistentes para códigos:
- entity_type
- current_value
- updated_at

Nunca decrece.

---

# 3. PROCEDENCIA Y EVIDENCIA

## 3.1 ProvenanceRecord

Registro reutilizable de procedencia.

Campos:
- id
- source_class
- source_subtype
- title
- author
- organization
- date
- url_or_reference
- notes
- confidence
- evidence_kind

`source_class`:
- FUENTE_PRIMARIA
- ACADEMICA
- COMUNIDAD
- FABRICANTE
- EXPERIMENTAL

`source_subtype` puede incluir:
- propia
- clase
- apunte
- libro
- artículo
- Glazy
- comunidad_individual
- comunidad_replicada
- fabricante
- anónima

`evidence_kind`:
- exacto_estequiometrico
- modelo_publicado
- estimacion_heuristica
- resultado_experimental

## 3.2 EntityProvenance

Relaciona procedencia con cualquier objeto:
- entity_type
- entity_id
- provenance_id
- role

La procedencia sobrevive a todas las etapas del flujo.

---

# 4. MATERIALES Y STOCK

## 4.1 Material

Identidad técnica de un insumo.

Campos:
- id
- code opcional
- name
- category
- reference_formula
- molar_mass
- ceramic_function
- technical_notes
- manufacturer_reference
- default_supplier_id
- active

Ejemplos:
- Sílice
- Caolín
- Carbonato de calcio
- Pigmento encapsulado naranja

`Material` responde:
**qué es**.

## 4.2 InventoryContainer

Existencia física concreta.

Campos:
- id
- code
- material_id
- supplier_id
- supplier_lot
- initial_quantity
- unit
- tare
- location
- opened_at
- verified_quantity
- verified_at
- low_stock_threshold
- qr_code_payload

Ejemplo:
un envase físico de 1 kg de sílice.

## 4.3 StockMovement

Ledger append-only.

Campos:
- id
- material_id
- container_id opcional
- movement_type
- quantity_delta
- unit
- occurred_at
- source_entity_type
- source_entity_id
- note

Tipos:
- PURCHASE
- PREPARATION_CONSUMPTION
- MANUAL_USE
- LOSS
- PHYSICAL_ADJUSTMENT
- RETURN

Regla:
Stock actual = suma de movimientos.
Nunca sobrescribir historial para corregir: crear un ajuste.

---

# 5. FÓRMULAS

## 5.1 Formula

Identidad conceptual de una fórmula.

Campos:
- id
- code
- name
- category
- status
- favorite
- archived_at
- primary_image_asset_id
- current_revision_id

Categorías:
- esmalte/base
- engobe
- acuarela
- barbotina
- pasta
- pigmento/preparación
- otro

Estados:
- BORRADOR
- EXPERIMENTAL
- APROBADA_TALLER
- REPETIDA
- VALIDADA_REPLICADA
- ARCHIVADA

## 5.2 FormulaRevision

Contenido técnico versionado.

Campos:
- id
- formula_id
- revision_number
- created_at
- composition
- batch_basis
- preparation_instructions
- target_temperature
- atmosphere
- notes

Regla crítica:
- un Ensayo referencia una revisión exacta;
- una revisión usada en un Ensayo no se modifica retroactivamente;
- editar composición crea nueva revisión;
- “Crear variante” crea nueva Formula relacionada.

## 5.3 FormulaRelation

Permite genealogía:
- parent_formula_id
- child_formula_id
- relation_type

Tipos:
- VARIANTE
- ADAPTACION
- DERIVADA_DE

---

# 6. LAB · ENSAYOS Y PREPARACIONES

## 6.1 Experiment

Ensayo conceptual/operativo.

Campos:
- id
- code  // AL-xxxx
- formula_revision_id
- project_id opcional
- title
- target_batch_g
- status
- target_support_material_id
- target_temperature
- atmosphere
- notes
- experimental_signature

Estados sugeridos:
- PLANIFICADO
- EN_PREPARACION
- MUESTRAS_CREADAS
- EN_PROCESO
- CERRADO
- ARCHIVADO

`experimental_signature` se genera con los parámetros relevantes para detectar duplicados/similitudes.

## 6.2 Preparation

Mezcla física realmente preparada.

Campos:
- id
- experiment_id
- prepared_at
- target_total_g
- actual_total_g
- preparation_notes
- status

Un Ensayo puede tener una o más Preparaciones.

## 6.3 PreparationComponent

Pesada real por componente:
- preparation_id
- material_id
- container_id opcional
- target_g
- actual_g
- stock_movement_id

Regla:
registrar consumo una sola vez.

---

# 7. OBJETOS FÍSICOS

Para Horno necesitamos una identidad común de cualquier cosa que pueda entrar a una hornada.

## 7.1 PhysicalItem

Entidad base física.

Campos:
- id
- code
- kind
- project_id opcional
- firing_scheme
- process_state
- archived_at

`kind`:
- SAMPLE
- PIECE

`firing_scheme`:
- MONO
- BI

No contiene todos los detalles de Tesela ni Pieza; sirve como identidad común para Quema.

## 7.2 Sample

Especialización experimental.

Campos:
- physical_item_id
- experiment_id
- preparation_id
- sample_index
- sample_type
- wet_weight_g
- dry_weight_g
- bisque_weight_g
- fired_weight_g
- wet_dimensions
- dry_dimensions
- bisque_dimensions
- fired_dimensions
- application_technique
- application_layers
- notes

Código recomendado:
`AL-0032-T01`

Tipos:
- tesela
- probeta
- placa
- otra muestra

## 7.3 Piece

Objeto de producción.

Campos:
- physical_item_id
- piece_type
- clay_material_id
- dry_weight_g
- dimensions
- technique
- finish
- labor_estimate
- notes

Código:
`P-xxxx`

Puede estar vinculado a una o más fórmulas mediante `PieceFormulaApplication`.

## 7.4 PieceFormulaApplication

Relaciona una pieza con fórmulas aplicadas:
- piece_id
- formula_revision_id
- role
- application_notes

Roles:
- esmalte
- engobe
- decoración
- otro

---

# 8. ESTADOS FÍSICOS

Para muestras/piezas:

Estados generales:
- CREATED
- PREPARING
- DRYING
- DRY
- APPLIED
- READY_FOR_FIRING
- IN_FIRING
- FIRED
- UNLOADED
- EVALUATED

En bicocción se registra además el historial de eventos de cocción y la pieza puede volver de UNLOADED_BISQUE a APPLIED/READY_FOR_FIRING.

Regla:
no inferir que “fin del programa” = “pieza evaluable”.

---

# 9. RESULTADOS Y EVALUACIÓN

## 9.1 Evaluation

Evaluación de un objeto físico en un momento concreto.

Campos:
- id
- physical_item_id
- firing_id
- evaluation_stage
- evaluated_at
- technical_result
- preference
- disposition
- defects
- comment
- approved
- evaluator_id

`technical_result`:
- FUNCIONO
- PARCIAL
- FALLO

`preference`:
- FAVORITO
- ME_GUSTA
- NEUTRO
- NO_ME_GUSTA

`disposition`:
- CONSERVAR
- REPETIR
- AJUSTAR
- ARCHIVAR
- DESCARTAR_FISICAMENTE

Regla:
descartar físicamente nunca borra Evaluation ni PhysicalItem.

## 9.2 ExperimentalMatch

No necesita persistirse inicialmente; puede calcularse.

Tipos:
- EXACT
- SIMILAR

Usa `experimental_signature` + tolerancias.

---

# 10. FOTOS Y ARCHIVOS

## 10.1 MediaAsset

Campos:
- id
- file_path_or_object_key
- media_type
- created_at
- caption
- hash
- metadata

## 10.2 EntityMedia

Relación:
- entity_type
- entity_id
- media_asset_id
- role
- sort_order

Roles:
- PRIMARY
- BEFORE_FIRING
- AFTER_FIRING
- DEFECT_DETAIL
- REVERSE
- NOTE_ATTACHMENT
- RECEIPT

Regla:
las fotos no se duplican al aparecer en Galería, Resultados o Proyecto.

---

# 11. PRODUCCIÓN

## 11.1 Project

Entidad general.

Campos:
- id
- code
- name
- project_type
- status
- start_date
- due_date
- client_name opcional
- notes

Tipos:
- PROJECT
- SERIES
- JOB

Estados:
- PLANNED
- ACTIVE
- ON_HOLD
- COMPLETED
- ARCHIVED

## 11.2 ProjectLink

Relaciona el proyecto con objetos existentes:
- project_id
- entity_type
- entity_id
- role

Evita copiar:
- fórmulas;
- ensayos;
- teselas;
- piezas;
- lotes;
- pedidos;
- hornadas;
- notas.

## 11.3 ProductionLot

Agrupación organizativa de piezas.

Campos:
- id
- code
- project_id opcional
- name
- status
- notes

No es una Hornada.

## 11.4 ProductionLotItem

- production_lot_id
- physical_item_id
- quantity_role opcional

Los PhysicalItem conservan identidad individual.

---

# 12. QUEMA 🔥

## 12.1 Kiln

Campos:
- id
- code
- name
- model
- capacity
- nominal_kw
- voltage
- controller
- default_duty_factor
- notes
- active

## 12.2 FiringProgram

Campos:
- id
- code
- name
- kiln_id opcional
- purpose
- stages
- estimated_duration
- target_temperature
- atmosphere
- notes

`stages`:
lista de rampas/mesetas.

## 12.3 Firing

Hornada/carga real.

Campos:
- id
- code
- kiln_id
- firing_program_id
- status
- scheduled_at
- started_at
- program_ended_at
- opened_at
- unloaded_at
- completed_at
- actual_energy_kwh opcional
- estimated_energy_kwh
- energy_cost
- notes

Estados:
- PROGRAMADA
- EN_COCCION
- ENFRIANDO
- LISTA_PARA_ABRIR
- ABIERTA_DESCARGANDO
- DESCARGADA
- COMPLETADA
- INTERRUMPIDA

## 12.4 FiringItem

Tabla de unión:
- firing_id
- physical_item_id
- firing_role
- position_note
- allocation_weight opcional
- allocated_cost opcional

Regla:
una Hornada agrupa, nunca fusiona objetos.

Una pieza puede aparecer en varias Hornadas por bicocción.

---

# 13. COMPRAS Y LISTA

## 13.1 PurchaseNeed

Elemento de Lista.

Campos:
- id
- material_id
- required_quantity
- unit
- priority
- reason
- source_entity_type
- source_entity_id
- preferred_supplier_id
- status

Estados:
- PENDING
- SELECTED
- CONVERTED_TO_ORDER
- RESOLVED
- ARCHIVED

No genera gasto ni stock.

## 13.2 Supplier

Campos:
- id
- code
- name
- contact
- whatsapp
- email
- address
- notes
- active

## 13.3 PurchaseOrder

Campos:
- id
- code
- supplier_id
- status
- ordered_at
- expected_at
- pickup_at
- received_at
- total_amount
- notes

Estados:
- DRAFT
- ORDERED
- WAITING
- IN_TRANSIT
- ARRIVES_TODAY
- READY_FOR_PICKUP
- RECEIVED
- CANCELLED

## 13.4 PurchaseOrderLine

- purchase_order_id
- material_id
- quantity
- unit
- unit_cost
- total_cost
- linked_purchase_need_id

Al recibir:
- crea StockMovement PURCHASE;
- actualiza/crea InventoryContainer;
- genera costo real.

---

# 14. COSTOS

Modelo basado en ledger, no en recálculo duplicado.

## 14.1 CostEntry

Campos:
- id
- occurred_at
- cost_type
- category
- amount
- currency
- status
- source_entity_type
- source_entity_id
- project_id opcional
- note

`cost_type`:
- DIRECT
- INDIRECT
- LABOR
- CONTINGENCY
- TAX
- COMMISSION

`status`:
- ESTIMATED
- REAL
- ALLOCATED
- PENDING

## 14.2 CostAllocation

Permite repartir un costo:
- cost_entry_id
- target_entity_type
- target_entity_id
- allocation_method
- allocated_amount

Métodos:
- EQUAL
- WEIGHT
- HOURS
- OCCUPANCY
- MANUAL

## 14.3 WorkLog

Mano de obra:
- id
- person_or_role
- started_at
- duration_minutes
- hourly_rate
- labor_type
- source_entity_type
- source_entity_id
- project_id opcional

`labor_type`:
- DIRECT
- INDIRECT

## 14.4 RateSchedule

Valores con vigencia:
- rate_type
- value
- unit
- valid_from
- valid_to

Ejemplos:
- tarifa eléctrica;
- valor/hora;
- alquiler mensual.

Regla:
históricos usan la tarifa vigente en la fecha original.

---

# 15. BITÁCORA

## 15.1 JournalEntry

Campos:
- id
- created_at
- title
- body
- entry_type
- project_id opcional
- archived_at

## 15.2 JournalLink

Relaciona una nota con:
- fórmula;
- ensayo;
- tesela;
- pieza;
- hornada;
- pedido;
- material;
- proyecto.

No copia esos objetos.

---

# 16. AGENDA / ASISTENTE DE INICIO

Inicio puede derivar muchas tareas de estados existentes, pero también necesitamos tareas manuales.

## 16.1 Task

Campos:
- id
- title
- due_at
- status
- priority
- source_entity_type opcional
- source_entity_id opcional
- auto_generated
- note

Estados:
- PENDING
- DONE
- DISMISSED
- OVERDUE

Ejemplos automáticos:
- pedido llega hoy;
- retirar material;
- teselas listas para horno;
- hornada lista para registrar temperatura;
- resultados pendientes de evaluar.

Regla:
cuando sea posible, Inicio deriva tareas de los objetos originales; no duplica estados.

---

# 17. BÚSQUEDA GLOBAL

No es fuente de verdad.

Índice derivado de:
- code
- name/title
- tags
- notes
- relaciones

Debe abrir siempre el objeto original.

---

# 18. INVARIANTES CRÍTICAS

1. Un objeto nunca se duplica por cambiar de departamento.
2. IDs y códigos no se reutilizan.
3. StockMovement es append-only.
4. CostEntry histórico no se reescribe con tarifas actuales.
5. FiringItem agrupa objetos, no los fusiona.
6. Una fórmula usada en un Ensayo queda congelada como FormulaRevision.
7. Editar una fórmula usada crea revisión nueva.
8. Descartar físicamente no borra evidencia.
9. Archivar no elimina relaciones.
10. Fotos se almacenan una sola vez y se referencian.
11. Inicio sólo agrega/deriva estado; no crea una base paralela.
12. Proyecto agrupa mediante referencias; no copia.
13. Configuración guarda defaults; no duplica maestros.
14. Una hornada finalizada no puede contaminar el estado de una hornada nueva.
15. Una misma pieza puede participar en varias hornadas.
16. Monococción y bicocción son rutas distintas sobre la misma identidad física.

---

# 19. RELACIONES PRINCIPALES

```
Formula
  └── FormulaRevision
        └── Experiment (AL-xxxx)
              └── Preparation
                    └── Sample / PhysicalItem (AL-xxxx-Txx)
                          ├── FiringItem → Firing (H-xxxx)
                          └── Evaluation
                                └── MediaAsset

Project
  ├── ProjectLink → Formula
  ├── ProjectLink → Experiment
  ├── ProjectLink → PhysicalItem/Piece
  ├── ProjectLink → ProductionLot
  ├── ProjectLink → PurchaseOrder
  └── ProjectLink → Firing

Piece / PhysicalItem
  ├── ProductionLotItem → ProductionLot
  ├── PieceFormulaApplication → FormulaRevision
  ├── FiringItem → Firing
  └── Evaluation

Material
  ├── InventoryContainer
  ├── StockMovement
  ├── PreparationComponent
  ├── PurchaseNeed
  └── PurchaseOrderLine

Firing
  ├── Kiln
  ├── FiringProgram
  ├── FiringItem
  └── CostEntry / CostAllocation
```

---

# 20. MAPEO CON DEPARTAMENTOS

## Inicio
lee:
- Task
- PurchaseOrder
- PurchaseNeed
- Stock
- Firing
- Experiment
- PhysicalItem
- Evaluation
- Project

## LAB
trabaja con:
- Formula / FormulaRevision
- Experiment
- Preparation
- Sample
- Evaluation
- MediaAsset

## Taller
trabaja con:
- JournalEntry
- Formula
- Project
- Piece
- ProductionLot

## Operaciones
trabaja con:
- Firing
- Kiln
- FiringProgram
- PurchaseNeed
- PurchaseOrder
- Supplier
- InventoryContainer
- StockMovement
- CostEntry
- WorkLog

## Aprender / Comunidad
futuro:
referencia fórmulas/resultados/procedencia existentes sin duplicarlos.

---

# 21. PERSISTENCIA

R3 DEMO usa estado en memoria.
vNext debe preparar Repository interfaces para que la implementación pueda pasar a persistencia durable.

Recomendación:
- desarrollo inmediato: Repository abstractions;
- versión durable: SQLite;
- fotos/archivos: almacenamiento externo/local con referencias en DB;
- exportación: paquete portable de DB + assets + manifest.

No depender de `gr.State` como fuente de verdad permanente.

---

# 22. PRÓXIMO PASO

Después de aprobar este modelo:

1. Crear MATRIZ DE MIGRACIÓN R3 → VNEXT.
2. Decidir qué código se conserva, adapta, mueve o elimina.
3. Definir orden de implementación.
4. Construir shell/navegación nueva.
5. Implementar Repository + entidades.
6. Migrar primero el flujo crítico:
   Fórmula → Ensayo → Tesela → Quema → Resultados.
7. Integrar Producción.
8. Integrar Compras/Stock/Costos.
9. Construir Demo vNext.
10. QA móvil y regresión.
