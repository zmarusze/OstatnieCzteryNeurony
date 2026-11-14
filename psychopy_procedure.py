#!/usr/bin/env python
# -*- coding: utf-8 -*-

import random
from datetime import datetime

from psychopy import visual, core, event
from pylsl import StreamInfo, StreamOutlet, local_clock
import csv



TRIALS_PER_CLASS = 10  #

trial_sequence = (['left'] * TRIALS_PER_CLASS + ['right'] * TRIALS_PER_CLASS + ['rest'] * TRIALS_PER_CLASS)
random.shuffle(trial_sequence)

info = StreamInfo(name='PsychoPyMarkers', type='Markers', channel_count=1, nominal_srate=0, channel_format='int32', source_id='mi_markers')  # type: ignore
outlet = StreamOutlet(info)


stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
log_file = open(f'outputs/marker_timestamps_3class_MI_{stamp}.csv', 'w', newline='')
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
    "Welcome to the 3-Class Motor Imagery Experiment\n\n"
    "When you see '+', stay still and prepare.\n"
    "When you see '<', imagine moving your LEFT hand.\n"
    "When you see '>', imagine moving your RIGHT hand.\n"
    "When you see 'O', fully RELAX and clear your mind.\n\n"
    "Press [SPACE] to begin, or [ESCAPE] to quit.")
txt_end = visual.TextStim(win, height=0.08, text="Experiment complete.")

fixation = visual.TextStim(win, text='+', height=0.15)
cue = visual.TextStim(win, text='', height=0.3, color='#FFD700')


def quit_experiment():
    log_file.close()
    win.close()
    core.quit()

def check_quit():
    if 'escape' in event.getKeys(keyList=['escape']):
        quit_experiment()

def wait_for_key():
    keys = event.waitKeys(keyList=['space', 'escape'])
    if 'escape' in keys:  # type: ignore
        quit_experiment()


def run_trial(trial_type):
    clock = core.Clock()
    step = 0
    
    if trial_type == 'right':
        mi_code = 2
        cue.text = '>'
    elif trial_type == 'left':
        mi_code = 3
        cue.text = '<'
    else:  # rest
        mi_code = 1
        cue.text = 'O'
    
    break_duration = random.uniform(1.5, 2.5)
    total_trial_time = 6.0 + break_duration

    while clock.getTime() < total_trial_time:
        t = clock.getTime()


        if t < 2.0:
            if step == 0:
                win.callOnFlip(send, 10, 'fixation_prep')
                step = 1
            fixation.draw()
            
        # Phase 1: Cue presentation & Task starts (2.0 - 3.25s) -> CUE (Code: 1, 2, or 3)
        elif t < 3.25:
            if step <= 1:
                win.callOnFlip(send, mi_code, f'{trial_type}_cue')
                step = 2
            cue.draw()
            
        # Phase 2: Task continues without cue (3.25 - 6.0s)
        elif t < 6.0:
            fixation.draw()
            
        else:
            if step == 2:
                win.callOnFlip(send, 99, 'break_blank')
                step = 3
                
        win.flip()
        check_quit()


txt_welcome.draw()
win.flip()
wait_for_key()

for i, current_trial in enumerate(trial_sequence):
    print(f"\n--- Starting Trial {i+1}/{len(trial_sequence)}: {current_trial.upper()} ---")
    run_trial(current_trial)

txt_end.draw()
win.flip()
core.wait(2.0)

quit_experiment()