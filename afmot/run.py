import numpy as np
import pickle

from time import sleep, time
from matplotlib import pyplot as plt

from utils import counter_measurement, save_osci, arm_osci, N_BITS, LENGTH
from registers import Pitaya


if __name__ == '__main__':
    rp = Pitaya('rp-f012ba.local', user='root', password='zeilinger')
    rp.connect()

    decimation = 5
    max_state = 4
    N_states = max_state + 1

    for cooling_duty_cycle in reversed([0.4, 0.6, 0.8]):
        print('duty cycle', cooling_duty_cycle)

        """ssh_cmd='sshpass -p zeilinger ssh root@rp-f012ba.local'
        import subprocess
        reset_cmd="/bin/bash /reset.sh"
        p = subprocess.Popen(' '.join([ssh_cmd, reset_cmd]).split(),
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)

        sleep(5)
        input('ok?')
        print('reset done')"""

        rp.init(
            decimation=decimation,
            N_zones=2,
            relative_length=1 / (2**decimation),
            zone_edges=[1-cooling_duty_cycle, 1, None],
            target_frequencies=[6000, 150, None, None],
            curvature_filtering_starts=[15, 15, None, None]
            #curvature_filtering_starts=[16383, 16383, 16383, 16383]
        )

        force = rp.pitaya.states('force')
        null = rp.pitaya.states()

        cooling_pin = 'gpio_n_do3_en'
        cam_trig_pin = 'gpio_n_do4_en'
        repumping_pin = 'gpio_n_do5_en'


        """if True:
            rp.set_enabled(0)
            rp.set_algorithm(0)
            actual_length = int(LENGTH / (2**decimation))
            first_feed_forward = np.array([0] * actual_length)
            #rp.set_algorithm(0)
            #rp.set_feed_forward(first_feed_forward)
            #rp.sync()
            rp.enable_channel_b_pid(True, p=200, i=10, d=100, reset=True)
            rp.enable_channel_b_pid(True, p=200, i=100, d=0, reset=False)
            rp.pitaya.set('control_loop_pid_enable_en', force)
            rp.pitaya.set('gpio_n_do0_en', rp.pitaya.states())
            rp.pitaya.set('gpio_n_do1_en', force)

            rp.pitaya.set(cooling_pin, force)
            rp.pitaya.set(repumping_pin, force)
            rp.sync()
            asd"""


        rp.pitaya.set('control_loop_sequence_player_stop_zone', 1)

        delay = 20 * 2000

        one_iteration = 16384 * N_states
        iterations_per_second = 7629.394531249999 / N_states
        one_second = one_iteration * iterations_per_second
        one_ms = one_second / 1000

        if True:
            pid_on = int(delay * one_iteration)
            pid_off = int(pid_on + 200 * one_second)
            cooling_on = 0
            cooling_off = pid_on
            cooling_on_again = int(cooling_off + 20 * one_ms)
            cooling_off_again = int(cooling_on_again + 2000 * one_second)
            repumping_on = cooling_off
            repumping_off = int(repumping_on + 2000 * one_second)
            camera_trigger = cooling_on_again + 20 * one_ms

            rp.pitaya.set('control_loop_sequence_player_stop_algorithm_after', delay-1)
            rp.pitaya.set('control_loop_sequence_player_stop_after', delay-1)
        else:
            pid_on = (1<<29)-1
            pid_off = pid_on
            cooling_on = 0
            cooling_off = pid_on
            cooling_on_again = 0
            cooling_off_again = pid_on
            repumping_on = cooling_on
            repumping_off = pid_on
            camera_trigger = 0

        #rp.set_enabled(1)
        #rp.set_algorithm(1)
        # TODO:
        # FIXME: remove

        # TTL0: enable PID
        rp.pitaya.set('ttl_ttl0_start', pid_on)
        rp.pitaya.set('ttl_ttl0_end', pid_off)

        rp.pitaya.set('control_loop_pid_enable_en', rp.pitaya.states('ttl_ttl0_out'))
        #print('PID IST OFF!!')
        #rp.pitaya.set('control_loop_pid_enable_en', rp.pitaya.states())

        # TTL1+TTL2: turn on and off cooling laser
        # do3_en (Kanal 4) ist cooling laser
        rp.pitaya.set('ttl_ttl1_start', cooling_on)
        rp.pitaya.set('ttl_ttl1_end', cooling_off)
        rp.pitaya.set('ttl_ttl2_start', cooling_on_again)
        rp.pitaya.set('ttl_ttl2_end', cooling_off_again)
        rp.pitaya.set(cooling_pin, rp.pitaya.states('ttl_ttl1_out') | rp.pitaya.states('ttl_ttl2_out'))

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
        #rp.pitaya.set('control_loop_pid_ki', 10)

        actual_length = int(LENGTH / (2**decimation))
        rp.set_max_state(4)

        rp.set_algorithm(0)
        rp.set_enabled(0)

        first_feed_forward = np.array([0] * actual_length)
        #rp.set_feed_forward(first_feed_forward)
        rp.sync()

        rp.set_enabled(1)
        rp.set_algorithm(1)

        rp.pitaya.set('control_loop_sequence_player_start_clocks', 1)

        # Trigger the cam on repeatedly for recording the AF-MOT loading curve
        start_time = time()
        target_time = delay / iterations_per_second

        # stop the continuous triggering 2 seconds before the AF-MOT atom number
        # is determined
        while time() - start_time < target_time - 2:
            rp.pitaya.set(cam_trig_pin, rp.pitaya.states('force'))
            sleep(.05)
            rp.pitaya.set(cam_trig_pin, rp.pitaya.states())
            sleep(.05)

        rp.pitaya.set(cam_trig_pin, cam_trig_ttl)

        print('waiting 10 seconds')
        sleep(10)

        start_time = time()
        while time() - start_time < 5:
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


        input('RESTART WAITING!')