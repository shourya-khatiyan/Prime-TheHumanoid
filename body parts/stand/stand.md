# Arm test stand

The wooden stick is the spine. Every printed joint plugs together before the screw is added. A plug is 0.3 mm smaller on each side than its pocket, so it slides in by hand and then stops. The screw only keeps it from coming back out.

## Print

Bambu P2S. Longest piece is 212 mm. The bed allows 246 mm. Sizes are in `cad/assembly_check.txt`.

Print `fit_coupon` first, in PETG. The plug must slide into the pocket. If it binds, the first layer is squashed. Sand that face, or open the gap by 0.1 mm, before printing the stand.

`cad/stand_print.zip` has 33 STL files, one for every piece. A shape used more than once is numbered (`tower_back_1` through `tower_back_3`). They are already lying down. Tower halves lie on their side so the beads run up the stand.

| File | Qty | What it is |
|---|---|---|
| fit_coupon | 1 | plug and pocket, print this first |
| tower_back | 3 | rear half, two plugs underneath, pockets on top, hole grid on the back |
| tower_front | 3 | front half, tongues that drop into the rear half |
| beam_x | 6 | long base beams, a plug on each end |
| beam_y | 4 | short base beams, a plug on each end |
| beam_center | 1 | from the foot to the far rail |
| coupler | 6 | straight block, a pocket in each end |
| corner | 4 | L block, one part turned for each corner |
| saddle | 1 | sits on the far rail and takes the center beam |
| foot | 1 | under the shell, stick hole and two pockets |
| clamp_lower | 1 | shoulder cradle, two plugs |
| clamp_upper | 1 | shoulder cap |
| odrive_plate | 1 | for the 135 × 50 mm ODESC board |

Screws are M5 through the plugs, and M4 for the back grid. The M5 hole is 6 mm so the 0.3 mm play in the plug does not make the screw miss. A nut goes on the open side.

## Assembly

1. Push each base beam into a coupler or a corner until the plug stops. It stops about 2 mm before the end of the pocket. Then put an M5 through the side hole.
2. Drop the saddle on the middle beam of the far rail and screw it down. Push the center beam into the foot and into the saddle.
3. Stand the stick through the foot. The 27 mm faces take the swing of the arm.
4. Slide the first rear half down the stick. Its two plugs drop into the foot. Pin them with M5 screws.
5. Slide the first front half down the stick. Its tongues drop into the grooves on the rear half. Pin them.
6. Do the same for the next two layers. Each rear half drops into the pockets on the one below.
7. The clamp plugs drop into the top pockets. Close the cap.
8. The ODESC plate screws to the 25 mm grid. Hold the nut through the open side of the shell.

A hanging arm clears the base beams by about 56 mm. That height is the 620 mm stick.

## Files

`cad/gen_stand.py` builds the solids. It stops if a plug does not fit, two pieces collide, a brace misses the frame, or a part is too big for the bed. `cad/assembly_check.txt` is the last run. `cad/stand.step` is the assembly. `cad/stand_preview.png` is the four views.
