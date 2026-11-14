import subprocess
import sys

print("Installing dependencies...")
subprocess.check_call(
    [sys.executable, "-m", "pip", "install", "--upgrade", "mne", "gpype[all]"]
)
print("Done! All dependencies are installed.")