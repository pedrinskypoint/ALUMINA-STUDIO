# ALUMINA STUDIO V14E.4 CLEAN R3 DEMO — QA

- 13/13 tests PASS.
- build_app(): PASS.
- Escenario Taller demo: PASS.
- Escenario Flujo completo: PASS (Planificado + Listo para horno + Cocido).
- Escenario Hornada lista para cerrar: PASS (Enfriando + 45 °C).
- Stock demo no negativo: PASS.
- Python unificado compila: PASS.

## Hallazgo corregido durante el demo

El modo demo expuso un bug estructural de R3: varios modelos (`RecipeComponent`, `DraftRecipe`, `MaterialSpeciesYield`, `InMemoryRepository`, `NavigationState`) habían perdido el decorador `@dataclass` durante la unificación/refactor. Se corrigió antes de generar los artefactos de migración.
