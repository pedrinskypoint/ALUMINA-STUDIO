from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "alumina"
OUT = ROOT / "build" / "ALUMINA_STUDIO_V14E4_CLEAN_R3_DEMO.py"

ORDER = [
    PKG / "data" / "reference.py",
    PKG / "core" / "models.py",
    PKG / "core" / "chemistry.py",
    PKG / "core" / "calculators.py",
    PKG / "services" / "domain.py",
    PKG / "services" / "demo.py",
    PKG / "ui" / "renderers.py",
    PKG / "ui" / "app.py",
]


def clean_module(text: str) -> str:
    lines = []
    skip_multiline_import = False
    paren_depth = 0
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "from __future__ import annotations":
            continue
        if skip_multiline_import:
            paren_depth += line.count("(") - line.count(")")
            if paren_depth <= 0:
                skip_multiline_import = False
            continue
        if re.match(r"^from \.{1,2}[A-Za-z0-9_.]+ import ", stripped):
            paren_depth = line.count("(") - line.count(")")
            skip_multiline_import = paren_depth > 0
            continue
        lines.append(line)
    return "\n".join(lines).strip() + "\n"


def main():
    OUT.parent.mkdir(exist_ok=True)
    parts = [
        "from __future__ import annotations\n\n",
        "# ALUMINA STUDIO V14E.4 CLEAN R3 DEMO — archivo unificado generado desde el repo modular.\n\n",
    ]
    for path in ORDER:
        parts.append(f"\n# ===== {path.relative_to(ROOT)} =====\n")
        parts.append(clean_module(path.read_text(encoding="utf-8")))
    parts.append("\n\nif __name__ == '__main__':\n    demo = build_app()\n    demo.launch(share=True, server_name='0.0.0.0', theme=THEME, css=CSS)\n")
    OUT.write_text("".join(parts), encoding="utf-8")
    compile(OUT.read_text(encoding="utf-8"), str(OUT), "exec")
    print(OUT)


if __name__ == "__main__":
    main()
