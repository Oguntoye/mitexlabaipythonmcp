import os
from dotenv import load_dotenv
load_dotenv()


import asyncio
from src.main import run_server



if __name__ == "__main__":
    asyncio.run(run_server())