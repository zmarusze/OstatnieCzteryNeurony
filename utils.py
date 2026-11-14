import csv
import threading
import gpype as gp
from pylsl import StreamInlet, resolve_byprop

MARKER_STREAM_NAME = "PsychoPyMarkers"

def pump_markers(marker_main: gp.Marker, specific_markers: dict, stop: threading.Event, csv_filename: str):
    """Forwards markers to the pipeline instantly to prevent dropped triggers."""
    inlet = None
    while not stop.is_set() and inlet is None:
        found = resolve_byprop("name", MARKER_STREAM_NAME, timeout=1.0)
        if found:
            inlet = StreamInlet(found[0], max_buflen=60)
            print(f"Connected to LSL stream '{MARKER_STREAM_NAME}'.")
    if inlet is None:
        return

    with open(csv_filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'marker']) 

        while not stop.is_set():
            samples, stamps = inlet.pull_chunk(timeout=0.05)
            for sample, ts in zip(samples, stamps): #type:ignore
                code = int(sample[0])
                marker_main.emit(code)
                if code in specific_markers:
                    specific_markers[code].emit(code)
                
                writer.writerow([ts, code])