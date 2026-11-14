#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime

from psychopy import visual, core, event
from pylsl import StreamInfo, StreamOutlet, local_clock
import csv


TARGET_HAND = 'right'  
NUM_TRIALS = 20

assert TARGET_HAND in ('right', 'left')


info = StreamInfo(name='PsychoPyMarkers', type='Markers', channel_count=1, nominal_srate=0, channel_format='int32', source_id='mi_markers') # type: ignore
outlet = StreamOutlet(info)


stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
log_file = open(f'outputs/marker_timestamps_{TARGET_HAND}_{stamp}.csv', 'w', newline='')
log_writer = csv.writer(log_file)
log_writer.writerow(['Timestamp', 'MarkerCode', 'Label'])


def send(marker_code, label):
    """Pushes an integer marker to LSL and logs it."""
    ts = local_clock()
    outlet.push_sample([marker_code], ts)
    print(f"[{ts:.3f}] sent: {marker_code} ({label})")
    log_writer.writerow([ts, marker_code, label])
    log_file.flush()  



win = visual.Window([1280, 720], monitor='testMonitor', units='norm', color=[-1, -1, -1])

txt_welcome = visual.TextStim(win, height=0.065, text=
    f"Welcome to the Motor Imagery Experiment\n\n"
    f"Focus ONLY on the {TARGET_HAND.upper()} hand.\n\n"
    "Press [SPACE] to begin, or [ESCAPE] to quit.")
txt_end = visual.TextStim(win, height=0.08, text="Experiment complete.")

fixation = visual.TextStim(win, text='+', height=0.15)
cue = visual.TextStim(win, text='<' if TARGET_HAND == 'left' else '>', height=0.3, color='#FFD700')



def quit_experiment():
    log_file.close()
    win.close()
    core.quit()


def check_quit():
    if 'escape' in event.getKeys(keyList=['escape']):
        quit_experiment()


def wait_for_key():
    keys = event.waitKeys(keyList=['space', 'escape'])
    # waitKeys already consumed the key, so check_quit() would never see it
    if 'escape' in keys:  # type: ignore
        quit_experiment()



def run_trial():
    clock = core.Clock()
    step = 0
    # MI integer code (2 for Right, 3 for Left)
    mi_code = 2 if TARGET_HAND == 'right' else 3

    while clock.getTime() < 8.0:
        t = clock.getTime()

        # Phase 0: Fixation (0 - 2s) -> REST (Code: 1)
        if t < 2.0:
            if step == 0:
                win.callOnFlip(send, 1, 'rest')
                step = 1
            fixation.draw()
        # Phase 1: Cue & MI starts (2 - 3s) -> MI (Code: 2 or 3)
        elif t < 3.0:
            if step <= 1:  # <= so the marker is still sent if a frame skip jumps past phase 0
                win.callOnFlip(send, mi_code, f'{TARGET_HAND}_MI')
                step = 2
            cue.draw()
        # Phase 2: MI continues (3 - 6s)
        elif t < 6.0:
            fixation.draw()
        # Phase 3: Break (6 - 8s) -> REST (Code: 1), blank screen
        else:
            if step == 2:
                win.callOnFlip(send, 1, 'rest')
                step = 3
        win.flip()
        check_quit()



txt_welcome.draw()
win.flip()
wait_for_key()

for trial_num in range(NUM_TRIALS):
    run_trial()

txt_end.draw()
win.flip()
core.wait(2.0)

quit_experiment()