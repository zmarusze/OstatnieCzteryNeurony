import threading
import gpype as gp
from utils import pump_markers

USE_REAL_DEVICE = False  
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

    bandpass = gp.Bandpass(f_lo=8, f_hi=13, name='miu') 
    notch50 = gp.Bandstop(f_lo=48, f_hi=52)

    # ---------------------------------------------------------
    # NEW LOGIC: Trigger, Baseline, and Collector for Epoching
    # ---------------------------------------------------------
    # Epoching -0.2s to 0.7s. Target = 2 (Right MI). 
    # Change target to 1, 3, or a list like [1,2,3] depending on what you want to extract.
    trigger = gp.Trigger(time_pre=0.1, time_post=4, target=[1,2,3]) #type:ignore
    baseline = gp.Baseline()
    collector = gp.Collector()
    # ---------------------------------------------------------

    merge_prep = gp.Router(input_channels={"eeg": gp.Router.ALL, "mrk": gp.Router.ALL})
    merge_vis = gp.Router(input_channels={"eeg": gp.Router.ALL, "mrk": gp.Router.ALL})
    merge_power = gp.Router(input_channels={"eeg": gp.Router.ALL, "mrk": gp.Router.ALL})

    scope = gp.TimeSeriesScope(
        name="Raw EEG",
        time_window=10,
        markers=[gp.TimeSeriesScope.Markers(color=color, label=label, channel=N_EEG_CHANNELS, value=code) for code, (label, color) in MARKER_STYLE.items()])
    
    eeg_writer = gp.EDFWriter(file_name=f"outputs/{FILE_PREFIX}_eeg.edf")

    motor_cortex = gp.ChannelSelector(labels=["C3", "C4"])
    fft = gp.FFT(window_size=250, window_function='hamming') 
    mu_power = gp.BandPower(bands=[[8.0, 13.0]])
    psd_scope = gp.SpectrumScope(num_averages=6)
    power_scope = gp.TimeSeriesScope(title="Live 8-13 Hz Power (C3, C4)", time_window=60, 
                                     markers=[gp.TimeSeriesScope.Markers(color=color, label=label, channel=2, value=code) for code, (label, color) in MARKER_STYLE.items()])
    
    power_writer = gp.EDFWriter(file_name=f"outputs/{FILE_PREFIX}_mu_power_features.edf", add_timestamp=False)

    p.connect(source, bandpass)
    p.connect(bandpass, notch50)
    
    # ---------------------------------------------------------
    # NEW LOGIC: Connect the epoching components
    # ---------------------------------------------------------
    # 1. Connect clean EEG (from notch filter) to the trigger's signal input
    p.connect(notch50, trigger)
    # 2. Connect the marker node to the trigger's dedicated trigger port
    p.connect(marker, trigger[gp.Trigger.PORT_TRIGGER])
    # 3. Connect the trigger through the baseline correction and into the collector
    p.connect(trigger, baseline)
    p.connect(baseline, collector)
    # ---------------------------------------------------------

    p.connect(notch50, merge_vis["eeg"])
    p.connect(marker, merge_vis["mrk"])
    p.connect(merge_vis, scope)

    p.connect(notch50, merge_prep["eeg"]) 
    p.connect(marker, merge_prep["mrk"])
    p.connect(merge_prep, eeg_writer)

    p.connect(notch50, motor_cortex)
    p.connect(motor_cortex, fft)
    p.connect(fft, psd_scope)
    p.connect(fft, mu_power)
    p.connect(mu_power, merge_power["eeg"])
    p.connect(marker, merge_power["mrk"])
    p.connect(merge_power, power_scope)
    p.connect(merge_power, power_writer)


    # 2. Add a NEW scope just for epochs
    epoch_scope = gp.TriggerScope(title="Epoched EEG (All MI)")
    
    # Connect baseline to the new epoch scope
    p.connect(baseline, epoch_scope)
    
    # Don't forget to add the new widget to the app!

    app.add_widget(scope)         
    app.add_widget(epoch_scope)
    app.add_widget(psd_scope)     
    app.add_widget(power_scope)   

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