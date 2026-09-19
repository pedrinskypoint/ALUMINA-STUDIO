# V14E.4 CLEAN R4 · FLOW UX

Estado: **demo funcional para validación de usuario**.

## Objetivo

Reordenar ALUMINA según el proceso real de taller y corregir los problemas detectados durante la prueba móvil de R3.

Ruta principal:

**Laboratorio → Ensayos → Horno → Evaluación → Tesela**

Capas transversales:

**Taller / Stock / Compras / Costos**

## Cambios incorporados

- Horno queda antes de Teselas en la navegación principal.
- Evaluación post-cocción sólo aparece para ensayos Cocido/Evaluado.
- Ensayo Listo para horno ofrece continuidad hacia Horno.
- Nueva hornada prioriza: ensayos listos → horno → programa.
- Programas de horno incluyen etapas, rampas, mesetas y duración.
- Unidad de rampa configurable entre °C/min y °C/h.
- El programa carga temperatura/duración y revisa compatibilidad con ensayos.
- Slider de pigmento se agrupa con su simulación visual y masa calculada.
- Tabla periódica visible con 118 elementos y ficha seleccionable.
- Tabla visual de materias primas cerámicas.
- Calculadoras se abren como herramienta/modal en vez de crecer hacia abajo.
- Medio/aplicación ampliado a Esmalte, Engobe, Bajo cubierta / underglaze, Pasta coloreada y Barbotina coloreada.
- Costos se muestran como parciales hasta incorporar hornada ejecutada/finalizada.

## Límites conscientes

- Wash/pátina queda pendiente de un motor propio; no se fuerza a porcentaje sobre base.
- Las curvas de horno son referencias de taller y deben validarse con manual/controlador y cono testigo.
- ALUMINA no infiere temperatura real por cronómetro; sigue requiriendo lectura del controlador.

## Criterio de validación

No cerrar esta revisión hasta que el flujo completo funcione en móvil:

Laboratorio → Ensayo → Pesado/Stock → Listo para horno → Hornada → Cocido → Evaluación → Tesela → Costo completo.
