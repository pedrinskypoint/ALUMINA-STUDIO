"""Servidor local: datos persistentes y acceso sólo desde este equipo."""
import argparse
import os
from pathlib import Path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ALUMINA STUDIO local")
    parser.add_argument("--port", type=int, default=7861)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("El puerto debe estar entre 1 y 65535")
    root = Path(__file__).resolve().parent
    os.environ.setdefault("ALUMINA_DATA_DIR", str(root / "alumina_data"))
    os.environ["GRADIO_SERVER_PORT"] = str(args.port)
    from alumina.app import launch

    print(f"Abrí ALUMINA en http://127.0.0.1:{args.port}", flush=True)
    print(f"Datos: {os.environ['ALUMINA_DATA_DIR']}", flush=True)
    launch(share=False, server_name="127.0.0.1")
