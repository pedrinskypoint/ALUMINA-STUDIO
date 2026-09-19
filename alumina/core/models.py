from __future__ import annotations
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Any, Generic, Protocol, TypeVar
import copy
T = TypeVar('T')

@dataclass
class NavigationState:
    module: str = 'Inicio'
    section: str | None = None

class ExperimentStatus(str, Enum):
    PLANIFICADO = 'Planificado'
    PESADO = 'Pesado'
    MEZCLADO = 'Mezclado'
    APLICADO = 'Aplicado'
    SECANDO = 'Secando'
    LISTO_HORNO = 'Listo para horno'
    EN_COCCION = 'En cocción'
    COCIDO = 'Cocido'
    EVALUADO = 'Evaluado'
    CERRADO = 'Cerrado'

class Repository(Protocol, Generic[T]):
    """Boundary for durable state. R3 uses the in-memory adapter; SQLite can replace it in V15."""

    def get(self, key: str) -> T | None:
        ...

    def put(self, key: str, value: T) -> None:
        ...

    def all(self) -> dict[str, T]:
        ...

@dataclass
class InMemoryRepository(Generic[T]):
    _records: dict[str, T] = field(default_factory=dict)

    def get(self, key: str) -> T | None:
        return self._records.get(key)

    def put(self, key: str, value: T) -> None:
        self._records[str(key)] = value

    def all(self) -> dict[str, T]:
        return copy.deepcopy(self._records)

@dataclass
class MaterialSpeciesYield:
    material_id: str
    target_species: str
    mol_target_per_mol_material: float
    assay: float = 1.0
    basis: str = 'estequiométrica'

    def equivalent_mass_g_per_target_mol(self, material_molar_mass: float) -> float:
        denom = float(self.mol_target_per_mol_material) * float(self.assay)
        if denom <= 0:
            raise ValueError('Rendimiento molar/pureza inválido')
        return float(material_molar_mass) / denom

@dataclass
class RecipeComponent:
    material_id: str
    grams: float
    role: str

@dataclass
class DraftRecipe:
    pigment_id: str
    vehicle: str
    base_formula_name: str
    base_mass_g: float
    pigment_pct: float
    pigment_formula: str
    profile: dict[str, float]
    components: tuple[RecipeComponent, ...]
    optical_base: str
    clay_body: str
    temperature_c: float
    atmosphere: str

    @property
    def pigment_grams(self) -> float:
        return sum((c.grams for c in self.components if c.role == 'pigment'))

    @property
    def total_grams(self) -> float:
        return sum((c.grams for c in self.components))

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d['components'] = [asdict(c) for c in self.components]
        return d
