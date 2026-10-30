# Safety MCU — Nucleo Build Guide

**What this is:** the guide we follow while building the VAYN Safety MCU.
**Board:** NUCLEO-G474RE (STM32G474RET6), the board named in the RT purchase list.
**Follows:** [VAYN-6.2](../VAYN%20-%206.2.md) §7, §49–§52, §78, and [VAYN-6.2.1](../VAYN%20-%206.2.1.md) I-12, I-13, I-14, §9.
**Date:** 2026-10-30

Read this from the top the first time. After that, use the phase you are in. Do not skip a phase because the next one looks more useful. Each phase has a pass test. The next phase starts only after that test passes.

This is a bench guide for one shoulder on a tethered rig. It is not a certified safety system. A later robot that people can stand next to needs a second independent channel, a safety-rated contactor, and a written hazard analysis. VAYN-6.2.1 I-15 already requires that analysis. This guide does not replace it.

---

# 1. What this board is for

VAYN-6.2 has three computers:

| Computer | Job | Does a build guide exist? |
| --- | --- | --- |
| Jetson Orin NX | Think. Cameras, language, predictions, motion ideas. | The architecture is in VAYN-6.2. A build guide of this kind does not exist yet. |
| RT core (Dell Latitude 5490) | Move. It owns the motors, the limits, and the stop ramps. | Yes. [RT Core Implementation](RT%20Core%20Implementation%20-%20VAYN%206.2.1.md) and [RT Core from fundamentals](RT%20Core%20-%20From%20Fundamentals%20to%20Advanced.md). |
| Safety MCU (this board) | Survive. It watches, and it can remove motor power. It does not steer the arm. | This document. |

The Safety MCU has four jobs, and only these four:

```text
Supervise
Detect a fault
Constrain
Disable
```

It does not plan motion. It does not hold the arm up. It does not replace the RT core. If the RT core dies, this board removes power. On this shoulder, removing power lets the arm fall. That is why the arm stays tied to the rig until a brake exists.

---

# 2. Rules we do not break

These come from the frozen baseline. A later idea that breaks one of them is a design change, not a shortcut.

1. The emergency stop is a real button in the wire. A button on a screen is not an emergency stop. ISO 13850 and IEC 60204-1 describe the emergency stop. IEC 60204-1 says that stop must be category 0 or category 1. Category 2 leaves power on, so it is not an emergency stop. NFPA 79 asks for a self-latching button. The contact must be opened by the button itself, not by a spring in the mechanism (Rockwell 800-WP008).
2. Pressing reset must not start the motor. Reset only allows a new start. A person still has to permit power.
3. CAN is a way to listen. It is not the only way to be safe. A stuck CAN chip can freeze the RT core and this board at the same time (VAYN-6.2.1 I-13).
4. The ODESC 3.6 has no safe-torque-off pin. The only category-0 stop we can make is to open the DC power (VAYN-6.2.1 I-14).
5. If the Jetson dies and the RT core is still healthy, do **not** cut power. The RT core is supposed to keep the arm under control. Cutting power in that case drops the arm for no safety reason.
6. If this board resets, crashes, or loses its own power, the motor power must fall open by itself. The safe state is "coil off".
7. This board never sends `clear_errors`, `set_input_pos`, or any other motion command. Those commands are listed in `odrive/backend/app/can_bus.py`.

Stop words, so the rest of the guide stays short:

| Word | Plain meaning |
| --- | --- |
| Category 0 | Power off now. The arm is not guided down. |
| Category 1 | Slow down under power, then power off. |
| Category 2 | Slow down and keep holding. The RT core does this. This board does not. |
| Contactor | A relay big enough for the motor supply. Contacts closed = motors can have power. |
| Permit | The signal that means "you may close the contactor". |
| Latch | A fault that stays until a person clears it. It does not clear itself. |

---

# 3. Parts

Buy these before Phase E. Phases A–D need only the first three rows.

| Part | What to buy | Why |
| --- | --- | --- |
| Board | NUCLEO-G474RE. The chip is STM32G474RET6. The board code is MB1367. | Named in the RT purchase list. It has FDCAN, an independent watchdog, and ADCs. |
| CAN transceiver | TJA1051**T/3** or TCAN1042, 3.3 V logic. A module is fine. | The Nucleo has no CAN transceiver (UM2505). The plain TJA1051 without `/3` speaks 5 V logic and can damage PA11/PA12. |
| USB cable | Data cable, Micro-B, to the ST-LINK connector CN1. | Powers the board and programs it. A charge-only cable looks like a dead board. |
| NTC | 10 kΩ, beta about 3435–3950. Already in the shoulder BOM. | Hard temperature limit. The ODESC pin GPIO4 is the encoder chip-select, so this NTC does not go to the drive (gate G-6). |
| Contactor or DC relay | DC-rated contacts for the bench current. Coil voltage written on the part. | Opens the 24 V bus. An AC relay welds on DC. |
| Small MOSFET | Logic-level N-MOSFET, for example AO3400 class. Plus a 1N4007 across the coil. | A Nucleo pin cannot drive a coil. |
| E-stop | Red mushroom, twist to release, at least two normally-closed contacts. | One contact cuts power. One contact tells this board the button is down. |
| Fuse | DC fuse, about 15 A, before the contactor. | Protects the wire if the contactor welds. |
| Resistors | 10 kΩ pull-downs, 100 Ω series, 120 Ω only if this node is a bus **end**. | See the wiring section. |
| 5 V brick | Small supply for this board only, if you leave USB unplugged during motion. | This board must stay alive when the motor supply is cut. |

Do not power this board from the ODESC 5 V pin. When the contactor opens, that 5 V dies, the board resets, and you cannot tell why.

---

# 4. How the power wires must work

Draw this and check it before any wire is cut.

```text
Motor 24 V supply
    │
   fuse
    │
 E-stop contact A (normally closed, opens when the button is down)
    │
 contactor main contacts (open unless the coil is powered)
    │
 ODESC DC+

E-stop contact B (also normally closed) ──► PB10 on the Nucleo
                                              (high = button not pressed)

Contactor coil:
    coil +  ── coil supply (same 24 V, taken BEFORE the contactor contacts)
    coil −  ── MOSFET drain
    MOSFET source ── ground
    MOSFET gate ── 100 Ω ── PB11 (permit pin)
                   └── 10 kΩ ── ground
    diode across the coil, stripe toward coil +

Nucleo power: USB or its own 5 V brick. Not the motor rail after the E-stop.
```

Why the gate has a pull-down: after reset, an STM32 pin is not driving. A floating gate can turn the MOSFET on from noise. The 10 kΩ holds the gate off. The board must drive PB11 **high** to allow power. Low, reset, or unplugged all mean power off.

Why the E-stop is in series with the contactor: if this firmware is wrong and holds PB11 high, the mushroom still cuts power. If the mushroom welds, this board can still open the contactor. Two different parts have to fail at once.

The E-stop contact that goes to PB10 needs a pull-up turned on inside the chip. Button not pressed: contact closed, pin reads low (wire it to ground through the contact). Button pressed: contact open, pull-up makes the pin high. If the wire falls off, the pin also reads high, and we treat that as "button pressed". A broken wire must not look like "all is well".

---

# 5. Pins we will use

Confirm each pin in STM32CubeMX before soldering. The names below match the board manual UM2505 and the Zephyr board file for this Nucleo.

| Signal | Pin | Notes |
| --- | --- | --- |
| CAN RX | PA11 | FDCAN1 RX. On the ST morpho header CN10. |
| CAN TX | PA12 | FDCAN1 TX. On CN10. |
| NTC analog | PA1 | Arduino A1. ADC. Do not use PA0. |
| E-stop sense | PB10 | Arduino D6. Internal pull-up. |
| Permit (coil) | PB11 | Output. Must come up low. External 10 kΩ to ground. |
| Transceiver silent | PB12 | High = transmitter off. External pull-up to 3.3 V so reset means silent. |
| User button B1 | PA0 | Already on the board. Used only as "person permits power". |
| Green LED LD2 | use the board LED | Heartbeat blink. CubeMX knows the pin. |

PA0 is the user button in UM2505. Do not also use it as the temperature input.

CAN transceiver wiring (TJA1051T/3):

| Transceiver pin | Goes to |
| --- | --- |
| TXD (1) | PA12 |
| GND (2) | Nucleo GND |
| VCC (3) | Nucleo 5 V |
| RXD (4) | PA11 |
| VIO (5) | Nucleo 3.3 V |
| CANL (6) | CAN low of the bus |
| CANH (7) | CAN high of the bus |
| S (8) | PB12, and a pull-up to 3.3 V |

S high means silent: it can still hear, and it cannot talk (NXP TJA1051). That is the safe default. We drive S low only after the self-test, and only if we have a reason to transmit. In the first CAN phases we stay silent forever. Listening does not need S low.

Put this board in the **middle** of the CAN cable, not at a new end. The bus already has two 120 Ω resistors at the two ends. A third resistor makes the bus look sick: frames arrive sometimes and then stop.

---

# 6. The state machine

One machine. Every phase of the firmware uses this same machine. Early phases simply have fewer inputs.

```text
BOOT
  self-test, permit pin forced low, transceiver silent
    │
    ▼
SAFE_OFF          contactor open, fault lamp steady
    │  person presses B1, and no fault is present
    ▼
PERMITTED         contactor may close
    │  a fault is true
    ▼
LATCHED_FAULT     contactor open, stays open
    │  person presses B1 again, after the fault is gone
    ▼
SAFE_OFF
```

There is no arrow from LATCHED_FAULT to PERMITTED by itself. Time passing does not clear a fault. A CAN frame does not clear a fault. Releasing the E-stop does not clear a fault. Only the blue button does, and only when the checks are clean.

At boot, start in SAFE_OFF even if the last run was fine. Power returning must not move the arm.

---

# 7. What we listen to on CAN

ODrive CAN id = `node_id << 5 | command`. Node 0 is the shoulder. The codec is `odrive/backend/app/can_bus.py`.

| Id | Who sends it | What we do with it |
| --- | --- | --- |
| 0x001 | ODESC heartbeat, every 10 ms | Bytes: axis error as uint32, then axis state as uint8, little-endian. Error not zero = drive fault. |
| 0x009 | Encoder reply, when the RT core polls | Two floats: motor turns, motor turns per second. Listen only. Do not send the poll. |
| 0x014 | Current reply | Two floats: setpoint amps, measured amps. |
| 0x017 | Bus voltage reply | One float, volts. |
| 0x040 | RT core heartbeat. **Not sent yet.** | Our frame. See below. |

Do not give any ODrive the node id 2. Id 0x040 is what a node-2 heartbeat would look like. If someone sets a drive to node 2, this board will treat drive frames as the RT heartbeat.

RT heartbeat, sent by the RT core every 20 ms, standard 11-bit id 0x040:

| Bytes | Field |
| --- | --- |
| 0–3 | sequence, uint32, +1 each frame |
| 4 | lifecycle byte from the RT core |
| 5 | 1 if the RT core is in control, 0 if not |
| 6–7 | CRC-16 of bytes 0–5 |

This frame does not exist in the RT code today. Phase C adds it. Until that code is on the laptop, the "RT heartbeat missing" check stays **off**. Turning it on before the sender exists would open the contactor all the time.

We do not send RTR polls. The RT core already polls. We only read the answers. A safety board that polls can, by accident, feed the ODESC watchdog and hide a dead RT core. On firmware 0.5.x, almost every CAN frame to the axis feeds that watchdog.

---

# 8. Limits used by this board

One header file, `safety_limits.h`. No limit is typed a second time inside the logic.

| Check | Value we start from | Where it comes from | Status |
| --- | --- | --- | --- |
| Drive heartbeat gap | 50 ms (five missed 10 ms frames) | RT spec heartbeat is 10 ms | use |
| RT heartbeat gap | 100 ms (five missed 20 ms frames) | this guide | off until the sender exists |
| Orin heartbeat gap | record only | VAYN-6.2 §51 lists it | must **not** cut power |
| Measured current above peak | 30 A for 100 ms | `vayn_shoulder.yaml` `current_peak_a` | backstop, not the normal limit |
| Bench bus voltage | below 18 V or above 30 V for 50 ms | bench is 24 V; 6.2.1 says set the drive trip near 28 V | bench only |
| Later battery window | 18 V to 52 V | same yaml `power` block | do not use on the 24 V bench |
| NTC warn | 80 °C | yaml `thermal.motor_warn_c` | unproven |
| NTC abort | 100 °C | yaml `thermal.motor_abort_c` | unproven, gate G-6 still open |
| NTC reading | near 0 or near 4095 | this guide | sensor fault = abort |
| E-stop | sense pin high | wiring section | cut, in hardware and in software |

The yaml file itself says unproven values must be replaced by measurements. When a thermal test changes `motor_abort_c`, change this header the same day. Print the compiled numbers on the serial port at boot so a wrong build is obvious.

The drive watchdog in that yaml is 0.5 s. The RT spec talks about 50 ms. Those are not the same number. This board does not depend on either one. It has its own timers.

---

# 9. Phases

Each phase has five fields: goal, wiring, firmware, pass test, and what usually goes wrong. Stay in the phase until the pass test is true three times in a row, not once.

## Phase A — the board is alive, and nothing else is connected

**Goal.** Prove the Nucleo, the cable, and the tools. No CAN parts. No coil. No motor supply.

**Wiring.** USB only, into CN1.

**Firmware.**

1. Install STM32CubeIDE and STM32CubeProgrammer.
2. In CubeMX pick the board NUCLEO-G474RE, not a bare chip and not NUCLEO-G431RB. The G431 is a different board that was suggested for the sensor MCU.
3. Clock from the internal HSI is enough in this phase. Do not enable FDCAN yet.
4. Blink LD2 at 1 Hz.
5. Print one line on the ST-LINK virtual COM port: `safety mcu phase A`.
6. Do not enable the independent watchdog yet. A watchdog plus a breakpoint looks like a dead board.

**Pass test.** The LED blinks. The serial line appears. Pressing B1 prints `button`. Unplugging USB turns the LED off within a second.

**What you will face.**

| What you see | Cause | What to do |
| --- | --- | --- |
| Windows shows an unknown USB device | ST-LINK driver, or the cable is charge-only | Install the ST-LINK driver. Try another cable. UM2505 says Windows 10 usually has the driver, older Windows does not. |
| LD3 (5 V) is off | The board is not getting 5 V | Check JP5. The default is USB power, pins 1–2. |
| LD1 (COM) stays off and the IDE cannot connect | ST-LINK firmware is old, or JP1 is fitted | Remove JP1. Update ST-LINK firmware from STM32CubeProgrammer. |
| The demo LED changes when you press B1, then your program does not run | The factory demo is still in flash, or you downloaded to the wrong chip | The demo is normal on a new board (UM2505 §3.3). Download again and hit reset. |
| Download fails at "target not found" | You picked the wrong board | CubeMX device must be STM32G474RE. |
| Serial port opens and then vanishes | The ST-LINK rebooted because the IDE started a debug session | Close the port and reconnect. This is normal. |

## Phase B — safe outputs, still no motor

**Goal.** Prove the permit pin, the silent pin, the watchdog, and the state machine. Use an LED in place of the MOSFET.

**Wiring.** LED plus 1 kΩ from PB11 to ground. LED on means "this would have closed the contactor". Second LED on PB12 if you want to see silent mode.

**Firmware.**

1. At the first line after pin init, write PB11 low and PB12 high.
2. Run the state machine from §6 with no CAN and no NTC. The only fault input is a test flag you set from the serial port (`fault 1`, `fault 0`).
3. B1 moves SAFE_OFF → PERMITTED only when the test fault is clear.
4. Turn on the independent watchdog (IWDG), about 100 ms. Feed it from the main loop only. Do not feed it from an interrupt that keeps running while the main loop is stuck.
5. In the debugger, freeze the watchdog while stopped (DBG stop of IWDG). The rig build must not freeze it. Use two build flags: `DEBUG` and `RIG`.

**Pass test.**

- Power-up: permit LED is off.
- Press B1: permit LED turns on.
- Send `fault 1`: permit LED turns off and stays off after `fault 0`.
- Press B1 again: LED comes back.
- Add a `while(1)` in the loop: the board resets within about 100 ms and the LED is off after the reset.
- Hold the debugger paused for one second in a `DEBUG` build: it does not reset. The same pause in a `RIG` build does reset.

**What you will face.**

| What you see | Cause | What to do |
| --- | --- | --- |
| Permit LED flashes once at plug-in | CubeMX set the pin high before your code runs | Set the pin's GPIO init level to low. Check it with a scope or the LED, not by reading the code only. |
| Watchdog resets the board in normal blink code | The feed is after a long `HAL_Delay`, or the reload is too short | Feed once per loop. Measure the loop time. Keep the timeout at 100 ms. |
| The board resets only when the debugger is attached | Watchdog runs while the CPU is halted | Freeze IWDG in debug, and only in the DEBUG build. |
| Reset reason is a mystery | You did not read the reset flags | At boot, print RCC reset flags (watchdog, pin, brown-out) and then clear them. |
| B1 does nothing | The button pin is wrong | UM2505 lists the user button on PA0. Trust CubeMX's board view if it disagrees, and write down which one you measured with a meter. |

## Phase C — listen to CAN, still no coil

**Goal.** Hear the ODESC heartbeat and, later, the RT heartbeat. Transmitter stays silent.

**Wiring.** Transceiver as in §5. Twisted pair to the existing bus. No extra 120 Ω. Common ground with the ODESC logic ground. Motor supply may be on, because the drive must be powered to speak. The arm stays tied down. Permit LED only. MOSFET not fitted.

**Firmware.**

1. FDCAN1, classic CAN, 1 Mbit/s, sample point near 80 %. Not CAN FD. The drive firmware is 0.5.1 and speaks classic CAN.
2. Filter so we accept 0x001, 0x009, 0x014, 0x017, and 0x040. Drop the rest.
3. S pin stays high. If a transmit function is called in this phase, that is a bug. Assert in debug.
4. Print, once a second: last heartbeat age, axis error, axis state, last current, last bus voltage.
5. RT-heartbeat check compiled out until the laptop sends 0x040.

**Pass test.** With the RT core or the existing CAN tool running: heartbeat age stays under 20 ms for ten minutes. Unplug the CAN pair: age climbs, and the serial line says `drive silent`. Plug it back: age recovers. The permit LED never turns on in this phase, because we have not reached PERMITTED with a coil. You can still walk the state machine with B1 and confirm a silent drive forces LATCHED_FAULT once you enable that check.

**What you will face.**

| What you see | Cause | What to do |
| --- | --- | --- |
| No frames at all | TX and RX swapped, or transceiver VCC/VIO missing, or the bus is off | Swap PA11/PA12 once. Check 5 V on VCC and 3.3 V on VIO. |
| Frames on the laptop sniffer, none on this board | This board is not on the same two wires, or its ground is missing | CAN needs CANH, CANL, and a shared ground. |
| Errors come and go | Three terminators, or the pair is running next to the motor phase wires | Remove the extra 120 Ω. Reroute the pair. |
| The drive watchdog no longer trips when the laptop stops | This board is transmitting | S must be high. A logic analyzer on PA12 must show no activity. |
| Heartbeat id is not 0x001 | The drive node id is not 0 | Fix the drive. Do not "just listen to whatever arrives". |
| Lots of error frames after you join | Bit timing, or a 5 V transceiver on a 3.3 V pin | Recalculate the bit time in CubeMX. Confirm the chip marking says TJA1051T/3. |
| You halt in the debugger and the bus dies | The CAN controller stops clocking while halted, or the watchdog reset the chip and the pin glitched | Same debug-freeze rule as Phase B. On the rig, do not leave the debugger attached during motion. |
| Bus-off | Too many error frames. The controller gives up. | On bus-off, go to LATCHED_FAULT. Do not auto-retry forever in the rig build. A retry loop can sit there while the arm is live. |

## Phase D — temperature sensor, still no coil

**Goal.** Read the 10 kΩ NTC and reject a broken sensor.

**Wiring.** 10 kΩ from 3.3 V to PA1. NTC from PA1 to ground. 100 nF from PA1 to ground. Twist the NTC leads. Keep them off the motor phase wires.

**Firmware.** Beta equation, with beta taken from the bag the sensor came in, not from memory. Sample 16 times and average. Convert to °C.

Open or short: ADC under about 50 or over about 4045 is a sensor fault, not a cold or hot motor. Sensor fault is an abort once this check is enabled.

Two builds:

- `BENCH_NO_NTC` — check off. Serial line prints `NTC CHECK OFF` every second. Not allowed on the rig.
- `RIG` — check on. If the header still says the abort temperature is unproven, print `NTC LIMIT UNPROVEN` every second. You may still run on the tethered rig. You may not pretend the number is final.

**Pass test.** Room reading within 3 °C of a room thermometer. Hold the sensor: the number rises. Unplug the sensor: fault. Short the sensor: fault. Warm it past the warn point with a heat gun on low, from a distance: warn, and it does not need to hit abort during this test if you cannot do it safely. Write the readings down.

**What you will face.**

| What you see | Cause | What to do |
| --- | --- | --- |
| Reading stuck at −40 or similar | NTC open, or the pull-up is missing | Meter the divider with the board off. |
| Reading stuck at the top | NTC shorted, or PA1 is also used by another function | Check CubeMX. PA1 must be analog only. |
| Number jumps by tens of degrees | Motor wires too close, or no capacitor | Add the 100 nF. Reroute. |
| Fine on the desk, nonsense on the robot | The sensor ground is not the Nucleo ground | Run the return wire back to the Nucleo, not to a random screw. |
| You used PA0 and the button acts weird | PA0 is the user button | Move the NTC to PA1. |

## Phase E — the coil, with a lamp instead of the robot

**Goal.** Prove the MOSFET, the diode, and the latch. The ODESC is not in this circuit yet.

**Wiring.** Full coil circuit from §4, but the contactor's **main** contacts feed a lamp on a bench supply, not the ODESC. The mushroom contact A is in that lamp circuit too.

**Firmware.** Same state machine. PERMITTED drives PB11 high. Any fault drives it low and latches. E-stop sense is now a real input.

**Pass test.** Do these in order.

1. Plug in. Lamp is off.
2. Press B1. Lamp is on.
3. Press the mushroom. Lamp goes off **even if you force PB11 high with a jumper**. That proves the button is in the wire, not only in the code.
4. Twist the mushroom back up. Lamp stays off.
5. Press B1. Lamp comes on.
6. Pull the E-stop sense wire off PB10. The board must latch off. A loose wire is a fault.
7. Stop feeding the watchdog in a test build. The board resets and the lamp is off.
8. Kill board power and restore it. Lamp stays off until B1.

**What you will face.**

| What you see | Cause | What to do |
| --- | --- | --- |
| Lamp on at the first moment of power | Gate pull-down missing, or the pin boots high | Fit the 10 kΩ. Fix the init level. Do not continue. |
| MOSFET gets hot with the lamp off | Gate is floating in the middle | Measure the gate. It must be near 0 V when off and near 3.3 V when on. |
| Coil clicks and the MOSFET dies | No diode | The coil kicks when it turns off. Stripe of the diode toward coil +. |
| Lamp stays on after the firmware opens the coil | Contacts welded, or you are looking at the wrong circuit | This is why the lamp test exists. Replace the relay before it ever sees the motor. |
| E-stop kills the Nucleo too | The Nucleo was powered from the motor rail | Move the Nucleo to USB or its own brick. |
| Coil supply is 24 V and the MOSFET is a small signal part rated 20 V | Wrong MOSFET | Drain voltage must be rated above the coil voltage, with margin. |

## Phase F — on the rig, power cut only

**Goal.** The contactor now feeds the ODESC. The arm is tied. Motion is not the point. Cutting power is the point.

**Wiring.** §4 for real. CAN from Phase C stays. NTC from Phase D stays. USB may stay for the log, but then the laptop ground is joined to the rig. If CAN errors appear only when USB is plugged in, use the 5 V brick and a USB isolator, or unplug USB after programming.

**Firmware.** `RIG` build. Drive-heartbeat check on. Current backstop on. Bus-voltage window is the **bench** window (18–30 V), not the 52 V battery window. RT heartbeat check still off until 0x040 exists. Orin check off.

**Pass test.** With the drive idle and the arm tied:

1. Permit power with B1. ODESC LEDs show it has bus voltage.
2. Press the mushroom. Bus voltage on the drive falls. The RT log shows undervoltage or a lost heartbeat, then FAULT.
3. Release the mushroom. Power stays off until B1.
4. Permit again. Stop the RT process. Within one second the drive disarms on its own watchdog **and** this board opens the contactor. Write down both times. They will not match until the drive watchdog is actually set to the RT spec's 50 ms. Today the yaml says 0.5 s.
5. Permit again. Unplug CAN at this board. It must latch and open the contactor. The drive may stay armed, because this board was only listening. That is expected. The RT core is still talking to the drive. This test proves we do not depend on CAN alone: the mushroom still kills power.
6. Leave it permitted and idle for 30 minutes. No false trip.

**What you will face.**

| What you see | Cause | What to do |
| --- | --- | --- |
| Opening the contactor while the motor is spinning arcs inside the relay | DC current and regen | Do this phase with the axis idle. A DC-rated contactor is still required. The 2 Ω brake resistor on the ODESC is what absorbs regen while the drive is connected. Once the contactor is open, the drive is off and cannot dump regen. |
| The arm drops when you cut power | There is no brake, and the drive has no hold without power | The tether must hold the arm. Do not run this phase untethered. |
| False trips at 24 V | You left the abort at a number inside the normal ripple | Log the voltage you actually see, then set the window outside it. 30 V is only a start. |
| The 52 V limit is still compiled | Battery window on a 24 V bench | The bench build must print `bus window 18 to 30`. |
| You sent `clear_errors` from this board to be helpful | That hides a real fault and is forbidden | Delete that transmit. The operator clears drive errors from the RT tool, after this board is in SAFE_OFF. |

## Phase G — RT heartbeat and fault drills

**Goal.** Add the 0x040 sender on the laptop. Turn the check on. Run the drills below on the tethered rig.

**Firmware on the RT core.** One small periodic frame, as in §7. Send it from the same real-time thread that already talks to the drive. If that thread dies, both the drive traffic and this heartbeat must stop. Do not send 0x040 from a separate thread that can stay alive after the motor thread is dead. That would hide the failure this board exists to catch.

**Pass test.** The scenario list in §10, rows marked Phase G, each done once and written in a log with the date.

**What you will face.**

| What you see | Cause | What to do |
| --- | --- | --- |
| Check trips immediately | The sender is not running, or the id is wrong, or the CRC does not match | Turn the check on only after a sniffer shows 0x040 every 20 ms and this board prints `rt age 20 ms`. |
| It never trips when you kill the RT process | 0x040 is sent from another thread or another program | Move the send into the motor thread. |
| CRC fails on every frame | Endianness or the CRC range includes the CRC bytes | CRC covers bytes 0–5 only. Print both CRCs once. |
| A second drive appears as node 2 | Id clash with 0x040 | Node ids 0 and 1 only, until we move this frame. |

## Phase H — later, not part of the first build

Do not start these while the shoulder is still being brought up.

- A brake or a phase-short, driven by its own pin, same pull-down rule as the contactor. VAYN-6.2.1 leaves this open because we do not yet know if the drive shorts the phases when idle (gate G-5).
- A separate CAN bus, so a flooded control bus cannot deafen this board (I-13, "later").
- The Orin heartbeat, as a **status** only. Loss of the Jetson must not drop the arm.
- A second temperature sensor, so one broken sensor is not the only opinion.
- Taking this off the tether. That waits for the brake decision and the hazard analysis.

---

# 10. Every situation, and the response

"Cut" means: PB11 low, contactor opens, state = LATCHED_FAULT, serial line names the reason. The mushroom does not need this table. It cuts power even if the chip is on fire.

| Situation | Phase where we test it | What the board does | What you should see |
| --- | --- | --- | --- |
| First plug-in | B | SAFE_OFF, permit low | LED off, log `boot safe_off` |
| Person presses B1, nothing wrong | B | PERMITTED | Permit LED on |
| Person presses B1 while a fault is still true | B | stays latched | LED stays off, log `reset refused` |
| E-stop pressed | E | hardware cuts power; software also latches | Lamp or bus dies even with the chip held in reset |
| E-stop released | E | stays latched | Power does not return |
| E-stop wire falls off | E | same as pressed | Latch |
| Both E-stop contacts disagree for 50 ms | E | latch | Log `estop mismatch` |
| Board reset, any reason | B | SAFE_OFF | Power off until B1 |
| Watchdog, main loop stuck | B | reset, then SAFE_OFF | Power off |
| Debugger halt, DEBUG build | B | no reset | You can debug |
| Debugger halt, RIG build | B | reset | Do not debug during motion |
| Brown-out on 3.3 V | B | reset if BOR is on | Enable brown-out in the option bytes so a dying rail cannot run wild and drive PB11 |
| CAN unplugged | C, F | if the drive check is on: latch | `drive silent` |
| CAN bus-off | C | latch, no fast retry | `bus off` |
| Transceiver left able to talk in Phase C | C | treat as a failed build | PA12 must be idle |
| Drive heartbeat error nonzero | F | latch | Log the error number. Do not clear it from this board. |
| Drive heartbeat missing 50 ms | F | latch | The drive may already be idle from its own watchdog |
| Current above 30 A for 100 ms | F | latch | Backstop. The RT core should have stopped it first. If only we stop it, the RT limit is wrong. |
| Bus above 30 V or below 18 V on the bench | F | latch | |
| NTC above 100 °C | D, F | latch | |
| NTC unplugged or shorted | D | latch | |
| NTC check compiled out on a RIG build | D | refuse to permit, forever | Log `NTC CHECK OFF` |
| RT heartbeat missing 100 ms | G | latch | Arm may already be falling. The tether holds it. |
| RT heartbeat sequence goes backward or jumps by more than 5 | G | latch | Replay or a second sender |
| RT heartbeat CRC bad three times in a row | G | latch | |
| Jetson dead, RT heartbeat healthy | H, not now | do not cut | Log `orin silent` only |
| Jetson dead and RT dead | G | latch because of the RT heartbeat | The Jetson is not the reason |
| Person kills only the motor thread | G | latch | This fails if 0x040 is sent from somewhere else |
| Contactor commanded open but bus voltage stays up | F | stay latched, log `contactor did not open` | Welded contacts or a bypass wire. Stop work. Fix the hardware. |
| Power returns after a blackout | B, F | SAFE_OFF | The arm must not twitch |
| Firmware download while the coil is connected | E | pin may glitch | Prefer to download with the coil supply off. The pull-down is the backup, not an excuse. |
| Wrong board (G431) | A | do not use it here | That board is the sensor-MCU candidate, not this one |
| Node id 2 added later | G | false RT heartbeats or missed ones | Keep id 0x040 reserved |
| Someone uses a GUI E-stop and expects this board to act | any | it will not, unless the GUI also drops a heartbeat | The mushroom is the emergency stop |
| Sensor MCU on the same bus is silent | any | ignore | That board is not our problem. Hall homing belongs to it. |
| ODESC reboot | F | heartbeat gap, then a fresh heartbeat with a new state | Latch. A reboot is not a clean start. |
| Encoder error inside the heartbeat | F | latch | Same as any nonzero axis error |
| Following-error, stale AI command, jerk limit | none | this board does nothing | Those are RT core jobs. If we also react, we will fight a category-2 hold and drop the arm. |
| FET overtemp | none directly | the drive errors, then we see the heartbeat error | Firmware 0.5.1 has no CAN temperature for the FETs |
| Regen spike when the contactor opens under load | F | avoid the case | Cut from idle in the early tests. A spinning cut is a welded-contact risk. |

---

# 11. What to log

Every state change is one serial line, and later one CAN status frame if we add it:

```text
t_ms  from  to  reason
```

Reasons are fixed words: `boot`, `person_permit`, `person_reset`, `estop`, `estop_wire`, `estop_mismatch`, `watchdog`, `drive_silent`, `drive_error`, `bus_off`, `overcurrent`, `bus_voltage`, `ntc_hot`, `ntc_sensor`, `rt_silent`, `rt_crc`, `contactor_stuck`, `reset_refused`.

No free-text reasons. A new situation gets a new word in this list and a new row in §10, in the same change.

---

# 12. Build flags

| Flag | Permit allowed? | NTC | RT heartbeat | Coil | Where it may run |
| --- | --- | --- | --- | --- | --- |
| `PHASE_A` to `PHASE_D` | state machine only, no coil | D onward | off | no | desk |
| `PHASE_E` | yes | optional | off | lamp | desk |
| `BENCH_RIG` | yes | on | off until Phase G | yes | tethered rig |
| `RIG` | yes | on | on | yes | tethered rig, after Phase G passes |

The `RIG` binary must print its flag and its limit numbers at boot. If it prints `NTC CHECK OFF` or `PHASE_A`, do not connect the coil.

---

# 13. Order of work next to the RT core

The RT plan (P1.0–P1.10) still runs with a mushroom and a supply current limit, and without this board. That sentence in the RT spec stays true.

Build this board in parallel, on the desk, through Phase E. Join the rig at Phase F only after the RT plan can idle the axis on CAN (their P1.4). Do not make the RT bring-up wait for this firmware. Do not make this firmware's first test a moving arm.

---

# 14. Sources

- ST UM2505, STM32G4 Nucleo-64 user manual (MB1367, NUCLEO-G474RE, STLINK-V3E, power jumpers, user button, LEDs). [https://www.st.com/resource/en/user_manual/um2505-stm32g4-nucleo64-boards-mb1367-stmicroelectronics.pdf](https://www.st.com/resource/en/user_manual/um2505-stm32g4-nucleo64-boards-mb1367-stmicroelectronics.pdf)
- Zephyr `nucleo_g474re` board file: FDCAN1 on PA11/PA12, IWDG enabled. [https://github.com/zephyrproject-rtos/zephyr/blob/main/boards/st/nucleo_g474re/nucleo_g474re.dts](https://github.com/zephyrproject-rtos/zephyr/blob/main/boards/st/nucleo_g474re/nucleo_g474re.dts)
- NXP TJA1051 datasheet: TJA1051T/3 is the 3.3 V-logic part; pin S high is silent mode. [https://www.nxp.com/docs/en/data-sheet/TJA1051.pdf](https://www.nxp.com/docs/en/data-sheet/TJA1051.pdf)
- NXP AH1014: silent mode as the way to stop a node from shouting on the bus. [https://www.nxp.com/docs/en/supporting-information/AH1014.pdf](https://www.nxp.com/docs/en/supporting-information/AH1014.pdf)
- ISO 13850:2015, emergency stop principles. The electrical rules are in IEC 60204-1. [https://www.iso.org/standard/59970.html](https://www.iso.org/standard/59970.html)
- IEC 60204-1 stop categories 0, 1, and 2, as summarized by ISA and by Control Design. Category 2 is not an emergency stop. [https://www.isa.org/intech-home/2019/september-october/features/integrated-or-separate-safety-systems](https://www.isa.org/intech-home/2019/september-october/features/integrated-or-separate-safety-systems) and [https://www.controldesign.com/displays/hmi/article/11296810/standards-and-options-for-e-stops](https://www.controldesign.com/displays/hmi/article/11296810/standards-and-options-for-e-stops)
- Rockwell 800-WP008: the emergency-stop contact must be direct-opening, not spring-opened. [https://literature.rockwellautomation.com/idc/groups/literature/documents/wp/800-wp008_-en-p.pdf](https://literature.rockwellautomation.com/idc/groups/literature/documents/wp/800-wp008_-en-p.pdf)
- ODrive 0.5.x CANSimple codec in this repo: `odrive/backend/app/can_bus.py`. Limits: `odrive/backend/profiles/vayn_shoulder.yaml`.
- VAYN-6.2 §§7, 49–52, 78 and VAYN-6.2.1 I-12 to I-15 and §9, in this vault.
