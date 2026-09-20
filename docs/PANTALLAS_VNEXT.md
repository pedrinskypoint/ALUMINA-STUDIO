# ALUMINA STUDIO · PANTALLAS VNEXT

Estado: especificación pantalla por pantalla.
Primera pantalla definida: INICIO.

---

# PANTALLA 01 · INICIO

## Objetivo

Inicio es el **productor/coordinador operativo** de ALUMINA.

No es una portada decorativa ni un módulo de carga de datos.

Debe responder de un vistazo:

- qué está pasando ahora;
- qué requiere atención;
- qué viene después;
- qué compras/pedidos están en curso;
- qué tareas hay hoy;
- qué está listo para horno;
- qué hornadas están activas;
- qué resultados faltan evaluar;
- dónde continuar el trabajo.

Inicio no guarda copias de información.
Lee y resume estados reales de LAB, Taller, Operaciones y Costos.

---

## 1. CABECERA FIJA

Siempre visible durante scroll.

### Móvil

Fila compacta:

**ALUMINA** | **Buscar** | **Alertas** | **Menú**

Al abrir Menú:
- Inicio
- LAB
- Taller
- Operaciones
- Aprender / Comunidad
- Configuración / Perfil

### Escritorio

Puede mostrar directamente:
- Inicio
- LAB
- Taller
- Operaciones
- Aprender / Comunidad
- Buscador
- Alertas
- Perfil

### Reglas

- Inicio siempre accesible.
- Buscador siempre accesible.
- No ocupar demasiada altura.
- Controles táctiles de 44–48 px mínimo.
- Sin overflow horizontal.
- La cabecera no debe tapar contenido.
- El módulo activo se resalta claramente.

---

## 2. BLOQUE “AHORA”

Primer bloque visible al abrir la app.

Objetivo:
mostrar sólo lo que está activo en este momento.

### Ejemplos

**H-014 · Enfriando**
68 °C
→ Registrar temperatura

**AL-032-T01 · Secando**
→ Ver tesela

**Pedido DP Colors**
Llega hoy
→ Ver pedido

**PR-004 · Tazas restaurante X**
12/24 piezas completadas
→ Continuar proyecto

### Comportamiento

- máximo 3–5 tarjetas visibles;
- priorizar actividad actual;
- tocar la tarjeta abre el objeto exacto;
- si no hay actividad, mostrar:
  **“No hay procesos activos ahora.”**

---

## 3. BLOQUE “SIGUIENTE ACCIÓN”

ALUMINA propone el siguiente paso lógico más importante.

No debe ser una recomendación abstracta.
Debe salir de estados reales.

### Ejemplos

**5 teselas listas para horno**
→ **Armar carga**

**H-014 está a 48 °C**
→ **Confirmar apertura**

**3 resultados pendientes**
→ **Evaluar resultados**

**Pedido recibido**
→ **Ingresar a Stock**

### Regla

Mostrar una sola acción principal.

Si existen varias:
orden de prioridad sugerido:

1. seguridad / horno;
2. entregas o retiros con horario;
3. procesos bloqueados;
4. resultados pendientes;
5. stock crítico;
6. tareas generales.

---

## 4. BLOQUE “HOY / AGENDA”

Rol:
agenda operativa del taller.

### Contenido

- tareas manuales;
- tareas derivadas automáticamente;
- entregas;
- retiros;
- vencimientos;
- citas;
- recordatorios.

### Ejemplos

**17:00 · Retirar caolín**
Pedido PO-008

**Hoy · Pedido llega**
DP Colors

**Antes de las 18:00 · Registrar temperatura**
H-014

**Pendiente · Fotografiar AL-032-T01**

### Acciones

- marcar como hecho;
- abrir objeto;
- posponer;
- editar;
- crear tarea manual.

### Estados visuales

- Hoy
- Próximo
- Vencido
- Completado

---

## 5. BLOQUE “ALERTAS”

Sólo problemas o cosas que requieren atención.

No mezclar con actividad normal.

### Alertas posibles

- stock bajo;
- stock crítico;
- pedido demorado;
- material faltante para ensayo;
- hornada sin temperatura registrada;
- tesela/pieza detenida demasiado tiempo;
- resultado pendiente;
- dato incompleto importante;
- costo pendiente de asignación.

### Ejemplo

**Stock crítico · Sílice**
240 g disponibles · mínimo 1 kg
→ Añadir a Lista

### Regla

Toda alerta debe tener una acción clara.

Nunca mostrar una alerta sin indicar qué puede hacer el usuario.

---

## 6. BLOQUE “PRODUCCIÓN / LAB”

Resumen de trabajo experimental y productivo.

### LAB

Mostrar:
- ensayos activos;
- teselas/muestras en proceso;
- teselas listas para horno;
- resultados pendientes.

Ejemplo:

**LAB**
2 ensayos activos
5 teselas en proceso
3 listas para horno
2 resultados sin evaluar
→ Abrir LAB

### TALLER / PRODUCCIÓN

Mostrar:
- proyectos activos;
- piezas en proceso;
- lotes abiertos;
- piezas listas para Quema.

Ejemplo:

**Producción**
PR-004 · 12/24 piezas
L-018 · listo para horno
→ Abrir Producción

---

## 7. BLOQUE “QUEMA 🔥”

Resumen de horno.

### Posibles estados

- cargas pendientes;
- hornada programada;
- en cocción;
- enfriando;
- lista para abrir;
- descargada pendiente de evaluación.

### Ejemplo

**Quema 🔥**
H-014 · Enfriando
68 °C
7 objetos
→ Ver hornada

Debajo, si aplica:

**Pendientes de carga**
5 teselas · 12 piezas
→ Armar hornada

### Regla

No inferir temperatura real sólo por tiempo.
Mostrar temperatura sólo si fue registrada o recibida de una fuente válida.

---

## 8. BLOQUE “COMPRAS Y LOGÍSTICA”

Debe ser muy operativo.

### Mostrar

- pedidos activos;
- llega hoy;
- listo para retirar;
- retrasados;
- necesidades críticas;
- cantidad de ítems en Lista.

### Ejemplo

**Compras**
PO-008 · En camino
Entrega estimada: hoy

**Lista**
4 materiales pendientes
→ Ver Lista

### Acciones

- Ver pedido.
- Marcar recibido.
- Ir a Lista.
- Añadir necesidad.
- Ver proveedor.

---

## 9. BLOQUE “COSTOS”

Resumen corto, no contabilidad completa.

### Selector rápido

- Hoy
- Semana
- Mes

### Mostrar

- gasto registrado;
- costo estimado pendiente;
- compras;
- hornadas;
- mano de obra si existe.

Ejemplo:

**Este mes**
Directos: ARS ...
Indirectos imputados: ARS ...
Mano de obra: ARS ...
Total: ARS ...
→ Ver Costos

### Regla

No mostrar números inventados.
Si hay datos incompletos:
**“Resumen parcial”**.

---

## 10. BLOQUE “ACTIVIDAD RECIENTE”

Timeline corto.

### Ejemplos

14:32 · AL-032-T01 marcada Seca
13:10 · Pedido PO-008 despachado
11:45 · F-014 guardada como Experimental
09:20 · H-013 descargada

### Regla

Máximo 5–8 eventos.
Acceso:
**Ver actividad completa**.

---

## 11. ACCESOS RÁPIDOS

Zona táctil.

Botones grandes.

### Primera fila sugerida

- Nuevo ensayo
- Nueva fórmula
- Nueva pieza
- Cargar horno

### Segunda fila sugerida

- Cámara / resultado
- Stock
- Lista
- Costos

### Regla

Usuario puede personalizar favoritos más adelante.

---

## 12. HERRAMIENTAS RÁPIDAS

No abrir todas las calculadoras.

Mostrar accesos compactos:

- Moles ↔ gramos
- Seger / UMF
- Contracción
- Absorción
- Tabla periódica
- Densidad de barbotina

Al tocar:
abre LAB > Herramientas químicas con la herramienta seleccionada.

---

## 13. BUSCADOR DESDE INICIO

Además del buscador fijo en cabecera, Inicio puede mostrar un campo grande si hay espacio.

Placeholder:

**“Buscar fórmula, material, ensayo, pieza, hornada…”**

Ejemplos:
- AL-032
- Naranja Talavera
- Sílice
- H-014
- PO-008

Resultado:
abre directamente el objeto original.

---

## 14. ESTADOS VACÍOS

Inicio debe funcionar también para usuario nuevo.

### Sin datos

Mostrar:

**Tu taller está listo.**

Acciones:
- Configurar taller
- Crear primera fórmula
- Registrar material
- Crear primera pieza

No mostrar tarjetas vacías ni ceros por todas partes.

### Sin tareas hoy

Mostrar:
**“No tenés tareas pendientes para hoy.”**

### Sin alertas

Mostrar:
**“Sin alertas.”**

---

## 15. ACTUALIZACIÓN AUTOMÁTICA

Regla obligatoria:

Cada vez que el usuario vuelve a Inicio:

1. releer estados;
2. actualizar tarjetas;
3. recalcular alertas;
4. reconstruir próxima acción;
5. actualizar agenda;
6. mantener scroll al inicio.

No exigir botón Actualizar.

Además:
acciones críticas realizadas desde otros módulos deben invalidar/refrescar el resumen correspondiente.

---

## 16. PRIORIDAD VISUAL

Orden vertical recomendado en móvil:

1. Cabecera fija
2. Ahora
3. Siguiente acción
4. Hoy / Agenda
5. Alertas
6. Quema
7. Producción / LAB
8. Compras / Logística
9. Accesos rápidos
10. Costos
11. Actividad reciente
12. Herramientas rápidas

Motivo:
primero operación inmediata, luego gestión, luego análisis.

---

## 17. INTERACCIÓN TÁCTIL

Reglas:

- toda tarjeta principal es tocable;
- no usar enlaces pequeños como única acción;
- botones 44–48 px mínimo;
- acciones frecuentes en mitad inferior;
- no abrir teclado salvo búsqueda o texto real;
- no exigir scroll hacia arriba para navegar;
- feedback inmediato al tocar;
- evitar modales innecesarios;
- una acción principal por tarjeta.

---

## 18. DATOS QUE INICIO LEE

Inicio no posee copias.

Lee:

- Task
- Experiment
- Sample / PhysicalItem
- Evaluation
- Project
- ProductionLot
- Firing
- PurchaseNeed
- PurchaseOrder
- Inventory / Stock
- CostEntry
- JournalEntry reciente

---

## 19. LO QUE INICIO NO HACE

Inicio no debe:

- editar fórmulas completas;
- pesar materiales;
- configurar hornadas completas;
- administrar stock detallado;
- evaluar una tesela completa;
- cargar gastos complejos;
- duplicar información.

Inicio:
**resume, alerta, coordina y dirige.**

---

## 20. FLUJO DE EJEMPLO

Usuario abre ALUMINA.

Ve:

**Siguiente acción**
5 teselas listas para horno
→ Armar carga

Toca.

ALUMINA abre:
Operaciones > Quema > Pendientes de carga

Selecciona 5 teselas + 3 tazas.

Crea H-021.

Vuelve a Inicio.

Inicio se actualiza:

**Ahora**
H-021 · Programada
8 objetos

Las 5 teselas ya no aparecen como “listas para horno”.

Ese comportamiento es la referencia para la implementación.
