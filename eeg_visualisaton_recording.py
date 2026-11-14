import threading

import gpype as gp
from pylsl import StreamInlet, local_clock, resolve_byprop

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
USE_REAL_DEVICE = False  # True: Unicorn Hybrid Black, False: synthetic data
DEVICE_SERIAL = "UN-2024.12.02"  # printed on the Unicorn, e.g. UN-2023.05.51
TEST_SIGNAL = False  # True: Unicorn sends its built-in test signal (no electrodes)

MARKER_STREAM_NAME = "PsychoPyMarkers"

# Unicorn Hybrid Black electrode layout, in channel order
CHANNEL_LABELS = ["Fz", "C3", "Cz", "C4", "Pz", "PO7", "Oz", "PO8"]
N_EEG_CHANNELS = len(CHANNEL_LABELS)  # 8; the marker channel gets index 8
FILE_PREFIX = "bci_unicorn" if USE_REAL_DEVICE else "bci_synthetic"

# Marker code -> (label, colour) for the live scope
MARKER_STYLE = {
    1: ("rest", "#888888"),
    2: ("right MI", "#FFD700"),
    3: ("left MI", "#00BFFF"),
}


def pump_markers(marker: gp.Marker, stop: threading.Event):
    """Forward the PsychoPy LSL marker stream into the pipeline.

    gp.LslReceiver only accepts regularly sampled streams. PsychoPy's marker
    stream is irregular (nominal_srate=0), so it is read with pylsl and
    emitted through gp.Marker, which places each event on the pipeline's
    timeline at the moment it was sent.
    """
    inlet = None
    while not stop.is_set() and inlet is None:
        # PsychoPy usually starts after the pipeline, so keep looking.
        found = resolve_byprop("name", MARKER_STREAM_NAME, timeout=1.0)
        if found:
            inlet = StreamInlet(found[0], max_buflen=60)
            print(f"Connected to LSL stream '{MARKER_STREAM_NAME}'.")
    if inlet is None:
        return

    offset = gp.ClockOffset(local_clock)  # LSL clock -> pipeline clock

    # Sender-to-here clock correction (0 when PsychoPy runs on this
    # machine). Read once, up front: the call can block, and the pipeline
    # refuses events older than its margin (40 ms by default).
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
                # Too old for the pipeline's event margin: stamp it now.
                marker.emit(code)
                print(f"Marker {code} arrived late; stamped on arrival.")
            print(f"Marker received: {code}")


if __name__ == "__main__":
    app = gp.MainApp()
    p = gp.Pipeline()
    # The marker bridge runs in a Python thread next to the GUI, so an event
    # can reach the pipeline a few tens of ms after it happened. The default
    # margin is 40 ms; 100 ms keeps those events on their true timestamp.
    p.event_margin_ms = 100.0

    # 1. Sources: EEG (real or synthetic) and the PsychoPy markers
    if USE_REAL_DEVICE:
        # 8 EEG channels at 250 Hz over Bluetooth. Pair the Unicorn in your
        # OS Bluetooth settings first.
        device = gp.HybridBlack(
            serial=DEVICE_SERIAL,
            channel_selection=list(range(N_EEG_CHANNELS)),
            test_signal=TEST_SIGNAL,
        )
    else:
        # Generator's default amplitudes are 0, which gives a flat line.
        device = gp.Generator(signal_amplitude=20.0, noise_amplitude=5.0)
    # Names the channels (shows up in the EDF); the data is untouched.
    source = gp.ChannelLabeler(labels=CHANNEL_LABELS)
    p.connect(device, source)
    marker = gp.Marker()

    # 2. Processing (For visualization only)
    bandpass = gp.Bandpass(f_lo=1, f_hi=30)
    notch50 = gp.Bandstop(f_lo=48, f_hi=52)
    reref = gp.Reference(reference=None)  # common average

    # Markers are events, EEG is a continuous stream: a Router joins them
    # into one stream (EEG channels + one marker channel).
    merge_raw = gp.Router(
        input_channels={"eeg": gp.Router.ALL, "mrk": gp.Router.ALL}
    )
    merge_vis = gp.Router(
        input_channels={"eeg": gp.Router.ALL, "mrk": gp.Router.ALL}
    )

    # 3. Sinks: the live plot, the EDF saver, and the CSV saver
    scope = gp.TimeSeriesScope(
        time_window=10,
        markers=[
            gp.TimeSeriesScope.Markers(
                color=color,
                label=label,
                channel=N_EEG_CHANNELS,
                value=code,
            )
            for code, (label, color) in MARKER_STYLE.items()
        ],
    )
    eeg_writer = gp.EDFWriter(file_name="bci_synthetic_eeg.edf")
    csv_writer = gp.CsvWriter(file_name="bci_synthetic_eeg_markers.csv")

    # --- CONNECTIONS ---
    # Filtered EEG + markers -> live scope
    p.connect(source, bandpass)
    p.connect(bandpass, notch50)
    p.connect(notch50, reref)
    p.connect(reref, merge_vis["eeg"])
    p.connect(marker, merge_vis["mrk"])
    p.connect(merge_vis, scope)

    # RAW EEG + markers -> EDF (markers become EDF+ annotations) and CSV
    p.connect(source, merge_raw["eeg"])
    p.connect(marker, merge_raw["mrk"])
    p.connect(merge_raw, eeg_writer)
    p.connect(merge_raw, csv_writer)

    app.add_widget(scope)

    # Start the pipeline, then the marker bridge (needs a running pipeline)
    p.start()
    stop_event = threading.Event()
    bridge = threading.Thread(
        target=pump_markers, args=(marker, stop_event), daemon=True
    )
    bridge.start()
    print("Synthetic pipeline running! Start your PsychoPy script now.")

    # Open the GUI
    app.run()

    # Cleanly stop everything when the GUI is closed
    stop_event.set()
    bridge.join(timeout=2.0)
    p.stop()