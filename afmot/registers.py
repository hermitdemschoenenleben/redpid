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
            'p': 0.05
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
            # channel A (PID channel)
            fast_a_brk=0,
            #fast_a_mod_amp=0x0,
            #fast_a_mod_freq=0,
            fast_a_x_tap=1,
            #fast_a_sweep_run=0,
            #fast_a_sweep_step=0,
            fast_a_y_tap=0,
            fast_a_dy_sel=self.pitaya.signal("zero"),
            fast_a_y_limit_min=-8192,
            fast_a_y_limit_max=8191,
            fast_a_x_hold_en=self.pitaya.signal('zero'),

            # channel B (channel for rect output)
            # fast_b_brk=1,
            # fast_b_dx_sel=self.pitaya.signal("zero"),#self.pitaya.signal("zero"),
            # fast_b_x_tap=0,
            # fast_b_y_tap=0,
            # fast_b_sweep_run=0,
            # fast_b_sweep_step=100000,
            # fast_b_dy_sel=self.pitaya.signal("zero"),
            # fast_b_mod_freq=0,
            # fast_b_mod_amp=0x0,

            #fast_a_relock_run=0,
            #fast_a_relock_en=self.pitaya.states(),
            fast_a_y_hold_en=self.pitaya.states(),
            fast_a_x_clear_en=self.pitaya.states('force'),
            fast_a_y_clear_en=self.pitaya.states('force'),
            fast_a_rx_sel=self.pitaya.signal('zero'),
            # fast_b_relock_run=0,
            # fast_b_relock_en=self.pitaya.states(),
            # fast_b_y_hold_en=self.pitaya.states(),
            # fast_b_y_clear_en=self.pitaya.states(),
            # fast_b_rx_sel=self.pitaya.signal('zero'),

            # trigger on GPIO trigger
            #scopegen_external_trigger=0,
            #scopegen_adc_a_sel=self.pitaya.signal("fast_a_y"),
            #scopegen_adc_b_sel=self.pitaya.signal("fast_b_y"),
            fast_b_sequence_player_clock_max=8191,


            gpio_p_oes=0xff,
            gpio_p_outs=0x0,
            gpio_n_oes=0xff,
            gpio_n_outs=0b1,

            gpio_n_do1_en=self.pitaya.states('fast_b_clock_high'),
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

        # clear
        #self.pitaya.set('fast_b_x_clear_en', self.pitaya.states('force'))
        #self.pitaya.set('fast_b_y_clear_en', self.pitaya.states('force'))

        # set PI parameters
        self.pitaya.set_iir("fast_a_iir_a", *make_filter('P', k=self.parameters['p']))

        # re-enable lock
        #self.pitaya.set('fast_b_y_clear_en', self.pitaya.states())
        #self.pitaya.set('fast_b_x_clear_en', self.pitaya.states())

    def _write_sequence(self, channel, data, N_bits):
        assert channel in ('a', 'b'), 'invalid channel'
        channel = 'fast_%s_sequence_player' % channel

        max_ = 1<<(N_bits - 1)
        full = 2 * max_
        def convert(num):
            if num < 0:
                num += full
            return num

        for addr, [v1, v2] in enumerate(zip(data[0::2], data[1::2])):
            # two 14-bit values are saved in a single register
            # register width is 32 bits of which we use 28

            # handle negative numbers properly
            v1, v2 = convert(v1), convert(v2)

            self.pitaya.set('%s_data_addr' % channel, addr)
            self.pitaya.set('%s_data_in' % channel, v1 + (v2 << N_bits))
            #self.pitaya.set('%s_data_write' % channel, 1)
            #self.pitaya.set('%s_data_write' % channel, 0)

        self.pitaya.set('%s_enabled' % channel, 1)

    def _read_sequence(self, channel, N_bits, N_points):
        assert channel in ('a', 'b'), 'invalid channel'
        channel = 'fast_%s_sequence_player' % channel

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

    def _read_error_signal(self, channel, N_points):
        assert channel in ('a', 'b'), 'invalid channel'
        channel = 'fast_%s_sequence_player' % channel

        data = []

        with self.pitaya.batch_reads:
            for address in range(N_points):
                self.pitaya.set('%s_error_signal_out_addr' % channel, address)
                data.append(self.pitaya.get('%s_error_signal_out' % channel))

        # convert batch read objects to integers
        data = [int(_) for _ in data]
        data = np.roll(data, -5)

        return data

    def start_clock(self, length, dcycle):
        channel = 'fast_b_sequence_player'
        print('dcycle', int(length * dcycle))
        self.pitaya.set('%s_dcycle' % channel, int(length * dcycle))
        self.pitaya.set('%s_enabled' % channel, 1)

    def set_feed_forward(self, feedforward, N_bits):
        self._write_sequence('a', feedforward, N_bits)

    def set_proportional(self, p):
        self.parameters['p'] = p
        self.write_registers()

    def record_control(self, channel='a', N_bits=14, N_points=16384):
        self.pitaya.set('fast_%s_sequence_player_recording' % channel, 1)
        # just to be sure...
        sleep(0.001)

        measured_control = self._read_sequence(channel, N_bits, N_points)
        return measured_control

    def record_error_signal(self, channel='a', N_points=16384):
        self.pitaya.set('fast_%s_sequence_player_recording' % channel, 1)
        # just to be sure...
        sleep(0.001)

        return self._read_error_signal(channel, N_points)

    def sync(self):
        # just read something to wait for completion of all commands
        self.pitaya.get('dna_dna')