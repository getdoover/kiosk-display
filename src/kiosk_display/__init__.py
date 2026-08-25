from pydoover.docker import run_app

from .application import KioskDisplayApplication

def main():
    """Run the application."""
    run_app(KioskDisplayApplication())
