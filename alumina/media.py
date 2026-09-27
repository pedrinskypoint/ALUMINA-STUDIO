"""Durable media references and portable backups, independent of Gradio cache."""
from __future__ import annotations

import base64
import io
import shutil
import uuid
from pathlib import Path

from PIL import Image, ImageOps


def media_path(data_dir, reference):
    if not reference:
        return None
    root = Path(data_dir).resolve()
    candidate = (root / reference).resolve()
    media_root = root / "media"
    if not candidate.is_relative_to(media_root) or not candidate.is_file():
        return None
    return candidate


def persist_media(data_dir, source, image_only=True):
    if not source:
        return ""
    owned = media_path(data_dir, source)
    if owned:
        return str(owned.relative_to(Path(data_dir).resolve()))
    source = Path(source)
    if not source.is_file():
        raise ValueError("La imagen o documento ya no está disponible. Volvé a adjuntarlo.")
    folder = Path(data_dir) / "media"
    folder.mkdir(parents=True, exist_ok=True)
    if image_only:
        with Image.open(source) as im:
            normalized = ImageOps.exif_transpose(im).convert("RGB")
            target = folder / f"{uuid.uuid4().hex}.jpg"
            normalized.save(target, format="JPEG", quality=95)
    else:
        target = folder / f"{uuid.uuid4().hex}{source.suffix.lower()}"
        shutil.copyfile(source, target)
    return target.relative_to(Path(data_dir)).as_posix()


def thumbnail_uri(data_dir, reference):
    path = media_path(data_dir, reference)
    if not path:
        return ""
    try:
        with Image.open(path) as im:
            im.thumbnail((240, 240))
            out = io.BytesIO()
            im.convert("RGB").save(out, format="JPEG", quality=80)
            return "data:image/jpeg;base64," + base64.b64encode(out.getvalue()).decode("ascii")
    except (OSError, ValueError):
        return ""


def migrate_media(data_dir, state):
    missing = []
    def visit(obj):
        if isinstance(obj, list):
            for item in obj:
                visit(item)
        elif isinstance(obj, dict):
            for key, value in obj.items():
                if key in {"photo_path", "original_photo", "original_file", "source_image"} and value:
                    try:
                        obj[key] = persist_media(data_dir, value, key != "original_file")
                    except (OSError, ValueError):
                        missing.append(str(value))
                elif isinstance(value, (list, dict)):
                    visit(value)
    visit(state)
    state.setdefault("migration_warnings", []).extend(f"Archivo anterior no recuperable: {x}" for x in missing)
    return state
