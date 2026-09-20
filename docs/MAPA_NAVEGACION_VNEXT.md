# ALUMINA STUDIO · MAPA DE NAVEGACIÓN VNEXT

Estado: propuesta consolidada para revisión antes de implementar.

## Navegación principal fija

Cabecera global siempre visible:
- Inicio
- LAB
- Taller
- Operaciones
- Aprender / Comunidad
- Buscador global
- Alertas
- Perfil / Configuración

Reglas:
- máximo 5 áreas principales;
- no duplicar navegación global dentro de cada área;
- móvil: cabecera compacta con menú táctil;
- módulo activo resaltado;
- volver a Inicio o buscar siempre disponible;
- acciones contextuales pueden saltar de un departamento a otro conservando el objeto activo.

---

## 1. INICIO

### Pantalla principal
Bloques:
1. Ahora / Hoy
2. Próxima acción
3. Agenda
4. Alertas
5. Compras y logística
6. Producción / Quema
7. Resultados pendientes
8. Actividad reciente
9. Accesos rápidos
10. Herramientas rápidas

### Tarjetas accionables
Ejemplos:
- “5 teselas listas para horno” → Operaciones > Quema > Pendientes de carga
- “H-014 enfriando · 68 °C” → Operaciones > Quema > H-014
- “Pedido DP Colors llega hoy” → Operaciones > Compras > Pedido
- “Retirar material 17:00” → Operaciones > Compras > Pedido
- “3 resultados pendientes” → LAB > Resultados
- “Sílice bajo mínimo” → Operaciones > Stock > Sílice
- “Faltan 2 kg de sílice” → Operaciones > Lista

### Accesos rápidos
- Nuevo ensayo
- Nueva fórmula
- Cámara / registrar resultado
- Nueva pieza
- Lista de compra
- Cargar horno
- Calculadoras
- Stock
- Costos

### Regla
Al entrar o volver a Inicio:
- refrescar estado automáticamente;
- no requerir botón “Actualizar”.

---

## 2. LAB

Subnavegación:
- Formular
- Ensayos
- Teselas / Muestras
- Resultados
- Herramientas químicas

### 2.1 Formular

Pantalla:
- Color objetivo
- Candidatos de pigmento
- ADN
- Perfil molar
- Fórmula
- Simulación visual
- Cómo preparar

Acciones:
- Guardar fórmula
- Continuar a ensayo
- Ver ficha de elemento
- Ver procedencia
- Crear variante

Condición:
sin candidato seleccionado:
- Perfil molar y bloques dependientes ocultos/desactivados;
- estado neutro, sin errores.

Transición:
Formular → Ensayo
con la misma fórmula enlazada, no copiada.

### 2.2 Ensayos

Pantalla:
- listado de ensayos;
- filtro por estado;
- ficha del ensayo;
- gramos;
- stock disponible;
- costo estimado;
- procedimiento.

Acciones:
- Iniciar preparación
- Registrar cantidades reales
- Crear tesela/muestra
- Añadir observación

Regla:
- iniciar preparación = registrar consumo físico;
- evitar botón separado sólo para “descontar”.

### 2.3 Teselas / Muestras

Pantalla:
- listado;
- estado físico;
- foto si existe;
- vínculo con ensayo;
- esquema de cocción;
- datos progresivos.

Estados:
- Creada
- En preparación
- Secando
- Seca
- Aplicada
- Lista para horno
- En hornada
- Cocida/Descargada
- Evaluada

Preguntas contextuales:
- peso húmedo;
- peso seco;
- medidas;
- técnica;
- capas;
- foto;
- absorción opcional.

Acciones:
- Editar datos
- Tomar foto
- Enviar a Horno
- Añadir varias seleccionadas a hornada

Transición:
Tesela Lista para horno → Operaciones > Quema

### 2.4 Resultados

Pantalla:
- pendientes de evaluar;
- evaluados;
- aprobados;
- parciales;
- fallidos;
- incompletos;
- archivados.

Ficha:
- foto principal;
- fotos adicionales;
- resultado técnico;
- valoración personal;
- defectos;
- comentario;
- decisión;
- antecedentes similares.

Acciones:
- Guardar evaluación
- Siguiente resultado
- Repetir ensayo
- Crear variante
- Aprobar fórmula
- Archivar
- Descartar físicamente

Regla:
descartar físicamente ≠ borrar registro.

Transición:
Resultado aprobado → Taller > Fórmulas
vinculando la misma fórmula.

### 2.5 Herramientas químicas

Selector táctil:
- Adición %
- Escalar / normalizar
- Moles ↔ gramos
- UMF / Seger
- Line blend
- Triaxial
- Contracción
- Absorción
- Densidad de barbotina
- Humedad
- LOI
- Tabla periódica

Una herramienta visible por vez.

---

## 3. TALLER

Subnavegación:
- Bitácora
- Fórmulas
- Producción

### 3.1 Bitácora

Pantalla:
- timeline cronológico;
- notas;
- fotos;
- incidencias;
- apuntes;
- referencias enlazadas.

Acciones:
- Nueva nota
- Añadir foto
- Vincular fórmula/ensayo/pieza/hornada
- Convertir/promocionar nota a fórmula

Regla:
no duplicar objetos enlazados.

### 3.2 Fórmulas

Vistas:
- Lista técnica
- Galería visual

Filtros:
- categoría
- procedencia
- estado
- temperatura
- favorito
- proyecto
- color / acabado

Ficha:
- composición;
- categoría;
- procedencia;
- fuente;
- estado;
- resultados vinculados;
- foto principal;
- historial de pruebas.

Acciones:
- Probar en LAB
- Crear variante
- Vincular resultado
- Favorito
- Archivar

### 3.3 Producción

Subpantallas:
- Proyectos / Series / Trabajos
- Piezas
- Lotes

#### Proyectos / Series / Trabajos
Ficha:
- estado;
- piezas;
- lotes;
- fórmulas;
- ensayos;
- teselas;
- compras;
- hornadas;
- costos;
- notas;
- pendientes.

Acciones:
- Nueva pieza
- Nuevo lote
- Añadir vínculo existente
- Ver costos
- Ver pendientes

#### Piezas
Ficha:
- ID;
- proyecto;
- tipo;
- pasta;
- peso seco;
- medidas;
- técnica;
- acabados;
- fórmulas;
- mono/bicocción;
- estado;
- costo.

Acciones:
- Añadir a lote
- Enviar a Quema
- Ver costos
- Añadir foto/nota

#### Lotes
Ficha:
- piezas incluidas;
- cantidad;
- proyecto;
- estado;
- costo parcial.

Acciones:
- Añadir/quitar piezas
- Enviar a Quema
- Ver costos

---

## 4. OPERACIONES

Subnavegación:
- Quema 🔥
- Compras
- Stock
- Lista
- Costos

### 4.1 Quema 🔥

Subpantallas:
- Hornos
- Programas
- Pendientes de carga
- Nueva hornada
- Activas
- Historial

#### Pendientes de carga
Recibe:
- teselas del LAB;
- piezas;
- lotes de producción.

Acción:
- seleccionar varios;
- crear hornada.

#### Hornada
Estados:
- Programada
- En cocción
- Enfriando
- Lista para abrir
- Abierta / Descargando
- Descargada
- Completada

Acciones por estado:
- Iniciar hornada
- Registrar temperatura
- Confirmar apertura
- Confirmar descarga
- Evaluar contenido

Regla:
al descargar:
- teselas → LAB > Resultados;
- piezas → ficha individual / producción;
- todos conservan ID.

### 4.2 Lista

Pantalla:
- necesidades pendientes;
- origen de necesidad;
- prioridad;
- proveedor sugerido;
- cantidad requerida.

Acciones:
- agregar manual;
- editar;
- agrupar;
- convertir en pedido.

### 4.3 Compras

Subpantallas:
- Por pedir
- Pedidos activos
- Llega hoy
- Retirar
- Recibidos
- Proveedores
- Historial

Estados:
- Por pedir
- Pedido
- En espera
- En camino
- Llega hoy
- Listo para retirar
- Recibido
- Cancelado

Transición:
Recibido → Stock

### 4.4 Stock

Pantalla:
- materiales;
- cantidad actual;
- stock mínimo;
- ubicación;
- lotes/envases;
- alertas.

Ficha de material:
- cantidad;
- movimientos;
- lotes;
- ficha técnica;
- proveedor;
- historial.

Acciones:
- entrada;
- salida manual;
- ajuste físico;
- ver ficha técnica;
- añadir a Lista.

### 4.5 Costos

Subpantallas:
- Resumen
- Gastos generales
- Costeo por proyecto
- Costeo por pieza
- Costeo por lote
- Costeo por hornada

Filtros:
- Hoy
- Semana
- Mes
- Año
- Personalizado

Resumen:
- directos;
- indirectos;
- mano de obra;
- contingencia;
- total.

---

## 5. APRENDER / COMUNIDAD

Se conserva como área principal, pero fuera del núcleo de la primera reestructuración.

### Aprender
- Técnicas
- Escuelas / tradiciones
- Prácticas / cursos
- Seguridad
- Referencias

### Comunidad
- Fórmulas compartidas
- Resultados compartidos
- Replicaciones
- Aportes / comentarios

Regla:
Comunidad referencia objetos existentes cuando corresponda; no crear copias innecesarias.

---

## TRANSICIONES ENTRE DEPARTAMENTOS

### LAB → Operaciones
Tesela lista para horno
→ Enviar a Horno
→ Operaciones > Quema > Pendientes de carga

### Operaciones → LAB
Hornada descargada
→ teselas individuales
→ LAB > Resultados > Pendientes de evaluación

### Taller → LAB
Fórmula
→ Probar en LAB

### LAB → Taller
Resultado aprobado
→ vincular/promover fórmula
→ Taller > Fórmulas

### Taller → Operaciones
Pieza / lote
→ Enviar a Quema

### Operaciones → Taller
Hornada descargada
→ piezas vuelven a Producción con estado actualizado

### Stock → Lista
Stock bajo
→ Añadir a Lista

### Lista → Compras
Seleccionar necesidades
→ Crear pedido

### Compras → Stock
Pedido recibido
→ registrar entrada

### Todo → Inicio
Cualquier cambio relevante
→ Inicio lo refleja automáticamente

---

## CONFIGURACIÓN Y PERFIL

Acceso desde cabecera, no como departamento principal.

### Perfil
- identidad;
- idioma;
- unidades;
- apariencia;
- notificaciones;
- accesibilidad.

### Configuración del taller
- horno habitual;
- tarifa;
- valor/hora;
- contingencia;
- margen;
- stock mínimo;
- temperaturas habituales;
- esquema de cocción;
- etiquetas;
- costeo;
- proveedor habitual.

---

## BUSCADOR GLOBAL

Acceso fijo en cabecera.

Busca:
- IDs;
- nombres;
- materiales;
- fórmulas;
- teselas;
- resultados;
- piezas;
- lotes;
- hornadas;
- pedidos;
- proveedores;
- bitácora;
- proyectos.

Resultado:
- agrupado por tipo;
- tocar abre objeto original.

---

## Regla de diseño

No construir pantallas que repitan datos.
Construir vistas distintas sobre objetos compartidos.

Cada transición debe conservar:
- ID;
- relaciones;
- procedencia;
- historial;
- costos;
- fotos;
- estado.
