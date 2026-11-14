#for MacOS:
import subprocess
import sys

print("Installing dependencies...")
<<<<<<< HEAD
=======

subprocess.check_call([
    sys.executable,
    "-m",
    "pip",
    "install",
    "--upgrade",
    "mne",
    "gpype[all]",
    "gpype[devices]"
])

>>>>>>> ac8e3f4efecfbda472ed201a2d441ee4be047411
subprocess.check_call(
    [sys.executable, "-m", "pip", "install", "--upgrade", "mne", "gpype[all]", "gpype[devices]"]
)
print("Done! All dependencies are installed.")

#for Windows: