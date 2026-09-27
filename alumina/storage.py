"""Transactional entity storage. Gradio only retains revision tokens."""
from __future__ import annotations

import copy
import json
import sqlite3
import threading
from contextlib import contextmanager, closing
from pathlib import Path


class ConflictError(ValueError):
    pass


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

    def connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=30)
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("CREATE TABLE IF NOT EXISTS entities (collection TEXT, id TEXT, payload TEXT NOT NULL, revision INTEGER NOT NULL, PRIMARY KEY(collection,id))")
        db.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value INTEGER NOT NULL)")
        db.execute("INSERT OR IGNORE INTO meta VALUES ('revision',0)")
        db.commit()
        return db

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
            return copy.deepcopy(active["state"])
        with closing(self.connect()) as db, db:
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
            current = self.read(db)
            active = {"state": copy.deepcopy(current), "before": current}
            self.local.transaction = active
            try:
                yield active
                self.write(db, active["state"], current, expected)
                active["committed"] = self.read(db)
            finally:
                self.local.transaction = None
