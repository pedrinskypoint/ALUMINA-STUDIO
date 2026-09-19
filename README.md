# ALUMINA STUDIO

Base modular migrada desde **V14E.4 CLEAN R3**. Google Colab queda como superficie de demo; el repositorio pasa a ser la fuente de verdad del desarrollo.

## Flujo maestro

Color → Pigmento → ADN / perfil molar → Fórmula → Ensayo → Pesado / Stock → Hornada → Costos → Resultado → Tesela.

## Estructura

- `alumina/data/`: tablas y datos de referencia.
- `alumina/core/`: modelos y cálculos puros.
- `alumina/services/`: operaciones de dominio y escenarios demo.
- `alumina/ui/`: Gradio + renderizadores.
- `tests/`: pruebas automáticas.
- `scripts/build_unified.py`: genera el `.py` único para Colab.
- `notebooks/`: Colab de demostración.

## Ejecutar local / Codespaces

```bash
pip install -r requirements.txt
python run.py
```

## Tests

```bash
pytest -q
```

## Generar Python unificado para Colab

```bash
python scripts/build_unified.py
```

## Modo Demo

En `Configuración → Demo` hay tres escenarios:

1. **Taller demo**: stock + horno, sin ensayos.
2. **Flujo completo**: un ensayo Planificado, uno Listo para horno y uno Cocido, más historial/costos.
3. **Hornada lista para cerrar**: hornada en Enfriando con 45 °C registrados, para probar el cierre.

`Borrar demo` devuelve la sesión a estado vacío. Los datos demo no son persistentes.

## Persistencia

R3 mantiene memoria temporal detrás de la frontera de repositorio. SQLite/QR durable se reserva para V15.
