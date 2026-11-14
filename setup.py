#for MacOS:
import subprocess
import sys

print("Installing dependencies...")
subprocess.check_call(
    [sys.executable, "-m", "pip", "install", "--upgrade", "mne", "gpype[all]", "gpype[devices]"]
)
print("Done! All dependencies are installed.")

#for Windows: