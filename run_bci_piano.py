import queue
import pygame
import gpype as gp
from Pianino import DashboardApp
from live_playing import MuPianoNeurofeedback 
from constants import DEVICE_SERIAL, CHANNEL_LABELS, N_EEG_CHANNELS


def main():
    print("Initializing Pygame Piano UI...")
    piano_app = DashboardApp()
    bin_queue = queue.Queue()

    def handle_bin_change(bin_number):
        """
        This callback is fired by the gpype background thread every time 
        the user's brainwaves transition to a new mu-rhythm bin.
        We push it to the queue so Pygame can read it safely.
        """
        bin_queue.put(bin_number)

    print("Connecting to EEG Device...")
    p = gp.Pipeline()

    device = gp.HybridBlack(serial=DEVICE_SERIAL,
                            channel_selection=list(range(N_EEG_CHANNELS)),
                            test_signal=False,
                            enable_oscar=True)
    
    source = gp.ChannelLabeler(labels=CHANNEL_LABELS)
    notch50 = gp.Bandstop(f_lo=48, f_hi=52)
    neuro_node = MuPianoNeurofeedback(channel_labels=CHANNEL_LABELS,
                                      on_bin_change=handle_bin_change,
                                      smoothing_steps=3)

    p.connect(device, source)
    p.connect(source, notch50)
    p.connect(notch50, neuro_node)

    p.start()
    print("BCI Pipeline running! Ready to play.")
    clock = pygame.time.Clock()
    running = True

    while running:
        new_bin = None
        while not bin_queue.empty():
            new_bin = bin_queue.get() 

        running = piano_app.update(number=new_bin, duration_ms=900)
        
        clock.tick(60)
    print("Closing application...")
    p.stop()
    pygame.quit()

if __name__ == "__main__":
    main()

