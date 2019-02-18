from migen import Memory

def create_memory(self, N_bits, N_points, name):
    setattr(self.specials, name, Memory(N_bits, N_points, name=name))
    mem = getattr(self, name)

    rdport = mem.get_port()
    wrport = mem.get_port(write_capable=True)

    return rdport, wrport