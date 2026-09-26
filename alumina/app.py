from .studio import APP_VERSION, build_app, launch

__all__ = ["APP_VERSION", "build_app", "launch"]

if __name__ == "__main__":
    launch(share=False)
