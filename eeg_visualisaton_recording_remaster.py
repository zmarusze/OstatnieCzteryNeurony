import threading
import gpype as gp
from utils import pump_markers
from mu_processing import MuProcessor
print("załadowane")

USE_REAL_DEVICE = True
print("połączone")
DEVICE_SERIAL = "UN-2024.12.02"  
print(DEVICE_SERIAL)
TEST_SIGNAL = False 

CHANNEL_LABELS = ["Fz", "C3", "Cz", "C4", "Pz", "PO7", "Oz", "PO8"]
N_EEG_CHANNELS = len(CHANNEL_LABELS) 
FILE_PREFIX = "bci_unicorn" if USE_REAL_DEVICE else "bci_synthetic"

MARKER_STYLE = { 1: ("rest", "#DA0EA3"), 2: ("right MI", "#FFD700"), 3: ("left MI", "#00BFFF")}

if __name__ == "__main__":
    app = gp.MainApp()
    p = gp.Pipeline()
    p.event_margin_ms = 100.0

    if USE_REAL_DEVICE: 
        device = gp.HybridBlack(serial=DEVICE_SERIAL,
                                channel_selection=list(range(N_EEG_CHANNELS)),
                                test_signal=TEST_SIGNAL,
                                enable_oscar=True) 
    else:
        device = gp.Generator(signal_amplitude=20.0, noise_amplitude=5.0)
        
    source = gp.ChannelLabeler(labels=CHANNEL_LABELS)
    p.connect(device, source)
    marker = gp.Marker()

    bandpass = gp.Bandpass(f_lo=1, f_hi=40) 
    notch50 = gp.Bandstop(f_lo=48, f_hi=52)

    trigger = gp.Trigger(time_pre=0.1, time_post=4, target=[1,2,3])
    baseline = gp.Baseline()
    collector = gp.Collector()
    print("załadowane do collectora")
    mu_processor = MuProcessor(
        channel_labels=CHANNEL_LABELS,
        pre_trigger_seconds=0.1,
        window_seconds=4.0,
        calibration_seconds=160.0
    )
    print("załadowane do mu_processor")
   
    epoch_scope = gp.TriggerScope(
        title="Epoched EEG (All Conditions)"
    )
    # ---------------------------------------------------------

    merge_prep = gp.Router(input_channels={"eeg": gp.Router.ALL, "mrk": gp.Router.ALL})
    merge_vis = gp.Router(input_channels={"eeg": gp.Router.ALL, "mrk": gp.Router.ALL})
    merge_power = gp.Router(input_channels={"eeg": gp.Router.ALL, "mrk": gp.Router.ALL})

    scope = gp.TimeSeriesScope(
        name="Raw EEG",
        time_window=10,
        markers=[gp.TimeSeriesScope.Markers(color=color, label=label, channel=N_EEG_CHANNELS, value=code) for code, (label, color) in MARKER_STYLE.items()])
    
    eeg_writer = gp.EDFWriter(file_name=f"outputs/{FILE_PREFIX}_eeg.edf")
    print("załadowane do connections")
    p.connect(source, bandpass)
    print("załadowane connection do bandpass")
    p.connect(bandpass, notch50)
    print("załadowane connection do notch50")
    p.connect(notch50, trigger)
    print("załadowane connection do trigger")
    p.connect(marker, trigger[gp.Trigger.PORT_TRIGGER])
    print("załadowane connection do trigger marker")
    p.connect(trigger, baseline)
    print("załadowane connection przed mu_processor")
    p.connect(baseline, mu_processor)
    print("załadowane connection do mu_processor")
    p.connect(baseline, epoch_scope)

    p.connect(notch50, merge_vis["eeg"])
    p.connect(marker, merge_vis["mrk"])
    p.connect(merge_vis, scope)
    print("po scopeach")

    p.connect(notch50, merge_prep["eeg"]) 
    p.connect(marker, merge_prep["mrk"])
    p.connect(merge_prep, eeg_writer)

    epoch_scope = gp.TriggerScope(title="Epoched EEG (All MI)")
    p.connect(baseline, epoch_scope)
    print("przed widgetami")
    app.add_widget(scope)         
    app.add_widget(epoch_scope)
    print("po widgetach")


    p.start()
    stop_event = threading.Event()
    bridge = threading.Thread(target=pump_markers, 
                              args=(marker, stop_event, "outputs/received_markers.csv"), 
                              daemon=True)
    bridge.start()
    
    print("Pipeline running! Start your PsychoPy script now.")

    app.run()
    
    stop_event.set()
    bridge.join(timeout=2.0)
    p.stop()

    # ---------------------------------------------------------
    # NEW LOGIC: Access your epochs after the pipeline stops
    # ---------------------------------------------------------
    if collector.result is not None:
        epochs = collector.result.data  
        print(f"\nExperiment finished! Collected epochs shape: {epochs.shape}")
        print("(Time samples, Channels, Trials)")
    else:
        print("\nNo epochs were collected (did the specified target marker arrive?)")
