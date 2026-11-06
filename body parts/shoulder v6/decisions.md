# Shoulder v6

Same 45:1 cycloid as v4. The printed v4 parts that did not change are listed at the bottom.

The motor turns the crank. The crank walks two discs around the ring pins. The discs turn the output pins and the arm.

## What was wrong on v4

The rear K 20×24×10 could not be installed. That cage is a closed ring, bore 20 mm. The Ø44 flange blocked it from the back, and the front journal, the same diameter and 1.05 mm off center, blocked it from the front. The front cage was already open.

The 46 ring pins were placed 3.9° off the disc, half a tooth. At that angle 28 pins entered each disc by about 1 mm, at every crank angle. The profile itself, with the pins at 0°, keeps about 0.07 mm of gap.

The rear 61906 had no seat. The disc bore was cut through the seat, so the housing wall at the bearing was 22.9 mm away from the outer ring. The rear carrier face sat 0.10 mm from the whole bearing, inner ring and outer ring together. The M2 head pocket was 1.4 mm deep and an ISO 4762 M2 head is 2.0 mm, so the head stood proud of the flange, 0.2 mm from that bearing. The output-pin screws were buried in solid pin ends.

## What changed

The crank flange is one piece: the motor disc and the sleeve that stops the rear cage. The shaft is a separate piece: a Ø16 core runs through both journals, and the journals are eccentric bosses on that core. The rear cage slides on from the back, over the Ø16 stem, and then the flange slides on. The front cage slides on from the front, and a washer on the nose closes it. Three M3 screws clamp the flange to the shaft. The four M2 screws still clamp the flange to the rotor, and the head pocket is 2.25 mm deep.

The ring pins are at 0°, which is the angle the disc was drawn for.

The rear bearing seat is a Ø47.6 bore. The disc chamber starts in front of it, so the seat is still there after the discs go in. A retainer ring, bolted on after the bearing, holds the outer ring. The hub shoulder is Ø33, which is inside the SKF shaft abutment of 32 to 34 mm. The retainer hole is Ø44, under the SKF housing abutment limit of 45 mm. The front plate is cut back in front of the outer ring, and the cover bore in front of the front bearing is the same Ø44.

The journals are Ø21. The K 20×24×10 roller bore is 20 mm, and a Ø20 journal was still loose, so both journals are 1 mm larger on the diameter. The discs, the flange, and the hub are unchanged.

The arm face moved from 53 mm to 57 mm so the retainer fits between the rear bearing and the rear carrier. The arm flange itself is the same shape.

## Build order

1. Rear cage onto the rear journal, from the back. Front cage on from the front. Washer and M4. Then the flange, three M3s, then four M2s into the rotor.
2. That crank into the housing from the back. The flange clears the Ø44 shoulder hole.
3. Rear 61906 in from the front, until it stops on the rear shoulder. Retainer, four M3s.
4. Rear carrier. The hub passes through the retainer and the bearing.
5. Both discs, from the front, onto the cages and the output pins.
6. Front plate, eight M3s into the pin ends. Cover, with the front 61906. Arm flange and cross pin.

## Printed again

Print from `cad/actuator_print.zip`. Keep the v4 parts that are not in this list.

| Print again | Why |
|---|---|
| 01 Housing | Bearing seat, pin angle, Ø4.6 pin holes |
| 02 Ring pins, all 46 | 41 mm long. The v4 pins are 37 mm and stop short of the cover |
| 07 Crank shaft | Journals are Ø21. Reprint this part only |
| 08 Rear carrier | Hub shoulder, tapped pin ends |
| 15 Front cover | Pin angle, Ø44 abutment |
| 19 Crank flange | One piece: the motor disc and the sleeve that stops the rear cage |
| 21 Front washer | New. Stops the front cage |
| 23 Front plate and hub | Outer-ring clearance, countersinks, Ø29.4 hub |
| 27 Bearing retainer | New |
| 31 Fit coupon | Try one 61906 and one cage before the housing |

Keep the v4 discs, the rear plate, the encoder lid, the arm flange, and the cross pin.

## Not run

No finite-element check. No print on the machine. The fit coupon is the first thing to print.
