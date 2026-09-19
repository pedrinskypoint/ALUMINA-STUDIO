from __future__ import annotations
from typing import Any
import re
from ..data.reference import MATERIAL_MASTER

MATERIAL_PM = {
    material_id: float(material.get('peso_molecular'))
    for material_id, material in MATERIAL_MASTER.items()
    if material.get('peso_molecular')
}

def _number(value: Any, label: str, *, minimum: float | None=None) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f'{label}: valor numérico inválido.') from exc
    if minimum is not None and result < minimum:
        raise ValueError(f'{label}: debe ser ≥ {minimum}.')
    return result

def calculate_addition(base_g: Any, pct: Any) -> dict[str, float]:
    base = _number(base_g, 'Base', minimum=0.0)
    percentage = _number(pct, 'Porcentaje', minimum=0.0)
    addition = base * percentage / 100.0
    return {'base_g': base, 'pct': percentage, 'addition_g': addition, 'total_g': base + addition}

def parse_recipe_text(text: str) -> list[tuple[str, float]]:
    items: list[tuple[str, float]] = []
    for raw in str(text or '').splitlines():
        match = re.match('(.+?)[\\s,:;]+([0-9]+(?:[.,][0-9]+)?)\\s*%?$', raw.strip())
        if match:
            items.append((match.group(1).strip(' -\t'), float(match.group(2).replace(',', '.'))))
    return items

def calculate_scaled_recipe(text: str, total_g: Any) -> list[dict[str, float | str]]:
    items = parse_recipe_text(text)
    if not items:
        raise ValueError('Una línea por material: Frita 60')
    source_total = sum((value for _, value in items))
    if source_total <= 0:
        raise ValueError('La suma de la receta debe ser mayor que cero.')
    target = _number(total_g, 'Total', minimum=0.0)
    return [{'name': name, 'source_value': value, 'grams': target * value / source_total} for name, value in items]

def calculate_moles(material_id: str, mode: str, quantity: Any) -> dict[str, Any]:
    if material_id not in MATERIAL_MASTER or material_id not in MATERIAL_PM:
        raise ValueError('Elegí una materia prima con peso molecular válido.')
    q = _number(quantity, 'Cantidad', minimum=0.0)
    pm = MATERIAL_PM[material_id]
    material = MATERIAL_MASTER[material_id]
    if mode == 'Moles → gramos':
        result = q * pm
        result_unit = 'g'
    elif mode == 'Gramos → moles':
        result = q / pm
        result_unit = 'mol'
    else:
        raise ValueError('Modo de conversión no reconocido.')
    return {'material_id': material_id, 'name': material.get('nombre', material_id), 'formula': material.get('formula', '—'), 'molar_mass_g_mol': pm, 'mode': mode, 'quantity': q, 'result': result, 'result_unit': result_unit}

def calculate_shrinkage(initial_length: Any, final_length: Any) -> float:
    initial = _number(initial_length, 'Longitud inicial')
    final = _number(final_length, 'Longitud final')
    if initial <= 0:
        raise ValueError('La longitud inicial debe ser mayor que cero.')
    return (initial - final) / initial * 100.0

def calculate_absorption(dry_weight: Any, wet_weight: Any) -> float:
    dry = _number(dry_weight, 'Peso seco')
    wet = _number(wet_weight, 'Peso húmedo')
    if dry <= 0:
        raise ValueError('El peso seco debe ser mayor que cero.')
    return (wet - dry) / dry * 100.0

def calculate_line_blend(total_g: Any, steps: Any) -> list[dict[str, float | int]]:
    total = _number(total_g, 'Gramos por muestra', minimum=0.0)
    try:
        n = int(steps)
    except (TypeError, ValueError) as exc:
        raise ValueError('La cantidad de pasos debe ser un entero.') from exc
    if n < 2:
        raise ValueError('Usá al menos 2 pasos.')
    result = []
    for index in range(n):
        b = index / (n - 1)
        a = 1.0 - b
        result.append({'index': index + 1, 'a_pct': a * 100, 'b_pct': b * 100, 'a_g': total * a, 'b_g': total * b})
    return result

def calculate_density(mass_g: Any, volume_ml: Any) -> float:
    mass = _number(mass_g, 'Masa', minimum=0.0)
    volume = _number(volume_ml, 'Volumen')
    if volume <= 0:
        raise ValueError('El volumen debe ser mayor que cero.')
    return mass / volume

def calculate_humidity(wet_weight: Any, dry_weight: Any) -> dict[str, float]:
    wet = _number(wet_weight, 'Peso húmedo')
    dry = _number(dry_weight, 'Peso seco', minimum=0.0)
    if wet <= 0 or wet < dry:
        raise ValueError('El peso húmedo debe ser > 0 y ≥ al peso seco.')
    water = wet - dry
    return {'water_g': water, 'wet_basis_pct': water / wet * 100.0, 'dry_basis_pct': water / dry * 100.0 if dry > 0 else 0.0}

def calculate_loi(dry_weight: Any, fired_weight: Any) -> dict[str, float]:
    dry = _number(dry_weight, 'Peso seco')
    fired = _number(fired_weight, 'Peso cocido', minimum=0.0)
    if dry <= 0:
        raise ValueError('El peso seco debe ser mayor que cero.')
    loss = dry - fired
    return {'loss_g': loss, 'loi_pct': loss / dry * 100.0}

def calculate_triaxial(total_g: Any, divisions: Any) -> list[dict[str, float | int]]:
    total = _number(total_g, 'Gramos por muestra')
    try:
        n = int(divisions)
    except (TypeError, ValueError) as exc:
        raise ValueError('Las divisiones deben ser un entero.') from exc
    if total <= 0 or not 2 <= n <= 10:
        raise ValueError('Usá 2–10 divisiones y gramos por muestra > 0.')
    rows: list[dict[str, float | int]] = []
    index = 1
    for ia in range(n, -1, -1):
        for ib in range(n - ia, -1, -1):
            ic = n - ia - ib
            a = ia / n
            b = ib / n
            c = ic / n
            rows.append({'index': index, 'a_pct': a * 100.0, 'b_pct': b * 100.0, 'c_pct': c * 100.0, 'a_g': total * a, 'b_g': total * b, 'c_g': total * c})
            index += 1
    return rows

def normalize_oxide_name(name: str) -> str:
    trans = str.maketrans('₀₁₂₃₄₅₆₇₈₉', '0123456789')
    return str(name or '').translate(trans).replace(' ', '')

def calculate_umf(text: str) -> dict[str, Any]:
    flux = {'Li2O', 'Na2O', 'K2O', 'MgO', 'CaO', 'SrO', 'BaO', 'ZnO', 'PbO', 'FeO', 'MnO', 'CoO', 'CuO'}
    r2o3 = {'Al2O3', 'B2O3', 'Fe2O3', 'Cr2O3'}
    ro2 = {'SiO2', 'TiO2', 'ZrO2', 'SnO2'}
    items: list[tuple[str, float]] = []
    for raw in str(text or '').splitlines():
        raw = raw.strip()
        if not raw:
            continue
        match = re.match('([^\\s,:;]+)[\\s,:;]+(-?[0-9]+(?:[.,][0-9]+)?)$', raw)
        if not match:
            continue
        name = normalize_oxide_name(match.group(1))
        value = float(match.group(2).replace(',', '.'))
        if value >= 0:
            items.append((name, value))
    if not items:
        raise ValueError('Una línea por óxido: Na2O 0.25')
    flux_sum = sum((value for name, value in items if name in flux))
    if flux_sum <= 0:
        raise ValueError('No se reconoció ningún óxido fundente para normalizar RO/R₂O a 1,00.')
    groups: dict[str, list[tuple[str, float]]] = {'RO / R₂O': [], 'R₂O₃': [], 'RO₂': [], 'Otros': []}
    for name, value in items:
        normalized = value / flux_sum
        if name in flux:
            group = 'RO / R₂O'
        elif name in r2o3:
            group = 'R₂O₃'
        elif name in ro2:
            group = 'RO₂'
        else:
            group = 'Otros'
        groups[group].append((name, normalized))
    return {'flux_sum_input': flux_sum, 'groups': groups}
