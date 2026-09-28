"""Test the real Gradio routes and their ancestor visibility."""
import os
os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"
import pytest
from alumina import studio

@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(studio, "DATA_DIR", tmp_path)
    monkeypatch.setattr(studio, "STATE_FILE", tmp_path / "state.json")
    return studio.build_app()

@pytest.mark.parametrize("button,section", [
    ("Fórmula", "## Color Sampler"), ("Ensayo", "## Ensayo"),
    ("Resultado", "## Resultado"), ("Estante", "## Estante"),
    ("Comprar", "## Compras"), ("Horno", "## Horno"),
    ("Pieza", "## Registro · piezas y lotes"), ("Costos", "## Estadísticas · costos"),
])
def test_route(app, button, section):
    btn = next(b for b in app.blocks.values() if b.__class__.__name__ == "Button" and b.value == button)
    fn = next(f for f in app.fns.values() if (btn._id, "click") in f.targets)
    values = fn.fn()
    assert len(values) == len(fn.outputs)
    updates = {b._id: v for b, v in zip(fn.outputs, values)}
    target = next(b for b in app.blocks.values() if b.__class__.__name__ == "Markdown" and b.value == section)
    def ancestors(node, path=()):
        if node["id"] == target._id:
            return path
        for child in node.get("children", []):
            found = ancestors(child, path + (node["id"],))
            if found is not None:
                return found
        return None
    path = ancestors(app.get_config_file()["layout"])
    assert path is not None
    for bid in path:
        visible = updates.get(bid, {}).get("visible", getattr(app.blocks.get(bid), "visible", True))
        assert visible, (button, bid)

def test_structure(app):
    choices = [[pair[1] for pair in b.choices] for b in app.blocks.values() if b.__class__.__name__ == "Radio"]
    assert ["Inicio", "LAB", "TALLER", "SABER"] in choices
    assert ["Color Sampler", "Ensayo", "Formulario"] in choices
    assert ["Bitácora", "Estante", "Operaciones"] in choices
    assert ["Portada", "Aprender", "Profe AI", "Comunidad"] in choices
    saved = studio.load_state()
    assert saved["schema_version"] == 2
    assert saved["formulas"] and saved["orders"] and saved["tiles"]

def test_self_checks(tmp_path, monkeypatch):
    monkeypatch.setattr(studio, "DATA_DIR", tmp_path)
    monkeypatch.setattr(studio, "STATE_FILE", tmp_path / "state.json")
    assert len(studio.run_self_test()) == 13
