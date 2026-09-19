# Migración inicial a GitHub

Repositorio: `pedrinskypoint/ALUMINA-STUDIO`

## Regla nueva

GitHub será la **fuente oficial del código**. Los `.py` unificados y notebooks Colab serán artefactos generados, no el lugar donde se edita el proyecto.

## Ramas sugeridas

- `main`: base estable.
- `develop`: integración de cambios.
- `feature/...`: funciones puntuales.

## Publicación inicial

1. Publicar la base modular R3 en `main`.
2. Crear `develop` desde `main`.
3. Trabajar por ramas/PR y exigir QA antes de fusionar.
