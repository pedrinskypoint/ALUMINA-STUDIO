from .ui.app import build_app, THEME, APP_VERSION
from .ui.renderers import CSS

def launch(*, share=False, server_name="0.0.0.0"):
    demo = build_app()
    return demo.launch(share=share, server_name=server_name, theme=THEME, css=CSS)

if __name__ == "__main__":
    launch()
