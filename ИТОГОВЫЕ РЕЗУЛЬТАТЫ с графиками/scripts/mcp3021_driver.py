from smbus2 import SMBus, i2c_msg


class MCP3021:
    def __init__(self, voltage=5.0, address=0x4D):
        self.bus = SMBus(1)
        self.address = address
        self.voltage = voltage

    def get_number(self):
        message = i2c_msg.read(self.address, 2)
        self.bus.i2c_rdwr(message)
        first, second = list(message)
        return (first * 256 + second) >> 2

    def deinit(self):
        self.bus.close()
