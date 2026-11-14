import threading
import gpype as gp
from pylsl import StreamInlet, local_clock, resolve_byprop

MARKER_STREAM_NAME = "PsychoPyMarkers"

def pump_markers(marker: gp.Marker, 
                 stop: threading.Event):
    """
    Forward the PsychoPy LSL marker stream into the pipeline.
    """
    inlet = None
    while not stop.is_set() and inlet is None:
        found = resolve_byprop("name", MARKER_STREAM_NAME, timeout=1.0)
        if found:
            inlet = StreamInlet(found[0], max_buflen=60)
            print(f"Connected to LSL stream '{MARKER_STREAM_NAME}'.")
    if inlet is None:
        return

    offset = gp.ClockOffset(local_clock)  
    try:
        correction = inlet.time_correction(timeout=2.0)
    except Exception:
        correction = 0.0

    while not stop.is_set():
        samples, stamps = inlet.pull_chunk(timeout=0.05)
        for sample, ts in zip(samples, stamps): #type:ignore
            code = int(sample[0])
            try:
                marker.emit(code, observed_at=offset.stamp(ts + correction))
            except ValueError:
                marker.emit(code)
                print(f"Marker {code} arrived late; stamped on arrival.")
            print(f"Marker received: {code}")