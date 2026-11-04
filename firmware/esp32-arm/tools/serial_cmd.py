"""Send one line to the esp32-arm firmware and print the reply.

Inputs: serial port name, then the command words.
Outputs: firmware lines until a short quiet gap.
"""

import argparse
import sys
import time

import serial


def main() -> int:
    parser = argparse.ArgumentParser(description="talk to esp32-arm over serial")
    parser.add_argument("port", help="com port, for example COM7")
    parser.add_argument("command", nargs="+", help="firmware command words")
    parser.add_argument("--baud", type=int, default=115200)
    args = parser.parse_args()

    line = " ".join(args.command) + "\n"
    with serial.Serial(args.port, args.baud, timeout=0.2) as ser:
        time.sleep(0.3)
        ser.reset_input_buffer()
        ser.write(line.encode("ascii"))
        end = time.time() + 2.5
        quiet_from = time.time()
        while time.time() < end:
            chunk = ser.read(256)
            if chunk:
                sys.stdout.write(chunk.decode("ascii", errors="replace"))
                quiet_from = time.time()
            elif time.time() - quiet_from > 0.4:
                break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
