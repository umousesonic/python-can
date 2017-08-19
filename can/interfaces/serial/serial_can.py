# -*- coding: utf-8 -*-
"""
A text based interface. For example use over serial ports like
"/dev/ttyS1" or "/dev/ttyUSB0" on Linux machines or "COM1" on Windows.
The interface is a simple implementation that has been used for
recording CAN traces.

"""

import logging

logger = logging.getLogger('can.serial')

try:
    import serial
except ImportError:
    logger.warning("You won't be able to use the serial can backend without "
                   "the serial module installed!")
    serial = None

from can.bus import BusABC
from can.message import Message


class SerialBus(BusABC):
    """
    Enable basic can communication over a serial device.
    """

    def __init__(self, channel, *args, **kwargs):
        """
        :param str channel:
            The serial device to open. For example "/dev/ttyS1" or
            "/dev/ttyUSB0" on Linux or "COM1" on Windows systems.
        :param int baudrate:
            Baud rate of the serial device in bit/s (default 115200).

            .. note:: Some serial port implementations don't care about the baud
                      rate.

        :param float timeout:
            Timeout for the serial device in seconds (default 0.1).
        """

        if channel == '':
            raise ValueError("Must specify a serial port.")
        else:
            self.channel_info = "Serial interface: " + channel
            baudrate = kwargs.get('baudrate', 115200)
            timeout = kwargs.get('timeout', 0.1)
            self.ser = serial.Serial(channel, baudrate=baudrate, 
                                     timeout=timeout)
        super(SerialBus, self).__init__(*args, **kwargs)

    def shutdown(self):
        """
        Close the serial interface.
        """
        self.ser.close()

    def send(self, msg, timeout=None):
        """
        Send a message over the serial device.

        :param can.Message msg:
            Message to send.

            .. note:: Flags like extended_id, is_remote_frame and is_error_frame
                      will be ignored.

            .. note:: If the timestamp a float value it will be convert to an
                      integer.

        :param timeout:
            This parameter will be ignored. The timeout value of the channel is
            used.
        """
        if isinstance(msg.timestamp, float):
            msg.timestamp = int(msg.timestamp)
        timestamp = msg.timestamp.to_bytes(4, byteorder='little')
        a_id = msg.arbitration_id.to_bytes(4, byteorder='little')
        dlc = msg.dlc.to_bytes(1, byteorder='little')
        byte_msg = bytes([0xAA]) + timestamp + dlc + a_id + msg.data + \
                   bytes([0xBB])
        self.ser.write(byte_msg)

    def recv(self, timeout=None):
        """
        Read a message from the serial device.

        :param timeout:
            This parameter will be ignored. The timeout value of the channel is
            used.
        :returns:
            Received message.

            .. note:: Flags like extended_id, is_remote_frame and is_error_frame
              will not be set over this function, the flags in the return
              message are the default values.

        :rtype:
            can.Message
        """
        try:
            # ser.read can return an empty string ''
            # or raise a SerialException
            rx_byte = self.ser.read()
        except serial.SerialException:
            return None

        if len(rx_byte) and ord(rx_byte) == 0xAA:
            s = bytearray(self.ser.read(4))
            timestamp = int.from_bytes(s, byteorder='little', signed=False)
            dlc = ord(self.ser.read())

            s = bytearray(self.ser.read(4))
            arb_id = int.from_bytes(s, byteorder='little', signed=False)

            data = self.ser.read(dlc)

            rxd_byte = ord(self.ser.read())
            if rxd_byte == 0xBB:
                # received message data okay
                return Message(timestamp=timestamp, arbitration_id=arb_id,
                               dlc=dlc, data=data)
            else:
                return None

        else:
            return None
