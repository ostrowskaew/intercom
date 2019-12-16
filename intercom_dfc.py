# Implementing a Data-Flow Control algorithm.

from intercom_binaural import Intercom_binaural
from intercom import Intercom
from intercom_buffer import Intercom_buffer
import struct
import numpy as np


class Intercom_dfc(Intercom_binaural):

    def init(self, args):
        Intercom_binaural.init(self, args)
        self.packet_format = f"!HB{self.frames_per_chunk//8}BB"
        self.dict_size = 4
        self.received_dict = {0: 0, 1: 0, 2: 0, 3: 0}
        self.received_out = 32
        self.received_in = 32
        self.delay = 2
        self.num_sent = 16


    def receive_and_buffer(self):
        message, source_address = self.receiving_sock.recvfrom(Intercom.MAX_MESSAGE_SIZE)
        chunk_number, bitplane_number, *bitplane, received_in = struct.unpack(self.packet_format, message)
        self.received_in = received_in
        self.received_dict[chunk_number % self.dict_size] += 1
        if chunk_number > self.delay:
            self.received_out = self.received_dict[(chunk_number-self.delay) % self.dict_size]
            self.received_dict[(chunk_number - self.delay - 1) % self.dict_size] = 0

        bitplane = np.asarray(bitplane, dtype=np.uint8)
        bitplane = np.unpackbits(bitplane)
        bitplane = bitplane.astype(np.int16)
        self._buffer[chunk_number % self.cells_in_buffer][:, bitplane_number % self.number_of_channels] |= (bitplane << bitplane_number//self.number_of_channels)
        return chunk_number

    def record_send_and_play_stereo(self, indata, outdata, frames, time, status):
        indata[:,0] -= indata[:,1]
        sign_plane = self.receive_and_buffer[self.played_chunk_number % self.cells_in_buffer] >> 15
        magn = self._buffer[self.played_chunk_number % self.cells_in_buffer] & 0x7FFF
        rec_chunk = magn + (magn * sign_plane * 2)
        self.record_and_send(indata)
        self._buffer[self.played_chunk_number % self.cells_in_buffer][:, 0] = rec_chunk
        self._buffer[self.played_chunk_number % self.cells_in_buffer][:,0] += self._buffer[self.played_chunk_number % self.cells_in_buffer][:,1]
        self.play(outdata)

    def record_and_send(self, indata):
        self.calculate_num_sent()
        for bitplane_number in range(self.number_of_channels*self.num_sent-1, -1, -1):
            bitplane = (indata[:, bitplane_number % self.number_of_channels] >> bitplane_number//self.number_of_channels) & 1
            bitplane = bitplane.astype(np.uint8)
            bitplane = np.packbits(bitplane)
            message = struct.pack(self.packet_format, self.recorded_chunk_number, bitplane_number, *bitplane, self.received_out)
            self.sending_sock.sendto(message, (self.destination_IP_addr, self.destination_port))
        self.recorded_chunk_number = (self.recorded_chunk_number + 1) % self.MAX_CHUNK_NUMBER

    def calculate_num_sent(self):
        if self.num_sent == self.received_in//2 and self.num_sent != 16:
            self.num_sent += 1
        elif self.num_sent < self.received_in//2:
            self.num_sent -= 1


if __name__ == "__main__":
    intercom = Intercom_dfc()
    parser = intercom.add_args()
    args = parser.parse_args()
    intercom.init(args)
    intercom.run()
