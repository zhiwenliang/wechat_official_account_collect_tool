"""
Main Entry Point for the GUI Application
"""
from utils.runtime_env import configure_runtime_environment

configure_runtime_environment()

from gui.app import WeChatScraperGUI

def main():
    """Launch the GUI application"""
    app = WeChatScraperGUI()
    app.run()

if __name__ == "__main__":
    main()
