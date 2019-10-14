import sounddevice as sd
import intercom as inter
import numpy
import socket
import struct

if __debug__:
    import sys


class IntercomBuffer(inter.Intercom):

    def run(self):
        sending_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        receiving_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        listening_endpoint = ("0.0.0.0", self.listening_port)
        receiving_sock.bind(listening_endpoint)
        self.buffer_size = 8
        self.messagebuffer = [numpy.zeros(
                    (self.samples_per_chunk, self.bytes_per_sample),
                    self.dtype)] * self.buffer_size
        self.sent_counter = 0
        self.received_counter = 0
        #formatowanie network (big endian), indeks, przesyłane wartości
        self.str = '!H{}h'.format(self.samples_per_chunk * self.number_of_channels)
        self.max_value_counter = 2**16


        def receive_and_buffer():

            messagepack, source_address = receiving_sock.recvfrom(
                inter.Intercom.max_packet_size)

            #rozpakowywanie indeksu i wszystkich elementów listy
            index, *msg = struct.unpack(self.str, messagepack)

            #asarray - przekształcanie listy do tablicy
            #umieszczanie otrzymanych wartości w bufferze
            self.messagebuffer[index % self.buffer_size + (self.buffer_size/2)] =\
                numpy.asarray(msg).reshape(self.samples_per_chunk, self.number_of_channels)

        def record_send_and_play(indata, outdata, frames, time, status):
            #interpretuje buffer jako jedno wymiarową tablice
            msg = numpy.frombuffer(indata, numpy.int16)

            #zwraca spakowanego stringa, indeks i wiadomość
            dataStruct = struct.pack(self.str, self.sent_counter, *msg)

            sending_sock.sendto(
                dataStruct,
                (self.destination_IP_addr, self.destination_port))

            #Jeśli przekroczymy możliwą liczbę w liczniku wysłanych odliczamy od zera
            self.sent_counter = (self.sent_counter+1) % self.max_value_counter

            #odcztujemy widomosc z buffera i zapisujemy ja do zmiennej message
            message = self.messagebuffer[self.received_counter % self.buffer_size]

            #zerujemy miejsce z którego odczytaliśmy
            self.messagebuffer[self.received_counter % self.buffer_size] = numpy.zeros(
                    (self.samples_per_chunk, self.bytes_per_sample),
                    self.dtype)

            self.received_counter += 1

            outdata[:] = message
            if __debug__:
                sys.stderr.write(".");
                sys.stderr.flush()

        with sd.Stream(
                samplerate=self.samples_per_second,
                blocksize=self.samples_per_chunk,
                dtype=self.dtype,
                channels=self.number_of_channels,
                callback=record_send_and_play):
            print('-=- Press <CTRL> + <C> to quit -=-')
            while True:
                receive_and_buffer()


if __name__ == "__main__":
    intercom = IntercomBuffer()
    args = intercom.parse_args()
    intercom.init(args)
    intercom.run()
