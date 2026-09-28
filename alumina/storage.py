"""Transactional entity storage. Gradio only retains revision tokens."""
from __future__ import annotations

import copy
import json
import sqlite3
import threading
import os
import re
from collections.abc import MutableMapping
from contextlib import contextmanager, closing
from pathlib import Path


class ConflictError(ValueError):
    pass


_MISSING = object()


class EntityMap(MutableMapping):
    """Read only the requested entity; enumeration explicitly reads a collection."""
    def __init__(self, state, collection):
        self.state, self.collection = state, collection

    def __getitem__(self, key):
        return self.state.row(self.collection, str(key))

    def __setitem__(self, key, value):
        self.state.set_row(self.collection, str(key), value)

    def __delitem__(self, key):
        self.state.delete_row(self.collection, str(key))

    def __iter__(self):
        keys = {r[0] for r in self.state.db.execute('SELECT id FROM entities WHERE collection=? AND id NOT IN (?,?)', (self.collection, '@kind', '@value'))}
        for (collection, key), value in self.state.cache.items():
            if collection == self.collection and key not in {'@kind', '@value'}:
                keys.discard(key) if value is _MISSING else keys.add(key)
        return iter(sorted(keys))

    def __len__(self):
        return sum(1 for _ in self)

    def items(self):
        # One query for a requested list, instead of N separate entity lookups.
        for key, payload, version in self.state.db.execute('SELECT id,payload,revision FROM entities WHERE collection=? AND id NOT IN (?,?)', (self.collection, '@kind', '@value')):
            self.state.remember(self.collection, key, payload, version)
        return ((key, self[key]) for key in self)

    def values(self):
        return (value for _, value in self.items())


class EntityState(MutableMapping):
    """Transaction-local unit of work. Original JSON is retained only for read rows."""
    def __init__(self, db):
        self.db, self.cache, self.original, self.revisions = db, {}, {}, {}
        self.collections = {c: k for c,k in db.execute("SELECT collection,id FROM entities WHERE id IN ('@kind','@value')")}

    def remember(self, collection, key, payload, version):
        pair = collection, key
        if pair not in self.cache:
            self.original[pair] = payload
            self.cache[pair] = json.loads(payload) if payload is not None else _MISSING
            if version is not None:
                self.revisions[json.dumps(list(pair))] = version

    def row(self, collection, key):
        pair = collection, key
        if pair not in self.cache:
            record = self.db.execute('SELECT payload,revision FROM entities WHERE collection=? AND id=?', pair).fetchone()
            self.remember(collection, key, *(record or (None, None)))
        value = self.cache[pair]
        if value is _MISSING:
            raise KeyError(key)
        return value

    def set_row(self, collection, key, value):
        try:
            self.row(collection, key)
        except KeyError:
            pass
        self.cache[collection, key] = value

    def delete_row(self, collection, key):
        self.row(collection, key)
        self.cache[collection, key] = _MISSING

    def __getitem__(self, collection):
        kind = self.collections[collection]
        return EntityMap(self, collection) if kind == '@kind' else self.row(collection, '@value')

    def __setitem__(self, collection, value):
        if collection in self.collections:
            del self[collection]
        if isinstance(value, (dict, EntityMap)):
            self.collections[collection] = '@kind'
            self.set_row(collection, '@kind', 'dict')
            for key, item in value.items():
                self.set_row(collection, str(key), item)
        else:
            self.collections[collection] = '@value'
            self.set_row(collection, '@value', value)

    def __delitem__(self, collection):
        kind = self.collections[collection]
        if kind == '@kind':
            for key in list(self[collection]):
                self.delete_row(collection, key)
        self.delete_row(collection, kind)
        del self.collections[collection]

    def __iter__(self):
        return iter(self.collections)

    def __len__(self):
        return len(self.collections)

    def materialize(self):
        return {key: dict(value.items()) if isinstance(value, EntityMap) else value for key,value in self.items()}

    def flush(self, expected):
        changed = {}
        for pair, value in self.cache.items():
            old = self.original[pair]
            new = None if value is _MISSING else json.dumps(value, ensure_ascii=False, allow_nan=False)
            if new == old:
                continue
            prior = json.loads(old) if old is not None else None
            if old is not None and value is not _MISSING and value == prior:
                continue
            token = json.dumps(list(pair))
            append = isinstance(prior, list) and isinstance(value, list) and value[:len(prior)] == prior
            if not append and expected.get(token) != self.revisions.get(token):
                raise ConflictError('Otro usuario modificó este registro. Recargá la ficha antes de guardar; tus cambios no se sobrescribieron.')
            changed[pair] = new
        if not changed:
            return {}
        revision = self.db.execute("SELECT value FROM meta WHERE key='revision'").fetchone()[0]+1
        for pair, payload in changed.items():
            if payload is None:
                self.db.execute('DELETE FROM entities WHERE collection=? AND id=?', pair)
            else:
                self.db.execute('INSERT INTO entities VALUES (?,?,?,?) ON CONFLICT(collection,id) DO UPDATE SET payload=excluded.payload,revision=excluded.revision', (*pair,payload,revision))
        self.db.execute("UPDATE meta SET value=? WHERE key='revision'", (revision,))
        return {json.dumps(list(pair)): revision if payload is not None else None for pair,payload in changed.items()}


class Snapshot(dict):
    def __init__(self, data, revisions=None):
        super().__init__(data)
        self.revisions = revisions or {}
        self.baseline = copy.deepcopy(data)


def entity_rows(data):
    rows = {}
    for collection, value in data.items():
        if isinstance(value, dict):
            rows[(collection, "@kind")] = "dict"
            for key, item in value.items():
                rows[(collection, str(key))] = item
        else:
            rows[(collection, "@value")] = value
    return rows


class Repository:
    def __init__(self, path):
        self.path = Path(path)
        self.local = threading.local()
        self.ready = False
        self.setup_lock = threading.Lock()

    def connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=30)
        db.execute("PRAGMA foreign_keys=ON")
        db.execute('PRAGMA synchronous=FULL')
        with self.setup_lock:
            if not self.ready:
                # WAL is opt-in for local disks, never assumed safe on mounted Drive.
                if os.getenv('ALUMINA_SQLITE_WAL') == '1':
                    db.execute('PRAGMA journal_mode=WAL')
                db.execute("CREATE TABLE IF NOT EXISTS entities (collection TEXT, id TEXT, payload TEXT NOT NULL, revision INTEGER NOT NULL, PRIMARY KEY(collection,id))")
                db.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value INTEGER NOT NULL)")
                db.execute("INSERT OR IGNORE INTO meta VALUES ('revision',0)")
                self.prepare_search(db)
                db.commit()
                self.ready = True
        return db

    def prepare_search(self, db):
        db.execute("CREATE INDEX IF NOT EXISTS entity_kinds ON entities(id,collection) WHERE id IN ('@kind','@value')")
        db.execute("CREATE INDEX IF NOT EXISTS formula_filter ON entities(collection,json_extract(payload,'$.vehicle'),json_extract(payload,'$.atmosphere'),json_extract(payload,'$.target_temp_c'))")
        db.execute("CREATE INDEX IF NOT EXISTS formula_profile ON entities(collection,json_extract(payload,'$.profile'))")
        created = not db.execute("SELECT 1 FROM sqlite_master WHERE name='entity_search'").fetchone()
        db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS entity_search USING fts5(collection UNINDEXED, entity_id, name, notes, tokenize='unicode61 remove_diacritics 2')")
        allowed = "('formulas','experiments','tiles','inventory','orders','projects')"
        projection = "new.rowid,new.collection,new.id,coalesce(json_extract(new.payload,'$.name'),json_extract(new.payload,'$.material_name'),json_extract(new.payload,'$.supplier_name'),''),coalesce(json_extract(new.payload,'$.notes'),'')"
        db.execute(f"CREATE TRIGGER IF NOT EXISTS entity_search_insert AFTER INSERT ON entities WHEN new.collection IN {allowed} AND new.id NOT IN ('@kind','@value') BEGIN INSERT INTO entity_search(rowid,collection,entity_id,name,notes) SELECT {projection}; END")
        db.execute(f"CREATE TRIGGER IF NOT EXISTS entity_search_update AFTER UPDATE ON entities WHEN new.collection IN {allowed} AND new.id NOT IN ('@kind','@value') BEGIN DELETE FROM entity_search WHERE rowid=old.rowid; INSERT INTO entity_search(rowid,collection,entity_id,name,notes) SELECT {projection}; END")
        db.execute("CREATE TRIGGER IF NOT EXISTS entity_search_delete AFTER DELETE ON entities BEGIN DELETE FROM entity_search WHERE rowid=old.rowid; END")
        if created:
            db.execute(f"INSERT INTO entity_search(rowid,collection,entity_id,name,notes) SELECT rowid,collection,id,coalesce(json_extract(payload,'$.name'),json_extract(payload,'$.material_name'),json_extract(payload,'$.supplier_name'),''),coalesce(json_extract(payload,'$.notes'),'') FROM entities WHERE collection IN {allowed} AND id NOT IN ('@kind','@value')")

    def search(self, query, limit=30):
        tokens = re.findall(r'[^\W_]+', query, flags=re.UNICODE)
        if not tokens:
            return []
        expression = ' AND '.join('"'+word+'"*' for word in tokens)
        with closing(self.connect()) as db:
            return db.execute('SELECT collection,entity_id,name FROM entity_search WHERE entity_search MATCH ? ORDER BY rank LIMIT ?', (expression,limit)).fetchall()

    def formula_candidates(self, temperature=None, atmosphere='', body='', vehicle='', profile='', tolerance=50):
        clauses = ["collection='formulas'", "id NOT IN ('@kind','@value')", "json_type(payload,'$.target_lab')='array'"]
        params = []
        for field, value in [('vehicle',vehicle),('atmosphere',atmosphere),('body',body),('profile',profile)]:
            if value:
                clauses.append(f"json_extract(payload,'$.{field}')=? COLLATE NOCASE")
                params.append(value.strip())
        if temperature:
            clauses.append("json_extract(payload,'$.target_temp_c') BETWEEN ? AND ?")
            params.extend([float(temperature)-tolerance,float(temperature)+tolerance])
        with closing(self.connect()) as db:
            return [json.loads(row[0]) for row in db.execute('SELECT payload FROM entities WHERE '+' AND '.join(clauses),params)]

    @contextmanager
    def view(self):
        with closing(self.connect()) as db, db:
            db.execute('BEGIN')
            state = EntityState(db)
            previous = getattr(self.local, 'read_view', None)
            self.local.read_view = state
            try:
                yield state
            finally:
                self.local.read_view = previous

    def read(self, db):
        data, revisions = {}, {}
        for collection, key, payload, version in db.execute("SELECT collection,id,payload,revision FROM entities ORDER BY collection,id"):
            value = json.loads(payload)
            revisions[json.dumps([collection, key])] = version
            if key == "@kind":
                data.setdefault(collection, {})
            elif key == "@value":
                data[collection] = value
            else:
                data.setdefault(collection, {})[key] = value
        return Snapshot(data, revisions)

    def load(self, seed):
        active = getattr(self.local, "transaction", None)
        if active:
            return active["state"]
        read_view = getattr(self.local, 'read_view', None)
        if read_view is not None:
            return read_view
        with closing(self.connect()) as db, db:
            state = self.read(db)
            if state:
                return state
            db.execute("BEGIN IMMEDIATE")
            state = self.read(db)
            if not state:
                self.write(db, seed(), state, {})
                state = self.read(db)
            return state

    def write(self, db, state, current, expected):
        before, after = entity_rows(current), entity_rows(state)
        changed = [key for key in before.keys() | after.keys() if before.get(key) != after.get(key) or (key in before) != (key in after)]
        for key in changed:
            token = json.dumps(list(key))
            before_value, after_value = before.get(key), after.get(key)
            append_only = isinstance(before_value, list) and isinstance(after_value, list) and after_value[:len(before_value)] == before_value
            if not append_only and expected.get(token) != current.revisions.get(token):
                raise ConflictError("Otro usuario modificó este registro. Recargá la ficha antes de guardar; tus cambios no se sobrescribieron.")
        if not changed:
            return
        revision = db.execute("SELECT value FROM meta WHERE key='revision'").fetchone()[0] + 1
        for collection, key in changed:
            if (collection, key) not in after:
                db.execute("DELETE FROM entities WHERE collection=? AND id=?", (collection, key))
            else:
                db.execute("INSERT INTO entities VALUES (?,?,?,?) ON CONFLICT(collection,id) DO UPDATE SET payload=excluded.payload,revision=excluded.revision", (collection, key, json.dumps(after[(collection, key)], ensure_ascii=False, allow_nan=False), revision))
        db.execute("UPDATE meta SET value=? WHERE key='revision'", (revision,))

    def save(self, state):
        active = getattr(self.local, "transaction", None)
        if active:
            active["state"] = state
            return
        if not isinstance(state, Snapshot):
            raise ConflictError("La escritura requiere una lectura vigente de la base de datos.")
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            current = self.read(db)
            # Three-way merge: independent entities survive stale snapshots.
            merged = copy.deepcopy(current)
            old, new = entity_rows(state.baseline), entity_rows(state)
            for collection, key in old.keys() | new.keys():
                if old.get((collection, key)) == new.get((collection, key)) and ((collection,key) in old) == ((collection,key) in new):
                    continue
                if key == "@kind":
                    merged.setdefault(collection, {})
                elif key == "@value":
                    if collection in state:
                        prior, proposed = state.baseline.get(collection), state[collection]
                        if isinstance(prior, list) and isinstance(proposed, list) and proposed[:len(prior)] == prior:
                            merged[collection] = copy.deepcopy(current.get(collection, [])) + copy.deepcopy(proposed[len(prior):])
                        else:
                            merged[collection] = copy.deepcopy(proposed)
                    else:
                        merged.pop(collection, None)
                elif key in state.get(collection, {}):
                    merged.setdefault(collection, {})[key] = copy.deepcopy(state[collection][key])
                else:
                    merged.get(collection, {}).pop(key, None)
            self.write(db, merged, current, state.revisions)
            fresh = self.read(db)
            state.clear()
            state.update(fresh)
            state.revisions = fresh.revisions
            state.baseline = copy.deepcopy(dict(fresh))

    @contextmanager
    def transaction(self, expected):
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            active = {"state": EntityState(db)}
            self.local.transaction = active
            try:
                yield active
                active['changed_revisions'] = active['state'].flush(expected)
                active['revisions'] = {json.dumps([c,k]): rev for c,k,rev in db.execute('SELECT collection,id,revision FROM entities')} if active.get('reload') else None
            finally:
                self.local.transaction = None
