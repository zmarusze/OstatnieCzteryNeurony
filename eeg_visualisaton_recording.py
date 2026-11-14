import threading

import gpype as gp
from utils import pump_markers


USE_REAL_DEVICE = True  
DEVICE_SERIAL = "UN-2024.12.02"  
TEST_SIGNAL = False 

CHANNEL_LABELS = ["Fz", "C3", "Cz", "C4", "Pz", "PO7", "Oz", "PO8"]
N_EEG_CHANNELS = len(CHANNEL_LABELS) 
FILE_PREFIX = "bci_unicorn" if USE_REAL_DEVICE else "bci_synthetic"
MARKER_STYLE = { 1: ("rest", "#DA0EA3"), 2: ("right MI", "#FFD700"), 3: ("left MI", "#00BFFF")}


if __name__ == "__main__":
    app = gp.MainApp()
    p = gp.Pipeline()
    p.event_margin_ms = 100.0

    if USE_REAL_DEVICE: device = gp.HybridBlack(serial=DEVICE_SERIAL,
                                                channel_selection=list(range(N_EEG_CHANNELS)),
                                                test_signal=TEST_SIGNAL,
                                                enable_oscar=True) #adaptive artifact correction
    else:
        device = gp.Generator(signal_amplitude=20.0, noise_amplitude=5.0)
    source = gp.ChannelLabeler(labels=CHANNEL_LABELS)
    p.connect(device, source)
    marker = gp.Marker()


    bandpass = gp.Bandpass(f_lo=1, f_hi=40)
    notch50 = gp.Bandstop(f_lo=48, f_hi=52)

    merge_prep = gp.Router(input_channels={"eeg": gp.Router.ALL, "mrk": gp.Router.ALL})
    merge_vis = gp.Router(input_channels={"eeg": gp.Router.ALL, "mrk": gp.Router.ALL})


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
    eeg_writer = gp.EDFWriter(file_name=f"{FILE_PREFIX}_eeg.edf", add_timestamp=False)
    csv_writer = gp.CsvWriter(file_name=f"{FILE_PREFIX}_eeg_markers.csv", add_timestamp=False)


    p.connect(source, bandpass)
    p.connect(bandpass, notch50)
    
    p.connect(notch50, merge_vis["eeg"])
    p.connect(marker, merge_vis["mrk"])
    p.connect(merge_vis, scope)

    p.connect(notch50, merge_prep["eeg"]) 
    p.connect(marker, merge_prep["mrk"])
    p.connect(merge_prep, eeg_writer)
    p.connect(merge_prep, csv_writer)

    app.add_widget(scope)

    p.start()
    stop_event = threading.Event()
    bridge = threading.Thread(target=pump_markers, args=(marker, stop_event), daemon=True)
    bridge.start()
    print("Pipeline running! Start your PsychoPy script now.")

    app.run()
    stop_event.set()
    bridge.join(timeout=2.0)
    p.stop()