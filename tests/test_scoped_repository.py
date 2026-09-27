import json
import copy
from contextlib import closing

import pytest

from alumina import studio
from alumina.storage import EntityState, Repository, ConflictError


@pytest.fixture
def workshop(tmp_path, monkeypatch):
    monkeypatch.setattr(studio, 'DATA_DIR', tmp_path)
    monkeypatch.setattr(studio, 'STATE_FILE', tmp_path/'legacy.json')
    studio.load_state()
    return studio.repository()


def callback(app, name):
    return next(f for f in app.fns.values() if f.fn.__name__ == name)


def test_note_reads_only_journal_and_returns_only_its_view(workshop, monkeypatch):
    app = studio.build_app()
    token = studio.session_token(studio.load_state())
    loaded = []
    remember = EntityState.remember
    def observed(self, collection, key, payload, version):
        loaded.append((collection,key))
        return remember(self,collection,key,payload,version)
    monkeypatch.setattr(EntityState,'remember',observed)
    def forbidden(*args, **kwargs):
        raise AssertionError('Whole-workshop copy/read on a journal action')
    monkeypatch.setattr(Repository,'read',forbidden)
    monkeypatch.setattr(copy,'deepcopy',forbidden)
    fn = callback(app,'journal_add_cb')
    values = fn.fn(token,'Nota','Only the journal')
    assert len(values) == len(fn.outputs) == 2
    assert set(loaded) == {('journal','@value')}
    assert 'Only the journal' in values[1]


def test_single_entity_edit_loads_and_commits_only_that_entity(workshop):
    state = studio.load_state()
    with workshop.transaction(state.revisions) as tx:
        tx['state']['inventory']['MAT-0001']['location'] = 'Shelf A'
        assert set(tx['state'].cache) == {('inventory','MAT-0001')}
    assert set(tx['changed_revisions']) == {json.dumps(['inventory','MAT-0001'])}
    assert studio.load_state()['inventory']['MAT-0001']['location'] == 'Shelf A'


def test_commit_failure_never_returns_success(workshop, monkeypatch):
    app = studio.build_app()
    token = studio.session_token(studio.load_state())
    flush = EntityState.flush
    def fail_after_sql(self, expected):
        flush(self, expected)
        raise ValueError('Simulated commit failure')
    monkeypatch.setattr(EntityState,'flush',fail_after_sql)
    with pytest.raises(Exception,match='Simulated commit failure'):
        callback(app,'journal_add_cb').fn(token,'Nota','Must roll back')
    assert all(item.get('text') != 'Must roll back' for item in studio.load_state()['journal'])


def test_fts_is_updated_atomically_with_entity(workshop):
    state = studio.load_state()
    with workshop.transaction(state.revisions) as tx:
        tx['state']['projects']['NEW'] = {'id':'NEW','name':'Cerámica Única','notes':'Lote turquesa'}
    assert workshop.search('ceramica uni')[0][1] == 'NEW'
    with pytest.raises(ValueError):
        with workshop.transaction(tx['changed_revisions']) as change:
            change['state']['projects']['NEW']['name'] = 'Neverindexed'
            raise ValueError('rollback')
    assert not workshop.search('Neverindexed')
    assert workshop.search('Cerámica')
    with workshop.transaction(tx['changed_revisions']) as change:
        del change['state']['projects']['NEW']
    assert not workshop.search('Cerámica Única')


def test_global_search_does_not_read_workshop_payloads(workshop):
    class NoState(dict):
        def __getitem__(self, key):
            raise AssertionError('Global scan')
    assert 'Caolín' in studio.global_search_html(NoState(),'caolin')
    assert 'Sin coincidencias' in studio.global_search_html(NoState(),'" OR 1=1 --')


def test_candidate_filters_run_before_color_calculation(workshop, monkeypatch):
    state = studio.load_state()
    template = dict(state['formulas']['CAM-0001'])
    template.update(profile='Baja temperatura', target_lab=[50,0,-82.7485])
    with workshop.transaction(state.revisions) as tx:
        for key, fields in [('OK',{}),('HOT',{'target_temp_c':1280}),('BODY',{'body':'Porcelana'}),('VEHICLE',{'vehicle':'Engobe'}),('ATM',{'atmosphere':'Reductora'}),('PROFILE',{'profile':'Gres de alta'})]:
            tx['state']['formulas'][key] = {**template, 'id':key, **fields}
    candidates = workshop.formula_candidates(1040,'Oxidante','Loza blanca','Esmalte','Baja temperatura',50)
    assert [f['id'] for f in candidates] == ['OK']
    monkeypatch.setattr(studio,'hex_to_lab',lambda _: (50,2.6772,-79.7751))
    def wrong_metric(*args):
        raise AssertionError('Delta E76 must never be used for a Delta E00 result')
    monkeypatch.setattr(studio,'delta_e76',wrong_metric)
    result = studio.formula_match_results({'external_refs':[]},'#000000',1040,'Oxidante','Loza blanca','Esmalte','Baja temperatura',50,candidates)
    assert 'ΔE00 2.04' in result
    assert 'HOT' not in result
    with closing(workshop.connect()) as db:
        plan = db.execute("EXPLAIN QUERY PLAN SELECT payload FROM entities WHERE collection='formulas' AND json_extract(payload,'$.vehicle')='Esmalte' AND json_extract(payload,'$.atmosphere')='Oxidante' AND json_extract(payload,'$.target_temp_c') BETWEEN 990 AND 1090").fetchall()
        assert any('formula_filter' in row[-1] for row in plan)


def test_external_comparisons_are_also_ciede2000():
    state = {'formulas':{},'external_refs':[{'name':'Reference','lab':[50,0,-82.7485]}]}
    from unittest.mock import patch
    with patch.object(studio,'hex_to_lab',return_value=(50,2.6772,-79.7751)):
        assert 'ΔE00 2.04' in studio.formula_match_results(state,'#000000',0,'','')


def test_wal_is_explicit_and_writes_are_durable(tmp_path, monkeypatch):
    monkeypatch.setenv('ALUMINA_SQLITE_WAL','1')
    repo = Repository(tmp_path/'local.sqlite3')
    state = repo.load(lambda: {'records':{}})
    with closing(repo.connect()) as db:
        assert db.execute('PRAGMA journal_mode').fetchone()[0] == 'wal'
        assert db.execute('PRAGMA synchronous').fetchone()[0] == 2
    with repo.transaction(state.revisions) as tx:
        tx['state']['records']['R']={'value':1}
    assert Repository(repo.path).load(lambda: {})['records']['R']['value']==1


def test_explicit_backup_and_replacement_can_materialize_all_data(workshop):
    state = studio.load_state()
    with workshop.transaction(state.revisions) as tx:
        backup = studio.export_backup_file(tx['state'])
        tx['state'].clear()
        tx['state'].update(studio.initial_state())
    assert backup.endswith('.zip')
    assert not studio.load_state()['formulas']


def test_consumption_updates_editable_stock_before_later_save(workshop):
    app = studio.build_app()
    state = studio.load_state()
    mid = 'MAT-0001'
    result = callback(app,'consume_cb').fn(studio.session_token(state),mid,10,'ENS-0001',False,False,'ONCE')
    fn = callback(app,'consume_cb')
    qty = next(v for c,v in zip(fn.outputs,result) if getattr(c,'label',None)=='Stock actual')
    assert qty == state['inventory'][mid]['qty']-10
    material = state['inventory'][mid]
    callback(app,'save_stock_cb').fn(result[0],mid,qty,material['min_qty'],material['location'],material.get('preferred_supplier_id',''))
    assert studio.load_state()['inventory'][mid]['qty'] == qty


def test_indirect_tile_change_requires_reloading_editor(workshop):
    app = studio.build_app()
    token = studio.session_token(studio.load_state())
    result = callback(app,'save_result_cb').fn(token,'TES-0001','#ffffff',None,'Funcionó','Me gusta','Conservar','Comentario','')
    tile_key = json.dumps(['tiles','TES-0001'])
    assert result[0]['revisions'][tile_key] == token['revisions'][tile_key]
    fresh = callback(app,'reload_tile_cb').fn(result[0],'TES-0001')
    assert fresh[0]['revisions'][tile_key] == studio.load_state().revisions[tile_key]
    assert fresh[0]['revisions'][tile_key] != token['revisions'][tile_key]
