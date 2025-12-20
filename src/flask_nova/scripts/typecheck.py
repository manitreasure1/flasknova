
import subprocess
import sys

def main()-> None:
    subprocess.run([sys.executable, "-m", "mypy", "src/flask_nova"], check=True)
