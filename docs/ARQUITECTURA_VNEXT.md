# ALUMINA STUDIO · ARQUITECTURA VNEXT

Estado: congelado conceptualmente a partir de la revisión de ALUMINA_STUDIO_V14E4_CLEAN_R3_DEMO_COLAB.ipynb.

## Principio central

ALUMINA no debe funcionar como una colección de módulos aislados.

Cada objeto existe una sola vez y los distintos departamentos lo consultan, modifican su estado o lo relacionan.

**Un objeto = un registro único = múltiples vistas y relaciones.**

Ejemplo:
- una fórmula F-014 se ve en Taller > Fórmulas;
- LAB la usa sin copiarla;
- una tesela puede vincularse a F-014;
- Resultados muestra el resultado de esa prueba;
- Costos consulta los movimientos asociados;
- Inicio sólo resume su estado.

## Estructura principal

### 1. INICIO

Rol: productor/coordinador del taller.

Debe responder:
- qué está ocurriendo;
- qué requiere atención;
- qué viene después;
- qué compras/pedidos están en espera;
- qué llega hoy;
- qué hay que retirar;
- qué teselas/piezas están listas para horno;
- qué hornadas están en cocción o enfriando;
- qué resultados faltan evaluar.

Elementos:
- Ahora / Hoy.
- Próxima acción.
- Alertas.
- Compras y logística.
- Actividad reciente.
- Accesos rápidos.
- Herramientas rápidas.

Reglas:
- todo es táctil y accionable;
- tocar una tarjeta lleva al objeto exacto;
- al volver a Inicio, se actualiza automáticamente;
- no requiere botón manual de Actualizar.

### 2. LAB

Rol: investigación, formulación, ensayo y evaluación experimental.

#### 2.1 Formular

Flujo:
Color → Pigmento → ADN → Perfil molar → Fórmula.

Concepto:
la fórmula en esta etapa es una hipótesis.

Acciones:
- Guardar fórmula.
- Continuar a ensayo.

Ajustes:
- acercar slider de % de pigmento a la simulación visual;
- mostrar rangos reales por componente en Perfil molar;
- no asumir 0–1 para todos;
- al tocar un elemento del ADN, abrir ficha contextual;
- fórmula debe incluir vista “Cómo preparar”.

Ejemplo de preparación:
- sólidos;
- agua;
- defloculante;
- orden de incorporación;
- mezcla/reposo/tamizado;
- densidad/viscosidad objetivo cuando corresponda.

Si no hay candidato seleccionado:
- no ejecutar Perfil molar ni cálculos dependientes;
- mostrar estado neutro “Seleccioná un candidato para continuar”.

#### 2.2 Ensayo / Preparación

Rol:
convertir una hipótesis en una preparación física real.

Al seleccionar ensayo:
- mostrar automáticamente gramos;
- stock;
- costo estimado;
- procedimiento.

No usar un botón separado sólo para “calcular/pesar”.

Cuando se inicia físicamente la preparación:
- registrar consumo;
- descontar stock una sola vez;
- permitir corregir cantidad real usada.

#### 2.3 Teselas / Muestras

Rol:
objeto físico derivado del ensayo.

Identidad:
- Ensayo: AL-001
- Teselas: AL-001-T01, AL-001-T02...
- nunca reutilizar IDs;
- los IDs no se reciclan aunque se archive o elimine visualmente un registro.

Estados físicos sugeridos:
- Creada
- En preparación
- Secando
- Seca
- Aplicada
- Lista para horno
- En hornada
- Cocida/Descargada
- Evaluada

Captura progresiva:
- húmeda: peso y medidas;
- seca: peso y medidas;
- aplicada: técnica/capas;
- bizcochada, si aplica: peso y medidas;
- cocida: peso, medidas, foto;
- absorción opcional.

La ficha se completa por etapas, no con un formulario enorme al principio.

Esquema de cocción:
- Monococción.
- Bicocción.

Bicocción:
Formada → Seca → Bizcocho → Descargada/Bizcochada → Aplicada/Esmaltada → Segunda cocción → Descargada → Resultado.

La pieza/tesela mantiene el mismo ID a través de todas las hornadas.

Acción desde Tesela:
**Enviar a Horno / Añadir a carga de horno.**

#### 2.4 Resultados

Nombre recomendado para lo que antes se llamaba Registro.

Rol:
evaluación post-horno de pruebas y teselas.

Ficha:
- foto;
- estado técnico: Funcionó / Parcial / Falló;
- valoración: Me gusta / Neutro / No me gusta / Favorito;
- defectos;
- comentario;
- decisión: Conservar / Repetir / Ajustar / Archivar / Descartar físicamente.

Reglas:
- descartar físicamente no borra el registro digital;
- los fallos se conservan;
- evaluación sólo después de descarga;
- comentarios deben ser cómodos en móvil;
- textarea estable, sin salto de scroll durante escritura;
- flujo “Guardar → Siguiente tesela”.

Cámara:
- Tomar foto.
- Elegir de galería.
- varias fotos por resultado;
- foto principal;
- mantener comentarios al volver de cámara.

Memoria experimental:
- detectar prueba exacta ya realizada;
- detectar prueba similar;
- advertir si una combinación ya falló;
- advertir si ya funcionó;
- permitir continuar;
- crear huella experimental por fórmula + pigmento + % + pasta/base + temperatura + atmósfera + programa.

Tesela aprobada:
- puede promover/vincular su fórmula a Fórmulas;
- no copiar sin trazabilidad;
- conservar vínculo con ensayo, foto, pasta, temperatura, horno, hornada, fecha y resultado.

### 3. TALLER

Rol:
memoria práctica, conocimiento reutilizable y producción.

#### 3.1 Bitácora

Cuaderno cronológico:
- notas;
- fotos;
- fórmulas manuales;
- incidencias;
- apuntes;
- observaciones;
- vínculos a fórmula, ensayo, tesela, hornada, pieza, pedido.

Una nota puede convertirse/promocionarse a fórmula sin duplicar el contenido.

#### 3.2 Fórmulas

Es la biblioteca técnica principal.

No crear un módulo separado “Biblioteca”.

Vistas sobre la misma colección:
- Lista técnica.
- Galería visual.

La galería usa fotos de resultados vinculados; no duplica datos.

Categorías técnicas:
- esmaltes/bases;
- engobes;
- acuarelas cerámicas;
- barbotinas;
- pastas;
- pigmentos/preparaciones;
- otros.

Procedencia:
- propia;
- estándar/publicada;
- comunidad;
- Glazy/referencia externa;
- clase;
- apunte;
- libro/artículo;
- fabricante;
- anónima.

Estado/confianza:
- Borrador.
- Experimental.
- Aprobada en taller.
- Repetida.
- Validada/replicada.
- Archivada.

Acciones:
- Probar en LAB.
- Crear variante.
- Vincular resultado.
- Marcar favorita.
- Archivar.

#### 3.3 Producción

Subáreas:
- Proyectos / Series / Trabajos.
- Piezas.
- Lotes.

##### Proyecto / Serie / Trabajo

Ubicación:
Taller > Producción.

No es un módulo global separado.

Proyecto es la entidad general.
- Serie = tipo de proyecto.
- Trabajo = tipo de proyecto/encargo.

Un proyecto relaciona sin copiar:
- piezas;
- lotes;
- fórmulas;
- ensayos;
- teselas;
- compras;
- hornadas;
- costos;
- notas.

Permite consultar:
- cuánto gasté;
- qué falta;
- qué pruebas hice;
- qué hornadas pertenecen;
- qué piezas están pendientes.

##### Pieza

Ficha de objeto físico de producción:
- ID único;
- tipo;
- pasta;
- peso seco;
- medidas;
- técnica;
- acabados;
- fórmula/engobe/esmalte;
- mono/bicocción;
- estado;
- costo estimado/real.

Costo por peso seco cuando corresponda, más mano de obra, acabados y hornada.

Acción:
**Añadir a lote.**

##### Lote de producción

Agrupa piezas para organizar trabajo.

No es una hornada.

Un lote:
- conserva IDs individuales;
- puede ser de piezas iguales o mixtas;
- luego puede enviarse a Quema.

### 4. OPERACIONES

Submódulos:
- Quema 🔥
- Compras
- Stock
- Lista

#### 4.1 Quema 🔥

Incluye:
- hornos;
- programas;
- pendientes de carga;
- nueva carga/hornada;
- en cocción;
- enfriando;
- apertura;
- descarga;
- historial.

Flujo de hornada:
Programada → En cocción → Enfriando → Lista para abrir → Abierta/Descargando → Descargada → Completada.

No usar “Terminar hornada” de forma ambigua.

Acciones contextuales:
- Registrar temperatura.
- Confirmar apertura.
- Confirmar descarga.
- Evaluar contenido.

La hornada es un agrupador temporal:
- teselas;
- piezas;
- lotes.

Durante la cocción:
- se gestionan juntas;
- mantienen sus IDs individuales.

Al descargar:
- vuelven a su identidad individual;
- teselas → LAB > Resultados;
- piezas → su ficha de producción/evaluación.

Costo energético:
- calculado desde horno + programa + duración/factor;
- ocupación sirve para analítica y reparto de costos, no para inventar consumo.

Bug a corregir:
- nueva hornada debe iniciar limpia;
- nunca heredar datos de hornada finalizada anterior.

#### 4.2 Lista

Lista/carrito de necesidades, anterior a una compra real.

Fuentes:
- stock bajo;
- faltante detectado por fórmula/ensayo;
- necesidad de producción;
- agregado manual.

Acciones:
- agregar/quitar;
- editar cantidad;
- agrupar por proveedor;
- prioridad;
- convertir selección en pedido.

Flujo:
Necesidad → Lista → Pedido/Compra → Recibido → Stock.

#### 4.3 Compras

Estados:
- Por pedir.
- Pedido realizado.
- En espera.
- En camino.
- Llega hoy.
- Listo para retirar.
- Recibido.
- Cancelado.

Incluye proveedores e historial.

Inicio debe mostrar:
- pedido en espera;
- llega hoy;
- retirar;
- retrasos.

#### 4.4 Stock

Stock = existencia física real.

Responde:
**qué tengo y cuánto tengo.**

Incluye:
- material;
- cantidad;
- lotes/envases;
- entradas/salidas;
- stock mínimo;
- movimientos;
- verificación física;
- futuro QR.

Movimiento de ejemplo:
- Compra +1000 g.
- Ensayo -15 g.
- Uso manual -20 g.
- Ajuste físico +8 g.

No crear un módulo paralelo “Estante” que duplique Stock.

Material = identidad/ficha técnica.
Stock = cantidad física disponible.

La ficha técnica del material puede abrirse desde Stock o desde LAB.

### 5. COSTOS

Rol:
estado económico del taller + costeo de producción.

Períodos:
- Hoy.
- Semana.
- Mes.
- Año.
- Personalizado.

Resumen:
- Directos.
- Indirectos.
- Mano de obra.
- Contingencia/imprevistos.
- Total.

Directos:
- materiales;
- energía asignada;
- embalaje específico;
- consumibles vinculados.

Indirectos:
- alquiler;
- expensas;
- electricidad base;
- agua/gas general;
- mantenimiento;
- amortización;
- limpieza;
- software;
- administración;
- seguros.

Mano de obra:
- directa;
- indirecta.

Contingencia:
- separada de gasto real.

Margen comercial:
- separado del costo.

Estados:
- Estimado.
- Real/registrado.
- Imputado.
- Pendiente.

Costos debe leer movimientos existentes y no duplicar cargas.

Gestión:
- Configuración > Costos del taller: valores base.
- Costos > Gastos generales: movimientos reales.
- Costos > Resumen: estado por período.

No recalcular históricos con valores actuales.

## CABECERA FIJA Y NAVEGACIÓN

La cabecera debe permanecer visible durante scroll.

Debe contener:
- ALUMINA;
- módulo actual;
- menú global;
- buscador global;
- alertas;
- perfil/configuración.

En móvil:
- compacta;
- táctil;
- sin overflow;
- botones 44–48 px mínimo.

## BUSCADOR GLOBAL

Accesible desde cabecera.

Debe buscar:
- IDs;
- nombres;
- materiales;
- fórmulas;
- teselas/resultados;
- piezas;
- lotes;
- hornadas;
- pedidos;
- proveedores;
- notas;
- proyectos.

Búsqueda incremental.
Resultados agrupados por tipo.
Tocar abre el registro original.

## CONFIGURACIÓN / DATOS MAESTROS

### Perfil / Usuario

Sólo preferencias personales:
- nombre/taller;
- idioma;
- unidades;
- apariencia;
- notificaciones;
- accesibilidad.

### Configuración del Taller

Defaults y políticas:
- horno habitual;
- tarifa eléctrica por defecto;
- valor/hora;
- contingencia;
- margen;
- stock mínimo global;
- temperaturas habituales;
- esquema de cocción por defecto;
- formato de etiquetas;
- criterios de costeo;
- proveedor habitual.

Regla:
Config referencia objetos reales, no los duplica.

Ejemplo:
HN-02 vive en Quema.
Config guarda default_kiln_id = HN-02.

## PROCEDENCIA Y TRAZABILIDAD

Transversal a todo el sistema.

Guardar:
- tipo de fuente;
- autor;
- fecha;
- enlace/referencia;
- confianza;
- evidencia;
- relación con resultados.

Clasificación de procedencia:
- FUENTE PRIMARIA;
- ACADÉMICA;
- COMUNIDAD;
- FABRICANTE;
- EXPERIMENTAL.

Comunidad:
- individual;
- replicada.

Además distinguir:
- cálculo exacto/estequiométrico;
- modelo publicado;
- estimación/heurística;
- resultado experimental.

La procedencia nunca desaparece al aprobar una fórmula.

## ARCHIVO, NO BORRADO

Regla:
- archivar es normal;
- eliminar definitivamente es excepcional;
- fallos, fórmulas viejas, proyectos, piezas y pedidos deben conservar historial;
- IDs nunca se reutilizan.

## BACKUP / EXPORTACIÓN

Requisito antes de considerar ALUMINA una herramienta de largo plazo.

Debe permitir:
- exportar proyecto;
- exportar fórmulas;
- exportar resultados/fotos;
- exportar stock/costos;
- copia completa del taller;
- restaurar copia.

## APRENDER Y COMUNIDAD

Se mantienen en roadmap.

No forman parte del núcleo de esta reestructuración.

Prioridad actual:
Inicio + LAB + Taller + Operaciones + Costos.

Después:
- Aprender.
- Comunidad.

## VOZ CONTEXTUAL

Idea futura ya aceptada.

Botón de micrófono contextual.

Usos:
- navegar;
- buscar;
- consultar stock;
- registrar cantidades;
- registrar temperatura;
- avanzar estados;
- dictar observaciones.

Seguridad:
- consulta: directa;
- acción reversible: ejecutar y mostrar;
- acción sensible: pedir confirmación.

## PRINCIPIOS UX

- táctil primero;
- muy poco teclado;
- botones grandes;
- tarjetas completas seleccionables;
- sliders gruesos;
- feedback inmediato;
- acciones contextuales;
- una columna en móvil;
- no mover la pantalla mientras se escribe;
- no perder contexto al usar cámara;
- Inicio siempre actualizado;
- navegación global siempre accesible.

## FLUJO EJEMPLO COMPLETO

F-014 · Naranja Talavera
→ LAB
→ AL-032
→ preparación 50 g
→ AL-032-T01
→ secado/aplicación
→ Enviar a Quema
→ H-021 junto a otras piezas
→ cocción/enfriado/apertura/descarga
→ AL-032-T01 vuelve a LAB > Resultados
→ foto + evaluación
→ Funcionó / Me gusta / Aprobada
→ F-014 se vincula como Aprobada en taller
→ la foto principal aparece en Galería de Fórmulas
→ Stock ya registró consumos
→ H-021 aporta costo energético
→ Costos consolida
→ si pertenece a PR-004, el proyecto lo relaciona
→ una futura prueba equivalente genera aviso de antecedente.

## Próximo paso recomendado

1. Congelar esta arquitectura como especificación.
2. Dibujar mapa de navegación y estados.
3. Definir modelo de datos/entidades y relaciones.
4. Definir migración desde R3 DEMO.
5. Construir esqueleto de navegación y repositorio único.
6. Implementar flujo LAB → Quema → Resultados.
7. Integrar Taller/Producción.
8. Integrar Operaciones/Compras/Stock.
9. Integrar Costos.
10. QA móvil y tests de regresión antes de expandir.
