# Story

This is the account we tell, and the account we can defend. The narrative is ours. The prices and ratings below are the public figures and our own design calculations, checked on 3 November 2026. Where a line we used to say does not match those figures, this file says so.

## What we are doing

We are building a humanoid. We started with the body. When we priced the joints, a humanoid-class actuator for every joint was beyond what we could pay, and it was not something we could order in India the way we order a bearing or a bolt.

We had two 90 KV brushless motors and one field-oriented motor controller. That is the hardware budget that was actually available. With two motors we could not build eighteen joints, so the first machine is a two-degree-of-freedom arm: our P0 shoulder actuator on one motor, and the same motor type driving the elbow directly.

P0 is a two-stage planetary actuator. The design rating is 30 N·m continuous and 50 N·m proof, in a 100 mm by 100.5 mm package, calculated mass 2.76 kg, ratio 30:1. Those are design calculations, not a dyno certificate. Backlash and backdrive torque have not been measured yet. We do not quote them.

The arm is proportioned to a stature of 160 cm. Upper arm 298 mm, forearm 234 mm. The arm with the elbow motor is 897 g. With the arm horizontal and a dummy hand, the shoulder sees about 3.1 N·m from gravity and 4.6 N·m with the design acceleration, against the 30 N·m continuous rating. The elbow is direct drive. Its steady thermal rating is 0.81 N·m if the winding is held at 70 °C with a thermal resistance of 3 K/W.

## Why the actuator became the product

The motors and the controller were already expensive for a student build. Two EaglePower LA8308 motors were ₹10,999 each on Technobotix on 7 October 2026, and a dual ODESC 3.6-class board was ₹10,999 on the same list. About ₹33,000 bought the entire electrical drive of this prototype, and it bought two axes.

Scaling that purchase to a body was a different problem. An integrated joint is a motor, a reducer, an encoder, and a driver sold as one part. For a full set of main joints we were looking at bills we could not pay, and at parts that were not sitting on an Indian shelf.

So the actuator joined the goal. We design it, we machine it, and we mean to sell it. The motor and the controller come next, in that order, because those are the other two parts that are costly and are not a normal Indian catalogue item in the size a humanoid joint needs. Bearings, magnets, and encoder chips stay purchased. Making a joint in India does not mean making the steel ball and the silicon in the same year.

## What we will build toward

The product sequence is the actuator, then the brushless motor, then our own field-oriented controller. Each one should be something another lab can buy without waiting on an export carton.

The longer aim is a domestic path for this class of part. Labs and colleges should be able to use the actuator in their own machines. Workshops are how the next group learns to design one. More makers of joints, motors, and drives is the point. A single humanoid from us is a demonstration. A catalogue other people can build on is the project.

China’s position in small robots comes from a supply chain that already contains the motor, the reducer, the driver, the magnet, the PCB, and the factory that will build a hundred. A lab there orders a joint. We are starting one layer down from that, with the joint we have already designed, and we are explicit about the layers we still buy.

## What we say about the twenty-lakh bill

The experience we had was that a full set of joints was quoted to us above ₹20 lakh, including the cheaper imported route we were shown. On stage we do not leave it as a memory. We show three bills a judge can open. Rupees use ₹94.9 per US dollar, the 3 November 2026 close reported by The Economic Times.

| Bill | What it is | 18 joints | Source |
|---|---|---:|---|
| China list, same week | RobStride RS04, 40 N·m rated, 120 N·m peak, $255 | about ₹4.4 lakh before freight and duty | robstride.com, 3 Nov 2026 |
| China list, nearer our torque | RobStride RS03, 21 N·m rated, 60 N·m peak, $225 | about ₹3.8 lakh before freight and duty | robstride.com, 3 Nov 2026 |
| India checkout, weaker than P0 | CubeMars AK10-9 on Robu, 15 N·m rated, 38 N·m peak, ₹80,780, out of stock, 25–30 day restock | ₹14.54 lakh | robu.in |
| India checkout, nearest torque class | MyActuator RMD-X8-60 on RoboTechMinds, ₹93,000, out of stock. Reseller text says 25 N·m rated. The maker’s catalogue for this 36:1 unit says 30 N·m rated and 60 N·m peak | ₹16.74 lakh | robotechminds.com; MyActuator RMD-X catalogue |
| Industrial strain-wave | Harmonic Drive FHA-14C-50, listed at $3,388. This is a small-frame unit | about ₹57.9 lakh | autopowerhub.com listing |

Eighteen RobStride joints at the company’s own dollar price are about ₹4 lakh, not ₹20 lakh. The sentence “even the cheap Chinese actuators were above twenty lakh” is not what those pages show. If we say it flat, the first phone in the room ends the talk.

What we can say, and what matches the pages:

- A catalogue strain-wave joint, even a small one, makes eighteen joints about ₹58 lakh before anyone ships it to India.
- The joint an Indian cart actually lists near our torque, the MyActuator X8-60, is ₹93,000 and was out of stock. Eighteen is ₹16.7 lakh, and that price is an importer’s page, not a factory page.
- The one robot-joint module on Robu in this class, the AK10-9, is ₹80,780, out of stock, and rated 15 N·m. Eighteen is ₹14.5 lakh for a joint weaker than P0.
- Factory prices in China are much lower. The gap between $225 and ₹93,000 is the gap we are pointing at: the part exists, and a builder in India still cannot treat it as a normal purchase.

Our own quote above ₹20 lakh stays in the story as what we were offered. We do not ask the room to treat it as the public list.

## Who already builds this in India

We do not say the market is empty.

Gephr Labs publishes a G1 joint at 31.8 N·m rated and 60.1 N·m peak, 21:1 cycloidal, and describes it as shipping. The page has specifications and an email. It has no price and no cart. A public company listing puts the firm at a handful of people, founded in 2024. They are a peer, not a catalogue.

NMotion sells the NDrive Z1, a single-axis field-oriented controller, at ₹13,999, 20 A continuous, with CAN and a dual-encoder path. An Indian controller board exists. A dual high-current board of the kind we are using still shows up on Indian shops as a Chinese ODrive-style clone: Flipsky and Makerbase, roughly ₹7,400 to ₹11,000.

The small 90 KV outrunners on Indian shops are imported brands. Ours is an EaglePower LA8308. Drone-class motors from T-Motor and Tarot are the ones a student can reorder. That is a different object from a joint module.

## What we will not claim

- That P0 is lighter or more efficient than an integrated Chinese joint. The X8-60 catalogue mass is about 0.9 kg. P0 is 2.76 kg. Their stated efficiency for that unit is 69 percent. We have not measured ours.
- That P0 is quasi-direct-drive. The ratio is 30:1. The elbow is the direct-drive joint, and it is direct drive because we had no second gearbox, and because a low elbow torque does not need one.
- That backlash is “near zero,” or that backdrive torque has a number, until we measure both.
- That eighteen factory-price Chinese joints cost ₹20 lakh.
- That no Indian company is attempting a humanoid joint or a field-oriented drive.
- That the arm has been run as a closed-loop product demo beyond what we have actually shown that day.
- That bearings, magnets, and the encoder IC are Indian parts. The AS5047P is an Infineon part. The shoulder bearings are purchased.

## Sources

- RobStride product pages, RS03 at $225 and RS04 at $255, retrieved 3 November 2026, https://robstride.com/ and the RS03 / RS04 product pages. A July 2026 specification table in the RobStride product repository also lists yuan prices (RS03 ¥999, RS04 ¥1,199), which are lower, not higher.
- CubeMars AK10-9 on Robu, ₹80,780 including GST, out of stock, https://oldwp.robu.in/product/t-motor-cubemars-ak10-9-v1-1-100kv-brushless-dc-actuator-robot-joint-motor/
- MyActuator RMD-X8-60, maker catalogue 30 N·m rated / 60 N·m peak, https://brushless.a2v.fr/doc/myactuator/catalogue-rmd-x.pdf ; Indian listing ₹93,000, https://www.robotechminds.com/product-page/myactuator-rmd-x8-60-v3-planetary-actuator-canrs485-dual-encoder
- Harmonic Drive FHA-14C-50 listed at $3,388, https://autopowerhub.com/products/harmonic-drive-systems-ac-24v-servo-actuator-fha-14c-50
- USD/INR 94.90 close, The Economic Times, 3 November 2026.
- EaglePower LA8308 and ODESC prices, `body parts/purchase.md`, pages read 7 October 2026.
- P0 and arm ratings, `body parts/shoulder/cad/calc.txt`, `body parts/arm/cad/calc.txt`, `body parts/arm/cad/mass.txt`, `body parts/shoulder/cad/mass.txt`.
- Gephr G1 specifications, https://gephr.com/
- NMotion NDrive Z1, ₹13,999, https://shop.nmotion.in/products/ndrive-z1
