import json
import os
from pathlib import Path
import shutil
import subprocess
import pytest
from alumina import studio, workbench as wb

@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(studio, 'DATA_DIR', tmp_path)
    monkeypatch.setattr(studio, 'STATE_FILE', tmp_path/'state.json')
    return studio.build_app()

def test_theme_observer_settles_after_external_dark_class():
    node = os.getenv('ALUMINA_NODE') or shutil.which('node')
    if not node:
        pytest.skip('Node.js required for theme script regression')
    # DOMTokenList mutations notify even when remove() finds no token.
    script = r'''
const fs = require('node:fs');
const source=JSON.parse(fs.readFileSync(0,'utf8'));
let callback, pending=0, iterations=0;
function element(){
  const tokens=new Set(['dark']);
  return {style:{},classList:{contains:x=>tokens.has(x),remove:x=>{tokens.delete(x);if(callback)pending++},add:x=>{tokens.add(x);if(callback)pending++}}};
}
global.document={documentElement:element(),body:element()};
global.MutationObserver=class{constructor(fn){this.fn=fn}observe(){callback=this.fn}};
eval('('+source+')')();
document.documentElement.classList.add('dark');
while(pending){pending--;callback();if(++iterations>50)throw Error('theme mutation loop');}
if(document.documentElement.classList.contains('dark'))throw Error('still dark');
console.log('settled',iterations);
'''
    result=subprocess.run([node,'-e',script],input=json.dumps(studio.FORCE_LIGHT_JS),text=True,capture_output=True,timeout=5)
    assert result.returncode == 0, result.stderr
    assert 'settled 2' in result.stdout


def test_parameter_navigation_does_not_cascade_to_blank_page(app):
    button=next(b for b in app.blocks.values() if getattr(b,'value',None)=='Parámetros')
    fn=next(f for f in app.fns.values() if (button._id,'click') in f.targets)
    result=fn.fn()
    # Simulate programmatic output changes. They must not fire main navigation.
    nav=fn.outputs[0]
    assert result[0]['value'] is None
    assert not any((nav._id,'change') in f.targets for f in app.fns.values())
    vis=[v['visible'] for v in result if isinstance(v,dict) and 'visible' in v]
    assert vis == [False,False,False,False,True,False,False]
    assert fn.queue is False


def test_user_navigation_leaves_only_selected_module_and_closes_tools(app):
    nav=next(b for b in app.blocks.values() if getattr(b,'elem_id',None)=='main-nav')
    fn=next(f for f in app.fns.values() if (nav._id,'input') in f.targets)
    for index,name in [(2,'TALLER'),(1,'LAB'),(3,'SABER'),(0,'Inicio'),(1,'LAB')]:
        values=fn.fn(name)
        assert [v['visible'] for v in values[:5]] == [i==index for i in range(5)]
        assert values[-2] is False and values[-1]['visible'] is False
    assert fn.queue is False


def test_subnavigation_is_user_input_only_and_not_queued(app):
    for b in app.blocks.values():
        if b.__class__.__name__=='Radio' and getattr(b,'choices',[]) and b.choices[0][1] in ['Color Sampler','Preparación','Bitácora','Agenda','Horneadas','Lista']:
            fn=next(f for f in app.fns.values() if (b._id,'input') in f.targets)
            assert fn.queue is False
            for i, (_,value) in enumerate(b.choices):
                assert [r['visible'] for r in fn.fn(value)] == [j==i for j in range(len(b.choices))]
            assert not any((b._id,'change') in f.targets for f in app.fns.values())


def test_material_disclosures_contain_real_details_and_escape_names():
    state=studio.initial_state()
    state['materials_library']['LIB-0001']['name']='<script>bad</script>'
    rendered=studio.materials_library_html(state)
    assert rendered.count('<details ') == len(state['materials_library'])
    assert 'Análisis de óxidos' in rendered and 'Fuente exacta' in rendered
    assert '<script>' not in rendered
    assert 'No hay materiales' in studio.materials_library_html(state,query='zzzzz')


def test_material_plus_opens_accordion(app):
    b=next(b for b in app.blocks.values() if b.__class__.__name__=='Button' and b.value=='+')
    fn=next(f for f in app.fns.values() if (b._id,'click') in f.targets)
    assert fn.fn()['open'] is True


def test_element_reference_has_118_unique_expandable_records():
    assert len(wb.ELEMENT_SYMBOLS)==len(wb.ELEMENT_NAMES)==118
    assert len(set(wb.ELEMENT_SYMBOLS))==118
    assert wb.periodic_html().count('<details ') == 118
    assert 'Silicio' in wb.periodic_html('Silicio')
    assert 'Oganesón' in wb.periodic_html('118')


def test_calculations_and_validation():
    assert wb.molecular_mass('SiO2') == pytest.approx(60.083)
    assert wb.shrinkage(100,90)==10
    assert wb.shrinkage(100,105)==-5
    assert wb.absorption(100,104)==4
    assert '600.000' in wb.scale_recipe('Caolín 30\nSílice 70',2000)
    assert '700' in wb.plaster_batch(1000,70)
    for fn,args in [(wb.shrinkage,(0,10)),(wb.absorption,(100,90)),(wb.plaster_batch,(1000,None)),(wb.scale_recipe,('A -10',100))]:
        with pytest.raises(ValueError): fn(*args)


def test_umf_uses_moles_and_preserves_boron_outside_flux_basis():
    # One mole CaO, two SiO2, half Al2O3, half B2O3.
    text='\n'.join(f'{o} {wb.molecular_mass(o)*n}' for o,n in [('CaO',1),('SiO2',2),('Al2O3',.5),('B2O3',.5)])
    result=wb.umf_calculation(text)
    assert '<td>2.00000</td>' in result
    assert result.count('<td>0.50000</td>')==4
    with pytest.raises(ValueError): wb.umf_calculation('Sílice 100')
    with pytest.raises(ValueError): wb.umf_calculation('SiO2 100')


def test_gradio_processes_parameter_and_module_transitions(app):
    import asyncio
    from gradio.state_holder import SessionState
    session=SessionState(app)
    nav=next(b for b in app.blocks.values() if getattr(b,'elem_id',None)=='main-nav')
    config=next(b for b in app.blocks.values() if getattr(b,'value',None)=='Parámetros')
    config_fn=next(f for f in app.fns.values() if (config._id,'click') in f.targets)
    nav_fn=next(f for f in app.fns.values() if (nav._id,'input') in f.targets)
    async def sequence():
        result=await app.process_api(config_fn,[],state=session)
        assert result['data'][5]['visible'] is True
        for name,index in [('LAB',1),('TALLER',2),('Inicio',0)]:
            result=await app.process_api(nav_fn,[name],state=session)
            assert result['data'][index]['visible'] is True
            assert sum(v.get('visible') is True for v in result['data'][:5])==1
    asyncio.run(sequence())
