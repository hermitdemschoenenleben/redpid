import numpy as np
from time import sleep, time

from csr import make_filter, PitayaLocal, PitayaSSHCustom
from utils import LENGTH
from devices import RedPitaya


class Pitaya:
    def __init__(self, host=None, user=None, password=None):
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
            gpio_n_outs=0b1,

            gpio_n_do1_en=self.pitaya.states('control_loop_clock_0'),
            gpio_n_do2_en=self.pitaya.states(),
            gpio_n_do3_en=self.pitaya.states(),
            gpio_n_do4_en=self.pitaya.states(),
            #gpio_n_do2_en=self.pitaya.states('control_loop_clock_1'),
            #gpio_n_do3_en=self.pitaya.states('control_loop_clock_2'),
            #gpio_n_do4_en=self.pitaya.states('control_loop_clock_3'),
            gpio_n_do0_en=self.pitaya.states()
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
            print('SET', k, int(v))

        # set PI parameters
        self.pitaya.set_iir("control_loop_iir_a", *make_filter('P', k=self.parameters['p']))
        self.pitaya.set_iir("control_loop_iir_c", *make_filter('I', f=10, k=.1))

    def _write_sequence(self, data, N_bits):
        channel = 'control_loop_sequence_player'

        max_ = 1<<(N_bits - 1)
        full = 2 * max_
        def convert(num):
            if num < 0:
                num += full
            return num

        assert not self.pitaya.get('%s_run_algorithm'), \
            'write is only possible if algorithm is not running'

        self.pitaya.set('%s_data_write', 1)

        for addr, v in enumerate(data):
            self.pitaya.set('%s_data_addr' % channel, addr)
            self.pitaya.set('%s_data_in' % channel, convert(v))

        self.pitaya.set('%s_data_write', 0)

    def _read_sequence(self, N_bits, N_points):
        channel = 'control_loop_sequence_player'

        data = []

        with self.pitaya.batch_reads:
            for address in range(N_points):
                self.pitaya.set('%s_data_out_addr' % channel, address)
                data.append(self.pitaya.get('%s_data_out' % channel))

        # convert batch read objects to integers
        data = [int(_) for _ in data]

        # data contains only positive numbers --> rescale
        max_ = 1<<(N_bits - 1)
        full = 2 * max_

        # there's a delay of several cycles in the recording of the data inside the FPGA
        data = np.roll(data, -5)

        data = [
            v if v < max_
            else (-full) + v
            for v in data
        ]

        return data

    def _read_error_signal(self, N_points):
        channel = 'control_loop_sequence_player'

        data = []

        with self.pitaya.batch_reads:
            for address in range(N_points):
                self.pitaya.set('%s_error_signal_out_addr' % channel, address)
                data.append(self.pitaya.get('%s_error_signal_out' % channel))

        # convert batch read objects to integers
        data = [int(_) for _ in data]
        data = np.roll(data, -5)

        return data

    def start_clock(self, length, end0, end1, end2):
        channel = 'control_loop_sequence_player'
        for i, end in enumerate((end0, end1, end2)):
            self.pitaya.set(
                '%s_zone_edge_%d' % (channel, i),
                int(length * end) if end is not None else -1
            )

        self.pitaya.set('%s_enabled' % channel, 1)

    def set_feed_forward(self, feedforward, N_bits):
        self._write_sequence(feedforward, N_bits)

    def set_proportional(self, p):
        self.parameters['p'] = p
        self.write_registers()

    def record_control(self, N_bits=14, N_points=16384):
        self.pitaya.set('control_loop_sequence_player_recording', 1)
        # just to be sure...
        sleep(0.001)
        self.pitaya.set('control_loop_sequence_player_recording', 0)

        measured_control = self._read_sequence(N_bits, N_points)
        return measured_control

    def record_error_signal(self, N_points=16384):
        self.pitaya.set('control_loop_sequence_player_recording', 1)
        # just to be sure...
        sleep(0.001)

        return self._read_error_signal(N_points)

    def sync(self):
        # just read something to wait for completion of all commands
        self.pitaya.get('dna_dna')