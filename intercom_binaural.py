# Exploiting binaural redundancy.

from intercom_bitplanes import Intercom_bitplanes

class Intercom_binaural(Intercom_bitplanes):

    def init(self, args):
        Intercom_bitplanes.init(self, args)
        if self.number_of_channels == 2:
            self.record_send_and_play = self.record_send_and_play_stereo

    def record_send_and_play_stereo(self, indata, outdata, frames, time, status):
        indata[:, 1] = indata[:, 0] - indata[:, 1]
        self.send(indata)
        self.recorded_chunk_number = (self.recorded_chunk_number + 1) % self.MAX_CHUNK_NUMBER
        chunk = self._buffer[self.played_chunk_number % self.cells_in_buffer]
        self._buffer[self.played_chunk_number % self.cells_in_buffer] = self.generate_zero_chunk()
        self.played_chunk_number = (self.played_chunk_number + 1) % self.cells_in_buffer
        chunk[:, 1] = chunk[:, 0] + chunk[:, 1]
        outdata[:] = chunk

if __name__ == "__main__":
    intercom = Intercom_binaural()
    parser = intercom.add_args()
    args = parser.parse_args()
    intercom.init(args)
    intercom.run()
