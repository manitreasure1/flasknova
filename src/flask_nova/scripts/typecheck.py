
import subprocess
import sys

def main():

    subprocess.run([sys.executable, "-m", "mypy", "src/flask_nova"], check=True)
