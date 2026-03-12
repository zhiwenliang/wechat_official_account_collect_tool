"""
Main Entry Point for the GUI Application
"""
import tkinter as tk
from gui.app import WeChatScraperGUI

def main():
    """Launch the GUI application"""
    app = WeChatScraperGUI()
    app.run()

if __name__ == "__main__":
    main()
