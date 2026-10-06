"""Single source of truth for every elbow actuator dimension (mm, deg).

Z = 0 at the rear face of the encoder lid, axis = Z, forward = +Z (output).
Base values are set first; every Z position is derived from them so a
change in one part moves the whole stack. calc.py and gen_actuator.py
import this module; nothing else hardcodes a dimension.
"""

# ---------------------------------------------------------------- loads (elbow/research.md s3, 165 cm, stage 2)
T_STATIC, T_CONT, T_PROOF = 3.47, 4.93, 8.23  # n*m at the output
RATIO = 20  # cycloid zp / (zp - zc)
ETA = 0.85  # gearbox efficiency used for current
DISC_SHARE = 0.55  # worst share of output torque on one disc
KV, R_PHASE_PP = 170.0, 0.270  # rpm/v, ohm phase-to-phase (t-motor)
I_PEAK_MOTOR, I_LIMIT = 15.0, 10.0  # a: motor 180 s peak, odesc current_lim
V_BUS = 24.0

# ---------------------------------------------------------------- vendor motor (t-motor mn5008, official step)
MOTOR_STEP_AXIS = (-2.701, -4.389)  # axis xy in the vendor step
MOTOR_STEP_BASE_Z = 42.1  # base face z in the vendor step
M_BASE_FLANGE_R, M_BASE_FLANGE_H = 15.5, 3.5  # pilot flange, local z 0..3.5
M_BASE_LOBE_Z0 = 3.5  # lobes / lead notch start (local z)
M_ROTOR_R, M_ROTOR_Z0 = 27.8, 8.25  # can radius, can bottom (local z)
M_TOP = 27.0  # rotor top flat face (local z), flat to r 12
M_TOP_FLAT_R = 12.0
M_SHAFT_TIP = 31.9  # max local z of the shaft tip (step 31.6..31.9)
M_SHAFT_D = 4.0
M_RETAINER_Z0 = 0.2  # shaft-end retainer (rotating) bottom, local z
M_ROTOR_HOLES = dict(pcd_r=6.0, angles=(45, 135, 225, 315), depth=8.5)  # 4 x m3, rotor top
M_BASE_HOLES = dict(pcd_r=12.5, angles=(84.8, 174.8, 264.8, 354.8), depth=7.0)  # 4 x m3, base
M_LEAD_ANGLE = 220.0  # phase-lead exit (deg)
M_LEAD_Z = (3.5, 5.5)  # local z of the lead notch
MOTOR_MASS_G = 128.0

# ---------------------------------------------------------------- cycloid stage
ZP = RATIO + 1  # ring pins
ZC = RATIO  # disc lobes
R_PINS = 30.0  # ring-pin circle radius
D_PIN = 5.0  # ring + output pins, iso 8734 hardened dowels
GROOVE_CLEAR = 0.0  # radial allowance on the open ring-pin grooves, set from the printed slice test (bom s5)
E = 1.0  # eccentricity
DR = 0.08  # equidistant profile relief (radial play on the pins)
N_OUT, R_OUT = 6, 20.0  # output pins and their circle radius
C_OUT = 0.10  # radial play output pin in disc hole
D_OUT_HOLE = D_PIN + 2 * E + 2 * C_OUT  # 7.2
T_DISC = 9.0  # disc thickness (contact stress, calc s3)
GAP = 0.5  # axial running gap between moving parts
PROFILE_PTS = 6000  # polyline points per disc outline

# ---------------------------------------------------------------- bought parts
BRG_ECC = dict(d=20.0, D=27.0, B=4.0, d1=22.0, D1=25.0, nballs=18, dball=2.0)  # 6704-2rs
BRG_ECC_LIP_D = 25.4  # shoulder for the outer ring (da max 25.4)
BRG_ECC_SHOULDER_R = 11.0  # inner-ring shoulder (da 21.6..22.3)
BRG_CAM_R = dict(d=17.0, D=23.0, B=4.0, d1=18.6, D1=21.4, nballs=16, dball=2.0)  # 6703-2rs, cam rear in the cage
BRG_CAM_F = dict(d=12.0, D=18.0, B=4.0, d1=13.6, D1=16.4, nballs=12, dball=1.6)  # 6701-2rs, cam front in the pin plate
CAM_R_SHOULDER_R = 9.0  # 6703 inner-ring shoulder (collar between 6703 and disc a)
SLIDE_CLEAR = 0.2  # collar trimmed to r (6704 bore - this) about the ecc-a axis so 6704-a slides on from the rear
CAM_F_SHOULDER_R = 6.6  # 6701 inner-ring shoulder
LIP_CAM_R_ID = 20.0  # rear-ring lip on the 6703 outer ring
BRG_OUT = dict(d=35.0, D=47.0, B=7.0, d1=38.2, D1=44.4, nballs=24, dball=3.5)  # 61807-2rs1
BRG_OUT_SHOULDER_D = 38.0  # inner-ring shoulder (da 37..38)
BRG_OUT_LIP_ID = 44.4  # outer-ring shoulder id (da max 45)
INSERT = dict(d_hole=4.0, length=5.7, depth=6.7, wall_min=1.6)  # ruthex rx-m3x5.7
D_M3_CLEAR, D_M3_MAJOR = 3.4, 3.0
D_M25_CLEAR, D_M25_MAJOR = 2.9, 2.5
M3_SHCS = dict(dk=5.5, k=3.0)  # din 912
M25_SHCS = dict(dk=4.5, k=2.5)  # din 912
WASHER_M3 = dict(od=7.0, id=3.2, t=0.5)  # iso 7089
DOWEL_D = 3.0

# ---------------------------------------------------------------- encoder (same pcb as shoulder p12)
PCB = dict(w=30.0, t=1.6, hole_r=17.0, hole_d=2.7)  # 30 x 30, 4 x m2.5 on pcd 34
IC = dict(l=5.0, w=4.4, h=0.9)  # as5047p tssop-14 body
MAG = dict(d=6.0, h=2.5)  # ams as5000-md6h-2, diametric
CUP = dict(d=10.0, h=3.0)  # 6061 magnet cup on the rotor retainer
AIR_GAP = 1.0  # ic top to magnet face (0.5..3.0 allowed)
ANG_PCB = 62.3  # pcb corner holes (deg); lid screws at +45
ANG_LID = ANG_PCB + 45.0

# ---------------------------------------------------------------- rear stack (z)
Z_LID0, T_LID = 0.0, 2.0
Z_PCB0 = Z_LID0 + T_LID + 0.5  # 0.5 air under the lid
Z_PCB1 = Z_PCB0 + PCB["t"]
Z_IC1 = Z_PCB1 + IC["h"]
Z_MAG = Z_IC1 + AIR_GAP  # magnet face = cup rear face
T_RING = 2.5  # 6061 clamp ring (csk m3 flush, pcb on its rear face)
Z_RING0, Z_RING1 = Z_PCB1, Z_PCB1 + T_RING
Z_M0 = Z_MAG + CUP["h"] - M_RETAINER_Z0  # motor base face (cup front = retainer bottom)
T_WALL = Z_M0 - Z_RING1  # printed wall clamped by the motor screws
R_RING_O, R_RING_I = 23.0, 6.0
R_WALL_BORE = CUP["d"] / 2 + 0.75
R_LID_SKIRT_I = 21.8
R_LID_SCREW = 18.5
COLLAR = dict(ri=M_BASE_FLANGE_R, ro=M_BASE_FLANGE_R + 2.0, h=2.0)  # motor pilot on the wall

# ---------------------------------------------------------------- motor (z)
Z_ROTOR0 = Z_M0 + M_ROTOR_Z0
Z_TOP = Z_M0 + M_TOP  # rotor top = cam rear face
Z_TIP = Z_M0 + M_SHAFT_TIP
R_MOTOR_BORE = M_ROTOR_R + 1.4

# ---------------------------------------------------------------- dog drive rotor -> cam (torque only)
DOG = dict(d=3.0, protrude=3.0, length=8.0)  # iso 4026 m3 x 8 set screws in the rotor pcd-12 holes
DOG_POCKET_D = 3.4  # 0.2 radial play: motor axis may sit 0.2 off the cam axis with no radial load
DOG_POCKET_DEPTH = 3.5

# ---------------------------------------------------------------- gearbox stack (z)
Z_CAM0 = Z_TOP + GAP  # cam rear face
T_LIP_RR = 1.0  # rear-ring lip behind the 6703 outer ring
Z_RR0 = Z_CAM0
Z_BCR0 = Z_RR0 + T_LIP_RR  # 6703 rear face
Z_RR1 = Z_BCR0 + BRG_CAM_R["B"]
Z_D1_0 = Z_RR1 + GAP
Z_D1_1 = Z_D1_0 + T_DISC
Z_D2_0 = Z_D1_1 + GAP
Z_D2_1 = Z_D2_0 + T_DISC
Z_B1_0 = (Z_D1_0 + Z_D1_1 - BRG_ECC["B"]) / 2  # bearing centred in disc
Z_B2_0 = (Z_D2_0 + Z_D2_1 - BRG_ECC["B"]) / 2
T_PIN_PLATE = 6.0
Z_PP0 = Z_D2_1 + GAP
Z_PP1 = Z_PP0 + T_PIN_PLATE
Z_BCF0 = Z_PP0  # 6701 rear face, flush with the pin-plate rear face
Z_CAM_F = Z_BCF0 + BRG_CAM_F["B"]  # cam front face
POCKET_RELIEF = 0.5  # pin-plate pocket bottom relief in front of the 6701 inner ring
Z_HF = Z_PP1 + GAP  # housing front face
T_RETAINER = 2.0
Z_BRG0 = Z_HF + T_RETAINER  # output bearing rear face
Z_BRG1 = Z_BRG0 + BRG_OUT["B"]
T_LIP = 2.0
Z_FRONT = Z_BRG1 + T_LIP  # cover front lip = actuator front face
HUB_RECESS = 0.4  # hub front below the inner ring so the forearm clamps the ring
Z_HUB1 = Z_BRG1 - HUB_RECESS
T_FLANGE_COVER = 5.0

# ---------------------------------------------------------------- radii
R_REAR_RING_O = 25.0
R_PIN_PLATE = 25.5
R_DISC_MAX = R_PINS + E - D_PIN / 2 - DR + E  # largest disc radius seen by the housing
R_BORE_DISC = R_DISC_MAX + 0.55  # disc-zone bore, pins exposed in grooves
R_HOUSING = R_PINS + D_PIN / 2 + 2.0
R_FLANGE = 40.0
R_FLANGE_SCREW = 35.5
R_HUB = BRG_OUT["d"] / 2
R_BOSS = BRG_OUT_SHOULDER_D / 2
R_NECK = BRG_OUT["D"] / 2 + 2.5
R_HUB_INSERT = 13.0

# ---------------------------------------------------------------- pins (z)
# the motor goes in from the front (r 29.2 rear bore, disc bore r 29.97 to the front face);
# ring pins are captured by the rear groove (opening narrower than the pin) and by the discs
PIN_LEN, OUT_PIN_LEN = 30.0, 30.0  # iso 8734 5 x 30 ring pins and output pins
Z_PIN1 = Z_HF - 0.2  # ring-pin front end, 0.2 under the retainer
Z_PIN0 = Z_PIN1 - PIN_LEN
Z_OPIN1 = Z_PP1  # output pins flush with the pin-plate front
Z_OPIN0 = Z_OPIN1 - OUT_PIN_LEN
Z_FLANGE0 = Z_HF - 8.0

# ---------------------------------------------------------------- angles
ANG_RING_PINS = [360.0 * k / ZP for k in range(ZP)]
ANG_OUT = [360.0 * k / N_OUT for k in range(N_OUT)]
ANG_FLANGE = [180.0 / ZP + 3 * 360.0 * k / ZP for k in range(7)]  # pin mid-angles, every 3rd
ANG_FLANGE_DOWEL = [180.0 / ZP + 360.0 / ZP, 180.0 / ZP + 10 * 360.0 / ZP]  # 25.7, 180.0
ANG_HUB_INSERT = [60.0 * k for k in range(6)]
ANG_HUB_DOWEL = [30.0, 210.0]
DISC_B_ROT = -180.0 / ZC  # disc b outline turn (deg)

# ---------------------------------------------------------------- fasteners (length, mm)
L_MOTOR_SCREW = 10.0  # iso 10642 m3, ring + wall -> motor base
L_LID_SCREW = 8.0  # iso 10642 m3, lid -> ring
L_PCB_SCREW = 5.0  # din 912 m2.5, pcb -> ring
L_FLANGE_SCREW = 12.0  # din 912 m3 + washer, cover + retainer -> housing inserts
L_DOWEL_FLANGE = 12.0  # iso 8734 3 x 12

# ---------------------------------------------------------------- materials (density g/cm3)
DENSITY = {"ASA": 1.05, "PLA": 1.24, "PET-CF": 1.29}  # bambu tds values (iso 1183)
