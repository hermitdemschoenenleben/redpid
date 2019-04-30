import sys
sys.path.append('/home/bebec/Desktop/Ben')

import numpy as np
import pickle

from time import sleep, time
from matplotlib import pyplot as plt
from devices import connect_to_device_service

from utils import counter_measurement, save_osci, arm_osci, N_BITS, LENGTH, \
    reset_fpga, MAX_STATE, N_STATES, ONE_ITERATION, ITERATIONS_PER_SECOND, \
    ONE_SECOND, ONE_MS, COOLING_PIN, CAM_TRIG_PIN, REPUMPING_PIN, END_DELAY, \
    load_old_data, BASE_FREQ
from registers import Pitaya
from record_afmot_loading import start_acquisition_process, program_old_style_detection, \
    do_old_style_detection, program_new_style_detection, do_new_style_detection, \
    new_style_record_background


FOLDER = '/media/depot/data/afmot/atom-numbers/'
FILENAME = 'test.pickle'
OLD_STYLE_DETECTION = False
LENGTH_FACTOR = 4
DECIMATION = 5
RELATIVE_LENGTH = 1 / (2**DECIMATION) * LENGTH_FACTOR
CURRENT_BEGIN = 130
MIN_CURRENT = 121.5
MAX_CURRENT = 150
CURRENT_STEP = 2
DETERMINE_CURRENTS = False
MOT_LOADING_TIME = int(30 * (BASE_FREQ / LENGTH_FACTOR) / N_STATES)


if __name__ == '__main__':
    cooling_duty_cycles = [.875]
    #    for duty_cycle in [.4, .5, .6, .7, .8, .85, .9, .95]:
    for cooling_duty_cycle in cooling_duty_cycles:
        print('----         DUTY CYCLE %.2f        ----' % cooling_duty_cycle)

        for iteration in range(10):
            print('----         ITERATION %d        ----' % iteration)

            reset_fpga('rp-f012ba.local', 'root', 'zeilinger')
            rp = Pitaya('rp-f012ba.local', user='root', password='zeilinger')
            rp.connect()

            states = lambda *names: rp.pitaya.states(*names)
            force = states('force')
            null = states()

            _initialized_ttl = []
            def init_ttl(idx, start, stop):
                assert idx not in _initialized_ttl, 'ttl already initialized'
                _initialized_ttl.append(idx)
                rp.pitaya.set('ttl_ttl%d_start' % idx, start)
                rp.pitaya.set('ttl_ttl%d_end' % idx,  stop)

            rp.init(
                decimation=DECIMATION,
                N_zones=2,
                relative_length=RELATIVE_LENGTH,
                zone_edges=[1-cooling_duty_cycle, 1, None],
                target_frequencies=[6000, 150, None, None],
                curvature_filtering_starts=[15, 15, None, None]
                #curvature_filtering_starts=[16383, 16383, 16383, 16383]
            )

            rp.pitaya.set('control_loop_sequence_player_stop_zone', 1)

            if OLD_STYLE_DETECTION:
                pid_on, pid_off, cam_trig_ttl = program_old_style_detection(
                    rp, init_ttl, MOT_LOADING_TIME, states
                )
            else:
                pid_on, pid_off, cam_trig_ttl, nanospeed_ttl = program_new_style_detection(
                    rp, init_ttl, MOT_LOADING_TIME, states,
                    LENGTH_FACTOR, absorption_detection=True
                )

            rp.pitaya.set(
                'control_loop_sequence_player_stop_algorithm_after',
                MOT_LOADING_TIME-1
            )
            rp.pitaya.set(
                'control_loop_sequence_player_stop_after',
                MOT_LOADING_TIME-1
            )

            # TTL0: enable PID
            init_ttl(0, pid_on, pid_off)
            rp.pitaya.set('control_loop_pid_enable_en', states('ttl_ttl0_out'))

            rp.enable_channel_b_pid(True, p=200, i=25, d=0, reset=False)

            rp.set_max_state(MAX_STATE)
            rp.pitaya.set('control_loop_sequence_player_step_size', 8)
            rp.pitaya.set('control_loop_sequence_player_decrease_step_size_after', 1000)

            rp.set_algorithm(0)
            rp.set_enabled(0)
            rp.pitaya.set('control_loop_sequence_player_start_clocks', 0)

            #actual_length = int(LENGTH  * RELATIVE_LENGTH)
            #first_feed_forward = np.array([0] * actual_length)
            #rp.set_feed_forward(first_feed_forward)
            rp.sync()

            # ---------------------------- START ALGORITHM ----------------------------
            #if iteration == 0:
            #    input('ready?')

            acquiry_process, pipe = start_acquisition_process(old_style=OLD_STYLE_DETECTION)

            if not OLD_STYLE_DETECTION:
                new_style_record_background(rp, force, null)

            rp.set_enabled(1)
            rp.set_algorithm(1)
            rp.pitaya.set('control_loop_sequence_player_start_clocks', 1)

            if OLD_STYLE_DETECTION:
                data = do_old_style_detection(rp, force, null, cam_trig_ttl, MOT_LOADING_TIME)
            else:
                data = do_new_style_detection(rp, cam_trig_ttl, nanospeed_ttl, pipe)
            