import asyncio
import sys
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import subprocess
import signal
import os

class RestartHandler(FileSystemEventHandler):
    def __init__(self, restart_func):
        self.restart_func = restart_func
        
    def on_modified(self, event):
        if event.src_path.endswith('.py'):
            print(f"File changed: {event.src_path}")
            self.restart_func()

class MCPServerRunner:
    def __init__(self):
        self.process = None
        
    def start_server(self):
        if self.process:
            self.process.terminate()
            self.process.wait()
            
        self.process = subprocess.Popen([
            sys.executable, "-c", 
            "from src.main import run_server; import asyncio; asyncio.run(run_server())"
        ])
        print("MCP Server started with auto-reload")
        
    def stop_server(self):
        if self.process:
            self.process.terminate()
            self.process.wait()

def main():
    runner = MCPServerRunner()
    
    # Start server initially
    runner.start_server()
    
    # Setup file watcher
    event_handler = RestartHandler(runner.start_server)
    observer = Observer()
    observer.schedule(event_handler, "src", recursive=True)
    observer.start()
    
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        runner.stop_server()
        print("Server stopped")
    
    observer.join()

if __name__ == "__main__":
    main()