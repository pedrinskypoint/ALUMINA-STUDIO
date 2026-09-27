"""Validated stock, formula and kiln operations on a transaction snapshot."""
from __future__ import annotations

import copy
import math
import uuid
from datetime import datetime, timezone


def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def number(value, label, minimum=0):
    if value is None:
        raise ValueError(f"Falta {label}.")
    value = float(value)
    if not math.isfinite(value) or value < minimum:
        raise ValueError(f"{label}: ingresá un número válido, mayor o igual a {minimum}.")
    return value


def stock_move(state, material_id, delta, kind, reference, *, reason, reverses=None):
    if material_id not in state["inventory"]:
        raise ValueError("Material no encontrado.")
    delta = float(delta)
    if not math.isfinite(delta):
        raise ValueError("Cantidad inválida.")
    old = number(state["inventory"][material_id]["qty"], "stock")
    balance = old + delta
    if balance < -1e-8:
        raise ValueError("El movimiento dejaría stock negativo. Revisá los consumos relacionados.")
    if abs(delta) < 1e-8:
        return None
    if not str(reason).strip():
        raise ValueError("Indicá el motivo del movimiento.")
    movement = {"id": "MOV-" + uuid.uuid4().hex, "at": timestamp(), "material_id": material_id,
                "delta": delta, "before": old, "after": max(0, balance), "type": kind,
                "reference_id": reference, "reason": reason, "reverses": reverses}
    state.setdefault("stock_movements", []).append(movement)
    state["inventory"][material_id]["qty"] = max(0, balance)
    return movement


def reverse_stock_move(state, movement_id, reason):
    movement = next((m for m in state["stock_movements"] if m.get("id") == movement_id), None)
    if not movement or movement.get("reverses"):
        raise ValueError("Seleccioná un movimiento original válido.")
    if movement.get("type") == "purchase_receipt":
        raise ValueError("Corregí la cantidad recibida desde el pedido para mantener pedido y stock vinculados.")
    if any(m.get("reverses") == movement_id for m in state["stock_movements"]):
        raise ValueError("Este movimiento ya fue revertido.")
    return stock_move(state, movement["material_id"], -movement["delta"], "reversal", movement.get("reference_id"), reason=reason, reverses=movement_id)


def confirm_consumption(state, material_id, quantity, reference, *, estimated=False, accept_estimate=False, confirmation_id=None):
    if not reference:
        raise ValueError("Seleccioná el ensayo, pieza o lote asociado.")
    records = {**state.get("experiments", {}), **state.get("projects", {}), **state.get("lots", {})}
    if reference not in records:
        raise ValueError("El registro asociado no existe.")
    if estimated and not accept_estimate:
        raise ValueError("La estimación requiere aceptación explícita antes de descontar stock.")
    if not confirmation_id:
        raise ValueError("Falta la identificación de esta confirmación.")
    if any(m.get("confirmation_id") == confirmation_id for m in state["stock_movements"]):
        raise ValueError("Este consumo ya fue confirmado.")
    movement = stock_move(state, material_id, -number(quantity, "consumo"), "consumption", reference, reason="Estimación aceptada" if estimated else "Consumo real confirmado")
    if movement:
        movement.update(confirmation_id=confirmation_id, evidence="estimated_accepted" if estimated else "measured")
    return movement


def normalized_components(components):
    original = copy.deepcopy(components or [])
    total = sum(number(c.get("amount"), "cantidad") for c in original)
    if total <= 0:
        raise ValueError("La fórmula debe tener una cantidad total mayor que cero.")
    units = {c.get("unit", "g") for c in original}
    if len(units) > 1:
        raise ValueError("Unificá las unidades antes de normalizar; no se mezclan gramos y porcentajes.")
    return [{**c, "amount": c["amount"] / total * 100, "unit": "%"} for c in original]


def formula_version(state, source_id, components=None, reason="Modificación"):
    source = state["formulas"][source_id]
    derived = copy.deepcopy(source)
    fid = "FOR-" + uuid.uuid4().hex
    derived.update(id=fid, derived_from=source_id, root_formula_id=source.get("root_formula_id", source_id),
                   version=int(source.get("version", 1)) + 1, version_reason=reason,
                   created_at=timestamp(), origin="Derivada", name=(source.get("name") or source_id) + " · versión")
    if components is not None:
        derived["components"] = copy.deepcopy(components)
    state["formulas"][fid] = derived
    return fid


def mass_variations(tile):
    stages = [("húmeda", "wet_weight"), ("seca", "dry_weight"), ("bizcocho", "bisque_weight"), ("final", "final_weight")]
    available = [(label, number(tile[key], "peso")) for label, key in stages if tile.get(key) is not None]
    return [{"from": a, "to": b, "loss_g": x-y, "loss_percent": (x-y)/x*100 if x else None}
            for (a, x), (b, y) in zip(available, available[1:])]


def transition_firing(state, fid, action, temperature=None):
    f = state["firings"][fid]
    expected = {"Programa finalizado": "En cocción", "Apertura": "Enfriando", "Descarga": "Abierto", "Completar": "Descargado"}
    if f.get("status") != expected[action]:
        raise ValueError(f"Esta acción requiere estado {expected[action]}. Estado actual: {f.get('status')}.")
    if action == "Programa finalizado":
        f.update(status="Enfriando", program_finished_at=timestamp())
    elif action == "Apertura":
        measured = number(temperature, "lectura actual del controlador")
        limit = number(state["settings"].get("opening_temp_c", 50), "límite de apertura")
        if measured > limit:
            raise ValueError(f"Apertura bloqueada: {measured:g} °C supera {limit:g} °C.")
        f.setdefault("temp_log", []).append({"at": timestamp(), "temp_c": measured, "stage": "Apertura confirmada"})
        f.update(status="Abierto", opened_at=timestamp())
    elif action == "Descarga":
        f.update(status="Descargado", unloaded_at=timestamp())
    else:
        f.update(status="Finalizada", completed_at=timestamp())
        for tid in f.get("tile_ids", []):
            tile = state["tiles"].get(tid)
            if tile:
                tile["firing_completed"] = min(int(tile.get("firing_required", 1)), int(tile.get("firing_completed", 0)) + 1)
                tile["stage"] = "Resultado" if tile["firing_completed"] >= tile.get("firing_required", 1) else "Cocción"
    return f


def cooling_history(state, firing):
    durations = []
    for old in state["firings"].values():
        if old.get("kiln_id") != firing.get("kiln_id") or old.get("program_name") != firing.get("program_name"):
            continue
        try:
            hours = (datetime.fromisoformat(old["opened_at"]) - datetime.fromisoformat(old["program_finished_at"])).total_seconds()/3600
            if hours > 0:
                durations.append(hours)
        except (KeyError, ValueError, TypeError):
            pass
    return {"samples": len(durations), "min_hours": min(durations), "max_hours": max(durations)} if len(durations) >= 3 else None
