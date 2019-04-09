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


#FOLDER = '/media/depot/data/afmot/atom-numbers/'
#FILENAME = 'test.pickle'
#OLD_STYLE_DETECTION = False
TARGET_FREQUENCY = 1e3
TUNING_TIME = 1e-6


DECIMATION = 0
RELATIVE_LENGTH = 1
current_freq = lambda: BASE_FREQ / (2**DECIMATION) / RELATIVE_LENGTH
# determine decimation
while current_freq() > TARGET_FREQUENCY:
    DECIMATION += 1
# determine relative length
RELATIVE_LENGTH = current_freq() / TARGET_FREQUENCY
RELATIVE_TUNING_TIME = TUNING_TIME * TARGET_FREQUENCY

MOT_LOADING_TIME = int(30 * 2000)
OLD_STYLE_DETECTION = False


if __name__ == '__main__':
        all_data = load_old_data()
        cooling_duty_cycles = [.05, .1, .15, .2, .25, .3, .35, .4, .45, .5, .55, .6, .65, .7, .75, .8, .85, .9, .95]
        for cooling_duty_cycle in cooling_duty_cycles:
            print('----         DUTY CYCLE %.2f        ----' % cooling_duty_cycle)

            for iteration in range(2):
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
                    N_zones=4,
                    relative_length=RELATIVE_LENGTH,
                    zone_edges=[
                        1 - cooling_duty_cycle - RELATIVE_TUNING_TIME,
                        1 - cooling_duty_cycle,
                        1 - RELATIVE_TUNING_TIME
                    ],
                    #curvature_filtering_starts=[16383, 16383, 16383, 16383]
                )

                rp.pitaya.set('gpio_n_do0_en', states('control_loop_clock_0'))
                rp.pitaya.set('gpio_n_do1_en', states('control_loop_clock_2'))

                rp.pitaya.set('control_loop_sequence_player_stop_zone', 1)

                if OLD_STYLE_DETECTION:
                    pid_on, pid_off, cam_trig_ttl = program_old_style_detection(
                        rp, init_ttl, MOT_LOADING_TIME, states
                    )
                else:
                    pid_on, pid_off, cam_trig_ttl = program_new_style_detection(
                        rp, init_ttl, MOT_LOADING_TIME, states
                    )

                rp.pitaya.set(
                    'control_loop_sequence_player_stop_algorithm_after',
                    MOT_LOADING_TIME-1
                )
                rp.pitaya.set(
                    'control_loop_sequence_player_stop_after',
                    MOT_LOADING_TIME-1
                )

                # TTL5: announcer
                # do2 (Kanal 3) ist announcer
                init_ttl(1, int(pid_on - ONE_MS), int(pid_on - ONE_MS + ONE_SECOND))
                rp.pitaya.set('gpio_n_do2_en', states('ttl_ttl1_out'))

                rp.set_max_state(MAX_STATE)
                rp.set_algorithm(0)
                rp.set_enabled(0)
                rp.pitaya.set('control_loop_sequence_player_start_clocks', 0)

                # ---------------------------- START ALGORITHM ----------------------------
                acquiry_process, pipe = start_acquisition_process(old_style=OLD_STYLE_DETECTION)

                if not OLD_STYLE_DETECTION:
                    new_style_record_background(rp, force, null)

                rp.set_enabled(1)
                rp.set_algorithm(1)
                rp.pitaya.set('control_loop_sequence_player_start_clocks', 1)

                if OLD_STYLE_DETECTION:
                    do_old_style_detection(rp, force, null, cam_trig_ttl, MOT_LOADING_TIME)
                else:
                    data = do_new_style_detection(rp, cam_trig_ttl, pipe)

                iteration_data = all_data.get(cooling_duty_cycle, [])
                iteration_data.append(data)
                all_data[cooling_duty_cycle] = iteration_data

                with open(FOLDER + FILENAME, 'wb') as f:
                    pickle.dump(all_data, f)