# ALUMINA STUDIO · R5 PASO A LIMPIO A1

Estado: checkpoint técnico para validación manual en Colab/iPhone.

## Principio

R3 DEMO continúa siendo el patrón funcional. R5 no reescribe el motor cerámico: conserva datos, química, calculadoras, pastas, stock, horno y renderers probados, y coloca encima una nueva organización modular.

## Estructura

- Inicio
- LAB
- Taller
- Operaciones
- Aprender / Comunidad

LAB:
- Formular
- Ensayos
- Teselas / Muestras
- Resultados
- Herramientas

Taller:
- Bitácora
- Fórmulas
- Producción

Operaciones:
- Quema
- Compras
- Stock
- Lista
- Costos

Flujo experimental:
Fórmula → Ensayo → Preparación → Tesela/Muestra → Quema → Descarga → Resultado.

## Decisión UI

La navegación interna usa Radio + Group, evitando depender de cambios programáticos de gr.Tab. El objetivo es reducir bloqueos y estados visuales inconsistentes en Gradio móvil.

## Arquitectura modular

- data/reference.py
- core/models.py
- core/chemistry.py
- core/calculators.py
- services/domain.py
- services/demo_r3.py
- services/workflow_vnext.py
- services/demo_vnext.py
- ui/renderers.py
- ui/renderers_vnext.py
- ui/callbacks.py
- ui/app.py

## QA

- pytest modular: 4/4 PASS
- comparación motor/flujo: 31/31 PASS
- py_compile: PASS
- build_app: PASS
- servidor Gradio local HTTP 200: PASS
- 430 componentes / 107 dependencias
- 118 elementos / 59 materiales / 8 programas / 4 fórmulas de pasta preservados
- doble descuento de stock bloqueado
- demo accionable
- apertura / descarga / completado de hornada separados

## Regla de promoción

R5 A1 no reemplaza R3 como base oficial hasta que el usuario complete una prueba manual satisfactoria en Colab/iPhone.
