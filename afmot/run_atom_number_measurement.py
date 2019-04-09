import numpy as np
import pickle

from time import sleep, time
from matplotlib import pyplot as plt
from devices import connect_to_device_service

from utils import counter_measurement, save_osci, arm_osci, N_BITS, LENGTH, \
    reset_fpga
from registers import Pitaya
from record_afmot_loading import start_acquisition_process


COOLING_PIN = 'gpio_n_do3_en'
CAM_TRIG_PIN = 'gpio_n_do4_en'
REPUMPING_PIN = 'gpio_n_do5_en'
FOLDER = '/media/depot/data/afmot/atom-numbers/'
FILENAME = 'test.pickle'
OLD_STYLE_DETECTION = False
DECIMATION = 5
RELATIVE_LENGTH = 1 / (2**DECIMATION)
MAX_STATE = 4
N_STATES = MAX_STATE + 1
ONE_ITERATION = 16384 * N_STATES
ITERATIONS_PER_SECOND = 7629.394531249999 / N_STATES
ONE_SECOND = ONE_ITERATION * ITERATIONS_PER_SECOND
ONE_MS = ONE_SECOND / 1000
MIN_CURRENT = 120
MAX_CURRENT = 150
CURRENT_STEP = .5
DETERMINE_CURRENTS = True

MOT_LOADING_TIME = int(30 * 2000)
END_DELAY = 5000 * ONE_SECOND


def analyze_tuning_time(data, start, stop):
    print('analyze', start, stop)
    plt.plot(data)
    plt.show()
    start_value = int(data[start])

    idx = start
    while idx < stop:
        idx += 1
        val = data[idx]

        if val != start_value:
            break

    return idx - start


def determine_tuning_time_balance(rp, cooling_light_duty_cycle):
    rp.record_now()
    addresses = list(range(int(rp.N_points * RELATIVE_LENGTH)))[::50]
    data = rp.read_error_signal(addresses=addresses)

    plt.plot(data)
    plt.show()

    mean_data = []
    for idx in range(int(np.floor(rp.N_points / 3))):
        mean_data.append(
            int(np.mean([data[3*idx], data[3*idx+1], data[3*idx+2]]))
        )

    repumping_end_idx = np.floor((1 - cooling_light_duty_cycle) * len(mean_data))
    cooling_start_idx = np.ceil((1 - cooling_light_duty_cycle) * len(mean_data))
    repumping_tuning_time, cooling_tuning_time = (
        # repumping
        analyze_tuning_time(mean_data, 0, repumping_end_idx),
        # cooling
        analyze_tuning_time(mean_data, cooling_start_idx, len(mean_data) - 1)
    )
    print('repumping', repumping_tuning_time, 'cooling', cooling_tuning_time)

    tuning_direction = -1 if repumping_tuning_time > cooling_light_duty_cycle \
        else 1

    print('tuning direction', tuning_direction)

    return tuning_direction


def program_old_style_detection(rp, init_ttl):
    pid_on = int(MOT_LOADING_TIME * ONE_ITERATION)
    pid_off = int(pid_on + END_DELAY)

    cooling_off = pid_on
    cooling_on_again = int(cooling_off + 2 * ONE_MS)

    repumping_on = cooling_off
    repumping_off = int(repumping_on + 2000 * ONE_SECOND)

    camera_trigger = int(cooling_off + 2 * ONE_MS)

    # TTL1: turn off cooling laser (it's inverse!)
    # do3_en (Kanal 4) ist cooling laser
    init_ttl(2, cooling_off, cooling_on_again)
    rp.pitaya.set(COOLING_PIN, states('ttl_ttl2_out'))

    # TTL2: turn on repumping laser
    # do5_en (Kanal 6) ist repumper!
    init_ttl(3, repumping_on, repumping_off)
    rp.pitaya.set(REPUMPING_PIN, states('ttl_ttl3_out'))

    # TTL4: trigger camera
    # do4_en (Kanal 5) ist cam trigger gpio_n_do4_en
    init_ttl(4, int(camera_trigger), int(camera_trigger + ONE_SECOND))
    cam_trig_ttl = states('ttl_ttl4_out')
    rp.pitaya.set(CAM_TRIG_PIN, cam_trig_ttl)

    return pid_on, pid_off, cam_trig_ttl


def do_old_style_detection(rp, force, null, cam_trig_ttl):
    # Trigger the cam on repeatedly for recording the AF-MOT loading curve
    start_time = time()
    target_time = MOT_LOADING_TIME / ITERATIONS_PER_SECOND

    # stop the continuous triggering 2 seconds before the AF-MOT atom number
    # is determined
    while time() - start_time < target_time - 5:
        rp.pitaya.set(CAM_TRIG_PIN, force)
        sleep(.05)
        rp.pitaya.set(CAM_TRIG_PIN, null)
        sleep(.05)

    # now, internal FPGA should control the camera trigger
    rp.pitaya.set(CAM_TRIG_PIN, cam_trig_ttl)

    print('waiting 5 seconds')
    sleep(10)

    # record MOT loading curve
    start_time = time()
    while time() - start_time < 30:
        rp.pitaya.set(CAM_TRIG_PIN, force)
        sleep(.05)
        rp.pitaya.set(CAM_TRIG_PIN, null)
        sleep(.05)

    print('waiting again')
    sleep(1.5)

    rp.pitaya.set(CAM_TRIG_PIN, force)
    sleep(.05)
    rp.pitaya.set(CAM_TRIG_PIN, null)
    sleep(.05)
    data = pickle.loads(pipe.recv())


def program_new_style_detection(rp, init_ttl):
    repumping_time = 2 * ONE_MS
    cooling_again_after = 3 * ONE_MS
    camera_trigger_after = 2 * ONE_MS

    pid_on = int(MOT_LOADING_TIME * ONE_ITERATION)
    pid_off = int(pid_on + END_DELAY)

    afmot_detection = pid_on
    mot_detection = int(afmot_detection + (MOT_LOADING_TIME * ONE_ITERATION))

    # AF-MOT detection

    cooling_off = afmot_detection
    cooling_on_again = int(afmot_detection + cooling_again_after)

    repumping_on = afmot_detection
    repumping_off = int(repumping_on + repumping_time)

    camera_trigger_1 = int(afmot_detection + camera_trigger_after)

    # MOT detection

    mot_start = afmot_detection + ONE_SECOND

    cooling_off_again = mot_detection
    cooling_last_time = int(mot_detection + cooling_again_after)

    repumping_on_again = int(mot_start)
    repumping_off_again = int(mot_detection + repumping_time)

    # this is after detection, just for checking how the MOT looks like
    final_repumping = int(mot_detection + ONE_SECOND)
    final_repumping_end = int(final_repumping + END_DELAY)

    camera_trigger_2 = int(mot_detection + camera_trigger_after)

    # TTL1: turn off cooling laser (it's inverse!)
    # do3_en (Kanal 4) ist cooling laser
    init_ttl(2, cooling_off, cooling_on_again)
    init_ttl(3, cooling_off_again, cooling_last_time)
    rp.pitaya.set(COOLING_PIN, states('ttl_ttl2_out', 'ttl_ttl3_out'))

    # TTL2: turn on repumping laser
    # do5_en (Kanal 6) ist repumper!
    init_ttl(4, repumping_on, repumping_off)
    init_ttl(7, repumping_on_again, repumping_off_again)
    init_ttl(8, final_repumping, final_repumping_end)
    rp.pitaya.set(REPUMPING_PIN, states(
        'ttl_ttl4_out', 'ttl_ttl7_out', 'ttl_ttl8_out'
    ))

    # TTL4: trigger camera
    # do4_en (Kanal 5) ist cam trigger gpio_n_do4_en
    init_ttl(5, int(camera_trigger_1), int(camera_trigger_1 + ONE_SECOND))
    init_ttl(6, int(camera_trigger_2), int(camera_trigger_2 + ONE_SECOND))
    cam_trig_ttl = states('ttl_ttl5_out', 'ttl_ttl6_out')
    rp.pitaya.set(CAM_TRIG_PIN, cam_trig_ttl)

    return pid_on, pid_off


def new_style_record_background(rp, force, null):
    # record one frame for background
    rp.pitaya.set(CAM_TRIG_PIN, force)
    sleep(.05)
    rp.pitaya.set(CAM_TRIG_PIN, null)


def do_new_style_detection(rp, cam_trig_ttl, pipe):
    sleep(1)
    # now, internal FPGA should control the camera trigger
    rp.pitaya.set(CAM_TRIG_PIN, cam_trig_ttl)

    # everything is controlled by FPGA, we don't have to do anything
    data = pickle.loads(pipe.recv())
    return data


def load_old_data():
    class OverrideData(Exception):
        pass

    try:
        with open(FOLDER + FILENAME, 'rb') as f:
            all_data = pickle.load(f)

        while True:
            append_data = input('file already exists. Append (a) or override (o) data?')
            if append_data not in ('a', 'o'):
                continue
            if append_data == 'o':
                raise OverrideData()
            else:
                break

    except OverrideData:
        all_data = {}

    return all_data


if __name__ == '__main__':
    if DETERMINE_CURRENTS:
        _ilx = connect_to_device_service('IP', 'ilx')
        def set_current(current):
            assert current >= MIN_CURRENT
            assert current <= MAX_CURRENT
            print('set laser current', current)
            _ilx.set_laser_current(current)
            sleep(1)

        last_current = float(MAX_CURRENT)
        set_current(last_current)
        currents = []

        for cooling_duty_cycle in [.1, .2, .3, .4, .5, .6, .7, .8, .9]:
            print('----         DUTY CYCLE %.2f        ----' % cooling_duty_cycle)
            print('currents', currents)

            did_turn = False
            current_before = last_current

            while True:
                reset_fpga('rp-f012ba.local', 'root', 'zeilinger')
                rp = Pitaya('rp-f012ba.local', user='root', password='zeilinger')
                rp.connect()

                rp.init(
                    decimation=DECIMATION,
                    N_zones=2,
                    relative_length=RELATIVE_LENGTH,
                    zone_edges=[1-cooling_duty_cycle, 1, None],
                    target_frequencies=[6000, 150, None, None],
                    curvature_filtering_starts=[15, 15, None, None]
                    #curvature_filtering_starts=[16383, 16383, 16383, 16383]
                )

                sleep(10)
                tuning_direction = determine_tuning_time_balance(rp, cooling_duty_cycle)

                if tuning_direction == -1:
                    if did_turn:
                        last_current -= float(CURRENT_STEP) / 8
                        set_current(last_current)
                        currents.append(last_current)
                        break

                    last_current -= float(CURRENT_STEP)

                    if last_current < MIN_CURRENT:
                        last_current = MIN_CURRENT
                        set_current(last_current)
                        currents.append(last_current)
                        break
                    else:
                        set_current(last_current)
                        continue
                else:
                    if not did_turn:
                        did_turn = True

                    if last_current < current_before:
                        last_current += float(CURRENT_STEP) / 4
                        set_current(last_current)
                        continue
                    else:
                        currents.append(last_current)
                        break

    else:
        all_data = load_old_data()

        #    for duty_cycle in [.4, .5, .6, .7, .8, .85, .9, .95]:
        for cooling_duty_cycle in [.1, .2, .3, .4, .5, .6, .7, .8, .9]:
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
                    N_zones=2,
                    relative_length=RELATIVE_LENGTH,
                    zone_edges=[1-cooling_duty_cycle, 1, None],
                    target_frequencies=[6000, 150, None, None],
                    curvature_filtering_starts=[15, 15, None, None]
                    #curvature_filtering_starts=[16383, 16383, 16383, 16383]
                )

                rp.pitaya.set('control_loop_sequence_player_stop_zone', 1)

                if OLD_STYLE_DETECTION:
                    pid_on, pid_off, cam_trig_ttl = program_old_style_detection(rp, init_ttl)
                else:
                    pid_on, pid_off = program_new_style_detection(rp, init_ttl)

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

                # TTL5: announcer
                # do2 (Kanal 3) ist announcer
                #init_ttl(1, int(pid_on - ONE_MS), int(pid_on - ONE_MS + ONE_SECOND))
                #rp.pitaya.set('gpio_n_do2_en', states('ttl_ttl1_out'))

                rp.enable_channel_b_pid(True, p=200, i=25, d=0, reset=False)

                actual_length = int(LENGTH / (2**DECIMATION))
                rp.set_max_state(4)

                rp.set_algorithm(0)
                rp.set_enabled(0)
                rp.pitaya.set('control_loop_sequence_player_start_clocks', 0)

                #first_feed_forward = np.array([0] * actual_length)
                #rp.set_feed_forward(first_feed_forward)
                rp.sync()

                # ---------------------------- START ALGORITHM ----------------------------
                if iteration == 0:
                    input('ready?')

                acquiry_process, pipe = start_acquisition_process(old_style=OLD_STYLE_DETECTION)

                if not OLD_STYLE_DETECTION:
                    new_style_record_background(rp, force, null)

                rp.set_enabled(1)
                rp.set_algorithm(1)
                rp.pitaya.set('control_loop_sequence_player_start_clocks', 1)

                if OLD_STYLE_DETECTION:
                    do_old_style_detection(rp, force, null, cam_trig_ttl)
                else:
                    data = do_new_style_detection(rp, cam_trig_ttl, pipe)

                iteration_data = all_data.get(cooling_duty_cycle, [])
                iteration_data.append(data)
                all_data[cooling_duty_cycle] = iteration_data

                with open(FOLDER + FILENAME, 'wb') as f:
                    pickle.dump(all_data, f)