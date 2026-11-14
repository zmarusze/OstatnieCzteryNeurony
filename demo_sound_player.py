from pathlib import Path
import pygame, sys, time

violin = {0: "violin-c4.wav", 1: "violin-d4.wav", 2: "violin-e4.wav", 3: "violin-f4.wav", 4: "violin-g4.wav", 5: "violin-a4.wav", 6: "violin-b4.wav", 7: "violin-c5.wav"}
piano = {0: "piano-c4.wav", 1: "piano-d4.wav", 2: "piano-e4.wav", 3: "piano-f4.wav", 4: "piano-g4.wav", 5: "piano-a4.wav", 6: "piano-b4.wav", 7: "piano-c5.wav"}

def play_sound(instrument, note):
    pygame.mixer.init()
    pygame.mixer.music.load(str(Path(__file__).resolve().parent / "sound_files" / instrument[note]))
    pygame.mixer.music.play(loops=0)
    while pygame.mixer.music.get_busy():
        pygame.time.wait(100)
intrument = violin
note = 0
while True:
    play_sound(intrument, note)
    note += 1
    if note > 7:
        note = 0
        if intrument == violin:
            intrument = piano
        else:
            intrument = violin