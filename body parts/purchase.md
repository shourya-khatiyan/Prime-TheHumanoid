# Purchase list (India)

Buy list for **one shoulder** and **one arm Rev 2** (the arm includes the direct-drive elbow). Quantities are the BOM quantities without spares. Printed parts and machined parts are not in these tables. Filament is included because the BOMs list it as something to buy.

Prices are the selling price shown on the linked page on 7 October 2026. “Incl. GST” means the page states the price includes tax. Pages change; confirm the figure at checkout.

A price of **not listed** means no public India price was found for that spec. Do not treat a nearby part as a substitute unless the row says the size and the rating match.

Sources: `shoulder/shoulder-bom.md` §2–§2.2, `arm/arm_bom.md` §3.

---

## Shoulder

| Component | India link | Price |
|---|---|---|
| BLDC motor, EaglePower LA8308 KV90 (1) | [Technobotix](https://www.technobotix.in/products/eagle-powor-la-8308-kv90-motor/1781252000000073016) | ₹10,999 incl. GST. [The Engineer Store](https://www.theengineerstore.in/products/eaglepower-la-8308-kv90-motor) lists ₹11,738.12 |
| Rear output bearing, 61813-2Z/C3, 65 × 85 × 10 (1) | — | Not listed. India listings found are 61813-2RS, and none of them state C3. The BOM requires C3 |
| Front output bearing, 61813-2RS1/C3, 65 × 85 × 10 (1) | [Bearing House, FBJ 6813-2RS](https://bearinghouse.in/shop/fbj-6813-2rs-ball-bearing/) | ₹828.36 incl. GST for the size only. Clearance on this page is not stated as C3. [Moglix SKF 61813-2RS1](https://www.moglix.com/skf-61813-2rs1-deep-groove-ball-bearing-65x85x10-mm/mp/msn2qo2s0lq1d3) is ₹7,473 incl. tax and is Normal clearance, not C3 |
| Planet needle bearing, HK0810, 8 × 12 × 10 (6) | [Moglix, SKF HK 0810](https://www.moglix.com/skf-hk-0810-drawn-cup-needle-roller-bearing-8x12x10-mm/mp/msn2vl65407auf) | ₹386 incl. tax each. SKF dynamic capacity on this page is 3.69 kN, which is the value the shoulder calc uses. [Bearing House FBJ HK 0810](https://bearinghouse.in/shop/fbj-hk-0810-needle-roller-bearing/) is ₹64.90 incl. GST; its load rating is not on the page |
| Wave spring, Smalley SSB-0335, bore 85 mm (1) | [Smalley dealer, Chennai](https://www.smalley.co.in/single-turn-wave-springs.html) | Not listed. Ask this dealer for SSB-0335 or the stated alternate LB-0335 |
| Dowel, ISO 8734 Ø3 × 8 (2) | — | Not listed |
| Dowel, ISO 8734 Ø4 × 8 (2) | — | Not listed |
| Dowel, ISO 8734 Ø3 × 6 (2) | — | Not listed |
| Encoder magnet, Ø6 × 2.5 NdFeB, diametric (1) | — | Not listed. Axial 6 mm discs are a different part and will not run the AS5047P |
| Homing magnet, Ø3 × 2 NdFeB N52, axial (1) | — | Not listed |
| Encoder IC, AS5047P-ATSM (1) | [LionCircuits](https://www.lioncircuits.com/parts/AS5047P-ATSM) | ₹890.29 each at qty 1 |
| Encoder PCB, 30 × 30 × 1.6, 2-layer, 4 holes on PCD 34 (1) | [LionCircuits prototype service](https://www.lioncircuits.com/make-in-india-pcb) | From ₹799 for 5 boards. That price is their minimum prototype order, not a populated encoder. The AS5047P still has to be soldered on |
| Homing hall sensor, TI DRV5033FAQDBZR (1) | [Evelta](https://evelta.com/drv5033faqdbzr-magnetic-omnipolar-switch-high-voltage-hall-effect-sensor-sot-23-3/) | ₹31.22 incl. GST. Page reports out of stock |
| Winding thermistor, 10 kΩ NTC (1) | [Probots MF52-103](https://probots.co.in/10k-ntc-thermistor-negative-temperature-coefficient.html) | ₹18 incl. GST. [Robu](https://oldwp.robu.in/product/10k-ohm-ntc-thermistor/) lists ₹14 incl. GST |
| Motor controller, ODESC class, ≥ 20 A phase (1) | [Technobotix, Flipsky ODESC V4.2 56 V, single drive](https://www.technobotix.in/products/odesc-v4-2-56v-/1781252000001361097) | ₹7,799 incl. GST. This board drives one motor. [Amazon.in](https://www.amazon.in/Single-Drive-High-Current-High-Precision-Controller-Configuration/dp/B0CB64MVHC) lists a Flipsky ODESC V4.2 from ₹6,197.50; the title says 24 V |
| Planet thrust washer candidate, DIN 988, 8 × 14 × 0.3 (12) | [Maedler India](https://maedler.in/product/shim-ring-din-988-08-x-14-x-03-material-steel-dc01-c590-sku-624308144/) | Not listed. Check that one sample spins free on the Ø8 h6 pin before buying the set |
| M4 wire thread insert, 1.5D, Helicoil / ISO 13050 type (6) | — | Not listed |
| Fasteners F01–F09 and F11 (lid, PCB, housing, stator, sun, carriers, cover, torso) | — | Not listed as single-size catalogue lines. F12 (M5 arm screws) is bought with the arm, not here |
| Gear grease, NLGI 2 EP lithium complex, about 5 g | — | Not listed for Mobilux EP 2 or Shell Gadus S2 V220 2 |
| Threadlocker, Loctite 243, 50 ml (1 bottle; also used on the arm) | [Amazon.in](https://www.amazon.in/dp/B014MMG3AM) | ₹520 incl. tax. Buy one bottle for both |
| Threadlocker, Loctite 222 | — | Not listed |
| Magnet adhesive, structural epoxy | — | Not listed for Loctite EA 9466 |
| Thermal epoxy for the thermistor | — | Not listed |

---

## Arm Rev 2 (with the direct-drive elbow)

The elbow motor is the LA8308 KV90 already in stock (same motor as the shoulder row). No elbow gearbox parts.

| Component | India link | Price |
|---|---|---|
| Pivot bearing, 6705-2RS, 25 × 32 × 4 (1) | — | Not listed. Alternative 61805 (25 × 37 × 7) needs a thicker boss in part 209 |
| O-ring 31.5 × 1.5 NBR 70 (1) | — | Not listed as a single size; buy an NBR O-ring kit |
| Heat-set inserts M3 × 5.7, Ø4.0 hole (48) | [Amazon.in, ruthex 100 pieces](https://www.amazon.in/ruthex-M3-Thread-Insert-RX-M3x5-7/dp/B08BCRZZS3) | ₹1,711 incl. tax for 100 |
| M3 × 10 countersunk ISO 10642 (52), M3 × 8 countersunk (3), M3 × 6 socket head (1), M3 nyloc (8) | [onlyscrews.in](https://onlyscrews.in/search?q=m3+countersunk) | Check the listing at order time |
| M4 × 16 countersunk (4) | [onlyscrews.in](https://onlyscrews.in/search?q=m4+countersunk) | Check the listing at order time |
| M5 × 12 socket head 12.9 (6) and M5 washers ISO 7089 (6) | — | Not listed as a 12.9 line. These are the screws the shoulder BOM calls “arm screws” |
| M2.5 × 6 countersunk + nuts (4 + 4) | [onlyscrews.in](https://onlyscrews.in/search?q=m2.5) | Check the listing at order time |
| Silicone tube Ø8 / Ø10, 120 mm | — | Not listed; local hardware or aquarium tubing |
| Rubber sheet 3 mm, small piece | — | Local |
| Winding thermistor, 10 kΩ NTC (1) | [Probots MF52-103](https://probots.co.in/10k-ntc-thermistor-negative-temperature-coefficient.html) | ₹18 incl. GST |
| Encoder IC, AS5047P-ATSM (1) | [LionCircuits](https://www.lioncircuits.com/parts/AS5047P-ATSM) | ₹890.29 each |
| Encoder PCB, 30 × 30 × 1.6 (1) | [LionCircuits prototype service](https://www.lioncircuits.com/make-in-india-pcb) | From ₹799 for 5 bare boards |
| Encoder magnet, Ø6 × 2.5 NdFeB, diametric (1) | — | Not listed. Axial discs will not work |
| Bambu PETG HF, 1 kg (arm uses about 466 g) | — | In stock |
| Structural epoxy (laps, magnet holder, NTC) | — | Not listed for a specific product |
| Threadlocker, Loctite 243 | [Amazon.in](https://www.amazon.in/dp/B014MMG3AM) | ₹520 incl. tax. Same bottle as the shoulder row |

---

## Buy once across the shoulder and the arm

| Item | How many to order |
|---|---|
| M3 × 5.7 inserts, pack of 100 | 1 pack (arm 48) |
| Loctite 243, 50 ml | 1 bottle |
| AS5047P-ATSM | 2 (shoulder motor, elbow motor) |
| Encoder PCBs | 2 bare boards, from one 5-board prototype order |
| Diametric Ø6 × 2.5 magnets | 2, once a seller is found |
| 10 kΩ NTC | 2 (shoulder winding, elbow stator) |
