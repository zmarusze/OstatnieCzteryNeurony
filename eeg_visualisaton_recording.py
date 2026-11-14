import threading
import os

import gpype as gp
from utils import pump_markers


USE_REAL_DEVICE = True
DEVICE_SERIAL = "UN-2024.12.02"
TEST_SIGNAL = False

CHANNEL_LABELS = ["Fz", "C3", "Cz", "C4", "Pz", "PO7", "Oz", "PO8"]
N_EEG_CHANNELS = len(CHANNEL_LABELS)
FILE_PREFIX = "bci_unicorn" if USE_REAL_DEVICE else "bci_synthetic"

MARKER_STYLE = {
    1: ("rest", "#DA0EA3"),
    2: ("right MI", "#FFD700"),
    3: ("left MI", "#00BFFF"),
}


REST_LEN_S = 4.0
MI_LEN_S = 4.0
PRE_S = 0.01  
EPOCH_AMPLITUDE_LIMIT = 50 

if __name__ == "__main__":
    app = gp.MainApp()
    p = gp.Pipeline()
    p.event_margin_ms = 100.0

    output_dir = "outputs"
    os.makedirs(output_dir, exist_ok=True)

    session_num = 1
    while os.path.exists(f"{output_dir}/{FILE_PREFIX}_session_{session_num:03d}_eeg.edf"):
        session_num += 1
    session_str = f"session_{session_num:03d}"
    print(f"Recording to session: {session_str} in /{output_dir}")

    if USE_REAL_DEVICE:
        device = gp.HybridBlack(
            serial=DEVICE_SERIAL,
            channel_selection=list(range(N_EEG_CHANNELS)),
            test_signal=TEST_SIGNAL,
            enable_oscar=True,
        )
    else:
        device = gp.Generator(signal_amplitude=20.0, noise_amplitude=5.0)
    
    source = gp.ChannelLabeler(labels=CHANNEL_LABELS)
    p.connect(device, source)
    

    marker_main = gp.Marker()
    marker_rest = gp.Marker()
    marker_right = gp.Marker()
    marker_left = gp.Marker()


    bandpass = gp.Bandpass(f_lo=1, f_hi=40)
    notch50 = gp.Bandstop(f_lo=48, f_hi=52)
    merge_prep = gp.Router(input_channels={"eeg": gp.Router.ALL, "mrk": gp.Router.ALL})
    merge_vis = gp.Router(input_channels={"eeg": gp.Router.ALL, "mrk": gp.Router.ALL})


    epocher_rest = gp.Trigger(time_pre=PRE_S, time_post=REST_LEN_S) 
    epocher_right = gp.Trigger(time_pre=PRE_S, time_post=MI_LEN_S)  
    epocher_left = gp.Trigger(time_pre=PRE_S, time_post=MI_LEN_S)  


    scope = gp.TimeSeriesScope(time_window=10,
                               markers=[
                               gp.TimeSeriesScope.Markers(
                               color=color, label=label, channel=N_EEG_CHANNELS, value=code)
                               for code, (label, color) in MARKER_STYLE.items()])
    
    scope_rest = gp.TriggerScope(amplitude_limit=EPOCH_AMPLITUDE_LIMIT)
    scope_right = gp.TriggerScope(amplitude_limit=EPOCH_AMPLITUDE_LIMIT)
    scope_left = gp.TriggerScope(amplitude_limit=EPOCH_AMPLITUDE_LIMIT)

    eeg_writer = gp.EDFWriter(file_name=f"{output_dir}/{FILE_PREFIX}_{session_str}_eeg.edf", timestamp=False)

    p.connect(source, bandpass)
    p.connect(bandpass, notch50)


    p.connect(notch50, merge_vis["eeg"])
    p.connect(marker_main, merge_vis["mrk"])
    p.connect(merge_vis, scope)


    p.connect(notch50, merge_prep["eeg"])
    p.connect(marker_main, merge_prep["mrk"])
    p.connect(merge_prep, eeg_writer)


    p.connect(notch50, epocher_rest)
    p.connect(marker_rest, epocher_rest[gp.Trigger.PORT_TRIGGER])
    p.connect(epocher_rest, scope_rest)

    p.connect(notch50, epocher_right)
    p.connect(marker_right, epocher_right[gp.Trigger.PORT_TRIGGER])
    p.connect(epocher_right, scope_right)

    p.connect(notch50, epocher_left)
    p.connect(marker_left, epocher_left[gp.Trigger.PORT_TRIGGER])
    p.connect(epocher_left, scope_left)

    app.add_widget(scope)
    #app.add_widget(scope_rest)
    #app.add_widget(scope_right)
    #app.add_widget(scope_left)

    p.start()
    
    specific_markers_dict = {
        1: marker_rest,
        2: marker_right,
        3: marker_left
    }
    
    stop_event = threading.Event()
    bridge = threading.Thread(
        target=pump_markers,
        args=(marker_main, specific_markers_dict, stop_event),
        daemon=True,
    )
    bridge.start()
    print("Pipeline running! Start your PsychoPy script now.")

    app.run()
    stop_event.set()
    bridge.join(timeout=2.0)
    p.stop()