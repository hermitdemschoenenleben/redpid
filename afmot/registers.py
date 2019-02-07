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
            'p': 1
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
            fast_a_brk=1,
            fast_a_mod_amp=0xeee,
            fast_a_mod_freq=0,
            fast_a_x_tap=0,
            fast_a_sweep_run=0,
            fast_a_sweep_step=300000,
            fast_a_y_tap=0,
            fast_a_dy_sel=self.pitaya.signal("zero"),#self.pitaya.signal("scopegen_dac_a"),

            # channel B (channel for rect output)
            fast_b_brk=1,
            fast_b_dx_sel=self.pitaya.signal("zero"),#self.pitaya.signal("zero"),
            fast_b_x_tap=0,
            fast_b_y_tap=0,
            fast_b_sweep_run=0,
            fast_b_sweep_step=100000,
            fast_b_dy_sel=self.pitaya.signal("scopegen_dac_b"),
            fast_b_mod_freq=0,
            fast_b_mod_amp=0x0,

            fast_a_relock_run=0,
            fast_a_relock_en=self.pitaya.states(),
            fast_a_y_hold_en=self.pitaya.states(),
            fast_a_y_clear_en=self.pitaya.states(),
            fast_a_rx_sel=self.pitaya.signal('zero'),
            fast_b_relock_run=0,
            fast_b_relock_en=self.pitaya.states(),
            fast_b_y_hold_en=self.pitaya.states(),
            fast_b_y_clear_en=self.pitaya.states(),
            fast_b_rx_sel=self.pitaya.signal('zero'),

            # trigger on GPIO trigger
            scopegen_external_trigger=0,
            scopegen_adc_a_sel=self.pitaya.signal("fast_a_y"),
            scopegen_adc_b_sel=self.pitaya.signal("fast_b_y"),

            gpio_p_oes=0,
            gpio_n_oes=0,
            gpio_p_outs=0,
            gpio_n_outs=0,
            gpio_n_do0_en=self.pitaya.signal('zero'),
            gpio_n_do1_en=self.pitaya.signal('zero'),
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
        self.pitaya.set('fast_b_x_clear_en', self.pitaya.states('force'))
        self.pitaya.set('fast_b_y_clear_en', self.pitaya.states('force'))

        # set PI parameters
        self.pitaya.set_iir("fast_a_iir_a", *make_filter('P', k=self.parameters['p']))

        # re-enable lock
        self.pitaya.set('fast_b_y_clear_en', self.pitaya.states())
        self.pitaya.set('fast_b_x_clear_en', self.pitaya.states())

    def _load_sequence(self, channel, data):
        assert channel in ('a', 'b'), 'invalid channel'
        channel = 'fast_%s_sequence_player' % channel

        for addr, value in enumerate(data):
            print(addr, value)
            self.pitaya.set('%s_data_addr' % channel, addr)
            self.pitaya.set('%s_data_in' % channel, value)
            #self.pitaya.set('%s_data_write' % channel, 1)
            #self.pitaya.set('%s_data_write' % channel, 0)

        self.pitaya.set('%s_enabled' % channel, 1)

    def start_clock(self, length, percentage):
        data = []

        for i in range(length):
            if i < percentage * length:
                data.append(8191)
            else:
                # FIXME: not 0
                data.append(1000)

        self._load_sequence('b', data)

    def set_feed_forward(self, feedforward):
        self._load_sequence('a', feedforward)

    def set_proportional(self, p):
        self.parameters['p'] = p
        self.write_registers()

    def record_control(self):
        # TODO: früher machen?

        self.scpi.set_acquisition_trigger(
            'EXT_PE',
            decimation=1,
            delay=8192
        )


        while not self.scpi.was_triggered():
            sleep(0.1)

        from matplotlib import pyplot as plt
        a, b = (
            self.scpi.fast_in[0].read_buffer(),
            self.scpi.fast_in[1].read_buffer()
        )
        plt.plot(a)
        plt.plot(b)

        plt.show()
        #print(control)
        asd

        data = []

        x_axis = np.linspace(0, DURATION*1e6, LENGTH)

        r.scope.trigger_source = 'ext_positive_edge'
        sleep(.1)
        measured_control = list(r.scope.curve()[0, :])
        before = measured_control
        measured_control = measured_control + measured_control
        offset = 8192 + int(234 / DECIMATION)
        measured_control = measured_control[offset:offset+int(LENGTH / FREQUENCY_MULTIPLIER)]
        """plt.plot(before, label='before')
        plt.plot(measured_control, label='mc')
        plt.legend()
        plt.show()"""

        data.append(measured_control)

        #plt.plot(measured_control)
        #plt.show()

        return x_axis, data