import sounddevice as sd
import intercom as inter
import numpy
import socket
import struct

if __debug__:
    import sys


class IntercomBuffer(inter.Intercom):

    def run(self):
