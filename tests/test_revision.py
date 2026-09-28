"""Regressions reproduced during the live 17.3 review."""
import pytest
from PIL import Image
from alumina import studio
from alumina.workbench import periodic_html

@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(studio,'DATA_DIR',tmp_path)
    monkeypatch.setattr(studio,'STATE_FILE',tmp_path/'legacy.json')
    return studio.build_app()

def callback(app,name):
    return next(f for f in app.fns.values() if f.fn.__name__==name)

def test_invalid_calculator_clears_previous_value(app):
    button=next(b for b in app.blocks.values() if getattr(b,'value',None)=='Calcular contracción')
    fn=next(f for f in app.fns.values() if (button._id,'click') in f.targets)
    assert fn.fn(100,90)==(10,'')
    value,message=fn.fn(0,90)
    assert value is None and message and 'danger' in message
    assert fn.fn(100,80)==(20,'')

def test_search_opens_correct_material(app):
    fn=callback(app,'open_search')
    output=fn.fn(studio.session_token(studio.load_state()),'inventory:MAT-0004')
    values={getattr(c,'label',None):v for c,v in zip(fn.outputs,output)}
    assert len(output)==len(fn.outputs)
    assert values['Stock actual']==180
    assert values['Material']['value']=='MAT-0004'

def test_compatibility_explains_optical_mismatch(app):
    st=studio.load_state()
    html=studio.formula_match_results(st,'#F25A18',1040,'Oxidante','Loza blanca','Esmalte',optics='Transparente')
    assert 'buscado Transparente; fórmula Opaca' in html
    assert 'compatibilidad técnica 100' not in html

def test_result_rejects_unfired_sample_without_writing(app):
    before=studio.load_state()
    with pytest.raises(Exception,match='no completó'):
        callback(app,'save_result_cb').fn(studio.session_token(before),'TES-0002','#ffffff',None,'Funcionó','Me gusta','Conservar','Comentario','')
    after=studio.load_state()
    assert before['results']==after['results']
    assert before['tiles']==after['tiles']

def test_real_temperature_blank_and_missing_rejected(app):
    field=next(b for b in app.blocks.values() if getattr(b,'label',None)=='Temperatura REAL del controlador °C')
    assert field.value is None
    before=studio.load_state()
    with pytest.raises(Exception,match='Falta'):
        callback(app,'log_temp_cb').fn(studio.session_token(before),'HOR-0002',None)
    assert studio.load_state()['firings']==before['firings']

def test_journal_photo_survives_temporary_source(app,tmp_path):
    source=tmp_path/'photo.png'; Image.new('RGB',(10,10),'blue').save(source)
    callback(app,'journal_add_cb').fn(studio.session_token(studio.load_state()),'Foto','Proceso',str(source))
    source.unlink()
    assert 'data:image/' in studio.journal_html(studio.load_state())

def test_empty_analysis_not_zero_and_periodic_exact_first(app):
    html=studio.material_detail_html(studio.load_state(),'LIB-0010')
    assert 'Sin datos' in html and '0.00%' not in html
    html=periodic_html('Co')
    assert html.index('Cobalto') < html.index('Cobre')


def test_demo_palette_is_unique_and_selectable(app):
    palette = studio.load_state()['color_palette']
    assert len(palette) == 256
    assert len({c['hex'] for c in palette.values()}) == 256
    assert {'#000000', '#FFFFFF'} <= {c['hex'] for c in palette.values()}
    for color in palette.values():
        assert color['lab'] == list(studio.hex_to_lab(color['hex']))
    assert callback(app, 'choose_palette_color').fn('DEMO-COLOR-256') == ('#FFFFFF', 'Digital · Selector')


def test_palette_upgrade_preserves_existing_data_and_is_idempotent(app):
    st = studio.load_state()
    with studio.repository().transaction(st.revisions) as tx:
        del tx['state']['color_palette']
    studio.ensure_demo_palette()
    st = studio.load_state()
    st['color_palette']['DEMO-COLOR-001']['name'] = 'Mi referencia'
    studio.save_state(st)
    before = studio.load_state()
    studio.ensure_demo_palette()
    after = studio.load_state()
    assert before == after
    assert before.revisions == after.revisions
    assert len(after['color_palette']) == 256


def test_non_demo_does_not_receive_demo_palette(app):
    st = studio.load_state()
    st['settings']['demo_mode'] = False
    del st['color_palette']
    studio.save_state(st)
    studio.ensure_demo_palette()
    assert not studio.load_state().get('color_palette')
