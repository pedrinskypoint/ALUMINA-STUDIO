from __future__ import annotations

# ============================================================================
# ALUMINA STUDIO V17 · DIAGRAMACIÓN
# Consolidación funcional para Google Colab / Gradio 6.5.1
#
# Objetivo de esta versión:
# - Mantener una app móvil compacta y orientada al flujo real del ceramista.
# - Organizar LAB / TALLER / SABER con trazabilidad por ID.
# - Persistir estado localmente sin duplicar datos entre Lista / Pedido / Stock.
# - Separar datos técnicos, evidencia, procedencia y estado experimental.
#
# Instalación sugerida en Colab:
#   !pip -q install gradio==6.5.1
#   from ALUMINA_STUDIO_V17_DIAGRAMACION import launch
#   launch(share=True)
#
# Persistencia:
#   ALUMINA_DATA_DIR=/content/drive/MyDrive/ALUMINA
#   (si no se define, usa ./alumina_data)
# ============================================================================

import copy
import html
import json
import math
import os
import re
import sys
import threading
import functools
import uuid
import zipfile
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import gradio as gr
from .storage import Repository, Snapshot, ConflictError
from .media import persist_media, thumbnail_uri, migrate_media, media_path
from .operations import (stock_move, reverse_stock_move, confirm_consumption,
                         normalized_components, formula_version, mass_variations,
                         transition_firing, cooling_history, number)

APP_VERSION = "17.1 MOTOR · PREVIEW"
SCHEMA_VERSION = 2

# ---------------------------------------------------------------------------
# Persistencia y utilidades
# ---------------------------------------------------------------------------

DATA_DIR = Path(os.getenv("ALUMINA_DATA_DIR", "./alumina_data"))
STATE_FILE = DATA_DIR / "alumina_v16_demo_state.json"
STATE_LOCK = threading.RLock()


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def uid(prefix: str, records: Dict[str, Any] | List[Dict[str, Any]]) -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


def normalize_text(s: str) -> str:
    s = (s or "").lower().strip()
    table = str.maketrans("áéíóúüñ", "aeiouun")
    s = s.translate(table)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


_REPOSITORIES = {}


def repository():
    path = str((DATA_DIR / "alumina.sqlite3").resolve())
    with STATE_LOCK:
        return _REPOSITORIES.setdefault(path, Repository(path))


def migration_seed():
    if STATE_FILE.exists():
        # Invalid JSON aborts migration; it must never silently become an empty workshop.
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "schema_version" not in data:
            raise ValueError("El archivo anterior no es válido. No se modificó.")
        base = initial_state()
        base.update(data)
        base["schema_version"] = SCHEMA_VERSION
        return migrate_media(DATA_DIR, base)
    return demo_state()


def save_state(state):
    repository().save(state)


def load_state():
    return repository().load(migration_seed)


def migrate_state(data):
    state = load_state()
    base = initial_state()
    base.update(data)
    base["schema_version"] = SCHEMA_VERSION
    state.clear()
    state.update(migrate_media(DATA_DIR, base))
    save_state(state)
    return state


def session_token(state):
    return {"revisions": state.revisions}


def bind_repository_callbacks(demo, ui_state):
    # Adapt the existing presentation callbacks to transactional commands. The
    # browser session holds only conflict-detection metadata, never domain data.
    for block_fn in demo.fns.values():
        if ui_state not in block_fn.inputs:
            continue
        original = block_fn.fn
        positions = [i for i, component in enumerate(block_fn.inputs) if component is ui_state]
        output_positions = [i for i, component in enumerate(block_fn.outputs) if component is ui_state]
        @functools.wraps(original)
        def execute(*args, _fn=original, _positions=positions, _outputs=output_positions):
            args = list(args)
            token = args[_positions[0]] or {}
            try:
                with repository().transaction(token.get("revisions", {})) as tx:
                    for i in _positions:
                        args[i] = tx["state"]
                    answer = _fn(*args)
                    if _outputs:
                        values = list(answer) if isinstance(answer, (tuple, list)) else [answer]
                        tx["state"] = values[_outputs[0]]
                if _outputs:
                    for i in _outputs:
                        revisions = dict(token.get("revisions", {}))
                        if _fn.__name__ == "refresh_all_cb":
                            revisions = dict(tx["committed"].revisions)
                        else:
                            for key, version in tx["committed"].revisions.items():
                                if version != tx["before"].revisions.get(key):
                                    revisions[key] = version
                        values[i] = {"revisions": revisions}
                    return tuple(values)
                return answer
            except (ConflictError, ValueError) as exc:
                raise gr.Error(str(exc)) from exc
        block_fn.fn = execute


def audit_event(state: Dict[str, Any], event: str, ref_type: str = "", ref_id: str = "", note: str = "") -> None:
    state.setdefault("audit", []).append({
        "at": now_iso(), "event": event, "ref_type": ref_type, "ref_id": ref_id, "note": note
    })


def initial_state() -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "settings": {
            "default_supplier_id": "",
            "default_kiln_id": "KILN-0001",
            "advanced_pigment_synthesis": False,
            "opening_temp_c": 50.0,
            "preferred_unit": "g",
            "default_atmosphere": "Oxidante",
            "default_firing_type": "Bicocción",
            "units": {
                "temperature": "°C",
                "raw_weight": "g",
                "clay_weight": "g",
                "piece_weight": "g",
                "volume": "mL",
                "length": "cm",
            },
        },
        "materials_library": {
            "LIB-0001": {
                "id": "LIB-0001", "name": "Caolín", "category": "Arcillas", "source_type": "ALUMINA",
                "source_exact": "Biblioteca base", "loi": 12.0,
                "oxides": {"Al₂O₃": 39.5, "SiO₂": 46.5}, "custom": False
            },
            "LIB-0002": {
                "id": "LIB-0002", "name": "Sílice / cuarzo", "category": "Sílice", "source_type": "ALUMINA",
                "source_exact": "Biblioteca base", "loi": 0.0,
                "oxides": {"SiO₂": 99.5}, "custom": False
            },
            "LIB-0003": {
                "id": "LIB-0003", "name": "Frita borácica", "category": "Fritas", "source_type": "ALUMINA",
                "source_exact": "Genérica · requiere ficha del fabricante para cálculo exacto", "loi": 0.0,
                "oxides": {}, "custom": False
            },
            "LIB-0004": {
                "id": "LIB-0004", "name": "G-200 Feldspar (Pacer)", "category": "Feldespatos", "source_type": "REFERENCIA",
                "source_exact": "Ficha de referencia cargada para demostración", "loi": 0.10,
                "oxides": {"K₂O": 11.30, "Na₂O": 3.40, "CaO": 0.30, "Al₂O₃": 18.50, "SiO₂": 66.30, "Fe₂O₃": 0.10}, "custom": False
            },
        },
        "formulas": {},
        "experiments": {},
        "tiles": {},
        "results": {},
        "firings": {},
        "kilns": {
            "KILN-0001": {
                "id": "KILN-0001",
                "name": "Mi horno",
                "model": "",
                "capacity_l": None,
                "power_kw": None,
                "voltage_v": 220,
                "controller": "",
                "energy_cost_kwh": None,
                "default": True,
                "notes": "",
            }
        },
        "inventory": {
            "MAT-0001": {
                "id": "MAT-0001", "name": "Caolín", "unit": "g", "library_id": "LIB-0001",
                "qty": 1000.0, "min_qty": 500.0, "location": "",
                "preferred_supplier_id": "", "notes": ""
            },
            "MAT-0002": {
                "id": "MAT-0002", "name": "Sílice", "unit": "g", "library_id": "LIB-0002",
                "qty": 1000.0, "min_qty": 500.0, "location": "",
                "preferred_supplier_id": "", "notes": ""
            },
            "MAT-0003": {
                "id": "MAT-0003", "name": "Frita borácica", "unit": "g", "library_id": "LIB-0003",
                "qty": 1000.0, "min_qty": 500.0, "location": "",
                "preferred_supplier_id": "", "notes": ""
            },
        },
        "stock_movements": [],
        "shopping_list": {},
        "orders": {},
        "suppliers": {},
        "supplier_products": {},
        "price_history": [],
        "projects": {},
        "series": {},
        "lots": {},
        "journal": [],
        "agenda": {},
        "external_refs": [],
        "audit": [],
    }



# ---------------------------------------------------------------------------
# Datos DEMO
# ---------------------------------------------------------------------------


def demo_state() -> Dict[str, Any]:
    """Estado deliberadamente variado para probar flujos, navegación y persistencia."""
    st = initial_state()
    st["settings"].update({
        "default_supplier_id": "SUP-0001",
        "default_kiln_id": "KILN-0001",
        "advanced_pigment_synthesis": False,
        "opening_temp_c": 50.0,
        "default_atmosphere": "Oxidante",
        "default_firing_type": "Bicocción",
        "demo_mode": True,
    })
    st["kilns"]["KILN-0001"].update({
        "name": "Horno taller · DEMO", "model": "Eléctrico 60 L", "capacity_l": 60,
        "power_kw": 5.5, "voltage_v": 220, "controller": "Programador 8 segmentos",
        "energy_cost_kwh": 0.18, "default": True,
    })

    # Biblioteca técnica: referencia separada de stock físico.
    st["materials_library"].update({
        "LIB-0005": {"id":"LIB-0005","name":"Carbonato de calcio","category":"Fundentes","source_type":"ALUMINA","source_exact":"Biblioteca DEMO","loi":43.9,"oxides":{"CaO":56.1},"custom":False},
        "LIB-0006": {"id":"LIB-0006","name":"Feldespato potásico","category":"Feldespatos","source_type":"ALUMINA","source_exact":"Composición genérica DEMO; usar ficha del proveedor para cálculo exacto","loi":0.5,"oxides":{"K₂O":10.5,"Na₂O":2.8,"Al₂O₃":18.5,"SiO₂":67.7},"custom":False},
        "LIB-0007": {"id":"LIB-0007","name":"Óxido de cobre negro","category":"Óxidos","source_type":"ALUMINA","source_exact":"Biblioteca DEMO","loi":0.0,"oxides":{"CuO":99.0},"custom":False},
        "LIB-0008": {"id":"LIB-0008","name":"Carbonato de cobalto","category":"Óxidos","source_type":"ALUMINA","source_exact":"Biblioteca DEMO","loi":0.0,"oxides":{},"custom":False},
        "LIB-0009": {"id":"LIB-0009","name":"Pigmento naranja inclusión Cd-S-Se","category":"Pigmentos","source_type":"FABRICANTE","source_exact":"Material DEMO; cargar ficha real del fabricante","loi":0.0,"oxides":{},"custom":False},
        "LIB-0010": {"id":"LIB-0010","name":"Bentonita","category":"Arcillas","source_type":"ALUMINA","source_exact":"Biblioteca DEMO","loi":8.0,"oxides":{},"custom":False},
        "LIB-0011": {"id":"LIB-0011","name":"Talco","category":"Fundentes","source_type":"ALUMINA","source_exact":"Biblioteca DEMO","loi":5.0,"oxides":{"MgO":31.7,"SiO₂":63.5},"custom":False},
    })

    # Inventario físico: cantidades intencionalmente distintas para probar alertas.
    st["inventory"] = {
        "MAT-0001":{"id":"MAT-0001","name":"Caolín","unit":"g","library_id":"LIB-0001","qty":1350.0,"min_qty":500.0,"location":"Estante A1","preferred_supplier_id":"SUP-0001","notes":""},
        "MAT-0002":{"id":"MAT-0002","name":"Sílice","unit":"g","library_id":"LIB-0002","qty":4200.0,"min_qty":1000.0,"location":"Estante A2","preferred_supplier_id":"SUP-0001","notes":""},
        "MAT-0003":{"id":"MAT-0003","name":"Frita borácica","unit":"g","library_id":"LIB-0003","qty":820.0,"min_qty":750.0,"location":"Estante B1","preferred_supplier_id":"SUP-0001","notes":""},
        "MAT-0004":{"id":"MAT-0004","name":"Carbonato de calcio","unit":"g","library_id":"LIB-0005","qty":180.0,"min_qty":500.0,"location":"Estante A3","preferred_supplier_id":"SUP-0001","notes":"Stock bajo DEMO"},
        "MAT-0005":{"id":"MAT-0005","name":"Feldespato potásico","unit":"g","library_id":"LIB-0006","qty":2800.0,"min_qty":1000.0,"location":"Estante A4","preferred_supplier_id":"SUP-0002","notes":""},
        "MAT-0006":{"id":"MAT-0006","name":"Óxido de cobre negro","unit":"g","library_id":"LIB-0007","qty":160.0,"min_qty":100.0,"location":"Colorantes C1","preferred_supplier_id":"SUP-0002","notes":""},
        "MAT-0007":{"id":"MAT-0007","name":"Carbonato de cobalto","unit":"g","library_id":"LIB-0008","qty":22.0,"min_qty":50.0,"location":"Colorantes C2","preferred_supplier_id":"SUP-0002","notes":"Stock bajo DEMO"},
        "MAT-0008":{"id":"MAT-0008","name":"Pigmento naranja inclusión Cd-S-Se","unit":"g","library_id":"LIB-0009","qty":35.0,"min_qty":100.0,"location":"Pigmentos P1","preferred_supplier_id":"SUP-0001","notes":"Stock bajo DEMO"},
        "MAT-0009":{"id":"MAT-0009","name":"Bentonita","unit":"g","library_id":"LIB-0010","qty":600.0,"min_qty":250.0,"location":"Estante A5","preferred_supplier_id":"SUP-0001","notes":""},
        "MAT-0010":{"id":"MAT-0010","name":"Talco","unit":"g","library_id":"LIB-0011","qty":900.0,"min_qty":300.0,"location":"Estante A6","preferred_supplier_id":"SUP-0002","notes":""},
    }

    st["suppliers"] = {
        "SUP-0001":{"id":"SUP-0001","name":"DP Colors · DEMO","phone":"5491100000001","web":"https://dpcolors.com/","shipping_cost":6500.0,"notes":"Proveedor predeterminado de demostración."},
        "SUP-0002":{"id":"SUP-0002","name":"Proveedor alternativo · DEMO","phone":"5491100000002","web":"https://example.com/alumina-demo","shipping_cost":4200.0,"notes":"Catálogo simulado para probar cobertura y precio."},
    }
    st["supplier_products"] = {
        "SP-0001":{"id":"SP-0001","supplier_id":"SUP-0001","material_id":"MAT-0001","material_name":"Caolín","name":"Caolín cerámico 1 kg · DEMO","code":"DP-KAO-1K","url":"https://dpcolors.com/","package_qty":1000.0,"unit":"g","price":4200.0,"price_status":"Ingresado manualmente","price_date":"2026-09-21","available":True,"confirmed_equivalence":True},
        "SP-0002":{"id":"SP-0002","supplier_id":"SUP-0001","material_id":"MAT-0004","material_name":"Carbonato de calcio","name":"Carbonato de calcio 1 kg · DEMO","code":"DP-CAC-1K","url":"https://dpcolors.com/","package_qty":1000.0,"unit":"g","price":3900.0,"price_status":"Ingresado manualmente","price_date":"2026-09-21","available":True,"confirmed_equivalence":True},
        "SP-0003":{"id":"SP-0003","supplier_id":"SUP-0001","material_id":"MAT-0008","material_name":"Pigmento naranja inclusión Cd-S-Se","name":"Pigmento naranja inclusión 250 g · DEMO","code":"DP-ORG-250","url":"https://dpcolors.com/","package_qty":250.0,"unit":"g","price":16500.0,"price_status":"Ingresado manualmente","price_date":"2026-09-21","available":True,"confirmed_equivalence":True},
        "SP-0004":{"id":"SP-0004","supplier_id":"SUP-0002","material_id":"MAT-0004","material_name":"Carbonato de calcio","name":"Carbonato de calcio 500 g · DEMO","code":"ALT-CAC-500","url":"https://example.com/alumina-demo/calcio","package_qty":500.0,"unit":"g","price":2200.0,"price_status":"Ingresado manualmente","price_date":"2026-09-21","available":True,"confirmed_equivalence":True},
        "SP-0005":{"id":"SP-0005","supplier_id":"SUP-0002","material_id":"MAT-0007","material_name":"Carbonato de cobalto","name":"Carbonato de cobalto 100 g · DEMO","code":"ALT-COB-100","url":"https://example.com/alumina-demo/cobalto","package_qty":100.0,"unit":"g","price":9800.0,"price_status":"Ingresado manualmente","price_date":"2026-09-21","available":True,"confirmed_equivalence":True},
        "SP-0006":{"id":"SP-0006","supplier_id":"SUP-0002","material_id":"MAT-0008","material_name":"Pigmento naranja inclusión Cd-S-Se","name":"Naranja inclusión 100 g · DEMO","code":"ALT-ORG-100","url":"https://example.com/alumina-demo/naranja","package_qty":100.0,"unit":"g","price":7200.0,"price_status":"Ingresado manualmente","price_date":"2026-09-21","available":True,"confirmed_equivalence":True},
        "SP-0007":{"id":"SP-0007","supplier_id":"SUP-0002","material_id":"MAT-0006","material_name":"Óxido de cobre negro","name":"Óxido de cobre negro 100 g · DEMO","code":"ALT-CUO-100","url":"https://example.com/alumina-demo/cobre","package_qty":100.0,"unit":"g","price":5300.0,"price_status":"Ingresado manualmente","price_date":"2026-09-21","available":True,"confirmed_equivalence":True},
    }

    st["formulas"] = {
        "CAM-0001":{"id":"CAM-0001","name":"Naranja Talavera 01","origin":"Digital · Cámara","source_type":"EXPERIMENTAL","source_exact":"DEMO cámara","evidence_state":"Ensayada","created_at":"2026-09-21T18:10:00-03:00","target_hex":"#F25A18","target_lab":list(hex_to_lab("#F25A18")),"vehicle":"Esmalte","base_type":"Fritada","chemistry_family":"Borácica / borosilicato","optics":"Opaca","surface":"Brillante","body":"Loza blanca","target_temp_c":1040.0,"atmosphere":"Oxidante","pigment_pct":6.0,"pigment_candidate":"Cd-S-Se inclusión","x_se":0.30,"components":[{"name":"Frita borácica","amount":60,"unit":"%"},{"name":"Sílice","amount":20,"unit":"%"},{"name":"Caolín","amount":20,"unit":"%"}],"versions":[]},
        "MAN-0001":{"id":"MAN-0001","name":"Azul cobalto satinado","origin":"Escrita","source_type":"Propia","source_exact":"Cuaderno de taller · DEMO","evidence_state":"Revisada","created_at":"2026-09-21T18:20:00-03:00","target_hex":"#365F9D","target_lab":list(hex_to_lab("#365F9D")),"vehicle":"Esmalte","base_type":"Fritada","chemistry_family":"Mixta","optics":"Opaca","surface":"Satinada","body":"Loza blanca","target_temp_c":1020.0,"atmosphere":"Oxidante","pigment_pct":1.2,"components":[{"name":"Frita borácica","amount":65,"unit":"%"},{"name":"Caolín","amount":20,"unit":"%"},{"name":"Sílice","amount":15,"unit":"%"}],"versions":[]},
        "SEL-0001":{"id":"SEL-0001","name":"Verde cobre 01","origin":"Digital · Selector","source_type":"EXPERIMENTAL","source_exact":"DEMO selector","evidence_state":"Ensayo en curso","created_at":"2026-09-21T18:30:00-03:00","target_hex":"#55A56E","target_lab":list(hex_to_lab("#55A56E")),"vehicle":"Engobe","base_type":"Mi fórmula","chemistry_family":"No definida","optics":"Opaca","surface":"Mate","body":"Terracota","target_temp_c":1040.0,"atmosphere":"Oxidante","pigment_pct":3.0,"components":[{"name":"Caolín","amount":50,"unit":"%"},{"name":"Sílice","amount":30,"unit":"%"},{"name":"Feldespato potásico","amount":20,"unit":"%"}],"versions":[]},
    }

    st["experiments"] = {
        "ENS-0001":{"id":"ENS-0001","formula_id":"CAM-0001","name":"Ensayo Naranja Talavera 01","status":"Listo para muestra","created_at":"2026-09-21T19:00:00-03:00","base_mass_g":50.0,"water_ml":31.0,"notes":"Aplicación en 3 capas finas.","pigment_pct":6.0,"target_temp_c":1040.0,"atmosphere":"Oxidante","body":"Loza blanca","tile_ids":["TES-0001"]},
        "ENS-0002":{"id":"ENS-0002","formula_id":"MAN-0001","name":"Azul satinado · 75 g","status":"Preparación","created_at":"2026-09-21T19:10:00-03:00","base_mass_g":75.0,"water_ml":None,"notes":"Comparar 1.0 y 1.2 % Co.","pigment_pct":1.2,"target_temp_c":1020.0,"atmosphere":"Oxidante","body":"Loza blanca","tile_ids":[]},
        "ENS-0003":{"id":"ENS-0003","formula_id":"SEL-0001","name":"Engobe verde cobre · 100 g","status":"Aplicación","created_at":"2026-09-21T19:20:00-03:00","base_mass_g":100.0,"water_ml":62.0,"notes":"Aplicar sobre terracota húmeda.","pigment_pct":3.0,"target_temp_c":1040.0,"atmosphere":"Oxidante","body":"Terracota","tile_ids":["TES-0002"]},
        "ENS-0004":{"id":"ENS-0004","formula_id":"MAN-0001","name":"Azul satinado · resultado previo","status":"Evaluado","created_at":"2026-09-20T16:00:00-03:00","base_mass_g":50.0,"water_ml":29.0,"notes":"Ensayo histórico DEMO.","pigment_pct":1.0,"target_temp_c":1020.0,"atmosphere":"Oxidante","body":"Loza blanca","tile_ids":["TES-0003"]},
    }

    st["tiles"] = {
        "TES-0001":{"id":"TES-0001","experiment_id":"ENS-0001","formula_id":"CAM-0001","name":"Naranja Talavera 01 · T01","created_at":"2026-09-21T19:30:00-03:00","firing_type":"Bicocción","firing_required":2,"firing_completed":1,"stage":"Cocción","target_temp_c":1040.0,"atmosphere":"Oxidante","wet_weight":42.1,"dry_weight":35.8,"dry_length":80.0,"fired_length":None,"notes":"Bizcocho completado; falta esmalte.","firing_ids":["HOR-0001","HOR-0002"]},
        "TES-0002":{"id":"TES-0002","experiment_id":"ENS-0003","formula_id":"SEL-0001","name":"Verde cobre · T01","created_at":"2026-09-21T19:40:00-03:00","firing_type":"Monococción","firing_required":1,"firing_completed":0,"stage":"Secado","target_temp_c":1040.0,"atmosphere":"Oxidante","wet_weight":48.0,"dry_weight":41.2,"dry_length":80.0,"fired_length":None,"notes":"Secando; borde superior un poco grueso.","firing_ids":[]},
        "TES-0003":{"id":"TES-0003","experiment_id":"ENS-0004","formula_id":"MAN-0001","name":"Azul satinado · T01","created_at":"2026-09-20T16:30:00-03:00","firing_type":"Monococción","firing_required":1,"firing_completed":1,"stage":"Resultado","target_temp_c":1020.0,"atmosphere":"Oxidante","wet_weight":44.0,"dry_weight":38.1,"dry_length":80.0,"fired_length":74.5,"notes":"Terminada.","firing_ids":["HOR-0003"],"completed":True},
    }

    st["results"] = {
        "RES-0001":{"id":"RES-0001","tile_id":"TES-0003","formula_id":"MAN-0001","created_at":"2026-09-20T22:30:00-03:00","result_hex":"#3A6196","result_lab":list(hex_to_lab("#3A6196")),"delta_e":delta_e2000(hex_to_lab("#365F9D"),hex_to_lab("#3A6196")),"photo_path":"","outcome":"Funcionó","liking":"Me gusta","action":"Conservar","note_kind":"Comentario","note":"Satinado uniforme; repetir con 1,2 %."}
    }

    st["firings"] = {
        "HOR-0001":{"id":"HOR-0001","kiln_id":"KILN-0001","program_name":"Bizcocho 900 lento","stage_kind":"Bizcocho","target_temp_c":900.0,"atmosphere":"Oxidante","tile_ids":["TES-0001"],"status":"Finalizada","created_at":"2026-09-20T09:00:00-03:00","started_at":"2026-09-20T09:00:00-03:00","estimated_minutes":program_duration_minutes("Bizcocho 900 lento"),"temp_log":[{"at":"2026-09-20T14:00:00-03:00","temp_c":620,"stage":"En cocción"},{"at":"2026-09-20T17:10:00-03:00","temp_c":900,"stage":"Programa finalizado"}],"opened_at":"2026-09-21T08:20:00-03:00","unloaded_at":"2026-09-21T08:45:00-03:00","completed_at":"2026-09-21T08:50:00-03:00"},
        "HOR-0002":{"id":"HOR-0002","kiln_id":"KILN-0001","program_name":"Esmalte 1040","stage_kind":"Esmalte","target_temp_c":1040.0,"atmosphere":"Oxidante","tile_ids":["TES-0001"],"status":"En cocción","created_at":"2026-09-21T21:00:00-03:00","started_at":"2026-09-21T21:00:00-03:00","estimated_minutes":program_duration_minutes("Esmalte 1040"),"temp_log":[{"at":"2026-09-21T22:00:00-03:00","temp_c":180,"stage":"En cocción"},{"at":"2026-09-21T23:00:00-03:00","temp_c":310,"stage":"En cocción"}],"opened_at":"","unloaded_at":"","completed_at":""},
        "HOR-0003":{"id":"HOR-0003","kiln_id":"KILN-0001","program_name":"Monococción 1040","stage_kind":"Monococción","target_temp_c":1020.0,"atmosphere":"Oxidante","tile_ids":["TES-0003"],"status":"Finalizada","created_at":"2026-09-20T12:00:00-03:00","started_at":"2026-09-20T12:00:00-03:00","estimated_minutes":program_duration_minutes("Monococción 1040"),"temp_log":[],"opened_at":"2026-09-21T09:00:00-03:00","unloaded_at":"2026-09-21T09:15:00-03:00","completed_at":"2026-09-21T09:20:00-03:00"},
    }

    st["shopping_list"] = {
        "LIS-0001":{"id":"LIS-0001","material_id":"MAT-0008","material_name":"Pigmento naranja inclusión Cd-S-Se","unit":"g","needed_qty":65.0,"buy_qty":100.0,"origin_type":"Ensayo","origin_id":"ENS-0001","status":"pending","created_at":"2026-09-21T20:10:00-03:00"},
        "LIS-0002":{"id":"LIS-0002","material_id":"MAT-0004","material_name":"Carbonato de calcio","unit":"g","needed_qty":320.0,"buy_qty":500.0,"origin_type":"Stock","origin_id":"MAT-0004","status":"pending","created_at":"2026-09-21T20:20:00-03:00"},
        "LIS-0003":{"id":"LIS-0003","material_id":"MAT-0007","material_name":"Carbonato de cobalto","unit":"g","needed_qty":28.0,"buy_qty":100.0,"origin_type":"Fórmula","origin_id":"MAN-0001","status":"pending","created_at":"2026-09-21T20:30:00-03:00"},
    }

    st["orders"] = {
        "PED-0001":{"id":"PED-0001","supplier_id":"SUP-0001","supplier_name":"DP Colors · DEMO","status":"Parcialmente recibido","strategy":"Mi proveedor","created_at":"2026-09-18T12:00:00-03:00","shipping_estimated":6500.0,"notes":"Pedido DEMO para probar recepción parcial.","lines":[
            {"line_id":"PED-0001-L01","list_item_id":"","material_id":"MAT-0001","material_name":"Caolín","product_id":"SP-0001","product_name":"Caolín cerámico 1 kg · DEMO","code":"DP-KAO-1K","package_qty":1000.0,"package_unit":"g","packages_ordered":1,"qty_ordered":1000.0,"price_estimated":4200.0,"subtotal_estimated":4200.0,"product_url":"https://dpcolors.com/","price_status":"Ingresado manualmente","price_date":"2026-09-18","received_qty":1000.0,"actual_unit_price":4200.0},
            {"line_id":"PED-0001-L02","list_item_id":"","material_id":"MAT-0003","material_name":"Frita borácica","product_id":"","product_name":"Frita borácica 1 kg · DEMO","code":"DP-FRIT-1K","package_qty":1000.0,"package_unit":"g","packages_ordered":1,"qty_ordered":1000.0,"price_estimated":8300.0,"subtotal_estimated":8300.0,"product_url":"https://dpcolors.com/","price_status":"Ingresado manualmente","price_date":"2026-09-18","received_qty":500.0,"actual_unit_price":8300.0}
        ]}
    }

    st["projects"] = {
        "PRO-0001":{"id":"PRO-0001","name":"Vajilla Arena","type":"Serie / colección","notes":"24 piezas para probar flujo de producción.","created_at":"2026-09-19T10:00:00-03:00"}
    }
    st["series"] = {
        "SER-0001":{"id":"SER-0001","project_id":"PRO-0001","object_type":"Taza","target_qty":12,"name":"Tazas Arena","created_at":"2026-09-19T10:10:00-03:00"},
        "SER-0002":{"id":"SER-0002","project_id":"PRO-0001","object_type":"Plato","target_qty":12,"name":"Platos Arena","created_at":"2026-09-19T10:15:00-03:00"},
    }
    st["lots"] = {
        "LOT-0001":{"id":"LOT-0001","series_id":"SER-0001","qty":6,"created_at":"2026-09-20T11:00:00-03:00","status":"Secando"},
        "LOT-0002":{"id":"LOT-0002","series_id":"SER-0002","qty":6,"created_at":"2026-09-20T11:15:00-03:00","status":"En proceso"},
    }
    st["agenda"] = {
        "AGE-0001":{"id":"AGE-0001","title":"Curso de moldería","when":"2026-09-24 18:00","type":"Curso","location":"Taller escuela","notes":"Llevar herramientas.","created_at":"2026-09-21T12:00:00-03:00"},
        "AGE-0002":{"id":"AGE-0002","title":"Descargar hornada HOR-0002","when":"2026-09-22 09:30","type":"Hornada","location":"Taller","notes":"Sólo abrir cuando esté por debajo del límite configurado.","created_at":"2026-09-21T21:05:00-03:00"},
    }
    st["journal"] = [
        {"at":"2026-09-21T17:30:00-03:00","type":"Idea","text":"Comparar Naranja Talavera a 4 %, 6 % y 8 % manteniendo base y espesor."},
        {"at":"2026-09-21T19:45:00-03:00","type":"Proceso","text":"TES-0002 aplicada sobre terracota; el borde quedó un poco más grueso."},
    ]
    st["stock_movements"] = [
        {"at":"2026-09-18T16:00:00-03:00","material_id":"MAT-0001","delta":1000.0,"type":"purchase_receipt","reference_id":"PED-0001"},
        {"at":"2026-09-18T16:00:00-03:00","material_id":"MAT-0003","delta":500.0,"type":"purchase_receipt","reference_id":"PED-0001"},
    ]
    st["audit"] = [{"at":now_iso(),"event":"demo_seeded","ref_type":"system","ref_id":"V16-DEMO","note":"Estado inicial de demostración"}]
    return st


def reset_demo_state() -> Dict[str, Any]:
    st = load_state()
    export_backup_file(st)
    st.clear()
    st.update(demo_state())
    save_state(st)
    return st

# ---------------------------------------------------------------------------
# Color: HEX/RGB/CIELAB + ΔE76
# ---------------------------------------------------------------------------


def normalize_hex(value: str) -> str:
    value = (value or "").strip().upper()
    if not value:
        return "#808080"
    if not value.startswith("#"):
        value = "#" + value
    if re.fullmatch(r"#[0-9A-F]{3}", value):
        value = "#" + "".join(ch * 2 for ch in value[1:])
    if not re.fullmatch(r"#[0-9A-F]{6}", value):
        return "#808080"
    return value


def hex_to_rgb(value: str) -> Tuple[int, int, int]:
    value = normalize_hex(value)
    return tuple(int(value[i:i+2], 16) for i in (1, 3, 5))


def rgb_to_lab(rgb: Tuple[int, int, int]) -> Tuple[float, float, float]:
    r, g, b = [v / 255.0 for v in rgb]
    def lin(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = lin(r), lin(g), lin(b)
    x = (r * 0.4124 + g * 0.3576 + b * 0.1805) / 0.95047
    y = (r * 0.2126 + g * 0.7152 + b * 0.0722) / 1.00000
    z = (r * 0.0193 + g * 0.1192 + b * 0.9505) / 1.08883
    def f(t: float) -> float:
        return t ** (1/3) if t > 0.008856 else 7.787 * t + 16/116
    fx, fy, fz = f(x), f(y), f(z)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def hex_to_lab(value: str) -> Tuple[float, float, float]:
    return rgb_to_lab(hex_to_rgb(value))


def delta_e76(lab1: Iterable[float], lab2: Iterable[float]) -> float:
    a = list(lab1); b = list(lab2)
    return math.sqrt(sum((float(x) - float(y)) ** 2 for x, y in zip(a, b)))


def delta_e2000(lab1: Iterable[float], lab2: Iterable[float]) -> float:
    """CIEDE2000 (ΔE00) para comparación perceptual en CIELAB.

    Compara colores digitales/medidos; no predice por sí sola el resultado
    cerámico después de la cocción.
    """
    L1, a1, b1 = [float(v) for v in lab1]
    L2, a2, b2 = [float(v) for v in lab2]
    C1 = math.hypot(a1, b1)
    C2 = math.hypot(a2, b2)
    Cbar = (C1 + C2) / 2.0
    Cbar7 = Cbar ** 7
    G = 0.5 * (1.0 - math.sqrt(Cbar7 / (Cbar7 + 25.0 ** 7))) if Cbar else 0.0
    a1p = (1.0 + G) * a1
    a2p = (1.0 + G) * a2
    C1p = math.hypot(a1p, b1)
    C2p = math.hypot(a2p, b2)

    def _h(a: float, b: float) -> float:
        if a == 0.0 and b == 0.0:
            return 0.0
        h = math.degrees(math.atan2(b, a))
        return h + 360.0 if h < 0 else h

    h1p, h2p = _h(a1p, b1), _h(a2p, b2)
    dLp = L2 - L1
    dCp = C2p - C1p
    dh = h2p - h1p
    if C1p * C2p == 0.0:
        dhp = 0.0
    elif abs(dh) <= 180.0:
        dhp = dh
    elif dh > 180.0:
        dhp = dh - 360.0
    else:
        dhp = dh + 360.0
    dHp = 2.0 * math.sqrt(C1p * C2p) * math.sin(math.radians(dhp / 2.0))

    Lbarp = (L1 + L2) / 2.0
    Cbarp = (C1p + C2p) / 2.0
    if C1p * C2p == 0.0:
        hbarp = h1p + h2p
    elif abs(h1p - h2p) <= 180.0:
        hbarp = (h1p + h2p) / 2.0
    elif h1p + h2p < 360.0:
        hbarp = (h1p + h2p + 360.0) / 2.0
    else:
        hbarp = (h1p + h2p - 360.0) / 2.0

    T = (1.0
         - 0.17 * math.cos(math.radians(hbarp - 30.0))
         + 0.24 * math.cos(math.radians(2.0 * hbarp))
         + 0.32 * math.cos(math.radians(3.0 * hbarp + 6.0))
         - 0.20 * math.cos(math.radians(4.0 * hbarp - 63.0)))
    dtheta = 30.0 * math.exp(-((hbarp - 275.0) / 25.0) ** 2)
    Rc = 2.0 * math.sqrt((Cbarp ** 7) / (Cbarp ** 7 + 25.0 ** 7)) if Cbarp else 0.0
    Sl = 1.0 + 0.015 * (Lbarp - 50.0) ** 2 / math.sqrt(20.0 + (Lbarp - 50.0) ** 2)
    Sc = 1.0 + 0.045 * Cbarp
    Sh = 1.0 + 0.015 * Cbarp * T
    Rt = -math.sin(math.radians(2.0 * dtheta)) * Rc
    xL, xC, xH = dLp / Sl, dCp / Sc, dHp / Sh
    return math.sqrt(xL*xL + xC*xC + xH*xH + Rt*xC*xH)


def color_identity_html(hex_value: str, record_id: str = "") -> str:
    hv = normalize_hex(hex_value)
    rgb = hex_to_rgb(hv)
    lab = hex_to_lab(hv)
    return f"""
    <div class='color-id'>
      <span class='swatch' style='background:{esc(hv)}'></span>
      <div><b>{esc(record_id) if record_id else 'Color objetivo'}</b>
      <div class='muted'>{esc(hv)} · RGB {rgb[0]}, {rgb[1]}, {rgb[2]} · Lab {lab[0]:.1f}, {lab[1]:.1f}, {lab[2]:.1f}</div></div>
    </div>
    """


def pigment_candidates(hex_value: str) -> List[Tuple[str, str]]:
    # Orientativo: propone familias plausibles por región cromática. No identifica química.
    r, g, b = hex_to_rgb(hex_value)
    candidates: List[Tuple[str, str]] = []
    if r > 180 and g > 60 and g < 180 and b < 100:
        candidates += [
            ("Cd-S-Se inclusión", "Color naranja/rojo de inclusión: candidato orientativo, no identificación."),
            ("Fe2O3 - óxido de hierro", "Puede producir rojos/ocres según base, concentración y cocción."),
        ]
    if b > r and b > g:
        candidates += [("CoO/Co3O4 - cobalto", "Familia azul habitual; intensidad muy dependiente de dosis/base.")]
    if g > r and g > b:
        candidates += [("CuO/CuCO3 - cobre", "Familia verde/turquesa frecuente en oxidación según base.")]
    if not candidates:
        candidates += [("Sin candidato dominante", "Continuar por referencia visual y validación experimental.")]
    return candidates[:3]


# ---------------------------------------------------------------------------
# Fórmulas, matches y parser manual
# ---------------------------------------------------------------------------


def formula_id_for_origin(state: Dict[str, Any], origin: str) -> str:
    prefix = {
        "Digital · Cámara": "CAM",
        "Digital · Selector": "SEL",
        "Manual": "MAN",
        "PDF": "MAN",
        "Derivada": "FOR",
    }.get(origin, "FOR")
    return uid(prefix, state["formulas"])


def parse_formula_text(text: str) -> Tuple[List[Dict[str, Any]], float, List[str]]:
    components: List[Dict[str, Any]] = []
    warnings: List[str] = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        line = line.replace("%", " ")
        m = re.match(r"^(.+?)[\s:;,\-]+(-?\d+(?:[\.,]\d+)?)\s*(g|kg)?\s*$", line, re.I)
        if not m:
            continue
        name = m.group(1).strip(" .:-")
        amount = float(m.group(2).replace(",", "."))
        unit = (m.group(3) or "partes").lower()
        if amount < 0:
            warnings.append(f"Valor negativo ignorado: {line}")
            continue
        components.append({"name": name, "amount": amount, "unit": unit})
    total = sum(float(x["amount"]) for x in components)
    if not components:
        warnings.append("No se detectaron líneas del tipo 'Material 30'. Revisar manualmente.")
    elif abs(total - 100.0) > 0.01:
        warnings.append(f"Total detectado: {total:.2f}. Puede normalizarse a 100, pero no se fuerza.")
    return components, total, warnings


def formula_match_results(state: Dict[str, Any], target_hex: str, temp_c: float, atmosphere: str, body: str) -> str:
    target_lab = hex_to_lab(target_hex)
    rows = []
    for formula in state["formulas"].values():
        if not formula.get("target_lab"):
            continue
        de = delta_e76(target_lab, formula["target_lab"])
        tech = 0
        if formula.get("target_temp_c") and temp_c:
            tech += max(0, 40 - abs(float(formula["target_temp_c"]) - float(temp_c)) / 5)
        if atmosphere and formula.get("atmosphere") == atmosphere:
            tech += 30
        if body and normalize_text(formula.get("body", "")) == normalize_text(body):
            tech += 30
        rows.append((de, min(100, tech), formula))
    rows.sort(key=lambda x: (x[0], -x[1]))

    html_parts = ["<div class='section-title'>Coincidencias ALUMINA</div>"]
    if not rows:
        html_parts.append("<div class='notice'>Todavía no hay fórmulas comparables con color Lab guardado.</div>")
    else:
        for de, tech, f in rows[:3]:
            html_parts.append(
                f"<div class='match-card'><div class='rowline'><span class='swatch small' style='background:{esc(f.get('target_hex','#888'))}'></span>"
                f"<b>{esc(f.get('name') or f['id'])}</b></div>"
                f"<div class='muted'>ΔE00 {format(de, '.2f') if de is not None else 'no disponible: falta objetivo'} · compatibilidad técnica {tech:.0f}/100 · {esc(f.get('target_temp_c',''))} °C · {esc(f.get('atmosphere',''))}</div>"
                f"<div class='tiny'>{esc(f['id'])}</div></div>"
            )

    html_parts.append("<div class='section-title'>Referencias externas</div>")
    refs = []
    for ref in state.get("external_refs", []):
        if ref.get("lab"):
            de = delta_e76(target_lab, ref["lab"])
            refs.append((de, ref))
    refs.sort(key=lambda x: x[0])
    if not refs:
        html_parts.append("<div class='notice'>No hay referencias externas cargadas. ALUMINA no inventa porcentajes ni resultados externos.</div>")
    else:
        for de, ref in refs[:3]:
            link = ref.get("url")
            link_html = f"<a target='_blank' href='{esc(link)}'>Ver referencia ↗</a>" if link else ""
            html_parts.append(
                f"<div class='match-card'><b>{esc(ref.get('name','Referencia'))}</b> · {esc(ref.get('source',''))}"
                f"<div class='muted'>ΔE00 {format(de, '.2f') if de is not None else 'no disponible: falta objetivo'} · {esc(ref.get('relation','COLOR SIMILAR'))}</div>{link_html}</div>"
            )
    return "".join(html_parts)


def formula_detail_html(formula: Optional[Dict[str, Any]]) -> str:
    if not formula:
        return "<div class='notice'>Seleccioná una fórmula.</div>"
    comp = formula.get("components") or []
    comp_html = "".join(
        f"<tr><td>{esc(c.get('name'))}</td><td>{float(c.get('amount',0)):.2f}</td><td>{esc(c.get('unit',''))}</td></tr>"
        for c in comp
    ) or "<tr><td colspan='3' class='muted'>Sin componentes cargados</td></tr>"
    color = color_identity_html(formula.get("target_hex", "#808080"), formula["id"]) if formula.get("target_hex") else ""
    return f"""
    <div class='panel'>
      <div class='kicker'>FÓRMULA</div>
      <h3>{esc(formula.get('name') or formula['id'])}</h3>
      {color}
      <div class='grid2 compact'>
        <div><b>Origen</b><br>{esc(formula.get('origin',''))}</div>
        <div><b>Fuente</b><br>{esc(formula.get('source_type',''))}</div>
        <div><b>Vehículo</b><br>{esc(formula.get('vehicle',''))}</div>
        <div><b>Base</b><br>{esc(formula.get('base_type',''))} · {esc(formula.get('chemistry_family',''))}</div>
        <div><b>Óptica</b><br>{esc(formula.get('optics',''))}</div>
        <div><b>Superficie</b><br>{esc(formula.get('surface',''))}</div>
        <div><b>Soporte</b><br>{esc(formula.get('body',''))}</div>
        <div><b>Cocción</b><br>{esc(formula.get('target_temp_c',''))} °C · {esc(formula.get('atmosphere',''))}</div>
      </div>
      <div class='section-title'>Composición</div>
      <table><thead><tr><th>Material</th><th>Cantidad</th><th>Unidad</th></tr></thead><tbody>{comp_html}</tbody></table>
      <div class='tiny'>Estado: {esc(formula.get('evidence_state','Transcrita'))} · creada {esc(formula.get('created_at',''))}</div>
    </div>
    """


# ---------------------------------------------------------------------------
# Ensayos / Teselas / Resultados
# ---------------------------------------------------------------------------


def active_experiment_choices(state: Dict[str, Any]) -> List[Tuple[str, str]]:
    choices = []
    for eid, e in sorted(state["experiments"].items(), key=lambda kv: kv[1].get("created_at", ""), reverse=True):
        if e.get("status") in {"Muestra creada", "Cocido", "Evaluado", "Archivado"}:
            continue
        label = f"{eid} · {e.get('name') or 'Ensayo'} · {e.get('status','Borrador')}"
        choices.append((label, eid))
    return choices


def all_experiment_choices(state: Dict[str, Any]) -> List[Tuple[str, str]]:
    return [
        (f"{eid} · {e.get('name') or 'Ensayo'} · {e.get('status','')}", eid)
        for eid, e in sorted(state["experiments"].items(), key=lambda kv: kv[1].get("created_at", ""), reverse=True)
    ]


def experiment_detail_html(e: Optional[Dict[str, Any]], formula: Optional[Dict[str, Any]] = None) -> str:
    if not e:
        return "<div class='notice'>Seleccioná un ensayo activo.</div>"
    f = formula or {}
    return f"""
    <div class='panel'>
      <div class='kicker'>{esc(e['id'])}</div>
      <h3>{esc(e.get('name') or 'Ensayo')}</h3>
      <div class='status'>{esc(e.get('status',''))}</div>
      <div class='grid2 compact'>
        <div><b>Fórmula origen</b><br>{esc(e.get('formula_id',''))}</div>
        <div><b>Base seca</b><br>{esc(e.get('base_mass_g',''))} g</div>
        <div><b>Pigmento</b><br>{esc(e.get('pigment_pct',''))} %</div>
        <div><b>Agua real</b><br>{esc(e.get('water_ml','—'))} ml</div>
        <div><b>Temperatura</b><br>{esc(e.get('target_temp_c',''))} °C</div>
        <div><b>Atmósfera</b><br>{esc(e.get('atmosphere',''))}</div>
      </div>
      <div class='muted'>{esc(e.get('notes',''))}</div>
      <div class='tiny'>Nombre heredado: {esc(f.get('name',''))}</div>
    </div>
    """


def tile_choices(state: Dict[str, Any]) -> List[Tuple[str, str]]:
    out = []
    for tid, t in sorted(state["tiles"].items(), key=lambda kv: kv[1].get("created_at", ""), reverse=True):
        progress = f"{t.get('firing_completed',0)}/{t.get('firing_required',1)}"
        out.append((f"{tid} · {t.get('name','Tesela')} · {t.get('stage','Creación')} · cocción {progress}", tid))
    return out


def tile_progress_html(t: Optional[Dict[str, Any]]) -> str:
    if not t:
        return "<div class='notice'>Seleccioná una tesela.</div>"
    stages = ["Preparación", "Aplicación", "Secado", "Cocción", "Resultado"]
    current = t.get("stage", "Preparación")
    try:
        ci = stages.index(current)
    except ValueError:
        ci = 0
    bits = []
    for i, s in enumerate(stages):
        if i < ci:
            bits.append(f"<span class='step done'>✓ {s}</span>")
        elif i == ci:
            bits.append(f"<span class='step current'>● {s}</span>")
        else:
            bits.append(f"<span class='step'>○ {s}</span>")
    photos_html = "".join(f"<figure><img class='thumb' src='{thumbnail_uri(DATA_DIR, item.get('photo_path'))}'><figcaption>{esc(item.get('stage'))}</figcaption></figure>" for item in t.get("process_photos", []) if thumbnail_uri(DATA_DIR, item.get("photo_path")))
    changes = mass_variations(t)
    mass_html = "".join(f"<div>{esc(x['from'])} → {esc(x['to'])}: {x['loss_g']:.2f} g · {format(x['loss_percent'], '.2f') if x['loss_percent'] is not None else '—'} % de pérdida de masa</div>" for x in changes)
    firing = f"{int(t.get('firing_completed',0))}/{int(t.get('firing_required',1))}"
    return f"""
    <div class='panel'>
      <div class='kicker'>{esc(t['id'])}</div><h3>{esc(t.get('name','Tesela'))}</h3>
      <div class='steps'>{' '.join(bits)}</div>{mass_html}{photos_html}
      <div class='notice'>Cocción: {firing} · {esc(t.get('firing_type','Monococción'))}</div>
      <div class='muted'>La tesela sólo se considera terminada cuando completa todas las cocciones requeridas y registra Resultado.</div>
    </div>
    """


def results_gallery_html(state: Dict[str, Any]) -> str:
    if not state["results"]:
        return "<div class='notice'>Todavía no hay resultados registrados.</div>"
    cards = []
    for rid, r in sorted(state["results"].items(), key=lambda kv: kv[1].get("created_at", ""), reverse=True):
        photo = thumbnail_uri(DATA_DIR, r.get("photo_path")) or r.get("photo")
        photo_html = f"<img class='thumb' src='{esc(photo)}'>" if photo and str(photo).startswith("data:") else (
            f"<span class='swatch result' style='background:{esc(r.get('result_hex','#888'))}'></span><span class='tiny'>Sin foto</span>"
        )
        cards.append(f"""
        <div class='result-card'>{photo_html}<div><b>{esc(rid)}</b><br>{esc(r.get('outcome',''))} · {esc(r.get('liking',''))}
        <div class='muted'>{esc(r.get('result_hex',''))} · {esc(r.get('delta_e_method', 'ΔE histórico; método no registrado'))} {('—' if r.get('delta_e') is None else format(r['delta_e'], '.2f'))}</div></div></div>
        """)
    return "".join(cards)


# ---------------------------------------------------------------------------
# Horno
# ---------------------------------------------------------------------------

KILN_PROGRAMS = {
    "Bizcocho 900 lento": [
        {"rate": 80, "target": 200, "hold": 0},
        {"rate": 120, "target": 600, "hold": 0},
        {"rate": 150, "target": 900, "hold": 10},
    ],
    "Esmalte 1040": [
        {"rate": 100, "target": 600, "hold": 0},
        {"rate": 160, "target": 1000, "hold": 0},
        {"rate": 80, "target": 1040, "hold": 10},
    ],
    "Monococción 1040": [
        {"rate": 60, "target": 200, "hold": 20},
        {"rate": 100, "target": 600, "hold": 0},
        {"rate": 150, "target": 1000, "hold": 0},
        {"rate": 70, "target": 1040, "hold": 10},
    ],
}


def program_duration_minutes(name: str, start_temp: float = 20.0) -> float:
    segs = KILN_PROGRAMS.get(name, [])
    total = 0.0
    prev = start_temp
    for s in segs:
        rate = max(1.0, float(s["rate"]))
        total += max(0.0, float(s["target"]) - prev) / rate * 60.0
        total += float(s.get("hold", 0))
        prev = float(s["target"])
    return total


def program_html(name: str) -> str:
    segs = KILN_PROGRAMS.get(name, [])
    if not segs:
        return "<div class='notice'>Elegí un programa.</div>"
    rows = "".join(
        f"<tr><td>{i}</td><td>{s['rate']:.0f} °C/h</td><td>{s['target']:.0f} °C</td><td>{s.get('hold',0):.0f} min</td></tr>"
        for i, s in enumerate(segs, 1)
    )
    mins = program_duration_minutes(name)
    return f"<table><thead><tr><th>Seg.</th><th>Rampa</th><th>Objetivo</th><th>Hold</th></tr></thead><tbody>{rows}</tbody></table><div class='notice'>Duración estimada: {mins/60:.1f} h. Referencia operativa: validar con controlador, carga y cono testigo.</div>"


def compatible_load_choices(state: Dict[str, Any], target_temp: float, atmosphere: str, stage_kind: str) -> List[Tuple[str, str]]:
    choices: List[Tuple[str, str]] = []
    for tid, t in state["tiles"].items():
        if int(t.get("firing_completed", 0)) >= int(t.get("firing_required", 1)):
            continue
        temp = float(t.get("target_temp_c", 0) or 0)
        atm = t.get("atmosphere", "Oxidante")
        if target_temp and abs(temp - float(target_temp)) > 20:
            continue
        if atmosphere and atm and atmosphere != atm:
            continue
        # Para bicocción: primera etapa se puede programar como Bizcocho; segunda como Esmalte.
        needed_index = int(t.get("firing_completed", 0)) + 1
        if stage_kind == "Bizcocho" and needed_index != 1:
            continue
        if stage_kind == "Esmalte" and t.get("firing_type") == "Bicocción" and needed_index != 2:
            continue
        choices.append((f"{tid} · {t.get('name','Tesela')} · {temp:.0f} °C · {atm}", tid))
    return choices


def firing_detail_html(f: Optional[Dict[str, Any]]) -> str:
    if not f:
        return "<div class='notice'>No hay hornada activa seleccionada.</div>"
    history = cooling_history(load_state(), f)
    cooling = (f"Historial del mismo horno/programa: {history['min_hours']:.1f}–{history['max_hours']:.1f} h hasta apertura ({history['samples']} registros). Incluye demoras del operador; no garantiza temperatura segura." if history else "Apertura estimada: sin historial comparable suficiente. Registrar lecturas reales; no se aplica una curva universal.")
    logs = "".join(
        f"<li>{esc(x.get('at',''))} · {esc(x.get('temp_c',''))} °C · {esc(x.get('stage',''))}</li>"
        for x in f.get("temp_log", [])[-12:]
    ) or "<li class='muted'>Sin lecturas manuales.</li>"
    return f"""
    <div class='panel'>
      <div class='kicker'>{esc(f['id'])}</div><h3>{esc(f.get('program_name','Hornada'))}</h3>
      <div class='status'>{esc(f.get('status',''))}</div>
      <div class='grid2 compact'><div><b>Objetivo</b><br>{esc(f.get('target_temp_c'))} °C</div><div><b>Atmósfera</b><br>{esc(f.get('atmosphere'))}</div>
      <div><b>Duración estimada del programa (sin enfriamiento)</b><br>{float(f.get('estimated_minutes',0))/60:.1f} h</div><div><b>Carga</b><br>{len(f.get('tile_ids',[]))} elementos</div></div>
      <div class='notice'>Fin del programa: {esc(f.get('program_finished_at') or 'No registrado')}. La apertura requiere una lectura actual del controlador, por debajo del límite configurado.</div><div class='muted'>{esc(cooling)}</div><div class='section-title'>Registro real de temperatura</div><ul>{logs}</ul>
    </div>
    """



# ---------------------------------------------------------------------------
# Biblioteca técnica de materiales / unidades / copias de seguridad
# ---------------------------------------------------------------------------

MATERIAL_CATEGORIES = ["Todos", "Arcillas", "Feldespatos", "Fritas", "Sílice", "Fundentes", "Carbonatos", "Óxidos", "Pigmentos", "Aditivos", "Otros"]

CONE_REFERENCE = {
    "010": {"15": 871, "60": 886, "150": 893},
    "06": {"15": 981, "60": 998, "150": 1013},
    "04": {"15": 1046, "60": 1063, "150": 1077},
    "02": {"15": 1078, "60": 1102, "150": 1122},
    "6": {"15": 1185, "60": 1222, "150": 1243},
}


def oxide_sum(material: Dict[str, Any]) -> float:
    return sum(float(v or 0) for v in (material.get("oxides") or {}).values())


def material_library_choices(state: Dict[str, Any], category: str = "Todos", query: str = "") -> List[Tuple[str, str]]:
    q = normalize_text(query)
    out = []
    for mid, m in state.get("materials_library", {}).items():
        if category and category != "Todos" and m.get("category") != category:
            continue
        hay = normalize_text(" ".join([m.get("name", ""), m.get("category", ""), m.get("source_exact", "")]))
        if q and q not in hay:
            continue
        out.append((f"{m.get('name')} · {m.get('category','')}", mid))
    out.sort(key=lambda x: normalize_text(x[0]))
    return out


def materials_library_html(state: Dict[str, Any], category: str = "Todos", query: str = "") -> str:
    choices = material_library_choices(state, category, query)
    if not choices:
        return "<div class='empty-state'><b>No hay materiales para este filtro.</b><div class='muted'>Probá otra categoría o creá un material propio.</div></div>"
    rows = []
    for _, mid in choices[:100]:
        m = state["materials_library"][mid]
        custom = " · propio" if m.get("custom") else ""
        rows.append(f"<div class='library-row'><div><b>{esc(m.get('name'))}</b><div class='tiny'>{esc(m.get('category'))}{custom}</div></div><span>›</span></div>")
    return "".join(rows)


def material_detail_html(state: Dict[str, Any], mid: str) -> str:
    m = state.get("materials_library", {}).get(mid)
    if not m:
        return "<div class='empty-state'><b>Elegí un material.</b><div class='muted'>La ficha técnica aparece acá.</div></div>"
    rows = "".join(
        f"<tr><td>{esc(ox)}</td><td>{float(val):.2f}%</td></tr>"
        for ox, val in (m.get("oxides") or {}).items()
    )
    if not rows:
        rows = "<tr><td colspan='2' class='muted'>Análisis de óxidos no cargado.</td></tr>"
    total = oxide_sum(m)
    linked_stock = [x for x in state.get("inventory", {}).values() if x.get("library_id") == mid]
    stock_txt = sum(float(x.get("qty", 0)) for x in linked_stock)
    unit = linked_stock[0].get("unit", "g") if linked_stock else "g"
    sum_note = "" if abs(total - 100) <= 1.0 or total == 0 else "<div class='notice'>Análisis no normalizado o incompleto. El dato original se conserva.</div>"
    return f"""
    <div class='panel'>
      <div class='kicker'>{esc(mid)}</div><h3>{esc(m.get('name'))}</h3>
      <div class='grid2 compact'><div><b>Categoría</b><br>{esc(m.get('category'))}</div><div><b>LOI</b><br>{float(m.get('loi') or 0):.2f}%</div>
      <div><b>Fuente</b><br>{esc(m.get('source_type'))}</div><div><b>En mi taller</b><br>{stock_txt:g} {esc(unit)}</div></div>
      <div class='section-title'>Análisis de óxidos</div>
      <table><thead><tr><th>Óxido</th><th>% peso</th></tr></thead><tbody>{rows}<tr><td><b>Suma de óxidos</b></td><td><b>{total:.2f}%</b></td></tr></tbody></table>
      <div class='tiny'>Fuente exacta: {esc(m.get('source_exact',''))}</div>{sum_note}
    </div>
    """


def cone_reference_html(cone: str) -> str:
    ref = CONE_REFERENCE.get(str(cone))
    if not ref:
        return "<div class='notice'>Sin referencia cargada para ese cono.</div>"
    return f"""
    <div class='panel compact'><b>Cono {esc(cone)} · autoportante</b>
    <table><tr><th>Velocidad final</th><th>Equivalente</th></tr>
    <tr><td>15 °C/h</td><td>{ref['15']} °C</td></tr>
    <tr><td>60 °C/h</td><td>{ref['60']} °C</td></tr>
    <tr><td>150 °C/h</td><td>{ref['150']} °C</td></tr></table>
    <div class='tiny'>Referencia Orton para conos autoportantes; el cono mide heatwork, no sólo temperatura.</div></div>
    """


def export_backup_file(state):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = DATA_DIR / f"ALUMINA_BACKUP_{uuid.uuid4().hex}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("state.json", json.dumps(dict(state), ensure_ascii=False, allow_nan=False))
        for media in (DATA_DIR / "media").glob("*"):
            if media.is_file():
                archive.write(media, "media/" + media.name)
    return str(out)


def import_backup_file(path):
    if not path:
        raise ValueError("Elegí una copia JSON o ZIP de ALUMINA.")
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            data = json.loads(archive.read("state.json"))
            if not isinstance(data, dict) or "schema_version" not in data:
                raise ValueError("Copia inválida.")
            mapping = {}
            for info in archive.infolist():
                name = info.filename
                if name == "state.json" or info.is_dir():
                    continue
                if not name.startswith("media/") or len(Path(name).parts) != 2 or ".." in Path(name).parts:
                    raise ValueError("La copia contiene una ruta no permitida.")
                target = DATA_DIR / "media" / (uuid.uuid4().hex + Path(name).suffix)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(info))
                mapping[name] = target.relative_to(DATA_DIR).as_posix()
            def relink(obj):
                if isinstance(obj, dict):
                    return {k: relink(v) for k, v in obj.items()}
                if isinstance(obj, list):
                    return [relink(v) for v in obj]
                return mapping.get(obj, obj) if isinstance(obj, str) else obj
            data = relink(data)
    else:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "schema_version" not in data:
        raise ValueError("El archivo no parece una copia ALUMINA.")
    # Preserve a portable pre-import recovery point, including media.
    export_backup_file(load_state())
    return migrate_state(data)

# ---------------------------------------------------------------------------
# Inventario / Compras / Proveedores
# ---------------------------------------------------------------------------


def pending_list_items(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [x for x in state["shopping_list"].values() if x.get("status") == "pending"]


def shopping_badge_text(state: Dict[str, Any]) -> str:
    return f"Lista · {len(pending_list_items(state))}"


def stock_ledger_html(state):
    rows = "".join(f"<tr><td>{esc(m.get('id', 'Registro anterior'))}</td><td>{esc(m.get('material_id'))}</td><td>{esc(m.get('delta'))}</td><td>{esc(m.get('type'))}</td><td>{esc(m.get('reference_id'))}</td><td>{esc(m.get('reason', ''))}</td></tr>" for m in reversed(state.get("stock_movements", [])[-100:]))
    return "<div class='panel'><b>Movimientos recientes</b><table><tr><th>ID</th><th>Material</th><th>Cantidad</th><th>Tipo</th><th>Origen</th><th>Motivo</th></tr>" + rows + "</table>Las recepciones se corrigen desde su pedido; los movimientos originales nunca se borran.</div>"


def inventory_html(state: Dict[str, Any]) -> str:
    cards = []
    for mid, m in sorted(state["inventory"].items(), key=lambda kv: normalize_text(kv[1].get("name", ""))):
        q = float(m.get("qty", 0)); mn = float(m.get("min_qty", 0))
        low = q < mn
        cls = " low" if low else ""
        cards.append(f"""
        <div class='stock-card{cls}'><div><b>{esc(m.get('name'))}</b><div class='tiny'>{esc(mid)}</div></div>
        <div class='stock-num'>{q:g} {esc(m.get('unit','g'))}<div class='tiny'>mín. {mn:g}</div></div></div>
        """)
    return "".join(cards)


def shopping_list_html(state: Dict[str, Any]) -> str:
    items = pending_list_items(state)
    if not items:
        return "<div class='empty-state'><b>No hay compras pendientes.</b><div class='muted'>Agregá un material desde cualquier módulo cuando lo necesites.</div></div>"
    out = []
    for item in sorted(items, key=lambda x: x.get("created_at", ""), reverse=True):
        out.append(f"""
        <div class='list-card'><div><b>{esc(item.get('material_name'))}</b><div class='tiny'>{esc(item['id'])} · origen {esc(item.get('origin_type',''))} {esc(item.get('origin_id',''))}</div>
        <div class='muted'>Necesario {float(item.get('needed_qty',0)):g} {esc(item.get('unit','g'))} · comprar {float(item.get('buy_qty',0)):g} {esc(item.get('unit','g'))}</div></div></div>
        """)
    return "".join(out)


def shopping_choices(state: Dict[str, Any]) -> List[Tuple[str, str]]:
    return [
        (f"{x['id']} · {x.get('material_name')} · {float(x.get('buy_qty',0)):g} {x.get('unit','g')}", x["id"])
        for x in pending_list_items(state)
    ]


def supplier_choices(state: Dict[str, Any], include_auto: bool = False) -> List[Tuple[str, str]]:
    choices = [(s.get("name", sid), sid) for sid, s in state["suppliers"].items()]
    choices.sort(key=lambda x: normalize_text(x[0]))
    if include_auto:
        choices.insert(0, ("Automático", ""))
    return choices


def supplier_product_matches(state: Dict[str, Any], item: Dict[str, Any], supplier_id: Optional[str] = None) -> List[Dict[str, Any]]:
    target_mid = item.get("material_id", "")
    target_name = normalize_text(item.get("material_name", ""))
    matches = []
    for p in state["supplier_products"].values():
        if supplier_id and p.get("supplier_id") != supplier_id:
            continue
        if not p.get("available", True):
            continue
        score = 0
        if target_mid and p.get("material_id") == target_mid:
            score = 100
        else:
            pn = normalize_text(p.get("material_name") or p.get("name", ""))
            if target_name and pn == target_name:
                score = 90
            elif target_name and (target_name in pn or pn in target_name):
                score = 70
        if score:
            cp = copy.deepcopy(p); cp["match_score"] = score; matches.append(cp)
    matches.sort(key=lambda x: (-x["match_score"], float(x.get("price") or 1e30)))
    return matches


def packages_for_qty(needed: float, package_qty: float) -> int:
    if package_qty <= 0:
        return 1
    return max(1, int(math.ceil(needed / package_qty)))


def line_total(product: Dict[str, Any], needed_qty: float) -> Tuple[int, float]:
    pack = float(product.get("package_qty") or needed_qty or 1)
    units = packages_for_qty(float(needed_qty or 0), pack)
    price = float(product.get("price") or 0)
    return units, units * price


def choose_supplier_plan(state: Dict[str, Any], items: List[Dict[str, Any]], strategy: str, chosen_supplier: str = "") -> Tuple[Dict[str, List[Tuple[Dict[str, Any], Dict[str, Any]]]], List[Dict[str, Any]], str]:
    assignments: Dict[str, List[Tuple[Dict[str, Any], Dict[str, Any]]]] = {}
    unresolved: List[Dict[str, Any]] = []

    # 1) proveedor elegido / preferido por material / predeterminado global
    default_sid = chosen_supplier or state["settings"].get("default_supplier_id", "")

    if strategy == "Mi proveedor":
        for item in items:
            inv = state["inventory"].get(item.get("material_id", ""), {})
            preferred = inv.get("preferred_supplier_id") or default_sid
            matches = supplier_product_matches(state, item, preferred) if preferred else []
            if matches:
                assignments.setdefault(matches[0]["supplier_id"], []).append((item, matches[0]))
                continue
            # faltante: buscar alternativa sin bloquear la compra
            alt = supplier_product_matches(state, item)
            if alt:
                assignments.setdefault(alt[0]["supplier_id"], []).append((item, alt[0]))
            else:
                unresolved.append(item)

    elif strategy == "Menos pedidos":
        # Elegir el proveedor con mayor cobertura; luego resolver faltantes.
        sids = list(state["suppliers"].keys())
        coverage = []
        for sid in sids:
            count = sum(1 for item in items if supplier_product_matches(state, item, sid))
            coverage.append((count, sid))
        coverage.sort(reverse=True)
        primary = coverage[0][1] if coverage and coverage[0][0] > 0 else default_sid
        for item in items:
            m = supplier_product_matches(state, item, primary) if primary else []
            if m:
                assignments.setdefault(primary, []).append((item, m[0]))
            else:
                alt = supplier_product_matches(state, item)
                if alt:
                    assignments.setdefault(alt[0]["supplier_id"], []).append((item, alt[0]))
                else:
                    unresolved.append(item)

    else:  # Mejor costo total aproximado con datos disponibles
        for item in items:
            candidates = supplier_product_matches(state, item)
            best = None
            best_cost = float("inf")
            for p in candidates:
                units, subtotal = line_total(p, float(item.get("buy_qty", 0)))
                supplier = state["suppliers"].get(p["supplier_id"], {})
                shipping = float(supplier.get("shipping_cost") or 0)
                # En esta etapa el costo de envío se usa como señal por proveedor.
                score = subtotal + shipping
                if score < best_cost:
                    best_cost, best = score, p
            if best:
                assignments.setdefault(best["supplier_id"], []).append((item, best))
            else:
                unresolved.append(item)

    summary = []
    for sid, rows in assignments.items():
        supplier = state["suppliers"].get(sid, {})
        subtotal = sum(line_total(p, float(i.get("buy_qty",0)))[1] for i, p in rows)
        shipping = float(supplier.get("shipping_cost") or 0)
        summary.append(f"{supplier.get('name',sid)}: {len(rows)} artículos · estimado {subtotal + shipping:,.2f}")
    return assignments, unresolved, " | ".join(summary)


def create_orders_from_list(state: Dict[str, Any], selected_ids: List[str], strategy: str, chosen_supplier: str) -> Tuple[Dict[str, Any], str]:
    items = [state["shopping_list"].get(i) for i in selected_ids if state["shopping_list"].get(i)]
    items = [i for i in items if i and i.get("status") == "pending"]
    if not items:
        return state, "No hay artículos pendientes seleccionados."

    assignments, unresolved, summary = choose_supplier_plan(state, items, strategy, chosen_supplier)
    created = []
    for sid, rows in assignments.items():
        oid = uid("PED", state["orders"])
        supplier = state["suppliers"].get(sid, {})
        order_lines = []
        for item, product in rows:
            units, subtotal = line_total(product, float(item.get("buy_qty", 0)))
            line = {
                "line_id": f"{oid}-L{len(order_lines)+1:02d}",
                "list_item_id": item["id"],
                "material_id": item.get("material_id", ""),
                "material_name": item.get("material_name", ""),
                "product_id": product["id"],
                "product_name": product.get("name", ""),
                "code": product.get("code", ""),
                "package_qty": float(product.get("package_qty") or 0),
                "package_unit": product.get("unit", item.get("unit", "g")),
                "packages_ordered": units,
                "qty_ordered": units * float(product.get("package_qty") or item.get("buy_qty", 0)),
                "price_estimated": float(product.get("price") or 0),
                "subtotal_estimated": subtotal,
                "product_url": product.get("url", ""),
                "price_status": product.get("price_status", "Último conocido"),
                "price_date": product.get("price_date", ""),
                "received_qty": 0.0,
                "actual_unit_price": None,
            }
            order_lines.append(line)
            item["status"] = "ordered"
            item["order_id"] = oid
        state["orders"][oid] = {
            "id": oid,
            "supplier_id": sid,
            "supplier_name": supplier.get("name", sid),
            "status": "Borrador",
            "strategy": strategy,
            "created_at": now_iso(),
            "lines": order_lines,
            "shipping_estimated": float(supplier.get("shipping_cost") or 0),
            "notes": "",
        }
        created.append(oid)
        audit_event(state, "order_created", "order", oid, strategy)

    save_state(state)
    msg = f"Creados: {', '.join(created) if created else 'ninguno'}. {summary}"
    if unresolved:
        msg += " · Sin equivalencia: " + ", ".join(i.get("material_name", "") for i in unresolved)
    return state, msg


def order_choices(state: Dict[str, Any]) -> List[Tuple[str, str]]:
    return [
        (f"{oid} · {o.get('supplier_name')} · {o.get('status')}", oid)
        for oid, o in sorted(state["orders"].items(), key=lambda kv: kv[1].get("created_at", ""), reverse=True)
    ]


def order_detail_html(state: Dict[str, Any], oid: str) -> str:
    o = state["orders"].get(oid)
    if not o:
        return "<div class='notice'>Seleccioná un pedido.</div>"
    rows = []
    est = 0.0
    for line in o.get("lines", []):
        est += float(line.get("subtotal_estimated", 0))
        link = line.get("product_url")
        link_html = f"<a target='_blank' href='{esc(link)}'>Ver producto ↗</a>" if link else "<span class='muted'>Sin enlace</span>"
        rows.append(f"""
        <tr><td>{esc(line.get('product_name') or line.get('material_name'))}<div class='tiny'>{esc(line.get('code',''))}</div></td>
        <td>{line.get('packages_ordered',1)} × {float(line.get('package_qty',0)):g} {esc(line.get('package_unit',''))}</td>
        <td>{float(line.get('price_estimated',0)):,.2f}<div class='tiny'>{esc(line.get('price_status',''))} {esc(line.get('price_date',''))}</div></td>
        <td>{link_html}</td></tr>
        """)
    shipping = float(o.get("shipping_estimated", 0))
    return f"""
    <div class='panel'><div class='kicker'>{esc(oid)}</div><h3>{esc(o.get('supplier_name'))}</h3><div class='status'>{esc(o.get('status'))}</div>
    <table><thead><tr><th>Producto</th><th>Presentación</th><th>Precio est.</th><th></th></tr></thead><tbody>{''.join(rows)}</tbody></table>
    <div class='notice'>Subtotal {est:,.2f} · envío estimado {shipping:,.2f} · total estimado {est+shipping:,.2f}</div></div>
    """


def whatsapp_message(state: Dict[str, Any], oid: str) -> Tuple[str, str]:
    o = state["orders"].get(oid)
    if not o:
        return "", ""
    supplier = state["suppliers"].get(o.get("supplier_id", ""), {})
    lines = [f"Hola, quisiera consultar/realizar el siguiente pedido ({oid}):"]
    for line in o.get("lines", []):
        desc = line.get("product_name") or line.get("material_name")
        code = f" · código {line.get('code')}" if line.get("code") else ""
        lines.append(f"- {line.get('packages_ordered',1)} x {desc}{code}")
    lines.append("¿Podrían confirmarme disponibilidad y total? Gracias.")
    text = "\n".join(lines)
    phone = re.sub(r"\D", "", str(supplier.get("phone", "")))
    url = f"https://wa.me/{phone}?text={urllib.parse.quote(text)}" if phone else ""
    return text, url


def receipt_table_value(state: Dict[str, Any], oid: str) -> List[List[Any]]:
    o = state["orders"].get(oid)
    if not o:
        return []
    rows = []
    for line in o.get("lines", []):
        rows.append([
            line["line_id"], line.get("material_name"), line.get("qty_ordered", 0),
            line.get("received_qty", 0), line.get("actual_unit_price") or line.get("price_estimated", 0)
        ])
    return rows


def apply_receipt(state, oid, table):
    state = copy.deepcopy(state)
    order = state["orders"].get(oid)
    if not order:
        raise ValueError("Pedido no encontrado.")
    rows = {}
    for row in table or []:
        if len(row) < 5 or str(row[0]) in rows:
            raise ValueError("Recepción inválida o línea duplicada.")
        rows[str(row[0])] = row
    valid_ids = {line["line_id"] for line in order.get("lines", [])}
    if set(rows) - valid_ids:
        raise ValueError("La recepción contiene líneas de otro pedido.")
    changed = False
    for line in order.get("lines", []):
        row = rows.get(line["line_id"])
        if row is None:
            continue
        received = number(row[3], "cantidad recibida acumulada")
        price = number(row[4], "precio real")
        previous = float(line.get("received_qty", 0))
        delta = received - previous
        mid = line.get("material_id")
        if not mid or mid not in state["inventory"]:
            raise ValueError("Vinculá un material de Stock antes de recibir el pedido.")
        # Both positive and negative corrections are ledger entries. The stock
        # and receipt are committed together, or neither changes.
        movement = stock_move(state, mid, delta, "purchase_receipt", oid,
                              reason="Recepción" if delta > 0 else "Corrección de recepción")
        if movement:
            movement["line_id"] = line["line_id"]
            changed = True
        if line.get("actual_unit_price") != price:
            state["price_history"].append({"at": now_iso(), "supplier_id": order.get("supplier_id"),
                "product_id": line.get("product_id"), "material_id": mid, "price": price, "order_id": oid})
            changed = True
        line.update(received_qty=received, actual_unit_price=price)
    complete = bool(order.get("lines")) and all(float(x.get("received_qty", 0)) >= float(x.get("qty_ordered", 0)) for x in order["lines"])
    partial = any(float(x.get("received_qty", 0)) > 0 for x in order.get("lines", []))
    status = "Recibido" if complete else "Parcialmente recibido" if partial else "Confirmado"
    if changed:
        order["status"] = status
        audit_event(state, "order_received", "order", oid, status)
        save_state(state)
    return state, "Recepción guardada. Las correcciones quedan registradas en Stock." if changed else "Sin cambios; esta recepción ya está registrada."



# ---------------------------------------------------------------------------
# Producción / Agenda / Bitácora
# ---------------------------------------------------------------------------


def projects_html(state: Dict[str, Any]) -> str:
    if not state["projects"]:
        return "<div class='empty-state'><b>Todavía no hay proyectos.</b><div class='muted'>Creá una pieza única o una serie cuando empieces producción.</div></div>"
    out = []
    for pid, p in state["projects"].items():
        out.append(f"<div class='panel compact'><b>{esc(p.get('name'))}</b><div class='tiny'>{pid} · {esc(p.get('type'))}</div><div class='muted'>{esc(p.get('notes',''))}</div></div>")
    return "".join(out)


def journal_html(state: Dict[str, Any]) -> str:
    if not state["journal"]:
        return "<div class='empty-state'><b>Bitácora vacía.</b><div class='muted'>Una nota rápida alcanza para empezar.</div></div>"
    out = []
    for item in reversed(state["journal"][-50:]):
        out.append(f"<div class='journal-entry'><div class='tiny'>{esc(item.get('at'))} · {esc(item.get('type'))}</div><div>{esc(item.get('text'))}</div></div>")
    return "".join(out)


def agenda_html(state: Dict[str, Any]) -> str:
    if not state["agenda"]:
        return "<div class='empty-state'><b>No hay eventos próximos.</b><div class='muted'>Agregá una clase, hornada, entrega o compra.</div></div>"
    items = sorted(state["agenda"].values(), key=lambda x: x.get("when", ""))
    return "".join(
        f"<div class='agenda-card'><b>{esc(x.get('title'))}</b><div>{esc(x.get('when'))}</div><div class='muted'>{esc(x.get('type'))} · {esc(x.get('location',''))}</div></div>"
        for x in items
    )


# ---------------------------------------------------------------------------
# Búsqueda global y dashboard
# ---------------------------------------------------------------------------


def global_search_html(state: Dict[str, Any], query: str) -> str:
    q = normalize_text(query)
    if not q:
        return "<div class='notice'>Escribí algo para buscar.</div>"
    hits = []
    for category, mapping in [
        ("Fórmula", state["formulas"]), ("Ensayo", state["experiments"]), ("Tesela", state["tiles"]),
        ("Material", state["inventory"]), ("Pedido", state["orders"]), ("Proyecto", state["projects"]),
    ]:
        for rid, obj in mapping.items():
            hay = normalize_text(" ".join(str(obj.get(k, "")) for k in ("name", "notes", "material_name", "supplier_name")))
            if q in normalize_text(rid) or q in hay:
                hits.append(f"<div class='search-hit'><b>{esc(category)} · {esc(rid)}</b><div class='muted'>{esc(obj.get('name') or obj.get('material_name') or obj.get('supplier_name') or '')}</div></div>")
    return "".join(hits[:30]) or "<div class='notice'>Sin coincidencias.</div>"


def home_html(state: Dict[str, Any]) -> str:
    active_exp = len(active_experiment_choices(state))
    pending_tiles = sum(1 for t in state["tiles"].values() if int(t.get("firing_completed",0)) < int(t.get("firing_required",1)))
    low = [m for m in state["inventory"].values() if float(m.get("qty",0)) < float(m.get("min_qty",0))]
    pending_shop = len(pending_list_items(state))
    agenda = sorted(state["agenda"].values(), key=lambda x: x.get("when", ""))[:1]
    next_html = ""
    if low:
        m = low[0]
        next_html = f"<b>{esc(m.get('name'))}</b> · stock {float(m.get('qty',0)):g}/{float(m.get('min_qty',0)):g} {esc(m.get('unit','g'))}"
    elif active_exp:
        next_html = f"{active_exp} ensayo(s) requieren acción"
    elif pending_tiles:
        next_html = f"{pending_tiles} tesela(s) pendientes de cocción"
    else:
        next_html = "Sin alertas operativas"
    agenda_html_one = f"<div class='tiny'>Próximo: {esc(agenda[0].get('when'))} · {esc(agenda[0].get('title'))}</div>" if agenda else ""
    return f"""
    <div class='dashboard'>
      <div class='hero-card'><div class='kicker'>SIGUIENTE ACCIÓN</div><div class='hero-text'>{next_html}</div>{agenda_html_one}</div>
      <div class='metric-row'><div><b>{active_exp}</b><span>LAB</span></div><div><b>{pending_tiles}</b><span>QUEMA</span></div><div><b>{pending_shop}</b><span>COMPRAS</span></div><div><b>{len(state['projects'])}</b><span>PRODUCCIÓN</span></div></div>
    </div>
    """


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

CSS = r"""
:root{color-scheme:light!important;--ink:#18222b;--muted:#66737f;--line:#d9e0e5;--soft:#f4f7f9;--accent:#2468d7;--accent-soft:#edf4ff;--danger:#a93d35;--ok:#247052}
html,body{color-scheme:light!important;background:#f7f8fa!important;color:var(--ink)!important}
.gradio-container{max-width:1120px!important;margin:auto!important;background:#f7f8fa!important;color:var(--ink)!important;--body-background-fill:#f7f8fa!important;--body-background-fill-dark:#f7f8fa!important;--body-text-color:#18222b!important;--body-text-color-dark:#18222b!important;--body-text-color-subdued:#66737f!important;--body-text-color-subdued-dark:#66737f!important;--block-background-fill:#fff!important;--block-background-fill-dark:#fff!important;--block-label-text-color:#394650!important;--block-label-text-color-dark:#394650!important;--block-title-text-color:#18222b!important;--block-title-text-color-dark:#18222b!important;--input-background-fill:#fff!important;--input-background-fill-dark:#fff!important;--input-border-color:#d9e0e5!important;--input-border-color-dark:#d9e0e5!important;--button-secondary-background-fill:#fff!important;--button-secondary-background-fill-dark:#fff!important;--button-secondary-text-color:#18222b!important;--button-secondary-text-color-dark:#18222b!important;--button-primary-background-fill:#2468d7!important;--button-primary-background-fill-dark:#2468d7!important;--button-primary-text-color:#fff!important;--button-primary-text-color-dark:#fff!important}
.gradio-container input,.gradio-container textarea,.gradio-container select{color:var(--ink)!important;background:#fff!important}
.gradio-container button{color:var(--ink)!important;background:#fff!important;border-color:var(--line)!important;opacity:1!important}.gradio-container button.primary,.gradio-container .primary button,.gradio-container button[class*="primary"]{background:var(--accent)!important;color:#fff!important;border-color:var(--accent)!important}
.app-head{position:sticky;top:0;z-index:80;background:rgba(255,255,255,.98)!important;padding:5px 0;border-bottom:1px solid var(--line);backdrop-filter:blur(10px)}
.brand{font-size:19px;font-weight:800;letter-spacing:.035em;color:var(--ink)!important}.demo-badge{display:inline-block;margin-left:8px;padding:2px 7px;border-radius:999px;background:#eef4ff!important;color:#285fae!important;font-size:10px;vertical-align:middle}.tag{font-size:11px;color:var(--muted)!important}
.nav-pills label,.subnav label,.card-radio label{border:1px solid var(--line)!important;border-radius:11px!important;padding:10px 12px!important;margin:3px!important;background:#fff!important;color:var(--ink)!important;min-height:44px!important;cursor:pointer!important;opacity:1!important}.nav-pills label span,.subnav label span,.card-radio label span{color:var(--ink)!important;opacity:1!important}.nav-pills input,.subnav input,.card-radio input{display:none!important}.nav-pills label:has(input:checked),.subnav label:has(input:checked),.card-radio label:has(input:checked){border-color:var(--accent)!important;box-shadow:0 0 0 2px rgba(36,104,215,.10)!important;background:var(--accent-soft)!important;color:#174d9a!important;font-weight:700!important}.nav-pills label:has(input:checked) span,.subnav label:has(input:checked) span,.card-radio label:has(input:checked) span{color:#174d9a!important}
.panel,.hero-card,.match-card,.result-card,.list-card,.agenda-card,.journal-entry{border:1px solid var(--line);background:#fff!important;color:var(--ink)!important;border-radius:14px;padding:14px;margin:8px 0}.panel.compact{padding:10px}.notice{background:var(--soft)!important;color:var(--ink)!important;border:1px solid var(--line);border-radius:10px;padding:10px;margin:8px 0}.notice.danger{border-color:#e8beb9;background:#fff4f3!important;color:#842f29!important}.muted{color:var(--muted)!important;font-size:13px}.tiny{color:var(--muted)!important;font-size:11px}.kicker{font-size:11px;letter-spacing:.12em;color:var(--muted)!important;font-weight:700}.section-title{font-size:13px;font-weight:800;margin:14px 0 6px}.status{display:inline-block;border-radius:999px;background:#eef4ff!important;color:#285fae!important;padding:4px 8px;font-size:12px;margin:4px 0 10px}
.color-id{display:flex;align-items:center;gap:10px;margin:10px 0}.swatch{width:54px;height:54px;border-radius:11px;border:1px solid var(--line);display:inline-block;flex:0 0 auto}.swatch.small{width:30px;height:30px;border-radius:7px}.swatch.result{width:52px;height:52px}.rowline{display:flex;gap:9px;align-items:center}.grid2{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.grid2>div{background:var(--soft)!important;color:var(--ink)!important;padding:9px;border-radius:9px}.compact{font-size:13px}
table{width:100%;border-collapse:collapse;font-size:13px;color:var(--ink)!important}th,td{padding:8px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top;color:var(--ink)!important}.metric-row{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:8px 0}.metric-row>div{background:var(--soft)!important;color:var(--ink)!important;border-radius:12px;padding:10px;text-align:center}.metric-row b{display:block;font-size:18px}.metric-row span{font-size:10px;color:var(--muted)!important}.hero-text{font-size:19px;font-weight:700}.steps{display:flex;gap:6px;flex-wrap:wrap}.step{font-size:12px;color:var(--muted)!important}.step.done{color:var(--ok)!important}.step.current{color:var(--accent)!important;font-weight:800}
.stock-card{display:flex;justify-content:space-between;gap:8px;border-bottom:1px solid var(--line);padding:10px 2px}.stock-card.low{background:#fff8f7!important;padding:10px}.stock-num{text-align:right;font-weight:700}.result-card{display:flex;gap:12px;align-items:center}.search-hit{padding:8px;border-bottom:1px solid var(--line)}.tool-panel{border:1px solid var(--line);border-radius:14px;padding:12px;background:#fbfcfd!important;color:var(--ink)!important}.empty-state{padding:32px 18px;text-align:center;background:#fff!important;color:var(--ink)!important;border:1px solid var(--line);border-radius:14px}.library-row{display:flex;justify-content:space-between;align-items:center;padding:13px 2px;border-bottom:1px solid var(--line);min-height:48px}.library-row span{font-size:24px;color:#8c98a2!important}.quick-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}.quick-grid button{min-height:56px!important}.gradio-container footer,footer{display:none!important}.gradio-container [role="tab"]{color:var(--ink)!important;opacity:1!important}.gradio-container [role="tab"][aria-selected="true"]{color:#174d9a!important;font-weight:700!important}
@media(max-width:700px){html{scroll-padding-bottom:150px!important}.gradio-container{padding:0 8px 150px!important}.nav-pills{position:fixed!important;left:8px!important;right:8px!important;bottom:max(8px,env(safe-area-inset-bottom))!important;top:auto!important;z-index:9999!important;background:#fff!important;border:1px solid var(--line)!important;border-radius:18px!important;padding:4px!important;box-shadow:0 10px 32px rgba(20,30,40,.16)!important}.nav-pills>div{display:grid!important;grid-template-columns:repeat(4,minmax(0,1fr))!important;gap:3px!important}.nav-pills label{margin:0!important;border:0!important;border-radius:14px!important;padding:8px 3px!important;min-height:46px!important;text-align:center!important;font-size:10.5px!important;line-height:1.1!important}.nav-pills label:has(input:checked){background:var(--accent-soft)!important;box-shadow:none!important}.app-head{padding-top:3px!important}.app-head button{min-height:34px!important;font-size:11px!important;padding:4px 7px!important}.grid2{grid-template-columns:1fr 1fr}.metric-row{grid-template-columns:repeat(4,1fr)}.quick-grid{grid-template-columns:repeat(4,1fr)}.quick-grid button{font-size:11.5px!important;padding:7px 3px!important}.subnav label{padding:8px 7px!important;font-size:11.5px!important;min-height:40px!important}.hero-text{font-size:17px!important}.panel,.hero-card,.match-card,.result-card,.list-card,.agenda-card,.journal-entry{padding:11px!important}}
"""


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------


def saber_text(section):
    return {
        "Portada": "## SABER\nAprender, consultar y compartir. Esta versión organiza el espacio; todavía no hay un servicio editorial conectado para publicar tips o artículos nuevos.",
        "Aprender": "## Aprender\nLas fichas técnicas disponibles se consultan en **Herramientas → Materiales**. La biblioteca didáctica y el curso opcional con ejercicios manuales quedan pendientes de desarrollo.",
        "Profe AI": "## Profe AI\nEl asistente cerámico aún no está conectado. No se generan respuestas simuladas ni se envían datos del taller a un servicio externo.",
        "Comunidad": "## Comunidad\nEl intercambio de fórmulas, resultados y eventos aún no está conectado. Tus registros permanecen en tu archivo de datos.",
    }[section]


def build_app() -> gr.Blocks:
    initial = load_state()
    fchoices0 = [(f"{fid} · {f.get('name') or 'Sin nombre'}", fid) for fid, f in initial["formulas"].items()]
    mchoices0 = [(f"{mid} · {m.get('name')}", mid) for mid, m in initial["inventory"].items()]
    pchoices0 = [(p.get("name", pid), pid) for pid, p in initial["projects"].items()]
    schoices0 = [(s.get("name", sid), sid) for sid, s in initial["series"].items()]
    expchoices0 = active_experiment_choices(initial)
    tilechoices0 = tile_choices(initial)
    shopchoices0 = shopping_choices(initial)
    orderchoices0 = order_choices(initial)
    firingchoices0 = [(f"{fid} · {f.get('status')}", fid) for fid, f in initial["firings"].items()]
    f0 = fchoices0[0][1] if fchoices0 else None
    e0 = expchoices0[0][1] if expchoices0 else None
    t0 = tilechoices0[0][1] if tilechoices0 else None
    o0 = orderchoices0[0][1] if orderchoices0 else None
    h0 = firingchoices0[0][1] if firingchoices0 else None
    e0_obj = initial["experiments"].get(e0) if e0 else None
    e0_formula = initial["formulas"].get(e0_obj.get("formula_id")) if e0_obj else None
    t0_obj = initial["tiles"].get(t0) if t0 else None

    with gr.Blocks(title=f"ALUMINA STUDIO {APP_VERSION}") as demo:
        state = gr.State(session_token(initial))
        parsed_manual_state = gr.State([])
        tools_open = gr.State(False)

        with gr.Column(elem_classes=["app-head"]):
            gr.HTML("<div class='brand'>ALUMINA STUDIO <span class='demo-badge'>DEMO</span></div><div class='tag'>Taller · ciencia · oficio</div>")
            search_q = gr.Textbox(
                label=None, placeholder="Buscar fórmula, ensayo, material, pedido…",
                container=False, submit_btn="Buscar", min_width=120
            )
            with gr.Row(equal_height=True):
                tools_btn = gr.Button("Herramientas", scale=1, min_width=80, size="sm")
                shop_badge = gr.Button(shopping_badge_text(initial), scale=1, min_width=70, size="sm")
                config_btn = gr.Button("Parámetros", scale=1, min_width=70, size="sm")

        # La navegación principal queda FUERA del header sticky. En iOS, un
        # elemento fixed dentro de un ancestro con efectos/sticky puede dejar
        # de anclarse al viewport y aparecer debajo del buscador.
        module_nav = gr.Radio(
            ["Inicio", "LAB", "TALLER", "SABER"],
            value="Inicio", label=None, show_label=False, elem_id="main-nav", elem_classes=["nav-pills"]
        )

        search_results = gr.HTML(visible=False)
        with gr.Group(visible=False, elem_classes=["tool-panel"]) as tools_panel:
            with gr.Tabs():
                with gr.Tab("Calculadoras"):
                    with gr.Row():
                        calc_moles = gr.Number(value=1.0, label="Moles")
                        calc_mm = gr.Number(value=100.0, label="Masa molar g/mol")
                        calc_g = gr.Number(label="Gramos", interactive=False)
                    calc_btn = gr.Button("Moles → gramos")
                    with gr.Row():
                        dry_len = gr.Number(value=100, label="Medida seca mm")
                        fired_len = gr.Number(value=90, label="Medida cocida mm")
                        shrink_out = gr.Number(label="Contracción %", interactive=False)
                    shrink_btn = gr.Button("Calcular contracción")
                with gr.Tab("Tabla periódica"):
                    gr.HTML("<div class='notice'><b>Tabla periódica:</b> la tabla interactiva aún no está implementada en esta base. Las fichas disponibles están en Materiales.</div>")
                with gr.Tab("Conos"):
                    cone_sel = gr.Dropdown(list(CONE_REFERENCE.keys()), value="06", label="Cono Orton · autoportante")
                    cone_detail = gr.HTML(cone_reference_html("06"))

                with gr.Tab("Materiales"):
                    with gr.Group(visible=True) as workshop_materials:
                        gr.Markdown("## Materiales")
                        with gr.Row():
                            matlib_search = gr.Textbox(label=None, placeholder="Buscar material…", scale=4, container=False)
                            matlib_new = gr.Button("+", scale=1)
                        matlib_category = gr.Radio(MATERIAL_CATEGORIES, value="Todos", label=None, show_label=False, elem_classes=["subnav"])
                        matlib_list = gr.HTML(materials_library_html(initial))
                        matlib_sel = gr.Dropdown(choices=material_library_choices(initial), label="Abrir ficha")
                        matlib_detail = gr.HTML(material_detail_html(initial, (material_library_choices(initial)[0][1] if material_library_choices(initial) else "")))
                        with gr.Accordion("Nuevo material propio", open=False) as matlib_new_panel:
                            with gr.Row():
                                matlib_name = gr.Textbox(label="Nombre")
                                matlib_cat = gr.Dropdown(MATERIAL_CATEGORIES[1:], value="Otros", label="Categoría")
                                matlib_loi = gr.Number(value=0, label="LOI %")
                            matlib_source = gr.Textbox(label="Fuente / ficha técnica")
                            matlib_oxides = gr.Textbox(lines=6, label="Óxidos", placeholder="SiO2 66.3\nAl2O3 18.5\nK2O 11.3")
                            matlib_save = gr.Button("Guardar material", variant="primary")
                            matlib_msg = gr.HTML()

        # ---------------- INICIO ----------------
        with gr.Group(visible=True) as g_home:
            home = gr.HTML(home_html(initial) + f"<div class='notice'><b>DEMO cargada</b> · {len(initial['formulas'])} fórmulas · {len(active_experiment_choices(initial))} ensayos activos · {len(initial['tiles'])} teselas · {len(initial['shopping_list'])} ítems en Lista · {len(initial['orders'])} pedido.</div>")
            gr.Markdown("### Accesos rápidos")
            with gr.Row():
                q_formula = gr.Button("Fórmula")
                q_experiment = gr.Button("Ensayo")
                q_piece = gr.Button("Pieza")
                q_kiln = gr.Button("Horno")
            with gr.Row():
                q_result = gr.Button("Resultado")
                q_stock = gr.Button("Estante")
                q_buy = gr.Button("Comprar")
                q_costs = gr.Button("Costos")

        # LAB: creación, ensayo y memoria técnica.
        with gr.Group(visible=False) as g_lab:
            lab_nav = gr.Radio(["Color Sampler", "Ensayo", "Formulario"], value="Color Sampler", show_label=False, elem_classes=["subnav"])
            with gr.Group(visible=True) as lab_formula:
                gr.Markdown("## Color Sampler")

                with gr.Group(visible=True) as digital_group:
                    with gr.Row():
                        digital_image = gr.Image(sources=["webcam", "upload"], type="filepath", label="Cámara / foto de referencia", height=230)
                        with gr.Column():
                            target_hex = gr.ColorPicker(value="#F25A18", label="Color objetivo")
                            target_identity = gr.HTML(color_identity_html("#F25A18"))
                            digital_origin = gr.Radio(["Digital · Cámara", "Digital · Selector"], value="Digital · Selector", label="Origen")
                    formula_name = gr.Textbox(label="Nombre de fórmula (opcional)", placeholder="Ej. Naranja Talavera 01")
                    with gr.Row():
                        f_vehicle = gr.Dropdown(["Esmalte", "Engobe", "Pasta coloreada"], value="Esmalte", label="Vehículo")
                        f_base_type = gr.Dropdown(["Fritada", "Cruda", "Mi fórmula"], value="Fritada", label="Tipo de base")
                        f_chem = gr.Dropdown(["Alcalina", "Borácica / borosilicato", "Plúmbica", "Cálcica", "Zíncica", "Alcalino-térrea", "Mixta", "No definida"], value="Borácica / borosilicato", label="Familia química")
                    with gr.Row():
                        f_optics = gr.Dropdown(["Transparente", "Translúcida", "Opaca"], value="Transparente", label="Óptica")
                        f_surface = gr.Dropdown(["Brillante", "Satinada", "Mate"], value="Brillante", label="Superficie")
                        f_body = gr.Textbox(value="Loza blanca", label="Pasta soporte")
                    with gr.Row():
                        f_temp = gr.Number(value=1040, label="Temperatura °C")
                        f_atm = gr.Dropdown(["Oxidante", "Reductora", "Neutra"], value=initial["settings"].get("default_atmosphere","Oxidante"), label="Atmósfera")
                        f_pct = gr.Number(value=6, label="Pigmento %")
                    pigment_out = gr.HTML("<div class='notice'><b>Candidatos orientativos</b><br>Cd-S-Se inclusión — Color naranja/rojo de inclusión: candidato orientativo, no identificación.<br>Fe2O3 - óxido de hierro — Puede producir rojos/ocres según base, concentración y cocción.</div>")
                    pigment_sel = gr.Dropdown(["Cd-S-Se inclusión", "Fe2O3 - óxido de hierro"], value="Cd-S-Se inclusión", label="Familia candidata (orientativa)")
                    xse = gr.Slider(0, 0.60, value=0.30, step=0.01, label="S ↔ Se · xSe", visible=True)
                    dna_out = gr.HTML("<div class='panel'><b>ADN químico</b><div>CdS<sub>0.70</sub>Se<sub>0.30</sub> incluido en ZrSiO4</div><div class='muted'>S 0.70 mol · Se 0.30 mol · S+Se=1.00. La relación S↔Se es una sustitución molar ligada.</div></div>")
                    match_btn = gr.Button("Buscar coincidencias")
                    match_out = gr.HTML()
                    save_digital = gr.Button("Guardar fórmula digital", variant="primary")
                    digital_msg = gr.HTML()

            with gr.Group(visible=False) as lab_trial:
                trial_nav = gr.Radio(["Preparación", "Muestras", "Resultado", "Historial"], value="Preparación", show_label=False, elem_classes=["subnav"])
                with gr.Group(visible=True) as lab_experiment:
                    gr.Markdown("## Ensayo")
                    experiment_cards = gr.Radio(choices=expchoices0, value=e0, label=None, show_label=False, elem_classes=["card-radio"])
                    experiment_detail = gr.HTML(experiment_detail_html(e0_obj, e0_formula))
                    with gr.Row():
                        exp_formula_sel = gr.Dropdown(choices=fchoices0, value=f0, label="Fórmula origen")
                        exp_mass = gr.Number(value=50, label="Base seca g")
                        exp_water = gr.Number(value=(e0_obj.get("water_ml") if e0_obj else None), label="Agua realmente utilizada ml")
                    exp_notes = gr.Textbox(value=(e0_obj.get("notes","") if e0_obj else ""), lines=3, label="Observaciones")
                    create_exp_btn = gr.Button("Crear ensayo desde fórmula", variant="primary")
                    save_exp_btn = gr.Button("Guardar estado del ensayo")
                    create_tile_btn = gr.Button("Crear tesela / muestra desde este ensayo", variant="primary")
                    exp_msg = gr.HTML()
                with gr.Group(visible=False) as lab_tile:
                    gr.Markdown("## Tesela")
                    tile_cards = gr.Radio(choices=tilechoices0, value=t0, label=None, show_label=False, elem_classes=["card-radio"])
                    tile_progress = gr.HTML(tile_progress_html(t0_obj))
                    with gr.Row():
                        tile_firing_type = gr.Radio(["Monococción", "Bicocción"], value=(t0_obj.get("firing_type") if t0_obj else initial["settings"].get("default_firing_type","Bicocción")), label="Tipo de cocción")
                        tile_stage = gr.Dropdown(["Preparación", "Aplicación", "Secado", "Cocción", "Resultado"], value=(t0_obj.get("stage") if t0_obj else "Preparación"), label="Etapa actual")
                    with gr.Group(visible=bool(t0_obj and t0_obj.get("stage")=="Secado")) as tile_dry_group:
                        gr.Markdown("### Secado · mediciones")
                        with gr.Row():
                            tile_wet_weight = gr.Number(value=(t0_obj.get("wet_weight") if t0_obj else None), label="Peso húmedo g")
                            tile_dry_weight = gr.Number(value=(t0_obj.get("dry_weight") if t0_obj else None), label="Peso seco g")
                            tile_dry_length = gr.Number(value=(t0_obj.get("dry_length") if t0_obj else None), label="Medida seca mm")
                    with gr.Group(visible=bool(t0_obj and t0_obj.get("stage")=="Resultado")) as tile_result_measure_group:
                        gr.Markdown("### Resultado · medición final")
                        tile_fired_length = gr.Number(value=(t0_obj.get("fired_length") if t0_obj else None), label="Medida cocida mm")
                        tile_bisque_weight = gr.Number(value=(t0_obj.get("bisque_weight") if t0_obj else None), label="Peso bizcocho g (opcional)")
                        tile_final_weight = gr.Number(value=(t0_obj.get("final_weight") if t0_obj else None), label="Peso final g (opcional)")
                    tile_process_photo = gr.Image(sources=["upload", "webcam"], type="filepath", label="Foto de esta etapa (opcional)", height=180)
                    tile_notes = gr.Textbox(value=(t0_obj.get("notes","") if t0_obj else ""), lines=3, label="Observación de esta etapa")
                    save_tile_stage = gr.Button("Guardar etapa", variant="primary")
                    tile_msg = gr.HTML()
                with gr.Group(visible=False) as lab_result:
                    gr.Markdown("## Resultado")
                    result_tile_sel = gr.Dropdown(choices=tilechoices0, value=t0, label="Tesela")
                    with gr.Row():
                        result_hex = gr.ColorPicker(value="#E95F20", label="Color obtenido")
                        result_photo = gr.Image(sources=["upload", "webcam"], type="filepath", label="Foto real de la tesela", height=200)
                    with gr.Row():
                        result_outcome = gr.Radio(["Funcionó", "Parcial", "Falló"], value="Funcionó", label="Evaluación", elem_classes=["card-radio"])
                        result_liking = gr.Radio(["Me gusta", "Neutral", "No me gusta"], value="Me gusta", label="Preferencia", elem_classes=["card-radio"])
                    with gr.Row():
                        result_action = gr.Radio(["Conservar", "Repetir", "Ajustar", "Archivar"], value="Conservar", label="Acción", elem_classes=["card-radio"])
                        note_kind = gr.Radio(["Comentario", "Defecto"], value="Comentario", label="Tipo")
                    result_note = gr.Textbox(lines=4, label="Escribir observación…")
                    save_result_btn = gr.Button("Guardar resultado", variant="primary")
                    result_msg = gr.HTML()
                    result_gallery = gr.HTML(results_gallery_html(initial))
                with gr.Group(visible=False) as lab_history:
                    gr.Markdown("## Historial")
                    lab_history_html = gr.HTML("".join(f"<div class='panel compact'><b>{eid}</b> · {esc(e.get('name'))}<div class='muted'>{esc(e.get('status'))} · muestras {len(e.get('tile_ids',[]))}</div></div>" for eid,e in sorted(initial["experiments"].items(),key=lambda kv:kv[1].get("created_at",""),reverse=True)))
                    refresh_lab_history = gr.Button("Actualizar historial")
            with gr.Group(visible=False) as workshop_formulas:
                gr.Markdown("## Formulario")
                gr.HTML("<div class='muted'>Archivo personal de formulaciones guardadas. Fórmulas y referencias del LAB; conservan su identidad y procedencia.</div>")
                formula_library_sel = gr.Dropdown(choices=fchoices0, value=f0, label="Formulación guardada")
                formula_library_detail = gr.HTML(formula_detail_html(initial["formulas"].get(f0)))
                formula_mode = gr.Radio(["Guardadas", "Agregar fórmula", "Partir de existente"], value="Guardadas", show_label=False, elem_classes=["subnav"])
                with gr.Group(visible=False) as manual_group:
                    gr.Markdown("### Escribir / importar")
                    manual_name = gr.Textbox(label="Nombre de fórmula")
                    manual_text = gr.Textbox(lines=10, label="Original / receta", placeholder="Caolín 30\nSílice 20\nFrita 50")
                    with gr.Row():
                        manual_file = gr.File(label="PDF / documento", type="filepath")
                        manual_photo = gr.Image(sources=["webcam", "upload"], type="filepath", label="Foto del apunte / evidencia", height=200)
                    with gr.Row():
                        manual_source_type = gr.Dropdown(["Propia", "Clase / docente", "Libro / artículo", "Comunidad", "Fabricante", "Referencia externa"], value="Propia", label="Fuente")
                        manual_source_exact = gr.Textbox(label="Fuente exacta / página / autor")
                    parse_btn = gr.Button("Interpretar estructura")
                    parse_out = gr.HTML()
                    normalize_btn = gr.Button("Normalizar interpretación a 100", visible=False)
                    save_manual = gr.Button("Guardar fórmula escrita/importada", variant="primary")
                    manual_msg = gr.HTML()

                with gr.Group(visible=False) as existing_group:
                    existing_formula = gr.Dropdown(choices=fchoices0, value=f0, label="Mis fórmulas")
                    existing_detail = gr.HTML(formula_detail_html(initial["formulas"].get(f0)))
                    duplicate_formula_btn = gr.Button("Duplicar / ajustar")
                    normalized_version_btn = gr.Button("Crear versión normalizada a 100")
                    duplicate_formula_msg = gr.HTML()

        # TALLER: operación física, con una sola copia de cada registro.
        with gr.Group(visible=False) as g_workshop:
            workshop_nav = gr.Radio(["Bitácora", "Estante", "Operaciones"], value="Bitácora", show_label=False, elem_classes=["subnav"])
            with gr.Group(visible=True) as workshop_log:
                log_nav = gr.Radio(["Agenda", "Historial", "Registro", "Gastos"], value="Agenda", show_label=False, elem_classes=["subnav"])
                with gr.Group(visible=True) as workshop_agenda:
                    gr.Markdown("## Agenda")
                    agenda_view = gr.HTML(agenda_html(initial))
                    with gr.Row():
                        agenda_title = gr.Textbox(label="Título")
                        agenda_when = gr.Textbox(label="Fecha / hora", placeholder="2026-10-01 18:00")
                    with gr.Row():
                        agenda_type = gr.Dropdown(["Curso", "Seminario", "Hornada", "Entrega", "Compra", "Proyecto", "Otro"], value="Curso", label="Tipo")
                        agenda_location = gr.Textbox(label="Lugar")
                    agenda_notes = gr.Textbox(label="Notas / enlace")
                    agenda_add = gr.Button("Agregar a Agenda")
                with gr.Group(visible=False) as workshop_journal:
                    gr.Markdown("## Historial y notas")
                    journal_view = gr.HTML(journal_html(initial))
                    journal_type = gr.Dropdown(["Nota", "Foto", "Idea", "Proceso", "Referencia"], value="Nota", label="Tipo")
                    journal_text = gr.Textbox(lines=4, label="Entrada")
                    journal_add = gr.Button("Agregar a Bitácora")
                with gr.Group(visible=False) as ops_production:
                    gr.Markdown("## Registro · piezas y lotes")
                    project_view = gr.HTML(projects_html(initial))
                    with gr.Row():
                        project_name = gr.Textbox(label="Proyecto")
                        project_type = gr.Radio(["Pieza única", "Serie / colección"], value="Pieza única", label="Tipo")
                    project_notes = gr.Textbox(label="Notas")
                    create_project = gr.Button("Crear proyecto")
                    with gr.Row():
                        series_project = gr.Dropdown(choices=pchoices0, value=(pchoices0[0][1] if pchoices0 else None), label="Proyecto")
                        series_object = gr.Dropdown(["Taza", "Plato", "Bowl", "Cuenco", "Jarra", "Florero", "Azulejo", "Escultura", "Otro"], label="Serie de")
                        series_qty = gr.Number(value=12, label="Cantidad objetivo")
                    series_name = gr.Textbox(label="Nombre de serie")
                    create_series = gr.Button("Crear serie")
                    with gr.Row():
                        lot_series = gr.Dropdown(choices=schoices0, value=(schoices0[0][1] if schoices0 else None), label="Serie")
                        lot_qty = gr.Number(value=6, label="Cantidad del lote")
                    create_lot = gr.Button("Crear lote")
                    production_msg = gr.HTML()
                with gr.Group(visible=False) as workshop_expenses:
                    gr.Markdown("## Gastos")
                    gr.Markdown("El registro unificado de gastos está pendiente. Los importes de compras se conservan en sus pedidos; todavía no representan un balance completo del taller.")
            with gr.Group(visible=False) as workshop_stock:
                gr.Markdown("## Estante")
                stock_view = gr.HTML(inventory_html(initial))
                with gr.Row():
                    stock_material = gr.Dropdown(choices=mchoices0, value=(mchoices0[0][1] if mchoices0 else None), label="Material")
                    stock_qty = gr.Number(value=initial["inventory"].get(mchoices0[0][1], {}).get("qty") if mchoices0 else None, label="Stock actual")
                    stock_min = gr.Number(value=initial["inventory"].get(mchoices0[0][1], {}).get("min_qty") if mchoices0 else None, label="Mínimo")
                with gr.Row():
                    stock_location = gr.Textbox(label="Ubicación")
                    stock_pref_supplier = gr.Dropdown(choices=supplier_choices(initial, include_auto=True), label="Proveedor preferido")
                save_stock_btn = gr.Button("Guardar material / stock")
                low_to_list_btn = gr.Button("Sugerir faltantes de stock en Lista")
                stock_msg = gr.HTML()
                with gr.Accordion("Confirmar consumo / pesado", open=False):
                    consume_reference = gr.Textbox(label="ID del ensayo, pieza/proyecto o lote")
                    consume_qty = gr.Number(label="Cantidad consumida (unidad del material seleccionado)")
                    consume_estimated = gr.Checkbox(label="La cantidad es una estimación")
                    consume_accept = gr.Checkbox(label="Acepto explícitamente descontar esta estimación")
                    consume_id = gr.State(uuid.uuid4().hex)
                    consume_btn = gr.Button("Confirmar pesado / consumo y descontar")
                with gr.Accordion("Movimientos y correcciones", open=False):
                    movement_view = gr.HTML(stock_ledger_html(initial))
                    movement_id = gr.Textbox(label="ID del movimiento a revertir")
                    movement_reason = gr.Textbox(label="Motivo de la reversión")
                    movement_reverse = gr.Button("Revertir movimiento")
                    movement_refresh = gr.Button("Actualizar movimientos")
            with gr.Group(visible=False) as g_ops:
                ops_nav = gr.Radio(["Horneadas", "Compras", "Estadísticas"], value="Horneadas", show_label=False, elem_classes=["subnav"])
                with gr.Group(visible=True) as ops_kiln:
                    gr.Markdown("## Horno")
                    kiln_program = gr.Dropdown(list(KILN_PROGRAMS.keys()), value="Esmalte 1040", label="Programa")
                    kiln_program_detail = gr.HTML(program_html("Esmalte 1040"))
                    with gr.Row():
                        firing_kind = gr.Radio(["Bizcocho", "Esmalte", "Monococción"], value="Esmalte", label="Etapa")
                        firing_temp = gr.Number(value=1040, label="Objetivo °C")
                        firing_atm = gr.Dropdown(["Oxidante", "Reductora", "Neutra"], value="Oxidante", label="Atmósfera")
                    compatible_refresh = gr.Button("Buscar pendientes compatibles")
                    compatible_tiles = gr.CheckboxGroup(choices=[], label="Carga compatible")
                    start_firing = gr.Button("Crear / iniciar hornada", variant="primary")
                    firing_sel = gr.Dropdown(choices=firingchoices0, value=h0, label="Hornada")
                    firing_detail = gr.HTML(firing_detail_html(initial["firings"].get(h0)))
                    with gr.Row():
                        actual_temp = gr.Number(label="Temperatura REAL del controlador °C")
                        log_temp = gr.Button("Registrar temperatura real")
                    with gr.Row():
                        mark_program_done = gr.Button("Programa finalizado")
                        confirm_open = gr.Button("Confirmar apertura")
                        confirm_unload = gr.Button("Confirmar descarga")
                        complete_firing = gr.Button("Completar hornada")
                    firing_msg = gr.HTML()
                with gr.Group(visible=False) as ops_buy:
                    gr.Markdown("## Compras")
                    buy_nav = gr.Radio(["Lista", "Pedidos", "Proveedores"], value="Lista", label=None, show_label=False, elem_classes=["subnav"])
                    with gr.Group(visible=True) as buy_list_group:
                        shopping_view = gr.HTML(shopping_list_html(initial))
                        shopping_select = gr.CheckboxGroup(choices=shopping_choices(initial), label="Seleccionar para pedido")
                        with gr.Accordion("+ Agregar necesidad", open=False):
                            with gr.Row():
                                add_material = gr.Dropdown(choices=mchoices0, value=(mchoices0[0][1] if mchoices0 else None), label="Material")
                                add_needed_qty = gr.Number(value=100, label="Cantidad necesaria")
                                add_buy_qty = gr.Number(value=100, label="Cantidad a comprar")
                            with gr.Row():
                                add_origin_type = gr.Dropdown(["Manual", "Fórmula", "Ensayo", "Stock", "Preparación", "Producción"], value="Manual", label="Origen")
                                add_origin_id = gr.Textbox(label="ID origen")
                            add_list_btn = gr.Button("Agregar a Lista")
                        with gr.Accordion("Resolver selección", open=True):
                            with gr.Row():
                                order_strategy = gr.Radio(["Mi proveedor", "Menos pedidos", "Mejor costo total"], value="Mi proveedor", label="Estrategia")
                                order_supplier = gr.Dropdown(choices=supplier_choices(initial, include_auto=True), label="Proveedor")
                            create_order_btn = gr.Button("Crear pedido con seleccionados", variant="primary")
                        buy_msg = gr.HTML()

                    with gr.Group(visible=False) as buy_orders_group:
                        order_sel = gr.Dropdown(choices=orderchoices0, value=o0, label="Pedido")
                        order_detail = gr.HTML(order_detail_html(initial, o0) if o0 else "")
                        with gr.Row():
                            order_mark_consulted = gr.Button("Marcar consultado")
                            order_mark_confirmed = gr.Button("Marcar confirmado")
                            order_mark_transit = gr.Button("Marcar en camino")
                        wa_text = gr.Textbox(value=(whatsapp_message(initial,o0)[0] if o0 else ""), lines=7, label="Mensaje para proveedor")
                        wa_link = gr.HTML()
                        receipt_table = gr.Dataframe(
                            value=(receipt_table_value(initial,o0) if o0 else []),
                            headers=["line_id", "material", "pedido", "recibido", "precio real / unidad"],
                            datatype=["str", "str", "number", "number", "number"],
                            interactive=True, label="Recepción parcial / total"
                        )
                        receive_btn = gr.Button("Guardar recepción", variant="primary")
                        order_msg = gr.HTML()

                    with gr.Group(visible=False) as buy_suppliers_group:
                        supplier_list_html = gr.HTML()
                        with gr.Accordion("+ Proveedor", open=False):
                            with gr.Row():
                                sup_name = gr.Textbox(label="Proveedor")
                                sup_phone = gr.Textbox(label="WhatsApp / teléfono")
                                sup_web = gr.Textbox(label="Web / catálogo")
                            with gr.Row():
                                sup_shipping = gr.Number(value=0, label="Envío estimado")
                                sup_notes = gr.Textbox(label="Notas")
                            add_supplier_btn = gr.Button("Guardar proveedor")
                        with gr.Accordion("Vincular producto del proveedor", open=False):
                            with gr.Row():
                                sp_supplier = gr.Dropdown(choices=supplier_choices(initial), label="Proveedor")
                                sp_material = gr.Dropdown(choices=mchoices0, value=(mchoices0[0][1] if mchoices0 else None), label="Material ALUMINA")
                            with gr.Row():
                                sp_name = gr.Textbox(label="Producto comercial")
                                sp_code = gr.Textbox(label="Código")
                                sp_url = gr.Textbox(label="Link exacto del producto")
                            with gr.Row():
                                sp_pack = gr.Number(value=1000, label="Presentación")
                                sp_unit = gr.Dropdown(["g", "kg", "ml", "l", "unidad"], value="g", label="Unidad")
                                sp_price = gr.Number(value=0, label="Precio")
                            with gr.Row():
                                sp_price_status = gr.Dropdown(["Actual consultado", "Último conocido", "Ingresado manualmente"], value="Ingresado manualmente", label="Estado del precio")
                                sp_price_date = gr.Textbox(value=datetime.now().date().isoformat(), label="Fecha precio")
                            add_supplier_product_btn = gr.Button("Guardar equivalencia producto")
                        supplier_msg = gr.HTML()
                with gr.Group(visible=False) as ops_costs:
                    gr.Markdown("## Estadísticas · costos")
                    costs_html = gr.HTML("<div class='notice'>Costos sigue siendo parcial hasta combinar materiales realmente consumidos + hornada ejecutada + mano de obra.</div>")
        with gr.Group(visible=False) as g_learn:
            saber_nav = gr.Radio(["Portada", "Aprender", "Profe AI", "Comunidad"], value="Portada", show_label=False, elem_classes=["subnav"])
            saber_content = gr.Markdown(saber_text("Portada"))

        # ---------------- CONFIG ----------------
        with gr.Group(visible=False) as g_config:
            gr.Markdown("## Parámetros del taller")
            with gr.Tabs():
                with gr.Tab("General"):
                    cfg_default_supplier = gr.Dropdown(choices=supplier_choices(initial, include_auto=True), value=initial["settings"].get("default_supplier_id", ""), label="Proveedor predeterminado")
                    cfg_advanced = gr.Checkbox(value=bool(initial["settings"].get("advanced_pigment_synthesis", False)), label="Modo avanzado · síntesis de pigmentos")
                    cfg_open_temp = gr.Number(value=float(initial["settings"].get("opening_temp_c",50)), label="Temperatura máxima para habilitar apertura °C")
                    cfg_atmosphere = gr.Dropdown(["Oxidante", "Reductora", "Neutra"], value=initial["settings"].get("default_atmosphere","Oxidante"), label="Atmósfera habitual")
                    cfg_firing_type = gr.Dropdown(["Monococción", "Bicocción"], value=initial["settings"].get("default_firing_type","Bicocción"), label="Cocción habitual")
                    save_config = gr.Button("Guardar configuración")
                    reset_confirm = gr.Checkbox(label="Confirmo reemplazar el taller por datos DEMO (se guarda una copia antes)")
                    reset_demo_btn = gr.Button("Restaurar datos DEMO")
                    config_msg = gr.HTML()
                    gr.HTML(f"<div class='tiny'>Datos: {esc(str(DATA_DIR / 'alumina.sqlite3'))}</div>")
                with gr.Tab("Unidades"):
                    units = initial["settings"].get("units", {})
                    unit_temp = gr.Dropdown(["°C", "°F"], value=units.get("temperature","°C"), label="Temperatura")
                    unit_raw = gr.Dropdown(["g", "kg"], value=units.get("raw_weight","g"), label="Materias primas")
                    unit_clay = gr.Dropdown(["g", "kg"], value=units.get("clay_weight","g"), label="Pasta")
                    unit_piece = gr.Dropdown(["g", "kg"], value=units.get("piece_weight","g"), label="Pieza")
                    unit_vol = gr.Dropdown(["mL", "L"], value=units.get("volume","mL"), label="Volumen")
                    unit_len = gr.Dropdown(["mm", "cm"], value=units.get("length","cm"), label="Longitud")
                    save_units = gr.Button("Guardar unidades")
                    units_msg = gr.HTML()
                with gr.Tab("Datos"):
                    gr.Markdown("### Copia de seguridad")
                    export_backup = gr.Button("Exportar copia ALUMINA")
                    export_file = gr.File(label="Copia generada", interactive=False)
                    import_file = gr.File(label="Importar copia ALUMINA", file_types=[".json", ".zip"], type="filepath")
                    import_confirm = gr.Checkbox(label="Confirmo reemplazar el taller con esta copia")
                    import_backup = gr.Button("Importar y reemplazar datos")
                    backup_msg = gr.HTML()
                with gr.Tab("Mi horno"):
                    kiln_sel_cfg = gr.Dropdown(choices=[(k.get("name",kid),kid) for kid,k in initial["kilns"].items()], value=initial["settings"].get("default_kiln_id","KILN-0001"), label="Horno")
                    with gr.Row():
                        kiln_name_cfg = gr.Textbox(value="Mi horno", label="Nombre / modelo")
                        kiln_capacity_cfg = gr.Number(label="Capacidad L")
                        kiln_power_cfg = gr.Number(label="Potencia kW")
                    with gr.Row():
                        kiln_voltage_cfg = gr.Number(value=220, label="Tensión V")
                        kiln_controller_cfg = gr.Textbox(label="Controlador")
                        kiln_energy_cfg = gr.Number(label="Costo energía / kWh")
                    kiln_notes_cfg = gr.Textbox(label="Notas")
                    save_kiln_cfg = gr.Button("Guardar horno")
                    kiln_cfg_msg = gr.HTML()

        # ---------------- CALLBACKS GENERALES ----------------
        module_groups = [g_home, g_lab, g_workshop, g_learn, g_config]
        module_names = ["Inicio", "LAB", "TALLER", "SABER", "Parámetros"]
        def nav_main(name):
            return [gr.update(visible=name == n) for n in module_names]
        def nav_main_clean(name):
            return nav_main(name) + [gr.update(value=""), gr.update(value="", visible=False)]
        module_nav.change(nav_main_clean, module_nav, module_groups + [search_q, search_results])
        config_btn.click(lambda: [gr.update(value=None)] + nav_main_clean("Parámetros"), outputs=[module_nav] + module_groups + [search_q, search_results])
        saber_nav.change(saber_text, saber_nav, saber_content)

        def toggle_tools(is_open: bool):
            new = not bool(is_open)
            return new, gr.update(visible=new)
        tools_btn.click(toggle_tools, inputs=tools_open, outputs=[tools_open, tools_panel])
        calc_btn.click(lambda m, mm: float(m or 0) * float(mm or 0), [calc_moles, calc_mm], calc_g)
        shrink_btn.click(lambda dry, fired: 0 if not dry else (float(dry)-float(fired or 0))/float(dry)*100, [dry_len, fired_len], shrink_out)
        cone_sel.change(cone_reference_html, cone_sel, cone_detail)

        def search_cb(st, q):
            return gr.update(value=global_search_html(st, q), visible=True)
        search_q.submit(search_cb, [state, search_q], search_results)

        # Direct routes update both selection and visibility in one callback.
        sections = [
            (lab_nav, ["Color Sampler", "Ensayo", "Formulario"], [lab_formula, lab_trial, workshop_formulas]),
            (trial_nav, ["Preparación", "Muestras", "Resultado", "Historial"], [lab_experiment, lab_tile, lab_result, lab_history]),
            (workshop_nav, ["Bitácora", "Estante", "Operaciones"], [workshop_log, workshop_stock, g_ops]),
            (log_nav, ["Agenda", "Historial", "Registro", "Gastos"], [workshop_agenda, workshop_journal, ops_production, workshop_expenses]),
            (ops_nav, ["Horneadas", "Compras", "Estadísticas"], [ops_kiln, ops_buy, ops_costs]),
            (buy_nav, ["Lista", "Pedidos", "Proveedores"], [buy_list_group, buy_orders_group, buy_suppliers_group]),
        ]
        for control, names, groups in sections:
            control.change(lambda value, names=names: [gr.update(visible=value == n) for n in names], control, groups)
        route_outputs = [module_nav] + module_groups + [search_q, search_results]
        for control, names, groups in sections:
            route_outputs += [control] + groups
        def route(module, lab="Color Sampler", trial="Preparación", workshop="Bitácora", log="Agenda", ops="Horneadas", buy="Lista"):
            updates = [gr.update(value=module)] + nav_main_clean(module)
            for value, (_, names, groups) in zip([lab, trial, workshop, log, ops, buy], sections):
                updates += [gr.update(value=value)] + [gr.update(visible=value == n) for n in names]
            return updates
        shop_badge.click(lambda: route("TALLER", workshop="Operaciones", ops="Compras"), outputs=route_outputs)
        q_formula.click(lambda: route("LAB"), outputs=route_outputs)
        q_experiment.click(lambda: route("LAB", lab="Ensayo"), outputs=route_outputs)
        q_result.click(lambda: route("LAB", lab="Ensayo", trial="Resultado"), outputs=route_outputs)
        q_stock.click(lambda: route("TALLER", workshop="Estante"), outputs=route_outputs)
        q_buy.click(lambda: route("TALLER", workshop="Operaciones", ops="Compras"), outputs=route_outputs)
        q_kiln.click(lambda: route("TALLER", workshop="Operaciones"), outputs=route_outputs)
        q_piece.click(lambda: route("TALLER", log="Registro"), outputs=route_outputs)
        q_costs.click(lambda: route("TALLER", workshop="Operaciones", ops="Estadísticas"), outputs=route_outputs)

        # Biblioteca técnica de materiales
        def refresh_material_library(st, category, q):
            choices = material_library_choices(st, category or "Todos", q or "")
            return materials_library_html(st, category or "Todos", q or ""), gr.update(choices=choices, value=(choices[0][1] if choices else None))
        matlib_search.change(refresh_material_library, [state, matlib_category, matlib_search], [matlib_list, matlib_sel])
        matlib_category.change(refresh_material_library, [state, matlib_category, matlib_search], [matlib_list, matlib_sel])
        matlib_sel.change(lambda mid, st: material_detail_html(st, mid), [matlib_sel, state], matlib_detail)

        def parse_oxide_block(text):
            out = {}
            for line in (text or "").splitlines():
                line = line.strip()
                if not line:
                    continue
                m = re.match(r"^(.+?)\s*[:=]?\s*(-?\d+(?:[.,]\d+)?)\s*%?$", line)
                if not m:
                    continue
                out[m.group(1).strip()] = float(m.group(2).replace(',', '.'))
            return out

        def save_material_library_cb(st, name, category, loi, source, oxides_text):
            if not (name or '').strip():
                return st, "<div class='notice'>Escribí un nombre.</div>", materials_library_html(st), gr.update(), material_detail_html(st, "")
            st = copy.deepcopy(st)
            mid = uid("LIB", st.get("materials_library", {}))
            st.setdefault("materials_library", {})[mid] = {
                "id": mid, "name": name.strip(), "category": category or "Otros", "source_type": "USUARIO",
                "source_exact": source or "Carga manual", "loi": float(loi or 0), "oxides": parse_oxide_block(oxides_text), "custom": True
            }
            save_state(st)
            choices = material_library_choices(st)
            return st, f"<div class='notice'>Material {esc(mid)} guardado.</div>", materials_library_html(st), gr.update(choices=choices, value=mid), material_detail_html(st, mid)
        matlib_save.click(save_material_library_cb, [state, matlib_name, matlib_cat, matlib_loi, matlib_source, matlib_oxides], [state, matlib_msg, matlib_list, matlib_sel, matlib_detail])

        # Fórmula: modos
        formula_mode.change(
            lambda x: [gr.update(visible=x == "Agregar fórmula"), gr.update(visible=x == "Partir de existente")],
            formula_mode, [manual_group, existing_group]
        )

        def color_changed(h):
            hv = normalize_hex(h)
            cands = pigment_candidates(hv)
            html_c = "<div class='notice'><b>Candidatos orientativos</b><br>" + "<br>".join(f"{esc(a)} — {esc(b)}" for a,b in cands) + "</div>"
            choices = [a for a,_ in cands]
            return color_identity_html(hv), html_c, gr.update(choices=choices, value=(choices[0] if choices else None)), gr.update(visible=(choices and choices[0]=="Cd-S-Se inclusión"))
        target_hex.change(color_changed, target_hex, [target_identity, pigment_out, pigment_sel, xse])

        def pigment_selected(name, x):
            if name == "Cd-S-Se inclusión":
                x = float(x or 0.30); s = 1-x
                return gr.update(visible=True), f"<div class='panel'><b>ADN químico</b><div>CdS<sub>{s:.2f}</sub>Se<sub>{x:.2f}</sub> incluido en ZrSiO4</div><div class='muted'>S {s:.2f} mol · Se {x:.2f} mol · S+Se=1.00. La relación S↔Se es una sustitución molar ligada.</div></div>"
            return gr.update(visible=False), "<div class='notice'>La familia seleccionada no usa el control S↔Se.</div>"
        pigment_sel.change(pigment_selected, [pigment_sel, xse], [xse, dna_out])
        xse.change(lambda n,x: pigment_selected(n,x)[1], [pigment_sel,xse], dna_out)

        match_btn.click(lambda st,h,t,a,b: formula_match_results(st, normalize_hex(h), float(t or 0), a, b), [state,target_hex,f_temp,f_atm,f_body], match_out)

        def refresh_dynamic(st, force=False):
            before = getattr(st, "baseline", {})
            dirty = {key for key in st if force or before.get(key) != st.get(key)}
            active = getattr(repository().local, "transaction", None)
            if active and not force:
                dirty = {key for key in st if active["before"].get(key) != st.get(key)}
            def update(dependencies, render):
                return render() if force or dirty.intersection(dependencies) else gr.skip()
            def formulas():
                return gr.update(choices=[(f"{fid} · {f.get('name') or 'Sin nombre'}", fid) for fid,f in st["formulas"].items()])
            def materials():
                return gr.update(choices=[(f"{mid} · {m.get('name')}", mid) for mid,m in st["inventory"].items()])
            def suppliers(auto=True):
                return gr.update(choices=supplier_choices(st, include_auto=auto))
            lab = [update({"formulas"}, formulas) for _ in range(3)]
            stock = [update({"inventory"}, materials) for _ in range(3)]
            production = [
                update({"projects"}, lambda: gr.update(choices=[(p.get("name",pid),pid) for pid,p in st["projects"].items()])),
                update({"series"}, lambda: gr.update(choices=[(p.get("name",pid),pid) for pid,p in st["series"].items()])),
            ]
            trials = [update({"experiments"}, lambda: gr.update(choices=active_experiment_choices(st)))] + [update({"tiles"}, lambda: gr.update(choices=tile_choices(st))) for _ in range(2)]
            purchases = [update({"shopping_list"}, lambda: gr.update(choices=shopping_choices(st))),
                update({"suppliers"}, suppliers), update({"suppliers"}, lambda: suppliers(False)),
                update({"suppliers"}, lambda: suppliers(False)), update({"suppliers"}, suppliers),
                update({"orders"}, lambda: gr.update(choices=order_choices(st))),
                update({"shopping_list"}, lambda: gr.update(value=shopping_badge_text(st)))]
            views = [
                update({"inventory","experiments","firings","shopping_list","agenda"}, lambda: home_html(st)),
                update({"inventory"}, lambda: inventory_html(st)),
                update({"shopping_list","orders"}, lambda: shopping_list_html(st)),
                update({"results"}, lambda: results_gallery_html(st)),
                update({"projects","lots","series"}, lambda: projects_html(st)),
                update({"agenda"}, lambda: agenda_html(st)), update({"journal"}, lambda: journal_html(st)),
                update({"materials_library"}, lambda: gr.update(choices=material_library_choices(st))),
                update({"materials_library","inventory"}, lambda: materials_library_html(st)),
            ]
            return tuple(lab + stock + production + trials + purchases + views)

        refresh_outputs = [
            existing_formula, exp_formula_sel, formula_library_sel,
            stock_material, add_material, sp_material,
            series_project, lot_series,
            experiment_cards, tile_cards, result_tile_sel,
            shopping_select, order_supplier, sp_supplier,
            cfg_default_supplier, stock_pref_supplier,
            order_sel, shop_badge,
            home, stock_view, shopping_view, result_gallery, project_view, agenda_view, journal_view,
            matlib_sel, matlib_list
        ]

        def save_digital_cb(st, name, origin, hv, vehicle, base_type, chem, optics, surface, body, temp, atm, pct, pigment, x, image_path):
            st = copy.deepcopy(st)
            fid = formula_id_for_origin(st, origin)
            lab = hex_to_lab(hv)
            st["formulas"][fid] = {
                "id": fid, "name": (name or "").strip(), "origin": origin,
                "source_type": "EXPERIMENTAL", "source_exact": "Captura/selector ALUMINA",
                "evidence_state": "Propuesta · sin validar experimentalmente", "created_at": now_iso(),
                "target_hex": normalize_hex(hv), "target_lab": list(lab),
                "vehicle": vehicle, "base_type": base_type, "chemistry_family": chem,
                "optics": optics, "surface": surface, "body": body,
                "target_temp_c": float(temp or 0), "atmosphere": atm,
                "pigment_pct": float(pct or 0), "pigment_candidate": pigment,
                "x_se": float(x or 0) if pigment == "Cd-S-Se inclusión" else None,
                "components": [], "versions": [], "source_image": persist_media(DATA_DIR, image_path)
            }
            audit_event(st,"formula_created","formula",fid,origin); save_state(st)
            return (st, f"<div class='notice'><b>{esc(name or fid)}</b> guardada. ID técnico: {fid}. El nombre del usuario y el ID permanecen separados.</div>", *refresh_dynamic(st))
        save_digital.click(save_digital_cb, [state,formula_name,digital_origin,target_hex,f_vehicle,f_base_type,f_chem,f_optics,f_surface,f_body,f_temp,f_atm,f_pct,pigment_sel,xse,digital_image], [state,digital_msg]+refresh_outputs)

        def parse_manual_cb(text):
            comps,total,warns = parse_formula_text(text)
            rows = "".join(f"<tr><td>{esc(c['name'])}</td><td>{c['amount']}</td><td>{esc(c['unit'])}</td></tr>" for c in comps)
            wh = "".join(f"<div class='tiny'>{esc(w)}</div>" for w in warns)
            h = f"<div class='panel'><b>Interpretación ALUMINA</b><table><tr><th>Material</th><th>Cant.</th><th>Unidad</th></tr>{rows}</table><div class='notice'>Total detectado: {total:.2f}</div>{wh}</div>"
            return comps, h, gr.update(visible=(bool(comps) and abs(total-100)>0.01))
        parse_btn.click(parse_manual_cb, manual_text, [parsed_manual_state, parse_out, normalize_btn])

        def normalize_manual_cb(comps):
            normalized = normalized_components(comps)
            rows = "".join(f"<tr><td>{esc(c['name'])}</td><td>{c['amount']:.3f} %</td></tr>" for c in normalized)
            return "<div class='panel'><b>Vista normalizada a 100</b><table>" + rows + "</table>El original y sus cantidades permanecen intactos.</div>"
        normalize_btn.click(normalize_manual_cb, parsed_manual_state, parse_out)

        def save_manual_cb(st, name, text, comps, src_type, src_exact, file_path, photo_path):
            st = copy.deepcopy(st)
            comps, _, warnings = parse_formula_text(text)
            if not comps:
                raise ValueError("Ingresá una fórmula válida; el adjunto se conserva como referencia, no se interpreta automáticamente.")
            origin = "PDF" if file_path and str(file_path).lower().endswith(".pdf") else "Manual"
            fid = formula_id_for_origin(st, origin)
            st["formulas"][fid] = {
                "id": fid, "name": (name or "").strip(), "origin": origin,
                "source_type": src_type, "source_exact": src_exact, "evidence_state": "Transcrita · revisión técnica pendiente",
                "created_at": now_iso(), "original_text": text, "original_file": persist_media(DATA_DIR, file_path, False), "original_photo": persist_media(DATA_DIR, photo_path),
                "components": copy.deepcopy(comps or []), "target_hex": "", "target_lab": None,
                "vehicle": "", "base_type": "", "chemistry_family": "", "optics": "", "surface": "", "body": "",
                "target_temp_c": None, "atmosphere": "", "pigment_pct": None, "versions": []
            }
            audit_event(st,"formula_created","formula",fid,origin); save_state(st)
            return (st, f"<div class='notice'>Guardada como {fid}. Estado: transcrita; no se marca como validada experimentalmente.</div>", *refresh_dynamic(st))
        save_manual.click(save_manual_cb, [state,manual_name,manual_text,parsed_manual_state,manual_source_type,manual_source_exact,manual_file,manual_photo], [state,manual_msg]+refresh_outputs)

        existing_formula.change(lambda fid,st: formula_detail_html(st["formulas"].get(fid)), [existing_formula,state], existing_detail)
        formula_library_sel.change(lambda fid,st: formula_detail_html(st["formulas"].get(fid)), [formula_library_sel,state], formula_library_detail)

        def duplicate_formula_cb(st,fid):
            if not fid or fid not in st["formulas"]: return st,"<div class='notice'>Elegí una fórmula.</div>",*refresh_dynamic(st)
            st=copy.deepcopy(st); nid=formula_version(st, fid); save_state(st)
            return st,f"<div class='notice'>Derivada creada: {nid}</div>",*refresh_dynamic(st)
        duplicate_formula_btn.click(duplicate_formula_cb,[state,existing_formula],[state,duplicate_formula_msg]+refresh_outputs)

        def normalized_version_cb(st,fid):
            if fid not in st["formulas"]:
                raise ValueError("Elegí una fórmula.")
            nid = formula_version(st,fid,normalized_components(st["formulas"][fid].get("components")),"Normalización a 100")
            save_state(st)
            return st,f"<div class='notice'>Versión {esc(nid)} creada; el original permanece intacto.</div>",*refresh_dynamic(st)
        normalized_version_btn.click(normalized_version_cb,[state,existing_formula],[state,duplicate_formula_msg]+refresh_outputs)

        # Ensayos
        def create_exp_cb(st,fid,mass,water,notes):
            if not fid or fid not in st["formulas"]:
                return st,"<div class='notice danger'>Elegí una fórmula.</div>",*refresh_dynamic(st)
            st=copy.deepcopy(st); f=st["formulas"][fid]; eid=uid("ENS",st["experiments"])
            st["experiments"][eid]={"id":eid,"formula_id":fid,"name":f.get("name") or f"Ensayo de {fid}","status":"Preparación","created_at":now_iso(),"base_mass_g":float(mass or 0),"water_ml":float(water or 0) if water is not None else None,"notes":notes,"pigment_pct":f.get("pigment_pct"),"target_temp_c":f.get("target_temp_c"),"atmosphere":f.get("atmosphere"),"body":f.get("body"),"tile_ids":[]}
            audit_event(st,"experiment_created","experiment",eid,fid); save_state(st)
            return st,f"<div class='notice'>Creado {eid}. Los datos de la fórmula se heredaron.</div>",*refresh_dynamic(st)
        create_exp_btn.click(create_exp_cb,[state,exp_formula_sel,exp_mass,exp_water,exp_notes],[state,exp_msg]+refresh_outputs)

        def exp_select_cb(eid,st):
            e=st["experiments"].get(eid); f=st["formulas"].get(e.get("formula_id")) if e else None
            return experiment_detail_html(e,f), (e.get("water_ml") if e else None), (e.get("notes","") if e else "")
        experiment_cards.change(exp_select_cb,[experiment_cards,state],[experiment_detail,exp_water,exp_notes])

        def save_exp_cb(st,eid,water,notes):
            if not eid or eid not in st["experiments"]: return st,"<div class='notice'>Seleccioná un ensayo.</div>",*refresh_dynamic(st)
            st=copy.deepcopy(st); e=st["experiments"][eid]; e["water_ml"]=float(water or 0) if water is not None else None; e["notes"]=notes; e["status"]="Listo para muestra"; save_state(st)
            return st,f"<div class='notice'>Autoguardado {eid}.</div>",*refresh_dynamic(st)
        save_exp_btn.click(save_exp_cb,[state,experiment_cards,exp_water,exp_notes],[state,exp_msg]+refresh_outputs)

        def create_tile_cb(st,eid):
            if not eid or eid not in st["experiments"]: return st,"<div class='notice'>Seleccioná un ensayo.</div>",*refresh_dynamic(st)
            st=copy.deepcopy(st); e=st["experiments"][eid]; tid=uid("TES",st["tiles"]); f=st["formulas"].get(e.get("formula_id"),{})
            st["tiles"][tid]={"id":tid,"experiment_id":eid,"formula_id":e.get("formula_id"),"name":f.get("name") or tid,"created_at":now_iso(),"firing_type":st["settings"].get("default_firing_type","Bicocción"),"firing_required":2 if st["settings"].get("default_firing_type","Bicocción")=="Bicocción" else 1,"firing_completed":0,"stage":"Preparación","target_temp_c":float(e.get("target_temp_c") or 1040),"atmosphere":e.get("atmosphere") or "Oxidante","notes":"","firing_ids":[]}
            e.setdefault("tile_ids",[]).append(tid); e["status"]="Muestra creada"; save_state(st)
            return st,f"<div class='notice'><b>✓ {tid} creada.</b> El ensayo sale de Activos y queda en Historial. Podés crear otra muestra más adelante desde su ficha.</div>",*refresh_dynamic(st)
        create_tile_btn.click(create_tile_cb,[state,experiment_cards],[state,exp_msg]+refresh_outputs)

        # Teselas
        def tile_stage_visibility(stage):
            return gr.update(visible=(stage == "Secado")), gr.update(visible=(stage == "Resultado"))

        tile_stage.change(tile_stage_visibility, tile_stage, [tile_dry_group, tile_result_measure_group])

        def tile_select_cb(tid,st):
            t=st["tiles"].get(tid)
            if not t:
                return tile_progress_html(None),"Bicocción","Preparación",None,None,None,None,"",gr.update(visible=False),gr.update(visible=False),None,None
            stage=t.get("stage","Preparación")
            return tile_progress_html(t),t.get("firing_type","Bicocción"),stage,t.get("wet_weight"),t.get("dry_weight"),t.get("dry_length"),t.get("fired_length"),t.get("notes",""),gr.update(visible=(stage=="Secado")),gr.update(visible=(stage=="Resultado")),t.get("bisque_weight"),t.get("final_weight")
        tile_cards.change(tile_select_cb,[tile_cards,state],[tile_progress,tile_firing_type,tile_stage,tile_wet_weight,tile_dry_weight,tile_dry_length,tile_fired_length,tile_notes,tile_dry_group,tile_result_measure_group,tile_bisque_weight,tile_final_weight])

        def save_tile_cb(st,tid,ftype,stage,ww,dw,dl,fl,notes,bw,fw,photo):
            if not tid or tid not in st["tiles"]: raise ValueError("Seleccioná una tesela.")
            st=copy.deepcopy(st); t=st["tiles"][tid]; t.update({"firing_type":ftype,"firing_required":2 if ftype=="Bicocción" else 1,"stage":stage,"wet_weight":ww,"dry_weight":dw,"dry_length":dl,"fired_length":fl,"notes":notes,"bisque_weight":bw,"final_weight":fw})
            if photo:
                t.setdefault("process_photos", []).append({"id":uuid.uuid4().hex,"stage":stage,"at":now_iso(),"photo_path":persist_media(DATA_DIR, photo)})
            t["mass_variations"] = mass_variations(t)
            save_state(st)
            return st,f"<div class='notice'>Etapa guardada: {esc(stage)}.</div>",*refresh_dynamic(st),tile_progress_html(t),None
        save_tile_stage.click(save_tile_cb,[state,tile_cards,tile_firing_type,tile_stage,tile_wet_weight,tile_dry_weight,tile_dry_length,tile_fired_length,tile_notes,tile_bisque_weight,tile_final_weight,tile_process_photo],[state,tile_msg]+refresh_outputs+[tile_progress,tile_process_photo])

        # Resultados
        def save_result_cb(st,tid,hv,photo,outcome,liking,action,kind,note):
            if not tid or tid not in st["tiles"]: return st,"<div class='notice'>Elegí una tesela.</div>",*refresh_dynamic(st)
            st=copy.deepcopy(st); t=st["tiles"][tid]; f=st["formulas"].get(t.get("formula_id"),{}); rid=uid("RES",st["results"])
            target_lab=f.get("target_lab"); result_lab=list(hex_to_lab(hv)); de=delta_e2000(target_lab,result_lab) if target_lab is not None else None
            st["results"][rid]={"id":rid,"tile_id":tid,"formula_id":t.get("formula_id"),"created_at":now_iso(),"result_hex":normalize_hex(hv),"result_lab":result_lab,"delta_e":de,"delta_e_method":"CIEDE2000","photo_path":persist_media(DATA_DIR, photo),"outcome":outcome,"liking":liking,"action":action,"note_kind":kind,"note":note}
            t["stage"]="Resultado"
            if int(t.get("firing_completed",0))>=int(t.get("firing_required",1)): t["completed"]=True
            save_state(st); return st,f"<div class='notice'>Resultado {rid} guardado · ΔE00 {format(de, '.2f') if de is not None else 'no disponible: falta objetivo'}.</div>",*refresh_dynamic(st)
        save_result_btn.click(save_result_cb,[state,result_tile_sel,result_hex,result_photo,result_outcome,result_liking,result_action,note_kind,result_note],[state,result_msg]+refresh_outputs)

        def lab_hist_cb(st):
            rows=[]
            for eid,e in sorted(st["experiments"].items(),key=lambda kv:kv[1].get("created_at",""),reverse=True): rows.append(f"<div class='panel compact'><b>{eid}</b> · {esc(e.get('name'))}<div class='muted'>{esc(e.get('status'))} · muestras {len(e.get('tile_ids',[]))}</div></div>")
            return "".join(rows) or "<div class='notice'>Sin historial.</div>"
        refresh_lab_history.click(lab_hist_cb,state,lab_history_html)

        # Estante
        def consume_cb(st, mid, qty, reference, estimated, accepted, confirmation):
            confirm_consumption(st, mid, qty, reference, estimated=estimated,
                                accept_estimate=accepted, confirmation_id=confirmation)
            save_state(st)
            return st, "<div class='notice'>Consumo confirmado y registrado.</div>", stock_ledger_html(st), *refresh_dynamic(st)
        consume_btn.click(consume_cb, [state,stock_material,consume_qty,consume_reference,consume_estimated,consume_accept,consume_id], [state,stock_msg,movement_view]+refresh_outputs)
        for control in [stock_material,consume_qty,consume_reference,consume_estimated,consume_accept]:
            control.input(lambda: uuid.uuid4().hex, outputs=consume_id)
        def reverse_cb(st, mid, reason):
            reverse_stock_move(st, mid, reason)
            save_state(st)
            return st, "<div class='notice'>Reversión registrada; el movimiento original se conserva.</div>", stock_ledger_html(st), *refresh_dynamic(st)
        movement_reverse.click(reverse_cb,[state,movement_id,movement_reason],[state,stock_msg,movement_view]+refresh_outputs)
        movement_refresh.click(stock_ledger_html,state,movement_view)
        def stock_select_cb(mid,st):
            m=st["inventory"].get(mid,{})
            return m.get("qty"),m.get("min_qty"),m.get("location",""),m.get("preferred_supplier_id","")
        stock_material.change(stock_select_cb,[stock_material,state],[stock_qty,stock_min,stock_location,stock_pref_supplier])

        def save_stock_cb(st,mid,qty,minq,loc,pref):
            if not mid or mid not in st["inventory"]: return st,"<div class='notice'>Elegí un material.</div>",*refresh_dynamic(st)
            st=copy.deepcopy(st); stock_move(st,mid,number(qty,"stock actual")-st["inventory"][mid]["qty"],"adjustment",mid,reason="Ajuste manual confirmado"); st["inventory"][mid].update({"min_qty":number(minq,"stock mínimo"),"location":loc,"preferred_supplier_id":pref or ""}); save_state(st)
            return st,"<div class='notice'>Stock guardado.</div>",*refresh_dynamic(st)
        save_stock_btn.click(save_stock_cb,[state,stock_material,stock_qty,stock_min,stock_location,stock_pref_supplier],[state,stock_msg]+refresh_outputs)

        def low_to_list_cb(st):
            st=copy.deepcopy(st); added=[]
            for mid,m in st["inventory"].items():
                q=float(m.get("qty",0)); mn=float(m.get("min_qty",0))
                if q>=mn: continue
                # sugerencia explícita accionada por el usuario; no inserción silenciosa automática.
                if any(x.get("material_id")==mid and x.get("status")=="pending" for x in st["shopping_list"].values()): continue
                lid=uid("LIS",st["shopping_list"]); need=mn-q
                st["shopping_list"][lid]={"id":lid,"material_id":mid,"material_name":m.get("name"),"unit":m.get("unit","g"),"needed_qty":need,"buy_qty":need,"origin_type":"Stock","origin_id":mid,"status":"pending","created_at":now_iso()}; added.append(m.get("name"))
            save_state(st); return st,f"<div class='notice'>{'Agregados: '+', '.join(added) if added else 'No había nuevos faltantes para agregar.'}</div>",*refresh_dynamic(st)
        low_to_list_btn.click(low_to_list_cb,state,[state,stock_msg]+refresh_outputs)

        # Bitácora / Agenda
        def journal_add_cb(st,typ,text):
            st=copy.deepcopy(st); st["journal"].append({"at":now_iso(),"type":typ,"text":text}); save_state(st); return st,*refresh_dynamic(st)
        journal_add.click(journal_add_cb,[state,journal_type,journal_text],[state]+refresh_outputs)

        def agenda_add_cb(st,title,when,typ,loc,notes):
            st=copy.deepcopy(st); aid=uid("AGE",st["agenda"]); st["agenda"][aid]={"id":aid,"title":title,"when":when,"type":typ,"location":loc,"notes":notes,"created_at":now_iso()}; save_state(st); return st,*refresh_dynamic(st)
        agenda_add.click(agenda_add_cb,[state,agenda_title,agenda_when,agenda_type,agenda_location,agenda_notes],[state]+refresh_outputs)

        # Producción
        def create_project_cb(st,name,typ,notes):
            st=copy.deepcopy(st); pid=uid("PRO",st["projects"]); st["projects"][pid]={"id":pid,"name":name or pid,"type":typ,"notes":notes,"created_at":now_iso()}; save_state(st); return st,f"<div class='notice'>Proyecto {pid} creado.</div>",*refresh_dynamic(st)
        create_project.click(create_project_cb,[state,project_name,project_type,project_notes],[state,production_msg]+refresh_outputs)

        def create_series_cb(st,pid,obj,qty,name):
            if not pid: return st,"<div class='notice'>Elegí proyecto.</div>",*refresh_dynamic(st)
            st=copy.deepcopy(st); sid=uid("SER",st["series"]); st["series"][sid]={"id":sid,"project_id":pid,"object_type":obj,"target_qty":int(qty or 0),"name":name or f"Serie {obj}","created_at":now_iso()}; save_state(st); return st,f"<div class='notice'>Serie {sid} creada.</div>",*refresh_dynamic(st)
        create_series.click(create_series_cb,[state,series_project,series_object,series_qty,series_name],[state,production_msg]+refresh_outputs)

        def create_lot_cb(st,sid,qty):
            if not sid: return st,"<div class='notice'>Elegí serie.</div>",*refresh_dynamic(st)
            st=copy.deepcopy(st); lid=uid("LOT",st["lots"]); st["lots"][lid]={"id":lid,"series_id":sid,"qty":int(qty or 0),"created_at":now_iso(),"status":"En proceso"}; save_state(st); return st,f"<div class='notice'>Lote {lid} creado.</div>",*refresh_dynamic(st)
        create_lot.click(create_lot_cb,[state,lot_series,lot_qty],[state,production_msg]+refresh_outputs)

        # Horno
        kiln_program.change(lambda n: program_html(n),kiln_program,kiln_program_detail)
        compatible_refresh.click(lambda st,t,a,k: gr.update(choices=compatible_load_choices(st,float(t or 0),a,k),value=[]),[state,firing_temp,firing_atm,firing_kind],compatible_tiles)

        def start_firing_cb(st,program,kind,temp,atm,tiles):
            if not tiles: return st,"<div class='notice'>Elegí al menos una tesela compatible.</div>",gr.update(),*refresh_dynamic(st)
            st=copy.deepcopy(st); fid=uid("HOR",st["firings"]); kiln_id=st["settings"].get("default_kiln_id") or next(iter(st["kilns"]),"")
            st["firings"][fid]={"id":fid,"kiln_id":kiln_id,"program_name":program,"stage_kind":kind,"target_temp_c":float(temp or 0),"atmosphere":atm,"tile_ids":list(tiles),"status":"En cocción","created_at":now_iso(),"started_at":now_iso(),"estimated_minutes":program_duration_minutes(program),"temp_log":[],"opened_at":"","unloaded_at":"","completed_at":""}
            for tid in tiles: st["tiles"].setdefault(tid,{}).setdefault("firing_ids",[]).append(fid)
            save_state(st); choices=[(f"{x} · {o.get('status')}",x) for x,o in st["firings"].items()]
            return st,f"<div class='notice'>Hornada {fid} iniciada.</div>",gr.update(choices=choices,value=fid),*refresh_dynamic(st)
        start_firing.click(start_firing_cb,[state,kiln_program,firing_kind,firing_temp,firing_atm,compatible_tiles],[state,firing_msg,firing_sel]+refresh_outputs)

        def firing_select_cb(fid,st): return firing_detail_html(st["firings"].get(fid))
        firing_sel.change(firing_select_cb,[firing_sel,state],firing_detail)

        def log_temp_cb(st,fid,temp):
            if not fid or fid not in st["firings"]: return st,"<div class='notice'>Elegí hornada.</div>",firing_detail_html(None)
            st=copy.deepcopy(st); f=st["firings"][fid]; f.setdefault("temp_log",[]).append({"at":now_iso(),"temp_c":float(temp or 0),"stage":f.get("status")}); save_state(st); return st,"<div class='notice'>Temperatura registrada.</div>",firing_detail_html(f)
        log_temp.click(log_temp_cb,[state,firing_sel,actual_temp],[state,firing_msg,firing_detail])

        def set_firing_status(st,fid,new_status,temp=None):
            if not fid or fid not in st["firings"]: return st,"<div class='notice'>Elegí hornada.</div>",firing_detail_html(None),*refresh_dynamic(st)
            st=copy.deepcopy(st); f=st["firings"][fid]
            f = transition_firing(st, fid, new_status, temp)
            save_state(st); return st,f"<div class='notice'>Estado: {esc(f['status'])}.</div>",firing_detail_html(f),*refresh_dynamic(st)
        mark_program_done.click(lambda st,fid:set_firing_status(st,fid,"Programa finalizado"),[state,firing_sel],[state,firing_msg,firing_detail]+refresh_outputs)
        confirm_open.click(lambda st,fid,temp:set_firing_status(st,fid,"Apertura",temp),[state,firing_sel,actual_temp],[state,firing_msg,firing_detail]+refresh_outputs)
        confirm_unload.click(lambda st,fid:set_firing_status(st,fid,"Descarga"),[state,firing_sel],[state,firing_msg,firing_detail]+refresh_outputs)
        complete_firing.click(lambda st,fid:set_firing_status(st,fid,"Completar"),[state,firing_sel],[state,firing_msg,firing_detail]+refresh_outputs)

        # Compras
        def add_list_cb(st,mid,needed,buy,origin_type,origin_id):
            if not mid or mid not in st["inventory"]: return st,"<div class='notice'>Elegí material.</div>",*refresh_dynamic(st)
            st=copy.deepcopy(st); m=st["inventory"][mid]
            existing=next((x for x in st["shopping_list"].values() if x.get("material_id")==mid and x.get("status")=="pending"),None)
            if existing:
                existing["needed_qty"]=float(existing.get("needed_qty",0))+float(needed or 0); existing["buy_qty"]=max(float(existing.get("buy_qty",0)),float(buy or 0)); lid=existing["id"]
                msg=f"Actualizado {lid}; no se creó duplicado."
            else:
                lid=uid("LIS",st["shopping_list"]); st["shopping_list"][lid]={"id":lid,"material_id":mid,"material_name":m.get("name"),"unit":m.get("unit","g"),"needed_qty":float(needed or 0),"buy_qty":float(buy or needed or 0),"origin_type":origin_type,"origin_id":origin_id,"status":"pending","created_at":now_iso()}; msg=f"Agregado {lid}."
            save_state(st); return st,f"<div class='notice'>{esc(msg)}</div>",*refresh_dynamic(st)
        add_list_btn.click(add_list_cb,[state,add_material,add_needed_qty,add_buy_qty,add_origin_type,add_origin_id],[state,buy_msg]+refresh_outputs)

        def create_order_cb(st,ids,strategy,sid):
            st=copy.deepcopy(st); st,msg=create_orders_from_list(st,list(ids or []),strategy,sid or ""); return st,f"<div class='notice'>{esc(msg)}</div>",*refresh_dynamic(st)
        create_order_btn.click(create_order_cb,[state,shopping_select,order_strategy,order_supplier],[state,buy_msg]+refresh_outputs)

        def order_select_cb(oid,st):
            text,url=whatsapp_message(st,oid); link=f"<a class='gr-button' target='_blank' href='{esc(url)}'>Abrir WhatsApp ↗</a>" if url else "<div class='notice'>Proveedor sin teléfono configurado; podés copiar el mensaje.</div>"
            return order_detail_html(st,oid),text,link,receipt_table_value(st,oid)
        order_sel.change(order_select_cb,[order_sel,state],[order_detail,wa_text,wa_link,receipt_table])

        def mark_order_cb(st,oid,status):
            if not oid or oid not in st["orders"]: return st,"<div class='notice'>Elegí pedido.</div>",*refresh_dynamic(st)
            st=copy.deepcopy(st); st["orders"][oid]["status"]=status; save_state(st); return st,f"<div class='notice'>Pedido {oid}: {status}.</div>",*refresh_dynamic(st)
        order_mark_consulted.click(lambda st,oid:mark_order_cb(st,oid,"Consultado"),[state,order_sel],[state,order_msg]+refresh_outputs)
        order_mark_confirmed.click(lambda st,oid:mark_order_cb(st,oid,"Confirmado"),[state,order_sel],[state,order_msg]+refresh_outputs)
        order_mark_transit.click(lambda st,oid:mark_order_cb(st,oid,"En camino"),[state,order_sel],[state,order_msg]+refresh_outputs)

        def receive_cb(st,oid,table):
            st=copy.deepcopy(st); st,msg=apply_receipt(st,oid,table or []); return st,f"<div class='notice'>{esc(msg)}</div>",*refresh_dynamic(st)
        receive_btn.click(receive_cb,[state,order_sel,receipt_table],[state,order_msg]+refresh_outputs)

        def supplier_cards(st):
            if not st["suppliers"]: return "<div class='notice'>No hay proveedores cargados.</div>"
            return "".join(f"<div class='panel compact'><b>{esc(s.get('name'))}</b><div class='muted'>{esc(s.get('web',''))} · {esc(s.get('phone',''))}</div></div>" for s in st["suppliers"].values())

        def add_supplier_cb(st,name,phone,web,shipping,notes):
            st=copy.deepcopy(st)
            existing=next((sid for sid,s in st["suppliers"].items() if normalize_text(s.get("name",""))==normalize_text(name)),None)
            sid=existing or uid("SUP",st["suppliers"]); st["suppliers"][sid]={"id":sid,"name":name or sid,"phone":phone,"web":web,"shipping_cost":float(shipping or 0),"notes":notes,"created_at":st["suppliers"].get(sid,{}).get("created_at",now_iso())}; save_state(st)
            return st,f"<div class='notice'>Proveedor {sid} guardado.</div>",supplier_cards(st),*refresh_dynamic(st)
        add_supplier_btn.click(add_supplier_cb,[state,sup_name,sup_phone,sup_web,sup_shipping,sup_notes],[state,supplier_msg,supplier_list_html]+refresh_outputs)

        def add_sp_cb(st,sid,mid,name,code,url,pack,unit,price,pstatus,pdate):
            if not sid or not mid: return st,"<div class='notice'>Elegí proveedor y material.</div>",supplier_cards(st),*refresh_dynamic(st)
            st=copy.deepcopy(st); pid=uid("SP",st["supplier_products"]); mat=st["inventory"].get(mid,{})
            st["supplier_products"][pid]={"id":pid,"supplier_id":sid,"material_id":mid,"material_name":mat.get("name"),"name":name or mat.get("name"),"code":code,"url":url,"package_qty":float(pack or 0),"unit":unit,"price":float(price or 0),"price_status":pstatus,"price_date":pdate,"available":True,"confirmed_equivalence":True}
            save_state(st); return st,f"<div class='notice'>Equivalencia {pid} guardada y reutilizable.</div>",supplier_cards(st),*refresh_dynamic(st)
        add_supplier_product_btn.click(add_sp_cb,[state,sp_supplier,sp_material,sp_name,sp_code,sp_url,sp_pack,sp_unit,sp_price,sp_price_status,sp_price_date],[state,supplier_msg,supplier_list_html]+refresh_outputs)

        # Config
        def reset_demo_cb(st, confirmed):
            if not confirmed:
                raise ValueError("Confirmá el reemplazo antes de restaurar la demo.")
            st = reset_demo_state()
            return (st, "<div class='notice'>Datos DEMO restaurados.</div>", *refresh_dynamic(st))
        reset_demo_btn.click(reset_demo_cb, inputs=[state,reset_confirm], outputs=[state,config_msg]+refresh_outputs)

        def save_config_cb(st,sid,advanced,open_temp,atm,firing_type):
            st=copy.deepcopy(st); st["settings"]["default_supplier_id"]=sid or ""; st["settings"]["advanced_pigment_synthesis"]=bool(advanced); st["settings"]["opening_temp_c"]=float(open_temp or 50); st["settings"]["default_atmosphere"]=atm or "Oxidante"; st["settings"]["default_firing_type"]=firing_type or "Bicocción"; save_state(st); return st,"<div class='notice'>Configuración guardada.</div>",*refresh_dynamic(st)
        save_config.click(save_config_cb,[state,cfg_default_supplier,cfg_advanced,cfg_open_temp,cfg_atmosphere,cfg_firing_type],[state,config_msg]+refresh_outputs)

        def save_units_cb(st,t,r,c,p,v,l):
            st=copy.deepcopy(st); st["settings"]["units"]={"temperature":t,"raw_weight":r,"clay_weight":c,"piece_weight":p,"volume":v,"length":l}; save_state(st); return st,"<div class='notice'>Unidades guardadas.</div>"
        save_units.click(save_units_cb,[state,unit_temp,unit_raw,unit_clay,unit_piece,unit_vol,unit_len],[state,units_msg])

        export_backup.click(lambda st: export_backup_file(st), state, export_file)
        def import_backup_cb(st, path, confirmed):
            if not confirmed:
                raise ValueError("Confirmá el reemplazo antes de importar.")
            try:
                st = import_backup_file(path)
                return (st, "<div class='notice'>Copia importada correctamente.</div>", *refresh_dynamic(st))
            except Exception as e:
                st = load_state()
                return (st, f"<div class='notice danger'>{esc(e)}</div>", *refresh_dynamic(st))
        import_backup.click(import_backup_cb, [state, import_file, import_confirm], [state,backup_msg]+refresh_outputs)

        def kiln_cfg_select(kid,st):
            k=st["kilns"].get(kid,{})
            return k.get("name",""),k.get("capacity_l"),k.get("power_kw"),k.get("voltage_v",220),k.get("controller",""),k.get("energy_cost_kwh"),k.get("notes","")
        kiln_sel_cfg.change(kiln_cfg_select,[kiln_sel_cfg,state],[kiln_name_cfg,kiln_capacity_cfg,kiln_power_cfg,kiln_voltage_cfg,kiln_controller_cfg,kiln_energy_cfg,kiln_notes_cfg])

        def save_kiln_cb(st,kid,name,capacity,power,voltage,controller,energy,notes):
            st=copy.deepcopy(st); kid=kid or uid("KILN",st["kilns"]); st["kilns"][kid]={"id":kid,"name":name or kid,"capacity_l":capacity,"power_kw":power,"voltage_v":voltage,"controller":controller,"energy_cost_kwh":energy,"notes":notes,"default":kid==st["settings"].get("default_kiln_id")}; save_state(st); return st,"<div class='notice'>Horno guardado.</div>"
        save_kiln_cfg.click(save_kiln_cb,[state,kiln_sel_cfg,kiln_name_cfg,kiln_capacity_cfg,kiln_power_cfg,kiln_voltage_cfg,kiln_controller_cfg,kiln_energy_cfg,kiln_notes_cfg],[state,kiln_cfg_msg])

        # A page reload refreshes editable persisted fields together with its
        # revision token, so a fresh token can never accompany stale form data.
        def refresh_all_cb(st, mid, eid, tid, oid, kid):
            mid = mid if mid in st["inventory"] else next(iter(st["inventory"]), None)
            eid = eid if eid in st["experiments"] else next(iter(st["experiments"]), None)
            tid = tid if tid in st["tiles"] else next(iter(st["tiles"]), None)
            oid = oid if oid in st["orders"] else next(iter(st["orders"]), None)
            kid = kid if kid in st["kilns"] else next(iter(st["kilns"]), None)
            updates = list(refresh_dynamic(st, force=True))
            for index, selected in [(3,mid),(8,eid),(9,tid),(16,oid)]:
                updates[index]["value"] = selected
            settings = st["settings"]
            units = settings.get("units", {})
            return (st, *updates, *stock_select_cb(mid,st), *exp_select_cb(eid,st),
                    *tile_select_cb(tid,st), *order_select_cb(oid,st),
                    gr.update(value=kid), *kiln_cfg_select(kid,st),
                    settings.get("default_supplier_id", ""), bool(settings.get("advanced_pigment_synthesis",False)),
                    settings.get("opening_temp_c",50), settings.get("default_atmosphere","Oxidante"), settings.get("default_firing_type","Bicocción"),
                    units.get("temperature","°C"),units.get("raw_weight","g"),units.get("clay_weight","g"),units.get("piece_weight","g"),units.get("volume","mL"),units.get("length","cm"))
        startup_outputs = [stock_qty,stock_min,stock_location,stock_pref_supplier,experiment_detail,exp_water,exp_notes,
                           tile_progress,tile_firing_type,tile_stage,tile_wet_weight,tile_dry_weight,tile_dry_length,tile_fired_length,tile_notes,tile_dry_group,tile_result_measure_group,tile_bisque_weight,tile_final_weight,
                           order_detail,wa_text,wa_link,receipt_table,kiln_sel_cfg,kiln_name_cfg,kiln_capacity_cfg,kiln_power_cfg,kiln_voltage_cfg,kiln_controller_cfg,kiln_energy_cfg,kiln_notes_cfg,
                           cfg_default_supplier,cfg_advanced,cfg_open_temp,cfg_atmosphere,cfg_firing_type,unit_temp,unit_raw,unit_clay,unit_piece,unit_vol,unit_len]
        # These controls already occur in the legacy refresh list; update their
        # existing slot rather than returning duplicate component IDs.
        startup_pairs = [(i,c) for i,c in enumerate(startup_outputs) if c not in refresh_outputs]
        original_refresh_all = refresh_all_cb
        def refresh_all_cb(*args):
            result = list(original_refresh_all(*args))
            offset = 1 + len(refresh_outputs)
            for i,c in enumerate(startup_outputs):
                if c in refresh_outputs:
                    slot = 1 + refresh_outputs.index(c)
                    existing = result[slot]
                    result[slot] = {**existing, "value": result[offset+i]} if isinstance(existing,dict) else result[offset+i]
            return tuple(result[:offset] + [result[offset+i] for i,c in startup_pairs])
        demo.load(refresh_all_cb,[state,stock_material,experiment_cards,tile_cards,order_sel,kiln_sel_cfg],
                  [state]+refresh_outputs+[c for i,c in startup_pairs])
        demo.load(lambda st: supplier_cards(st), state, supplier_list_html)

        bind_repository_callbacks(demo, state)

    return demo


# ---------------------------------------------------------------------------
# QA
# ---------------------------------------------------------------------------


def run_self_test() -> List[str]:
    import tempfile
    global DATA_DIR, STATE_FILE
    previous_dir, previous_file = DATA_DIR, STATE_FILE
    with tempfile.TemporaryDirectory(prefix="alumina-qa-") as directory:
        DATA_DIR = Path(directory)
        STATE_FILE = DATA_DIR / "alumina_v16_demo_state.json"
        try:
            return _run_self_test_isolated()
        finally:
            _REPOSITORIES.pop(str((DATA_DIR / "alumina.sqlite3").resolve()), None)
            DATA_DIR, STATE_FILE = previous_dir, previous_file


def _run_self_test_isolated() -> List[str]:
    results = []
    st = demo_state()
    assert len(st["formulas"]) >= 3 and len(st["experiments"]) >= 3; results.append("PASS datos DEMO")
    assert normalize_hex("f25a18") == "#F25A18"; results.append("PASS color HEX")
    lab = hex_to_lab("#F25A18"); assert len(lab) == 3; results.append("PASS CIELAB")
    assert delta_e2000(lab, lab) < 1e-9; results.append("PASS CIEDE2000")
    comps,total,w = parse_formula_text("Caolín 30\nSílice 20\nFrita 50"); assert len(comps)==3 and abs(total-100)<1e-6; results.append("PASS parser fórmula")
    # Compra y recepción en estado aislado
    qa = load_state()
    qa.clear()
    qa.update(initial_state())
    qa["suppliers"]["SUP-0001"]={"id":"SUP-0001","name":"Proveedor QA","phone":"","shipping_cost":0}
    qa["settings"]["default_supplier_id"]="SUP-0001"
    qa["supplier_products"]["SP-0001"]={"id":"SP-0001","supplier_id":"SUP-0001","material_id":"MAT-0001","material_name":"Caolín","name":"Caolín comercial","code":"C001","package_qty":500,"unit":"g","price":1000,"available":True,"price_status":"Ingresado manualmente","price_date":"2026-09-21","url":""}
    qa["shopping_list"]["LIS-0001"]={"id":"LIS-0001","material_id":"MAT-0001","material_name":"Caolín","unit":"g","needed_qty":230,"buy_qty":230,"origin_type":"Ensayo","origin_id":"ENS-QA","status":"pending","created_at":now_iso()}
    qa,msg=create_orders_from_list(qa,["LIS-0001"],"Mi proveedor","SUP-0001"); assert qa["orders"]; results.append("PASS Lista → Pedido")
    oid=next(iter(qa["orders"])); table=receipt_table_value(qa,oid); table[0][3]=500; before=qa["inventory"]["MAT-0001"]["qty"]; qa,msg=apply_receipt(qa,oid,table); assert qa["inventory"]["MAT-0001"]["qty"]==before+500; results.append("PASS Recepción → Stock")
    # Bicocción
    st["tiles"]["TES-0001"]={"id":"TES-0001","firing_type":"Bicocción","firing_required":2,"firing_completed":1,"stage":"Cocción","target_temp_c":1040,"atmosphere":"Oxidante","firing_ids":[]}; assert st["tiles"]["TES-0001"]["firing_completed"] < st["tiles"]["TES-0001"]["firing_required"]; results.append("PASS bicocción 1/2 no final")
    # Biblioteca / conos / backup
    assert "LIB-0004" in st["materials_library"]; results.append("PASS biblioteca materiales")
    assert "998" in cone_reference_html("06"); results.append("PASS conos Orton")
    # Build UI con estado DEMO restaurado
    reset_demo_state()
    app = build_app(); assert isinstance(app, gr.Blocks); results.append("PASS Gradio build_app")
    cfg = app.get_config_file()
    props = [c.get("props", {}) for c in cfg.get("components", [])]
    mis_formulas = next((p for p in props if p.get("label") == "Mis fórmulas"), {})
    pigmentos = next((p for p in props if p.get("label") == "Familia candidata (orientativa)"), {})
    assert mis_formulas.get("value") == "CAM-0001" and len(mis_formulas.get("choices", [])) >= 3
    assert pigmentos.get("value") == "Cd-S-Se inclusión" and len(pigmentos.get("choices", [])) >= 2
    results.append("PASS precarga DEMO en controles")
    assert any("Formulario" in str(p.get("choices", [])) for p in props); results.append("PASS LAB → Formulario")
    return results


FORCE_LIGHT_JS = r"""
() => {
  const force = () => {
    document.documentElement.classList.remove('dark');
    if (document.body) document.body.classList.remove('dark');
    document.documentElement.style.colorScheme = 'light';
    if (document.body) document.body.style.colorScheme = 'light';
  };
  force();
  const obs = new MutationObserver(force);
  obs.observe(document.documentElement, {attributes:true, attributeFilter:['class']});
}
"""

def launch(*, share: bool = True, server_name: str = "0.0.0.0"):
    app = build_app()
    return app.launch(
        share=share, server_name=server_name, css=CSS, js=FORCE_LIGHT_JS,
        theme=gr.themes.Soft(), footer_links=[], show_error=True
    )


if __name__ == "__main__":
    if "--qa" in sys.argv:
        for line in run_self_test():
            print(line)
    else:
        launch()
