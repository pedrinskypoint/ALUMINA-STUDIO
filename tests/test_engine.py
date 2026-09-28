import copy
import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from PIL import Image

from alumina import studio
from alumina.media import persist_media, thumbnail_uri, media_path
from alumina.operations import (
    stock_move, reverse_stock_move, confirm_consumption, normalized_components,
    formula_version, mass_variations, transition_firing, cooling_history,
)
from alumina.storage import Repository, ConflictError


@pytest.fixture
def data(tmp_path, monkeypatch):
    monkeypatch.setattr(studio, "DATA_DIR", tmp_path)
    monkeypatch.setattr(studio, "STATE_FILE", tmp_path / "legacy.json")
    return tmp_path


def test_entity_merge_and_conflict(data):
    a = studio.load_state()
    b = studio.load_state()
    a["inventory"]["MAT-0001"]["location"] = "A"
    studio.save_state(a)
    b["inventory"]["MAT-0002"]["location"] = "B"
    studio.save_state(b)
    assert studio.load_state()["inventory"]["MAT-0001"]["location"] == "A"
    a["inventory"]["MAT-0002"]["location"] = "Stale"
    with pytest.raises(ConflictError):
        studio.save_state(a)
    assert studio.load_state()["inventory"]["MAT-0002"]["location"] == "B"


def test_parallel_commands_no_lost_records(data):
    studio.load_state()
    def create(i):
        repo = Repository(data / "alumina.sqlite3")
        state = repo.load(studio.demo_state)
        with repo.transaction(state.revisions) as tx:
            tx["state"]["agenda"][f"A-{i}"] = {"id": f"A-{i}", "title": str(i)}
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(create, range(12)))
    assert all(f"A-{i}" in studio.load_state()["agenda"] for i in range(12))


def test_failed_command_rolls_back(data):
    state = studio.load_state()
    with pytest.raises(ValueError):
        with studio.repository().transaction(state.revisions) as tx:
            tx["state"]["agenda"].clear()
            raise ValueError("fail")
    assert studio.load_state()["agenda"] == state["agenda"]


def test_json_migration_preserves_original_and_restarts(data):
    original = studio.demo_state()
    studio.STATE_FILE.write_text(json.dumps(original))
    before = studio.STATE_FILE.read_bytes()
    loaded = studio.load_state()
    assert loaded["formulas"] == original["formulas"]
    loaded["settings"]["default_atmosphere"] = "Reductora"
    studio.save_state(loaded)
    assert Repository(data / "alumina.sqlite3").load(lambda: {}).get("settings")["default_atmosphere"] == "Reductora"
    assert studio.STATE_FILE.read_bytes() == before


def test_corrupt_json_never_seeds_demo(data):
    studio.STATE_FILE.write_text("broken json")
    with pytest.raises(json.JSONDecodeError):
        studio.load_state()
    assert studio.STATE_FILE.read_text() == "broken json"


def test_image_survives_gradio_cache_removal_and_zip(data, tmp_path):
    source = tmp_path / "temporary.png"
    Image.new("RGB", (30, 30), "red").save(source)
    ref = persist_media(data, source)
    source.unlink()
    assert thumbnail_uri(data, ref).startswith("data:image/jpeg;base64,")
    state = studio.load_state()
    state["results"]["RES-0001"]["photo_path"] = ref
    studio.save_state(state)
    backup = studio.export_backup_file(state)
    # Roundtrip into a separate workshop and verify that links resolve there.
    studio.DATA_DIR = data / "restored"
    studio.STATE_FILE = studio.DATA_DIR / "legacy.json"
    restored = studio.import_backup_file(backup)
    new_ref = restored["results"]["RES-0001"]["photo_path"]
    assert media_path(studio.DATA_DIR, new_ref).is_file()
    assert thumbnail_uri(studio.DATA_DIR, new_ref)


def receipt_fixture():
    state = studio.load_state()
    state.clear()
    state.update(studio.initial_state())
    state["suppliers"]["S"] = {"id":"S", "name":"QA", "shipping_cost":0}
    state["supplier_products"]["P"] = {"id":"P", "supplier_id":"S", "material_id":"MAT-0001", "material_name":"Caolín", "name":"Caolín", "package_qty":500, "unit":"g", "price":1000, "available":True}
    state["shopping_list"]["L"] = {"id":"L", "material_id":"MAT-0001", "material_name":"Caolín", "unit":"g", "needed_qty":500, "buy_qty":500, "status":"pending"}
    state, _ = studio.create_orders_from_list(state, ["L"], "Mi proveedor", "S")
    oid = next(iter(state["orders"]))
    return state, oid, studio.receipt_table_value(state, oid)


def test_receipt_correction_and_idempotency(data):
    state, oid, table = receipt_fixture()
    before = state["inventory"]["MAT-0001"]["qty"]
    table[0][3] = 500
    state, _ = studio.apply_receipt(state, oid, table)
    count = len(state["stock_movements"])
    state, _ = studio.apply_receipt(state, oid, table)
    assert len(state["stock_movements"]) == count
    table[0][3] = 300
    state, _ = studio.apply_receipt(state, oid, table)
    assert state["inventory"]["MAT-0001"]["qty"] == before + 300
    assert state["stock_movements"][-1]["delta"] == -200
    table[0][3] = -1
    with pytest.raises(ValueError):
        studio.apply_receipt(state, oid, table)
    assert studio.load_state()["inventory"]["MAT-0001"]["qty"] == before + 300


def test_stock_reversal_and_estimation(data):
    state = studio.load_state()
    before = state["inventory"]["MAT-0001"]["qty"]
    movement = stock_move(state, "MAT-0001", -5, "consumption", "ENS-0001", reason="Pesado")
    reverse_stock_move(state, movement["id"], "Corrección")
    assert state["inventory"]["MAT-0001"]["qty"] == before
    with pytest.raises(ValueError):
        reverse_stock_move(state, movement["id"], "Again")
    with pytest.raises(ValueError):
        confirm_consumption(state, "MAT-0001", 10, "ENS-0001", estimated=True, confirmation_id="A")
    confirm_consumption(state, "MAT-0001", 10, "ENS-0001", estimated=True, accept_estimate=True, confirmation_id="A")
    with pytest.raises(ValueError):
        confirm_consumption(state, "MAT-0001", 10, "ENS-0001", confirmation_id="A")


def test_formula_normalization_and_version_leave_original(data):
    state = studio.load_state()
    source_id = "MAN-0001"
    before = copy.deepcopy(state["formulas"][source_id])
    normalized = normalized_components(before["components"])
    assert sum(x["amount"] for x in normalized) == pytest.approx(100)
    fid = formula_version(state, source_id, normalized, "Normalización")
    assert state["formulas"][source_id] == before
    assert state["formulas"][fid]["derived_from"] == source_id


def test_mass_is_measured_loss_not_rheology():
    changes = mass_variations({"wet_weight":100,"dry_weight":80,"bisque_weight":72,"final_weight":70})
    assert changes[0]["loss_percent"] == 20
    assert changes[1]["loss_percent"] == 10
    assert mass_variations({"wet_weight":0,"dry_weight":0})[0]["loss_percent"] is None


def test_firing_requires_fresh_reading_and_completes_once(data):
    state = studio.load_state()
    f = state["firings"]["HOR-0002"]
    f["status"] = "En cocción"
    tid = f["tile_ids"][0]
    state["tiles"][tid]["firing_required"] = 2
    state["tiles"][tid]["firing_completed"] = 0
    with pytest.raises(ValueError):
        transition_firing(state, "HOR-0002", "Apertura", 20)
    transition_firing(state, "HOR-0002", "Programa finalizado")
    with pytest.raises(ValueError):
        transition_firing(state, "HOR-0002", "Apertura")
    with pytest.raises(ValueError):
        transition_firing(state, "HOR-0002", "Apertura", 200)
    transition_firing(state, "HOR-0002", "Apertura", 40)
    transition_firing(state, "HOR-0002", "Descarga")
    transition_firing(state, "HOR-0002", "Completar")
    with pytest.raises(ValueError):
        transition_firing(state, "HOR-0002", "Completar")
    assert state["tiles"][tid]["firing_completed"] == 1
    assert cooling_history(state, f) is None


def callback(app, name):
    return next(f for f in app.fns.values() if f.fn.__name__ == name)


def test_gradio_only_stores_ui_token_and_rejects_stale_write(data):
    app = studio.build_app()
    fn = callback(app, "save_stock_cb")
    token = studio.session_token(studio.load_state())
    first = fn.fn(token,"MAT-0001",900,50,"A","")
    assert set(first[0]) == {"revisions"}
    with pytest.raises(Exception, match="Otro usuario"):
        fn.fn(token,"MAT-0001",700,50,"B","")
    assert studio.load_state()["inventory"]["MAT-0001"]["qty"] == 900


def test_result_without_target_and_persistent_photo(data):
    state = studio.load_state()
    tid = "TES-0003"
    state["formulas"][state["tiles"][tid]["formula_id"]]["target_lab"] = None
    studio.save_state(state)
    app = studio.build_app()
    fn = callback(app, "save_result_cb")
    fn.fn(studio.session_token(studio.load_state()),tid,"#ffffff",None,"Funcionó","Me gusta","Conservar","Comentario","")
    results = studio.load_state()["results"]
    assert any(r.get("delta_e") is None for r in results.values())


def test_unrelated_update_skips_formula_and_result_rendering(data):
    app = studio.build_app()
    fn = callback(app,"journal_add_cb")
    values = fn.fn(studio.session_token(studio.load_state()),"Nota","test")
    for component, value in zip(fn.outputs, values):
        if getattr(component,"label",None) == "Mis fórmulas":
            assert value == {"__type__":"update"}
    assert studio.load_state()["journal"][-1]["text"] == "test"


def test_unseen_changes_do_not_gain_a_fresh_session_token(data):
    app = studio.build_app()
    old_token = studio.session_token(studio.load_state())
    stock = callback(app, "save_stock_cb")
    stock.fn(old_token,"MAT-0001",850,50,"A","")
    note = callback(app,"journal_add_cb").fn(old_token,"Nota","Una nota independiente")
    with pytest.raises(Exception, match="Otro usuario"):
        stock.fn(note[0],"MAT-0001",600,50,"B","")


def test_reload_returns_current_values_with_current_token(data):
    app = studio.build_app()
    old = studio.session_token(studio.load_state())
    state = studio.load_state()
    state["inventory"]["MAT-0001"]["qty"] = 777
    studio.save_state(state)
    fn = callback(app,"refresh_all_cb")
    values = fn.fn(old,"MAT-0001","ENS-0001","TES-0001","PED-0001","KILN-0001")
    assert len(values) == len(fn.outputs)
    assert len({b._id for b in fn.outputs}) == len(fn.outputs)
    quantity = next(v for b,v in zip(fn.outputs,values) if getattr(b,"label",None) == "Stock actual")
    assert quantity == 777
    assert values[0] == studio.session_token(studio.load_state())


def test_tile_photo_and_weight_callback(data):
    image = data / "cache.png"
    Image.new("RGB",(20,20),"blue").save(image)
    app = studio.build_app()
    fn = callback(app,"save_tile_cb")
    values = fn.fn(studio.session_token(studio.load_state()),"TES-0001","Bicocción","Secado",100,80,100,None,"test",None,None,str(image))
    assert len(values) == len(fn.outputs)
    image.unlink()
    saved = studio.load_state()["tiles"]["TES-0001"]
    assert saved["mass_variations"][0]["loss_percent"] == 20
    assert thumbnail_uri(data,saved["process_photos"][0]["photo_path"])


def test_ciede2000_reference_pair():
    assert studio.delta_e2000((50,2.6772,-79.7751),(50,0,-82.7485)) == pytest.approx(2.0425, abs=0.0001)
