import asyncio
import sys
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import subprocess
import signal
from typing import Optional
import time
import os
from dotenv import load_dotenv
load_dotenv()

class RestartHandler(FileSystemEventHandler):
    def __init__(self, restart_func, type_check_func):
        self.restart_func = restart_func
        self.type_check_func = type_check_func
        
    def on_modified(self, event):
        if event.src_path.endswith('.py'):
            print(f"\n{'='*50}")
            print(f"📁 File changed: {event.src_path}")
            print(f"{'='*50}")
            
            # Run type checking first
            if self.type_check_func():
                print("✅ Type checking passed - restarting server...")
                self.restart_func()
            else:
                print("❌ Type checking failed - server not restarted")
                print("Fix the type errors above and save again")

class MCPServerRunner:
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        
    def run_type_check(self) -> bool:
        """Run mypy type checking and return True if successful"""
        print("🔍 Running type check...")
        
        try:
            result = subprocess.run([
                "uv", "run", "mypy", "src", "--pretty", "--error-summary"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print("✅ Type checking passed!")
                return True
            else:
                print("❌ Type checking failed:")
                print("-" * 40)
                print(result.stdout)
                if result.stderr:
                    print("STDERR:")
                    print(result.stderr)
                print("-" * 40)
                return False
                
        except subprocess.TimeoutExpired:
            print("⏰ Type checking timed out")
            return False
        except FileNotFoundError:
            print("⚠️  mypy not found - install with: uv add --dev mypy")
            return True  # Continue without type checking
        except Exception as e:
            print(f"⚠️  Type checking error: {e}")
            return True  # Continue despite error
        
    def start_server(self):
        """Start the MCP server"""
        if self.process:
            print("🛑 Stopping existing server...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            
        print("🚀 Starting MCP server...")
        try:
            self.process = subprocess.Popen([
                "uv", "run", "python", "-c", 
                "from src.main import run_server; import asyncio; asyncio.run(run_server())"
            ])
            print("✅ MCP Server started with auto-reload")
        except Exception as e:
            print(f"❌ Failed to start server: {e}")
            
    def stop_server(self):
        """Stop the MCP server"""
        if self.process:
            print("🛑 Stopping server...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            self.process = None

def main():
    print("🔧 Starting Development Server with Type Checking")
    print("=" * 60)
    
    runner = MCPServerRunner()
    
    # Run initial type check
    print("🔍 Initial type check...")
    if runner.run_type_check():
        # Start server initially
        runner.start_server()
    else:
        print("❌ Initial type check failed. Fix errors and save a file to restart.")
    
    # Setup file watcher
    event_handler = RestartHandler(runner.start_server, runner.run_type_check)
    observer = Observer()
    observer.schedule(event_handler, "src", recursive=True)
    observer.start()
    
    print("\n👀 Watching for file changes...")
    print("Press Ctrl+C to stop")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        observer.stop()
        runner.stop_server()
        print("✅ Server stopped")
    
    observer.join()

if __name__ == "__main__":
    main()