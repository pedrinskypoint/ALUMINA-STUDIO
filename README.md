# ALUMINA STUDIO

## V17.4 · Correcciones de la revisión funcional · versión de prueba

Ver [correcciones y límites V17.4](docs/REVISION_V17_4.md).

El refresco universal se reemplazó por salidas específicas de cada acción. Los callbacks leen entidades bajo demanda y confirman las escrituras en SQLite antes de responder. La búsqueda usa FTS5 y filtros SQL; las coincidencias de color usan CIEDE2000. Ver [alcance y validación V17.3](docs/RESPUESTA_V17_3.md).

Base recuperada de V16 DEMO FIX3, con navegación **LAB / TALLER / SABER** y una primera migración operativa a SQLite. Esta entrega prioriza persistencia, conflictos entre sesiones, fotos durables, movimientos de stock y etapas de horno antes de ampliar la interfaz.

Correcciones de esta entrega: [navegación y herramientas](docs/NAVEGACION_V17_2.md).

Ver [garantías y límites](docs/MOTOR_V17_1.md) y [diagramación](docs/DIAGRAMACION_V17.md).

## Ejecutar

```bash
pip install -r requirements.txt
python run.py
```

La carpeta predeterminada es `./alumina_data`. Se puede configurar `ALUMINA_DATA_DIR` antes de ejecutar la app. Sin datos se crea un taller de demostración.

## Archivo único para Colab

```bash
python scripts/export_colab.py
```

Genera `build/ALUMINA_STUDIO_V17_4_REVISION.py`, con motor e interfaz incluidos. En Colab, instalar `gradio==6.5.1` y `numpy==2.3.5`, subir el archivo y ejecutarlo con `%run ALUMINA_STUDIO_V17_4_REVISION.py`.

La carpeta temporal de Colab desaparece al terminar el entorno. Descargar una copia ZIP desde Parámetros antes de cerrarlo y restaurarla en la siguiente sesión. No ejecutar varias instancias de SQLite sobre una carpeta sincronizada de Drive: la protección de sesiones está probada dentro de una base local compartida, no entre runtimes de Colab.

## Validación actual

```bash
pytest tests/test_engine.py tests/test_navigation.py tests/test_workbench.py tests/test_scoped_repository.py tests/test_revision.py -q
python scripts/export_colab.py
python build/ALUMINA_STUDIO_V17_4_REVISION.py --qa
```

El modo `--qa` utiliza una carpeta temporal aislada. El workflow específico valida este motor y la navegación con Python 3.11.

La migración modular R3 histórica sigue incompleta: sus tests requieren módulos ausentes (`alumina.ui`, `services`, `data` y `core.chemistry`). Se conservan esas pruebas y su workflow, pero no representan la validación de la aplicación recuperada.
