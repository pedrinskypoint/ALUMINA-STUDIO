"""Export the recovered application without reconstructing missing R3 modules."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main():
    import ast
    text = (ROOT / "alumina" / "studio.py").read_text()
    lines = text.splitlines(keepends=True)
    tree = ast.parse(text)
    omitted = set()
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and (node.level or node.module == "__future__"):
            omitted.update(range(node.lineno - 1, node.end_lineno))
    parts = ["from __future__ import annotations\n"]
    for name in ["storage", "media", "operations", "workbench"]:
        module = (ROOT / "alumina" / f"{name}.py").read_text()
        parts.append(module.replace("from __future__ import annotations", ""))
    parts.append("".join(line for i, line in enumerate(lines) if i not in omitted))
    source = "\n\n".join(parts).encode("utf-8")
    output = ROOT / "build" / "ALUMINA_STUDIO_V17_2_NAVEGACION.py"
    compile(source, str(output), "exec")
    output.parent.mkdir(exist_ok=True)
    output.write_bytes(source)
    print(output)

if __name__ == "__main__":
    main()
