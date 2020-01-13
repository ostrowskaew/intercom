# Don't send empty bitplanes.
#
# The sender adds to the number of received bitplanes the number of
# skipped (zero) bitplanes of the chunk sent.

# The receiver computes the first received
# bitplane (apart from the bitplane with the signs) and report a
# number of bitplanes received equal to the real number of received
# bitplanes plus the number of skipped bitplanes.

import struct
import numpy as np
from intercom import Intercom
from intercom_dfc import Intercom_DFC

if __debug__:
    import sys

class Intercom_empty(Intercom_DFC):

    def init(self, args):
        Intercom_DFC.init(self, args)
        self.packet_format = f"!HBB{self.frames_per_chunk // 8}BB"
        self.zero_rec = 0
        self.zero_sent = 0

    def receive_and_buffer(self):
        message, source_address = self.receiving_sock.recvfrom(Intercom.MAX_MESSAGE_SIZE)
        received_chunk_number, received_bitplane_number, self.NORB, zero_bit, *bitplane = struct.unpack(self.packet_format,
                                                                                             message)
        self.NORB = self.NORB + zero_bit
        if zero_bit != 0:
            for x in range(zero_bit):
                bitplane = np.zeros((1, 1024), dtype=np.uint16)
                self._buffer[received_chunk_number % self.cells_in_buffer][:,
                received_bitplane_number - zero_bit % self.number_of_channels] |= (
                        bitplane << received_bitplane_number - zero_bit // self.number_of_channels)
                self.received_bitplanes_per_chunk[received_chunk_number % self.cells_in_buffer] += 1
                zero_bit -= 1
        else:
            bitplane = np.asarray(bitplane, dtype=np.uint8)
            bitplane = np.unpackbits(bitplane)
            bitplane = bitplane.astype(np.uint16)
            self._buffer[received_chunk_number % self.cells_in_buffer][:,
            received_bitplane_number % self.number_of_channels] |= (
                 bitplane << received_bitplane_number // self.number_of_channels)
            self.received_bitplanes_per_chunk[received_chunk_number % self.cells_in_buffer] += 1
        return received_chunk_number

    def send_bitplane(self, indata, bitplane_number):
        bitplane = (indata[:,
                    bitplane_number % self.number_of_channels] >> bitplane_number // self.number_of_channels) & 1
        count_zero = not np.any(bitplane)
        if count_zero:
            self.zero_sent += 1
        else:
            bitplane = bitplane.astype(np.uint8)
            bitplane = np.packbits(bitplane)
            message = struct.pack(self.packet_format, self.recorded_chunk_number, bitplane_number,
                                self.received_bitplanes_per_chunk[
                                    (self.played_chunk_number + 1) % self.cells_in_buffer] + 1, self.zero_sent *bitplane)
            self.sending_sock.sendto(message, (self.destination_IP_addr, self.destination_port))
            self.zero_sent = 0


if __name__ == "__main__":
    intercom = Intercom_empty()
    parser = intercom.add_args()
    args = parser.parse_args()
    intercom.init(args)
    intercom.run()
