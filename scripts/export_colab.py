"""Export the recovered application without reconstructing missing R3 modules."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main():
    source = (ROOT / "alumina" / "studio.py").read_bytes()
    output = ROOT / "build" / "ALUMINA_STUDIO_V17_DIAGRAMACION.py"
    compile(source, str(output), "exec")
    output.parent.mkdir(exist_ok=True)
    output.write_bytes(source)
    print(output)

if __name__ == "__main__":
    main()
