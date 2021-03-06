import numpy as np
from time import sleep, time

from csr import make_filter, PitayaLocal, PitayaSSHCustom
from utils import LENGTH
from devices import RedPitaya


class Pitaya:
    def __init__(self, host=None, user=None, password=None, N_zones=4):
        self.host = host
        self.user = user
        self.password = password

        self._cached_data = {}
        self.parameters = {
            'decimation': 1,
            # unused, right now
            'p': 0.01,
            'i': 1e-6
        }

        self.N_points = 16384
        self.N_bits = 14

        self.N_zones = N_zones

    def connect(self):
        self.scpi = RedPitaya(self.host, delay_scpi_connection=True)

        self.use_ssh = self.host is not None and self.host != 'localhost'

        if self.use_ssh:
            self.pitaya = PitayaSSHCustom(
                ssh_cmd="sshpass -p %s ssh %s@%s" % (self.password, self.user, self.host)
            )
            # FIXME: das geht eleganter
            sleep(1)
        else:
            self.pitaya = PitayaLocal()

    def write_registers(self):
        new = dict(
            control_loop_brk=1,
            control_loop_x_tap=1,
            control_loop_y_tap=1,
            control_loop_dy_sel=self.pitaya.signal("zero"),
            control_loop_y_limit_min=-8192,
            control_loop_y_limit_max=8191,
            control_loop_x_hold_en=self.pitaya.signal('zero'),

            control_loop_y_hold_en=self.pitaya.states(),
            control_loop_x_clear_en=self.pitaya.states('force'),
            control_loop_y_clear_en=self.pitaya.states('force'),
            control_loop_rx_sel=self.pitaya.signal('zero'),

            gpio_p_oes=0xff,
            gpio_p_outs=0x0,
            gpio_n_oes=0xff,
            gpio_n_outs=0b0,

            gpio_n_do0_en=self.pitaya.states('control_loop_clock_0'),
            gpio_n_do1_en=self.pitaya.states('control_loop_clock_1'),
            gpio_n_do2_en=self.pitaya.states('control_loop_clock_2'),
            gpio_n_do3_en=self.pitaya.states('control_loop_clock_3'),
            #gpio_n_do4_en=self.pitaya.states(),
            #gpio_n_do5_en=self.pitaya.states(),
        )

        # filter out values that did not change
        new = dict(
            (k, v)
            for k, v in new.items()
            if (
                (k not in self._cached_data)
                or (self._cached_data.get(k) != v)
            )
        )
        self._cached_data.update(new)

        for k, v in new.items():
            self.pitaya.set(k, int(v))

        # set PI parameters
        self.pitaya.set_iir("control_loop_iir_a", *make_filter('P', k=self.parameters['p']))
        self.pitaya.set_iir("control_loop_iir_c", *make_filter('I', f=10, k=.1))

    def init(self, decimation=0, N_zones=2, relative_length=1,
             zone_edges=[0.5, 1, None, None], target_frequencies=[1000, 2000],
             curvature_filtering_starts=[100, 100, 100, None]
             ):
        self.start_clock(self.N_points, *[
            int((self.N_points - 1) * relative_length * edge)
            if edge is not None
            else None
            for edge in zone_edges
        ])
        self.pitaya.set(
            'control_loop_sequence_player_last_point',
            int(relative_length * (self.N_points - 1))
        )
        self.set_target_frequencies(target_frequencies)
        self.set_ff_target_curvatures([1, 1, 1, 1])
        self.set_curvature_filtering_starts(curvature_filtering_starts)

        self.pitaya.set('control_loop_decimation', decimation)
        self.pitaya.set('control_loop_sequence_player_keep_constant_at_end', 0)

        self.enable_channel_b_loop_through(0)

        self.write_registers()


    def _write_sequence(self, data):
        channel = 'control_loop_sequence_player'

        max_ = 1<<(self.N_bits - 1)
        full = 2 * max_
        def convert(num):
            if num < 0:
                num += full
            return num

        assert not self.pitaya.get('%s_run_algorithm' % channel), \
            'write is only possible if algorithm is not running'

        self.pitaya.set('%s_data_write' % channel, 1)

        for addr, v in enumerate(data):
            self.pitaya.set('%s_data_addr' % channel, addr)
            self.pitaya.set('%s_data_in' % channel, convert(v))

        self.pitaya.set('%s_data_write' % channel, 0)

    def read_control_signal(self, addresses=None):
        channel = 'control_loop_sequence_player'

        data = []

        if addresses is None:
            addresses = range(self.N_points)

        with self.pitaya.batch_reads:
            for address in addresses:
                self.pitaya.set('%s_data_out_addr' % channel, address)
                data.append(self.pitaya.get('%s_data_out' % channel))

        # convert batch read objects to integers
        data = [int(_) for _ in data]

        # data contains only positive numbers --> rescale
        max_ = 1<<(self.N_bits - 1)
        full = 2 * max_

        # there's a delay of several cycles in the recording of the data inside the FPGA
        data = np.roll(data, -5)

        data = [
            v if v < max_
            else (-full) + v
            for v in data
        ]

        return data

    def read_error_signal(self, addresses=None):
        channel = 'control_loop_sequence_player'

        data = []

        if addresses is None:
            addresses = range(self.N_points)

        with self.pitaya.batch_reads:
            for address in addresses:
                self.pitaya.set('%s_error_signal_out_addr' % channel, address)
                data.append(self.pitaya.get('%s_error_signal_out' % channel))

        # convert batch read objects to integers
        data = [int(_) for _ in data]
        data = np.roll(data, 0)

        return data

    def start_clock(self, length, end0, end1, end2):
        channel = 'control_loop_sequence_player'
        for i, end in enumerate((end0, end1, end2)):
            self.pitaya.set(
                '%s_zone_edge_%d' % (channel, i),
                end if end is not None else -1
            )

        self.pitaya.set('%s_enabled' % channel, 1)

    def set_feed_forward(self, feedforward):
        self._write_sequence(feedforward)

    def set_proportional(self, p):
        self.parameters['p'] = p
        self.write_registers()

    def record_now(self):
        self.pitaya.set('control_loop_sequence_player_request_recording', 1)
        # just to be sure...
        sleep(0.1)
        self.pitaya.set('control_loop_sequence_player_request_recording', 0)

    def schedule_recording_after(self, delay):
        self.pitaya.set('control_loop_sequence_player_record_after', delay)

    def sync(self):
        # just read something to wait for completion of all commands
        self.pitaya.get('dna_dna')

    def set_enabled(self, enabled):
        self.pitaya.set('control_loop_sequence_player_enabled', 1 if enabled else 0)

    def set_algorithm(self, enabled):
        self.pitaya.set('control_loop_sequence_player_run_algorithm', enabled)

    def set_max_state(self, state):
        self.pitaya.set('control_loop_sequence_player_max_state', state)

    def set_curvature_filtering_starts(self, starts):
        assert len(starts) == self.N_zones

        for i, start in enumerate(starts):
            if start is None:
                continue

            self.pitaya.set(
                'control_loop_sequence_player_ff_curvature_filtering_start_%d' % i,
                start
            )

    def set_ff_target_directions(self, directions):
        assert len(directions) == self.N_zones

        for i, direction in enumerate(directions):
            assert direction in (1, -1, 0, None)
            if direction is None:
                continue

            self.pitaya.set(
                'control_loop_sequence_player_ff_direction_%d' % i,
                direction
            )

    def set_ff_target_curvatures(self, curvatures):
        assert len(curvatures) == self.N_zones

        for i, curvature in enumerate(curvatures):
            assert curvature in (1, -1, 0, None)
            if curvature is None:
                continue

            self.pitaya.set(
                'control_loop_sequence_player_ff_curvature_%d' % i,
                curvature
            )

    def enable_channel_b_loop_through(self, enabled):
        self.pitaya.set(
            'control_loop_dy_sel',
            self.pitaya.signal('control_loop_other_x' if enabled else 'zero')
        )

    def enable_channel_b_pid(self, enabled, p=None, i=None, d=None, reset=True):
        self.pitaya.set(
            'control_loop_dy_sel',
            self.pitaya.signal('control_loop_pid_out' if enabled else 'zero')
        )
        self.pitaya.set('control_loop_pid_reset', 1 if reset else 0)
        if p is not None:
            self.pitaya.set('control_loop_pid_kp', p)
        if i is not None:
            self.pitaya.set('control_loop_pid_ki', i)
        if d is not None:
            self.pitaya.set('control_loop_pid_kd', d)

    def set_target_frequencies(self, frequencies):
        assert len(frequencies) == self.N_zones
        directions = []

        last = [f for f in frequencies if f is not None][-1]
        frequencies = [last] + frequencies

        for idx in range(4):
            previous = frequencies[idx]
            current = frequencies[idx + 1]

            if current is None or previous is None:
                directions.append(None)
            else:
                directions.append(
                    -1 if (current > previous) else 1
                )

        self.set_ff_target_directions(directions)