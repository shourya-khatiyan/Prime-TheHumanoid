> **Revision note (2026-10-20, VAYN-6.2.1):**  
> **Motor identity.** The motor in hand is the **EaglePower LA8308 KV90** (`shoulder-bom.md` P01: Ø92.0 × 32.5 mm, 336 g). The table below is a translated seller listing labelled "W92-25"; treat its values as seller claims.  
> **Measured on the ODESC.** 20 pole pairs (counted). Phase resistance 0.0846 Ω, consistent with the listed 0.186 Ω if that figure is line-to-line (0.093 Ω per phase). Phase inductance 37 µH. KV has **not** been measured.  
> **Torque constant.** This page used Kt = 60/(2π·KV) = 0.1061 N·m/A. The ODESC and all VAYN docs use ODrive's convention for line-to-line KV, **Kt = 8.27/KV = 0.0919 N·m/A**, so the torques in §1–4 below are about 15% optimistic.  
> **Built gearbox.** Two planetary stages: 6:1 (18/36/90) as stage 1, then 5:1 (18/27/72) as stage 2, for **30:1**. These are the same two gear sets proposed here, with the stage order swapped.  
> **Expected output.** 30 N·m continuous / 50 N·m proof targets (theoretical, untested).

Here is the specification translated into English:

| Parameter | Specification |
| ---| --- |
| Motor Type / Model | W92-25 KV90 (seller listing; the motor in hand is EaglePower LA8308 KV90) |
| Iron Core Size (mm) | Not specified in image |
| Motor Size (mm) | Not specified in image |
| Weight | Not specified in image |
| Idle Current (24 V) | 0.6 A |
| Supported Battery | 12S LiPo |
| Maximum Continuous Current | 22 A |
| Maximum Continuous Power | 900 W |
| Internal Resistance | 0.186 Ω |

### What the Chinese fields mean
- **型号 (Motor Type)** → Motor Model
- **铁芯尺寸 (Iron Core Size)** → Iron Core Size
- **电机尺寸 (Motor Size)** → Motor Dimensions
- **重量 (Weight)** → Weight
- **空载电流 (24V)** → No-load / Idle Current at 24 V
- **支持锂电 (Support Lithium Battery)** → Supported LiPo Battery
- **最大电流 (Max Continuous Current)** → Maximum Continuous Current
- **最大功率 (Max Continuous Power)** → Maximum Continuous Power
- **内阻 (Internal Resistance)** → Internal Resistance

**Important:** The image does **not** provide values for the iron-core size, motor dimensions, or weight; those cells are blank.

The biggest constraint is this: **a single-stage planetary gearbox is not realistically capable of giving you the ~26–30:1 reduction you need from this motor.** A practical single planetary stage is usually around **3:1–6:1**. Trying to make 30:1 in one stage produces absurd tooth counts and poor geometry.
Using your **KV90 motor** (EaglePower LA8308; note the Kt convention correction in the revision note above):
### 1. Motor torque at 18 A
For a 90 KV motor:
\\[ K_t=\\frac{60}{2\\pi K_V} \\]\\[ K_t=\\frac{60}{2\\pi(90)}\\approx0.1061\\ Nm/A \\]
At 18 A:
\\[ T_m=0.1061\\times18 \\]\\[ \\boxed{T_m\\approx1.91\\ Nm} \\]
You want:
\\[ T_{out}=50\\ Nm \\]
Therefore, with **100% gearbox efficiency**:
\\[ R=\\frac{50}{1.91}\\approx26.2:1 \\]
With a realistic planetary efficiency of about 90%:
\\[ R=\\frac{50}{1.91\\times0.90} \\]\\[ \\boxed{R\\approx29.1:1} \\]
So your real target should be approximately **30:1 overall reduction**.

---

## 2. Can we make 30:1 with one planetary stage?
For a simple planetary with:
- Sun = input
- Ring = fixed
- Carrier = output

the ratio is:

\\[ R=1+\\frac{N_R}{N_S} \\]

where:

- \\(N_R\\) = ring gear teeth
- \\(N_S\\) = sun gear teeth

For 30:1:

\\[ 30=1+\\frac{N_R}{N_S} \\]\\[ N_R=29N_S \\]

For example, if:

\\[ N_S=18 \\]

then:

\\[ N_R=522 \\]

Planet teeth:

\\[ N_P=\\frac{N_R-N_S}{2} \\]\\[ N_P=\\frac{522-18}{2}=252 \\]

So:

| Gear | Teeth |
| ---| --- |
| Sun | 18 |
| Planet | 252 |
| Ring | 522 |
| Ratio | 30:1 |

**This is completely impractical for your actuator.**
The gearbox would be enormous and the geometry would be poor.

---

# 3. A practical single planetary stage
A very reasonable choice is **5:1**.
For example:

| Gear | Teeth |
| ---| --- |
| Sun | 18 |
| Planet | 27 |
| Ring | 72 |
| Ratio | 5:1 |

Check:
\\[ R=1+\\frac{72}{18}=5 \\]
and:
\\[ 18+2(27)=72 \\]
So the geometry is valid.

\\(\\tau = rF\\sin(\\theta)\\)
\\(\\tau=(\\text{3})(\\text{7})\\sin(\\text{90}^{\\circ})=\\text{21}\\,\\text{N m}\\)
Only the perpendicular part of F turns the lever.
\\(F\\)

N

\\(r\\)

m

\\(\\theta\\)

°

pivotr = 3 mθ = 90°F⊥ = 7 NFτ = 21 N m
Give feedback
At 18 A:
\\[ 1.91\\times5\\times0.90 \\]\\[ \\boxed{T_{out}\\approx8.6\\ Nm} \\]
So **5:1 is nowhere near your 50 Nm target**.

---

# 4. What I would actually use
For your actuator, I would use **two planetary stages**, not one.
A very simple combination is:
### Stage 1 — 5:1

| Gear | Teeth |
| ---| --- |
| Sun | 18 |
| Planet | 27 |
| Ring | 72 |
| Ratio | 5:1 |

### Stage 2 — 6:1

| Gear | Teeth |
| ---| --- |
| Sun | 18 |
| Planet | 36 |
| Ring | 90 |
| Ratio | 6:1 |

Check:
\\[ 18+2(36)=90 \\]
Therefore:
\\[ R_2=1+\\frac{90}{18}=6 \\]
Overall:
\\[ R_{total}=5\\times6 \\]\\[ \\boxed{R_{total}=30:1} \\]
At 18 A and assuming approximately 90% efficiency per stage:
\\[ T_{out}=1.91\\times30\\times0.9^2 \\]\\[ \\boxed{T_{out}\\approx46.4\\ Nm} \\]
If the combined gearbox efficiency is ~92%:
\\[ 1.91\\times30\\times0.92 \\]\\[ \\boxed{52.7\\ Nm} \\]
So **30:1 is the correct neighborhood** for your 50 Nm target.
### Bottom line
For your **90 KV motor at 18 A**:
- Motor torque ≈ **1.91 Nm**
- Required theoretical reduction ≈ **26.2:1**
- Practical reduction allowing losses ≈ **29–30:1**
- **One-stage planetary: not recommended**
- **Two-stage planetary: 5:1 × 6:1 = 30:1**
- Example tooth counts:
    - Stage 1: **18 / 27 / 72**
    - Stage 2: **18 / 36 / 90**
- Expected output torque: roughly **46–53 Nm**, depending on actual gearbox efficiency.

One important correction: **50 Nm at 18 A should not be treated as guaranteed from the motor's 22 A continuous-current specification.** We should verify the motor's actual torque constant, winding configuration, and thermal limit before freezing the gearbox design.
