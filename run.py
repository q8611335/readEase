#!/usr/bin/env python3
"""
ReadEase - Dyslexia-Friendly Text Tool
Run this script to start the web application.
"""
import subprocess
import sys
import webbrowser
import time

def check_flask():
    try:
        import flask
        return True
    except ImportError:
        return False

if __name__ == '__main__':
    if not check_flask():
        print("Installing Flask...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'flask'])

    print("=" * 50)
    print("  ReadEase — Dyslexia-Friendly Text Tool")
    print("=" * 50)
    print("  Starting server at http://localhost:5000")
    print("  Press Ctrl+C to stop")
    print("=" * 50)

    # Give server a moment then open browser
    import threading
    def open_browser():
        time.sleep(1.5)
        webbrowser.open('http://localhost:5000')
    threading.Thread(target=open_browser, daemon=True).start()

    from app import app
    app.run(debug=False, port=5000)