"""Build the VAYN elbow actuator Rev 1.0 as exact OpenCascade solids.

All dimensions come from params.py, the disc outline from cycloid.py and the
motor from the official T-Motor MN5008 STEP (vendor/). Shoulder primitives,
checks and writers are reused from shoulder/cad. Writes, beside this script:
  actuator.step       coloured, named assembly (Fusion: File > Open)
  actuator.3mf        named, coloured meshes
  actuator_stl.zip    every part, assembled position
  actuator_print.zip  printed parts only

Run with the D: environment:
  D:\\VAYN-CAD-env\\venv\\Scripts\\python.exe gen_actuator.py
"""

import math
import os
import sys
import time

import cadquery as cq

import cycloid as cy
import params as p

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "shoulder", "cad"))
import gen_actuator_3mf as g  # noqa: E402  (shoulder module, path set above)
import gen_actuator_occ as occ  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "actuator")
VENDOR_STEP = os.path.join(HERE, "vendor", "tmotor-mn5008.step")
REV = "1.0"
SPLINE_PTS = 1200  # disc outline interpolation points
PRINT_PARTS = {1, 10, 14, 16, 18, 20, 24, 26, 28}

g.MATERIALS.update({
    "ASA": ("#E6E1D3", p.DENSITY["ASA"]),
    "PLA": ("#D2603A", p.DENSITY["PLA"]),
    "PET-CF": ("#3A3D42", p.DENSITY["PET-CF"]),
    "Brass insert": ("#C8A24A", 8.50),
})


def at(r, deg):
    """(x, y) for radius r at angle deg (shoulder g.polar)."""
    return g.polar(r, deg)


def ring_of(fn, r, angles):
    """Union of fn(x, y) placed on radius r at each angle."""
    return occ.pattern(lambda a: fn(*at(r, a)), angles)


def disc_solid(name):
    """Exact cycloid disc (own frame): spline outline, bearing bore, lip, output holes."""
    rot_deg = p.DISC_B_ROT if name == "B" else 0.0
    pts = cy.disc_profile(p.R_PINS, p.E, p.D_PIN / 2, p.ZC, SPLINE_PTS, p.DR, rot_deg)
    edge = cq.Edge.makeSpline([cq.Vector(x, y, 0) for x, y in pts], periodic=True)
    z0, z1 = (p.Z_D1_0, p.Z_D1_1) if name == "A" else (p.Z_D2_0, p.Z_D2_1)
    zb = p.Z_B1_0 if name == "A" else p.Z_B2_0
    s = occ.Solid(cq.Solid.extrudeLinear(cq.Wire.assembleEdges([edge]), [], cq.Vector(0, 0, z1 - z0))).translate((0, 0, z0))
    seat, lip = p.BRG_ECC["D"] / 2, p.BRG_ECC_LIP_D / 2
    if name == "A":  # lip on the rear face, bearing goes in from the front
        s = s - occ.cyl(lip, z0 - 1, zb) - occ.cyl(seat, zb, z1 + 1)
    else:  # lip on the front face
        s = s - occ.cyl(seat, z0 - 1, zb + p.BRG_ECC["B"]) - occ.cyl(lip, zb + p.BRG_ECC["B"], z1 + 1)
    return s - ring_of(lambda x, y: occ.cyl(p.D_OUT_HOLE / 2, z0 - 1, z1 + 1, x, y), p.R_OUT, p.ANG_OUT)


def cam_solid():
    """One-piece cam: 6703 journal, two eccentric 6704 journals, lens shoulder, 6701 journal."""
    e, rj = p.E, p.BRG_ECC["d"] / 2
    z_a1 = p.Z_B1_0 + p.BRG_ECC["B"]
    s = occ.cyl(p.BRG_CAM_R["d"] / 2, p.Z_CAM0, p.Z_RR1)
    s = s + (occ.cyl(p.CAM_R_SHOULDER_R, p.Z_RR1, p.Z_D1_0) ^ occ.cyl(rj - p.SLIDE_CLEAR, p.Z_RR1, p.Z_D1_0, e, 0))
    s = s + occ.cyl(rj, p.Z_D1_0, z_a1, e, 0)
    s = s + (occ.cyl(p.BRG_ECC_SHOULDER_R, z_a1, p.Z_B2_0, e, 0) ^ occ.cyl(p.BRG_ECC_SHOULDER_R, z_a1, p.Z_B2_0, -e, 0))
    s = s + occ.cyl(rj, p.Z_B2_0, p.Z_B2_0 + p.BRG_ECC["B"], -e, 0)
    s = s + occ.cyl(p.CAM_F_SHOULDER_R, p.Z_B2_0 + p.BRG_ECC["B"], p.Z_BCF0)
    s = s + occ.cyl(p.BRG_CAM_F["d"] / 2, p.Z_BCF0, p.Z_CAM_F)
    s = s - occ.cyl(p.M_SHAFT_D / 2 + 0.5, p.Z_CAM0 - 1, p.Z_TIP + 0.5)  # shaft tip clearance, no fit
    return s - ring_of(lambda x, y: occ.cyl(p.DOG_POCKET_D / 2, p.Z_CAM0 - 1, p.Z_CAM0 + p.DOG_POCKET_DEPTH, x, y),
                       p.M_ROTOR_HOLES["pcd_r"], p.M_ROTOR_HOLES["angles"])


def housing_solid():
    """Printed housing: rear wall + motor pilot, motor bore with vents, ring-pin grooves, front insert flange."""
    z_ch = p.Z_FLANGE0 - (p.R_FLANGE - p.R_HOUSING)  # 45 deg chamfer under the flange, prints rear face down
    s = occ.cyl(p.R_HOUSING, p.Z_RING1, z_ch) + occ.cyl(p.R_FLANGE, p.Z_FLANGE0, p.Z_HF)
    s = s + occ.Kernel.cylinder(p.Z_FLANGE0 - z_ch, p.R_HOUSING, p.R_FLANGE).translate((0, 0, z_ch))
    s = s - occ.cyl(p.R_WALL_BORE, p.Z_RING1 - 1, p.Z_M0 + 1)
    s = s - occ.cyl(p.R_MOTOR_BORE, p.Z_M0, p.Z_D1_0 - p.GAP) - occ.cyl(p.R_BORE_DISC, p.Z_D1_0 - p.GAP, p.Z_HF + 1)
    s = s + occ.tube(p.COLLAR["ro"], p.COLLAR["ri"], p.Z_M0, p.Z_M0 + p.COLLAR["h"])
    s = s - ring_of(lambda x, y: occ.cyl(p.D_PIN / 2 + p.GROOVE_CLEAR, p.Z_PIN0, p.Z_HF + 1, x, y), p.R_PINS, p.ANG_RING_PINS)
    wall = (p.Z_RING1 - 1, p.Z_M0 + 1)
    s = s - ring_of(lambda x, y: occ.cyl(p.D_M3_CLEAR / 2, *wall, x, y), p.M_BASE_HOLES["pcd_r"], p.M_BASE_HOLES["angles"])
    s = s - ring_of(lambda x, y: occ.cyl(p.D_M3_CLEAR / 2, *wall, x, y), p.R_LID_SCREW, g.every(4, p.ANG_LID))
    s = s - ring_of(lambda x, y: occ.cyl(p.D_M25_CLEAR / 2, *wall, x, y), p.PCB["hole_r"], g.every(4, p.ANG_PCB))
    s = s - ring_of(lambda x, y: occ.cyl(p.INSERT["d_hole"] / 2, p.Z_HF - p.INSERT["depth"], p.Z_HF + 1, x, y),
                    p.R_FLANGE_SCREW, p.ANG_FLANGE)
    s = s - ring_of(lambda x, y: occ.cyl(p.DOWEL_D / 2, p.Z_HF - 6.0, p.Z_HF + 1, x, y), p.R_FLANGE_SCREW, p.ANG_FLANGE_DOWEL)
    port = occ.box(p.R_MOTOR_BORE - 1, p.R_HOUSING + 1, -4.0, 4.0, p.Z_M0 + 1.0, p.Z_M0 + 7.0)
    v = p.VENT
    vents = occ.pattern(lambda a: occ.box(p.R_MOTOR_BORE - 1, p.R_HOUSING + 1, -v["w"] / 2, v["w"] / 2, v["z0"], v["z1"])
                        .rotate((0, 0, a)), v["angles"])
    return s - port.rotate((0, 0, p.M_LEAD_ANGLE)) - vents


def lid_solid():
    """Printed encoder lid: disc, skirt, 4 screw bosses, pcb-screw head holes, cable slot."""
    s = occ.cyl(p.R_RING_O, p.Z_LID0, p.T_LID) + occ.tube(p.R_RING_O, p.R_LID_SKIRT_I, p.T_LID, p.Z_RING0)
    s = s + ring_of(lambda x, y: occ.cyl(3.0, p.T_LID - 0.1, p.Z_RING0, x, y), p.R_LID_SCREW, g.every(4, p.ANG_LID))
    for a in g.every(4, p.ANG_LID):
        s = s - g.csk_hole(*at(p.R_LID_SCREW, a), p.Z_LID0, p.Z_RING0, 3.0, 1)
    s = s - ring_of(lambda x, y: occ.cyl(2.75, p.Z_LID0 - 1, p.T_LID + 0.1, x, y), p.PCB["hole_r"], g.every(4, p.ANG_PCB))
    slot = occ.box(p.R_LID_SKIRT_I - 1, p.R_RING_O + 1, -4.0, 4.0, p.T_LID, p.Z_RING0 + 1)
    return s - slot.rotate((0, 0, p.M_LEAD_ANGLE))


def carrier_solid():
    """Printed output carrier: pin plate, 6701 pocket, inner-ring boss, hub with inserts and dowel holes."""
    s = occ.cyl(p.R_PIN_PLATE, p.Z_PP0, p.Z_PP1) + occ.cyl(p.R_BOSS, p.Z_PP1, p.Z_BRG0) + occ.cyl(p.R_HUB, p.Z_BRG0, p.Z_HUB1)
    s = s - ring_of(lambda x, y: occ.cyl(p.D_PIN / 2, p.Z_PP0 - 1, p.Z_PP1, x, y), p.R_OUT, p.ANG_OUT)
    s = s - occ.cyl(p.BRG_CAM_F["D"] / 2, p.Z_PP0 - 1, p.Z_CAM_F)
    s = s - occ.cyl(p.BRG_CAM_F["D1"] / 2 - 0.7, p.Z_CAM_F - 0.1, p.Z_CAM_F + p.POCKET_RELIEF)
    s = s - ring_of(lambda x, y: occ.cyl(p.INSERT["d_hole"] / 2, p.Z_HUB1 - p.INSERT["depth"], p.Z_HUB1 + 1, x, y),
                    p.R_HUB_INSERT, p.ANG_HUB_INSERT)
    return s - ring_of(lambda x, y: occ.cyl(p.DOWEL_D / 2, p.Z_HUB1 - 5.0, p.Z_HUB1 + 1, x, y), p.R_HUB_INSERT, p.ANG_HUB_DOWEL)


def vendor_motor():
    """Official MN5008 step on the axis: (stator/base, rotor) with tapped holes opened to M3 major."""
    solids = sorted(cq.importers.importStep(VENDOR_STEP).solids().vals(), key=lambda s: s.Volume())
    shift = (-p.MOTOR_STEP_AXIS[0], -p.MOTOR_STEP_AXIS[1], p.Z_M0 - p.MOTOR_STEP_BASE_Z)
    solids = [occ.Solid(s).translate(shift) for s in solids]
    base = next(s for s in solids if 2700 < s.volume() < 2850)  # S2 base + stator (2769.9 mm3)
    rotor = [s for s in solids if s is not base]
    rot = rotor[0]
    for s in rotor[1:]:
        rot = rot + s
    holes_r = ring_of(lambda x, y: occ.cyl(p.D_M3_MAJOR / 2, p.Z_TOP - p.M_ROTOR_HOLES["depth"], p.Z_TOP + 0.01, x, y),
                      p.M_ROTOR_HOLES["pcd_r"], p.M_ROTOR_HOLES["angles"])
    holes_b = ring_of(lambda x, y: occ.cyl(p.D_M3_MAJOR / 2, p.Z_M0 - 0.01, p.Z_M0 + p.M_BASE_HOLES["depth"], x, y),
                      p.M_BASE_HOLES["pcd_r"], p.M_BASE_HOLES["angles"])
    return base - holes_b, rot - holes_r


def build():
    """Return list of (name, material, solid) for the whole elbow actuator."""
    parts = []

    def add(name, mat, solid):
        parts.append((name, mat, solid))

    lid_ang, pcb_ang = g.every(4, p.ANG_LID), g.every(4, p.ANG_PCB)
    # ---- encoder end (Z 0 .. motor base)
    add("01 Encoder lid (ASA)", "ASA", lid_solid())
    for i, a in enumerate(lid_ang):
        add(f"02.{i + 1} Screw M3x8 ISO 10642 lid->ring", "Steel 12.9 fastener", g.csk(*at(p.R_LID_SCREW, a), p.Z_LID0, p.L_LID_SCREW, 3.0, 1))
    pcb = occ.box(-p.PCB["w"] / 2, p.PCB["w"] / 2, -p.PCB["w"] / 2, p.PCB["w"] / 2, p.Z_PCB0, p.Z_PCB1).rotate((0, 0, p.ANG_PCB - 45))
    pcb = pcb - ring_of(lambda x, y: occ.cyl(p.PCB["hole_d"] / 2, p.Z_PCB0 - 1, p.Z_PCB1 + 1, x, y), p.PCB["hole_r"], pcb_ang)
    add("03 Encoder PCB 30x30x1.6 (shoulder P12)", "Electronics", pcb)
    add("04 AS5047P TSSOP-14 (envelope)", "Electronics",
        occ.box(-p.IC["l"] / 2, p.IC["l"] / 2, -p.IC["w"] / 2, p.IC["w"] / 2, p.Z_PCB1, p.Z_IC1))
    for i, a in enumerate(pcb_ang):
        add(f"05.{i + 1} Screw M2.5x5 DIN 912 pcb->ring", "Steel 12.9 fastener", g.shcs(*at(p.PCB["hole_r"], a), p.Z_PCB0, p.L_PCB_SCREW, 2.5, 1))
    ring = occ.tube(p.R_RING_O, p.R_RING_I, p.Z_RING0, p.Z_RING1)
    for a in p.M_BASE_HOLES["angles"]:
        ring = ring - g.csk_hole(*at(p.M_BASE_HOLES["pcd_r"], a), p.Z_RING0, p.T_RING, 3.0, 1)
    ring = ring - ring_of(lambda x, y: occ.cyl(p.D_M25_MAJOR / 2, p.Z_RING0 - 1, p.Z_RING1 + 1, x, y), p.PCB["hole_r"], pcb_ang)
    ring = ring - ring_of(lambda x, y: occ.cyl(p.D_M3_MAJOR / 2, p.Z_RING0 - 1, p.Z_RING1 + 1, x, y), p.R_LID_SCREW, lid_ang)
    add("06 Motor clamp ring 6061-T6 D46/D12x2.5", "6061-T6", ring)
    for i, a in enumerate(p.M_BASE_HOLES["angles"]):
        add(f"07.{i + 1} Screw M3x10 ISO 10642 ring+wall->motor", "Steel 12.9 fastener",
            g.csk(*at(p.M_BASE_HOLES["pcd_r"], a), p.Z_RING0, p.L_MOTOR_SCREW, 3.0, 1))
    z_cup = p.Z_MAG
    add("08 Magnet cup 6061-T6 D10x3 (on rotor retainer)", "6061-T6",
        occ.cyl(p.CUP["d"] / 2, z_cup, z_cup + p.CUP["h"]) - occ.cyl(p.MAG["d"] / 2, z_cup - 1, z_cup + p.MAG["h"]))
    add("09 Encoder magnet D6x2.5 diametric", "NdFeB magnet", occ.cyl(p.MAG["d"] / 2, z_cup, z_cup + p.MAG["h"]))
    # ---- housing and motor
    add("10 Housing (ASA)", "ASA", housing_solid())
    base, rotor = vendor_motor()
    add("11 MN5008 stator + base (vendor STEP)", "Motor envelope", base)
    add("12 MN5008 rotor + shaft (vendor STEP)", "Motor envelope", rotor)
    for i, a in enumerate(p.M_ROTOR_HOLES["angles"]):
        x, y = at(p.M_ROTOR_HOLES["pcd_r"], a)
        z1 = p.Z_TOP + p.DOG["protrude"]
        add(f"13.{i + 1} Dog set screw M3x8 ISO 4026", "Steel 12.9 fastener", occ.cyl(p.DOG["d"] / 2, z1 - p.DOG["length"], z1, x, y))
    # ---- gearbox
    add("14 Cam (PLA)", "PLA", cam_solid())
    for k, v in occ.ball_bearing(z0=p.Z_BCR0, seals=True, **p.BRG_CAM_R).items():
        add(f"15 6703-2RS cam rear {k}", "Bearing (purchased)", v)
    rr = occ.tube(p.R_REAR_RING_O, p.LIP_CAM_R_ID / 2, p.Z_RR0, p.Z_RR1) - occ.cyl(p.BRG_CAM_R["D"] / 2, p.Z_BCR0, p.Z_RR1 + 1)
    rr = rr - ring_of(lambda x, y: occ.cyl(p.D_PIN / 2, p.Z_RR0 - 1, p.Z_RR1 + 1, x, y), p.R_OUT, p.ANG_OUT)
    add("16 Cage rear ring (PLA)", "PLA", rr)
    for disc, no, zb, sx in (("A", 17, p.Z_B1_0, p.E), ("B", 19, p.Z_B2_0, -p.E)):
        for k, v in occ.ball_bearing(z0=zb, seals=True, **p.BRG_ECC).items():
            add(f"{no} 6704-2RS disc {disc} {k}", "Bearing (purchased)", v.translate((sx, 0, 0)))
        add(f"{no + 1} Cycloid disc {disc} (PET-CF)", "PET-CF", disc_solid(disc).translate((sx, 0, 0)))
    for i, a in enumerate(p.ANG_RING_PINS):
        add(f"21.{i + 1} Ring pin D5x30 ISO 8734", "52100 bearing steel", occ.cyl(p.D_PIN / 2, p.Z_PIN0, p.Z_PIN1, *at(p.R_PINS, a)))
    for i, a in enumerate(p.ANG_OUT):
        add(f"22.{i + 1} Output pin D5x30 ISO 8734", "52100 bearing steel", occ.cyl(p.D_PIN / 2, p.Z_OPIN0, p.Z_OPIN1, *at(p.R_OUT, a)))
    for k, v in occ.ball_bearing(z0=p.Z_BCF0, seals=True, **p.BRG_CAM_F).items():
        add(f"23 6701-2RS cam front {k}", "Bearing (purchased)", v)
    add("24 Output carrier: pin plate + hub (PLA)", "PLA", carrier_solid())
    for i, a in enumerate(p.ANG_HUB_INSERT):
        add(f"25.{i + 1} Insert RX-M3x5.7 hub", "Brass insert",
            occ.tube(p.INSERT["d_hole"] / 2, p.D_M3_MAJOR / 2, p.Z_HUB1 - p.INSERT["length"], p.Z_HUB1).translate((*at(p.R_HUB_INSERT, a), 0)))
    # ---- front closure
    ret = occ.tube(p.R_FLANGE, p.BRG_OUT_LIP_ID / 2, p.Z_HF, p.Z_BRG0)
    ret = ret - ring_of(lambda x, y: occ.cyl(p.D_M3_CLEAR / 2, p.Z_HF - 1, p.Z_BRG0 + 1, x, y), p.R_FLANGE_SCREW, p.ANG_FLANGE)
    ret = ret - ring_of(lambda x, y: occ.cyl(p.DOWEL_D / 2, p.Z_HF - 1, p.Z_BRG0 + 1, x, y), p.R_FLANGE_SCREW, p.ANG_FLANGE_DOWEL)
    add("26 Retainer ring (ASA)", "ASA", ret)
    for k, v in occ.ball_bearing(z0=p.Z_BRG0, seals=True, **p.BRG_OUT).items():
        add(f"27 61807-2RS1 output {k}", "Bearing (purchased)", v)
    z_fl1 = p.Z_BRG0 + p.T_FLANGE_COVER
    cov = occ.tube(p.R_FLANGE, p.BRG_OUT["D"] / 2, p.Z_BRG0, z_fl1) + occ.tube(p.R_NECK, p.BRG_OUT["D"] / 2, z_fl1, p.Z_BRG1)
    cov = cov + occ.tube(p.R_NECK, p.BRG_OUT_LIP_ID / 2, p.Z_BRG1, p.Z_FRONT)
    cov = cov - ring_of(lambda x, y: occ.cyl(p.D_M3_CLEAR / 2, p.Z_BRG0 - 1, z_fl1 + 1, x, y), p.R_FLANGE_SCREW, p.ANG_FLANGE)
    z_dowel1 = p.Z_HF - 6.0 + p.L_DOWEL_FLANGE
    cov = cov - ring_of(lambda x, y: occ.cyl(p.DOWEL_D / 2, p.Z_BRG0 - 1, z_dowel1 + 0.2, x, y), p.R_FLANGE_SCREW, p.ANG_FLANGE_DOWEL)
    add("28 Front cover (ASA)", "ASA", cov)
    for i, a in enumerate(p.ANG_FLANGE):
        x, y = at(p.R_FLANGE_SCREW, a)
        add(f"29.{i + 1} Insert RX-M3x5.7 housing", "Brass insert",
            occ.tube(p.INSERT["d_hole"] / 2, p.D_M3_MAJOR / 2, p.Z_HF - p.INSERT["length"], p.Z_HF).translate((x, y, 0)))
        add(f"30.{i + 1} Washer M3 ISO 7089", "Steel 12.9 fastener",
            occ.tube(p.WASHER_M3["od"] / 2, p.WASHER_M3["id"] / 2, z_fl1, z_fl1 + p.WASHER_M3["t"]).translate((x, y, 0)))
        add(f"31.{i + 1} Screw M3x12 DIN 912 cover->housing", "Steel 12.9 fastener",
            g.shcs(x, y, z_fl1 + p.WASHER_M3["t"], p.L_FLANGE_SCREW, 3.0, -1))
    for i, a in enumerate(p.ANG_FLANGE_DOWEL):
        add(f"32.{i + 1} Dowel D3x12 ISO 8734 cover/housing", "52100 bearing steel",
            occ.cyl(p.DOWEL_D / 2, p.Z_HF - 6.0, z_dowel1, *at(p.R_FLANGE_SCREW, a)))
    return parts


def gaps(parts):
    """Print exact minimum gaps between functional pairs (prefix match, min over matches)."""
    pairs = [("18 ", "21."), ("20 ", "21."), ("18 ", "22."), ("20 ", "22."), ("18 ", "10 "), ("20 ", "10 "),
             ("12 ", "10 "), ("12 ", "16 "), ("12 ", "14 "), ("08 ", "11 "), ("08 ", "10 "), ("14 ", "16 "),
             ("14 ", "18 "), ("14 ", "20 "), ("14 ", "24 "), ("16 ", "18 "), ("18 ", "20 "), ("20 ", "24 "),
             ("24 ", "10 "), ("24 ", "26 "), ("16 ", "10 "), ("24 ", "21."), ("16 ", "21."), ("13.", "14 ")]
    print("exact minimum gaps (mm):")
    for a, b in pairs:
        sa = [(n, s) for n, _, s in parts if n.startswith(a)]
        sb = [(n, s) for n, _, s in parts if n.startswith(b) and not n.startswith(a)]
        best = min(((x.min_gap(y, 1.0), na, nb) for na, x in sa for nb, y in sb), key=lambda t: t[0])
        print(f"  {best[0]:7.3f}  {best[1]}  <->  {best[2]}")


if __name__ == "__main__":
    t0 = time.time()
    occ.use_occ_kernel()
    model = build()
    print(f"built {len(model)} exact solids in {time.time() - t0:.0f} s")
    gaps(model)
    g.check(model, meshes=[], motor_g=p.MOTOR_MASS_G)
    occ.write_step(model, OUT + ".step", f"VAYN_Elbow_Actuator_Rev{REV}")
    g.write_3mf(model, OUT + ".3mf", f"VAYN Elbow Actuator Rev {REV}")
    g.write_stl_zip(model, OUT + "_stl.zip")
    g.write_stl_zip([q for q in model if g.part_no(q[0]) in PRINT_PARTS], OUT + "_print.zip")
    print(f"total {time.time() - t0:.0f} s")
