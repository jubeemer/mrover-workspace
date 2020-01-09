# i2c driver for motorcontrollers

import os
import fcntl
import array as arr
import asyncio
from rover_common import aiolcm
from rover_common.aiohelper import run_coroutines
from rover_msgs import Control, Telemetry

lcm_ = aiolcm.AsyncLCM()

I2C_SLAVE = 0x0703

TELEMETRY_SIZE = 17
CONTROL_SIZE = 6
filename = "/dev/i2c-2"
I2C_FD = 0

START_DELIMITER = 0xFF
END_DELIMITER = 0xAA


def fxp_10_22_to_float(fxp, signed=False):
    CONVERSION_CONST = 0.0000002384185791015625
    raw = float(fxp)
    return raw * CONVERSION_CONST


def control_callback(channel, msg):
    cmd = Control.decode(msg)

    # Create byte array to be transmitted
    control_msg = arr.array('B', [0, 0, 0, 0, 0, 0, 0])
    control_msg[0] = 0xFF & START_DELIMITER
    control_msg[1] = 0xFF & ((cmd.controlMode & 0x3F) << 2)
    control_msg[1] |= 0xFF & ((cmd.motorAddr & 0x300) >> 8)
    control_msg[2] = 0xFF & cmd.motorAddr
    control_msg[3] = 0xFF & (cmd.setpoint >> 8)
    control_msg[4] = 0xFF & (cmd.setpoint)
    control_msg[5] = 0xFF & END_DELIMITER

    # Write bytes to I2C bus
    bytes_written = os.write(I2C_FD, control_msg)
    if(bytes_written != CONTROL_SIZE):
        print("I2C write failed.")


async def get_telemetry():
    telemetry = Telemetry()
    while True:
        # Perform read of telemetry data from Nucleo
        telemetry_packet = os.read(I2C_FD, TELEMETRY_SIZE)
        print('i2c read')

        vel_bytes = telemetry_packet[11] << 24
        vel_bytes |= telemetry_packet[12] << 16
        vel_bytes |= telemetry_packet[13] << 8
        vel_bytes |= telemetry_packet[14]
        vel_bytes &= 0xFFFFFFFF

        # Pack bytes into LCM message
        telemetry.ID = (telemetry_packet[1] << 8) | telemetry_packet[2]
        telemetry.ENCODER = (telemetry_packet[3] << 8) | telemetry_packet[4]
        telemetry.ISENA = (telemetry_packet[5] << 8) | telemetry_packet[6]
        telemetry.ISENB = (telemetry_packet[7] << 8) | telemetry_packet[8]
        telemetry.ISENC = (telemetry_packet[9] << 8) | telemetry_packet[10]
        telemetry.VELOCITY = fxp_10_22_to_float(vel_bytes, signed=False)
        telemetry.SWITCH = telemetry_packet[15]

        # Publish LCM message
        lcm_.publish('/telemetry', telemetry.encode())

        # 100 Hz
        await asyncio.sleep(0.01)


def main():
    I2C_FD = os.open(filename, os.O_RDWR)
    if (I2C_FD < 0):
        print("Failed to open the bus")
        exit(1)

    devAddr = 15
    if(fcntl.ioctl(I2C_FD, I2C_SLAVE, devAddr) < 0):
        print("Failed to acquire bus access or talk to slave")

    lcm_.subscribe("/control", control_callback)
    run_coroutines(get_telemetry(), lcm_.loop())


if(__name__ == "__main__"):
    main()
