import numpy as np
import pickle
import subprocess

from time import sleep, time
from matplotlib import pyplot as plt

from utils import counter_measurement, save_osci, arm_osci, N_BITS, LENGTH
from registers import Pitaya

from record_afmot_loading import record_afmot_loading

from multiprocessing import Process, Pipe

FOLDER = '/media/depot/data/afmot/atom-numbers/'

def reset_fpga():
    ssh_cmd='sshpass -p zeilinger ssh root@rp-f012ba.local'
    reset_cmd="/bin/bash /reset.sh"
    p = subprocess.Popen(' '.join([ssh_cmd, reset_cmd]).split(),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
    p.wait()


if __name__ == '__main__':
    """rp = Pitaya('rp-f012ba.local', user='root', password='zeilinger')
    rp.connect()
    force = rp.pitaya.states('force')
    null = rp.pitaya.states()
    cooling_pin = 'gpio_n_do3_en'
    rp.pitaya.set(cooling_pin, null)
    asd"""
    FILENAME = 'test.pickle'

    all_data = []

    for duty_cycle in [.4, .5, .6, .7, .8, .85, .9, .95]:
        print('----         DUTY CYCLE %.2f        ----' % duty_cycle)

        iteration_data = []
        all_data.append(iteration_data)

        for iteration in range(3):
            print('----         ITERATION %d        ----' % iteration)

            reset_fpga()

            rp = Pitaya('rp-f012ba.local', user='root', password='zeilinger')
            rp.connect()

            force = rp.pitaya.states('force')
            null = rp.pitaya.states()

            decimation = 5
            max_state = 4
            N_states = max_state + 1

            #for cooling_duty_cycle in reversed([0.4, 0.6, 0.8]):
            #cooling_duty_cycle = .2
            cooling_duty_cycle = duty_cycle
            #print('duty cycle', cooling_duty_cycle)

            rp.init(
                decimation=decimation,
                N_zones=2,
                relative_length=1 / (2**decimation),
                zone_edges=[1-cooling_duty_cycle, 1, None],
                target_frequencies=[6000, 150, None, None],
                curvature_filtering_starts=[15, 15, None, None]
                #curvature_filtering_starts=[16383, 16383, 16383, 16383]
            )


            cooling_pin = 'gpio_n_do3_en'
            cam_trig_pin = 'gpio_n_do4_en'
            repumping_pin = 'gpio_n_do5_en'

            rp.pitaya.set('control_loop_sequence_player_stop_zone', 1)

            one_iteration = 16384 * N_states
            iterations_per_second = 7629.394531249999 / N_states
            one_second = one_iteration * iterations_per_second
            one_ms = one_second / 1000

            delay = int(30 * 2000)
            end_delay = 2000 * one_second

            pid_on = int(delay * one_iteration)
            pid_off = int(pid_on + 200 * one_second + end_delay)
            cooling_on = 0
            cooling_off = pid_on
            cooling_on_again = int(cooling_off + 2 * one_ms)
            cooling_off_again = int(cooling_on_again + 2000 * one_second)
            repumping_on = cooling_off
            repumping_off = int(repumping_on + 2000 * one_second)
            camera_trigger = int(cooling_off + 2 * one_ms)

            rp.pitaya.set('control_loop_sequence_player_stop_algorithm_after', delay-1)
            rp.pitaya.set('control_loop_sequence_player_stop_after', delay-1)

            # TTL0: enable PID
            rp.pitaya.set('ttl_ttl0_start', pid_on)
            rp.pitaya.set('ttl_ttl0_end', pid_off)

            rp.pitaya.set('control_loop_pid_enable_en', rp.pitaya.states('ttl_ttl0_out'))

            # ALT: TTL1+TTL2: turn on and off cooling laser
            # NEU: TTL1: turn off cooling laser (it's inverse!)
            # do3_en (Kanal 4) ist cooling laser
            #rp.pitaya.set('ttl_ttl1_start', cooling_on)
            #rp.pitaya.set('ttl_ttl1_end', cooling_off)
            #rp.pitaya.set('ttl_ttl2_start', cooling_on_again)
            #rp.pitaya.set('ttl_ttl2_end', cooling_off_again)
            #rp.pitaya.set(cooling_pin, rp.pitaya.states('ttl_ttl1_out') | rp.pitaya.states('ttl_ttl2_out'))
            rp.pitaya.set('ttl_ttl1_start', cooling_off)
            rp.pitaya.set('ttl_ttl1_end',  cooling_on_again)
            rp.pitaya.set(cooling_pin, rp.pitaya.states('ttl_ttl1_out'))

            # TTL2: turn on repumping laser
            # do5_en (Kanal 6)ist repumper!
            rp.pitaya.set('ttl_ttl3_start', repumping_on)
            rp.pitaya.set('ttl_ttl3_end', repumping_off)
            rp.pitaya.set(repumping_pin, rp.pitaya.states('ttl_ttl3_out'))

            # TTL4: trigger camera
            # do4_en (Kanal 5) ist cam trigger gpio_n_do4_en
            rp.pitaya.set('ttl_ttl4_start', int(camera_trigger))
            rp.pitaya.set('ttl_ttl4_end', int(camera_trigger + one_second))
            cam_trig_ttl = rp.pitaya.states('ttl_ttl4_out')
            rp.pitaya.set(cam_trig_pin, cam_trig_ttl)

            # TTL5: announcer
            # do2 (Kanal 3) ist announcer
            rp.pitaya.set('ttl_ttl5_start', int(pid_on - one_ms))
            rp.pitaya.set('ttl_ttl5_end', int(pid_on - one_ms + one_second))
            rp.pitaya.set('gpio_n_do2_en', rp.pitaya.states('ttl_ttl5_out'))

            rp.enable_channel_b_pid(True, p=200, i=25, d=0, reset=False)

            actual_length = int(LENGTH / (2**decimation))
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
            pipe, child_pipe = Pipe()
            acquiry_process = Process(target=record_afmot_loading, args=(child_pipe,))
            acquiry_process.start()
            sleep(2)

            rp.set_enabled(1)
            rp.set_algorithm(1)
            rp.pitaya.set('control_loop_sequence_player_start_clocks', 1)

            # Trigger the cam on repeatedly for recording the AF-MOT loading curve
            start_time = time()
            target_time = delay / iterations_per_second

            # stop the continuous triggering 2 seconds before the AF-MOT atom number
            # is determined
            while time() - start_time < target_time - 5:
                rp.pitaya.set(cam_trig_pin, rp.pitaya.states('force'))
                sleep(.05)
                rp.pitaya.set(cam_trig_pin, rp.pitaya.states())
                sleep(.05)

            # now, internal FPGA should control the camera trigger
            rp.pitaya.set(cam_trig_pin, cam_trig_ttl)

            print('waiting 5 seconds')
            sleep(10)

            # record MOT loading curve
            start_time = time()
            while time() - start_time < 30:
                rp.pitaya.set(cam_trig_pin, rp.pitaya.states('force'))
                sleep(.05)
                rp.pitaya.set(cam_trig_pin, rp.pitaya.states())
                sleep(.05)

            print('waiting again')
            sleep(1.5)

            rp.pitaya.set(cam_trig_pin, rp.pitaya.states('force'))
            sleep(.05)
            rp.pitaya.set(cam_trig_pin, rp.pitaya.states())
            sleep(.05)

            #acquiry_process.join()
            data = pickle.loads(pipe.recv())

            #plt.plot(data['times'], data['atom_numbers'])
            #plt.grid()
            #plt.show()

            iteration_data.append(data)

            with open(FOLDER + FILENAME, 'wb') as f:
                pickle.dump(all_data, f)