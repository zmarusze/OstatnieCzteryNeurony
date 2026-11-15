import gpype as gp
import numpy as np
import mido
import threading
import time

'''
Native PTP amplitude-based auditory artifact artifact detection system. 
'''
USE_REAL_DEVICE = True
DEVICE_SERIAL = "UN-2019.02.66"  

CHANNEL_LABELS = ["Fz", "C3", "Cz", "C4", "Pz", "PO7", "Oz", "PO8"]
N_EEG_CHANNELS = len(CHANNEL_LABELS) 

class ArtifactToMusicProcessor(gp.Sink):
    def __init__(self, window_seconds=2.0, s_rate=250):
        super().__init__()
        self.window_size = int(window_seconds * s_rate)
        self.buffer = None 
        
        try:
            self.midi_out = mido.open_output('Brainwave MIDI', virtual=True) #type:ignore
            print("\n" + "="*60)
            print(f"🎵 Created Virtual MIDI Port: '{self.midi_out.name}'")
            print("🎵 OPEN GARAGEBAND (or any music app). It will automatically play!")
            print("="*60 + "\n")
        except Exception as e:
            print(f"Warning: Could not create MIDI port: {e}")
            self.midi_out = None

        self.scale = [70, 80, 90, 100] 
        self.artifact_threshold = 60.0 

    def step(self, data):
        chunk = data["in"] 
        
        if self.buffer is None or self.buffer.shape[0] != chunk.shape[0]:
            self.buffer = np.empty((chunk.shape[0], 0))
            
        self.buffer = np.hstack((self.buffer, chunk))
        
        while self.buffer.shape[1] >= self.window_size:
            window = self.buffer[:, :self.window_size]
            self.buffer = self.buffer[:, self.window_size:]
            
            all_amps = np.ptp(window, axis=1) 
            num_ch = len(all_amps)
            
            front_blink = all_amps[0] if num_ch > 0 else 0
            left_jaw    = all_amps[1] if num_ch > 1 else 0
            right_jaw   = all_amps[3] if num_ch > 3 else 0
            neck_back   = all_amps[6] if num_ch > 6 else 0
            
            four_features = [front_blink, left_jaw, right_jaw, neck_back]
            self.trigger_music(four_features)

    def trigger_music(self, features):
        print(f"Blink: {features[0]:.0f} | L-Jaw: {features[1]:.0f} | R-Jaw: {features[2]:.0f} | Neck: {features[3]:.0f}")
        
        if self.midi_out is None:
            return

        notes_to_play = []
        for i, amp in enumerate(features):
            if amp > self.artifact_threshold:
                velocity = int(min(127, max(10, amp * 0.8))) 
                notes_to_play.append((self.scale[i], velocity))

        if notes_to_play:
            threading.Thread(target=self._play_chord, args=(notes_to_play,), daemon=True).start()

    def _play_chord(self, notes):
        for note, vel in notes:
            self.midi_out.send(mido.Message('note_on', note=note, velocity=vel)) #type:ignore
        
        time.sleep(0.5) 
        
        for note, vel in notes:
            self.midi_out.send(mido.Message('note_off', note=note)) #type:ignore


if __name__ == "__main__":
    app = gp.MainApp()
    p = gp.Pipeline()

    if USE_REAL_DEVICE: 
        device = gp.HybridBlack(serial=DEVICE_SERIAL, channel_selection=list(range(N_EEG_CHANNELS)), enable_oscar=True) 
    else:
        # Fake generator
        device = gp.Generator(signal_amplitude=20.0, noise_amplitude=5.0)
        
    source = gp.ChannelLabeler(labels=CHANNEL_LABELS)

    bandpass = gp.Bandpass(f_lo=1, f_hi=40) 
    notch50 = gp.Bandstop(f_lo=48, f_hi=52)

    music_processor = ArtifactToMusicProcessor(window_seconds=3.0, s_rate=250)
    scope = gp.TimeSeriesScope(name="Continuous EEG", time_window=10)
    
    p.connect(device, source)
    p.connect(source, bandpass)
    p.connect(bandpass, notch50)
    
    p.connect(notch50, scope)
    p.connect(notch50, music_processor)

    app.add_widget(scope)         

    print("Pipeline running! Listening for artifacts in 2-second windows...")
    
    p.start()
    app.run()
    p.stop()