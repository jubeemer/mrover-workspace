import Adafruit_BBIO.GPIO as GPIO
import asyncio
from rover_msgs import MosfetCmd, AutonState
from rover_common import aiolcm


lcm_ = aiolcm.AsyncLCM()
leg_done = False

async def leg_complete_led():
    led_cmd = MosfetCmd()
    led_cmd.device = MosfetCmd.DEV2 # TODO: change device
    while True:
        if leg_done:
            # Flash Leg Complete LED 3 times
            for i in range(0, 3):
                cmd.enable = 1
                lcm_.publish("/mosfet_cmd", led_cmd.encode())
                await asyncio.sleep(1)
                cmd.enable = 0
                lcm_.publish("/mosfet_cmd", led_cmd.encode())
                await asyncio.sleep(1)
        else:
            cmd.enable = 0
            lcm_.publish("/mosfet_cmd", led_cmd.encode())

        await asyncio.sleep(0.1)



def auton_state_callback(channel, msg):
    state = AutonState.decode(msg)

    auton_led_cmd = MosfetCmd()
    auton_led_cmd.device = MosfetCmd.DEV0 # TODO: change device
    auton_led_cmd.enable = state.is_auton

    teleop_led_cmd = MosfetCmd()
    teleop_led_cmd.device = MosfetCmd.DEV1 # TODO: change device
    teleop_led_cmd.enable = not state.is_auton

    # TODO: Update according to how Elizabeth updates the AutonState LCM
    # leg_done = state.???

    lcm_.publish("/mosfet_cmd", auton_led_cmd.encode())
    lcm_.publish("/mosfet_cmd", teleop_led_cmd.encode())


def main():
    lcm_.subscribe("/auton", auton_state_callback)

    run_coroutines(lcm_.loop(), leg_complete_led())


if __name__ == "__main__":
    main()