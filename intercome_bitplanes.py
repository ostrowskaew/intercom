# Adding a buffer.

import sounddevice as sd
import numpy as np
import struct
from intercom_buffer import Intercom_buffer
from intercom import Intercom

if __debug__:
    import sys

class Intercom_bitplanes(Intercom_buffer):
    def init(self, args):
        Intercom_buffer.init(self, args)
        self.bitpacks_per_chunk = self.frames_per_chunk//8
        self.packet_format = f"HH{self.bitpacks_per_chunk}B"


    def run(self):
        self.bits_number = 15
        self.recorded_chunk_number = 0
        self.played_chunk_number = 0
        self.column_iterator = 0

        def receive_and_buffer():
            message, source_address = self.receiving_sock.recvfrom(Intercom.MAX_MESSAGE_SIZE)
            bitplane_number, chunk_number, *bitplane = struct.unpack(self.packet_format, message)



            bitplane = np.asarray(bitplane, dtype=np.uint8)
            bitplane = np.unpackbits(bitplane)


            print(bitplane_number)
            self._buffer[chunk_number % self.cells_in_buffer][:, bitplane_number % 2] |= (bitplane << bitplane_number//2)

            return chunk_number



        def record_send_and_play(indata, outdata, frames, time, status):
            print('indata')
            print(indata)
            self.bitplane_number = 0

            self.recorded_chunk_number += 1
            for j in range(16):
                bit_plane_weight = ((indata >> self.bits_number - j) & 1)[:, 0]

                #send 1st channel
                bit_plane_weight = bit_plane_weight.astype(np.uint8)
                bit_plane_weight = np.packbits(bit_plane_weight)
                message = struct.pack(self.packet_format, self.bitplane_number, self.recorded_chunk_number, *bit_plane_weight)
                self.bitplane_number += 1
                self.sending_sock.sendto(message, (self.destination_IP_addr, self.destination_port))

                bit_plane_weight = ((indata >> self.bits_number - j) & 1)[:, 1]
                # send 2nd channel
                bit_plane_weight = bit_plane_weight.astype(np.uint8)
                bit_plane_weight = np.packbits(bit_plane_weight)
                message = struct.pack(self.packet_format, self.bitplane_number, self.recorded_chunk_number,
                                      *bit_plane_weight)
                self.bitplane_number += 1
                self.sending_sock.sendto(message, (self.destination_IP_addr, self.destination_port))



            chunk = self._buffer[self.played_chunk_number % self.cells_in_buffer]
            print('chunk')
            print(chunk)
            self._buffer[self.played_chunk_number % self.cells_in_buffer] = self.generate_zero_chunk()
            self.played_chunk_number = (self.played_chunk_number + 1) % self.cells_in_buffer
            outdata[:] = chunk



            if __debug__:
                sys.stderr.write(".");
                sys.stderr.flush()

        with sd.Stream(samplerate=self.frames_per_second, blocksize=self.frames_per_chunk, dtype=np.int16,
                       channels=self.number_of_channels, callback=record_send_and_play):
            print("-=- Press CTRL + c to quit -=-")
            first_received_chunk_number = receive_and_buffer()
            self.played_chunk_number = (first_received_chunk_number - self.chunks_to_buffer) % self.cells_in_buffer
            while True:
                receive_and_buffer()



if __name__ == "__main__":
    intercom = Intercom_bitplanes()
    parser = intercom.add_args()
    args = parser.parse_args()
    intercom.init(args)
    intercom.run()
