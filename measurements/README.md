# Bought-part measurements

Numbers for parts that get bolted or pressed into a VAYN design. A new actuator reads this folder. It does not copy a guess out of an old CAD file.

Status on every row:

| Status | Meaning |
|---|---|
| MEASURED | Vernier, caliper, or a count on the part we have |
| FITTED | The existing plate or gear bolted on, but nobody wrote the caliper number |
| CATALOGUE | Seller page or a datasheet, not checked on our part |
| ASSUMED | Used in CAD. Not measured. Do not reuse it |
| OPEN | We know the feature exists and it is not in the CAD |

Sheets:

- [`eaglepower-la8308.md`](eaglepower-la8308.md) — shoulder and elbow motor
- [`encoder-meukron.md`](encoder-meukron.md) — Meukron AS5047P board, magnet, screws

When a measurement comes in, change the status on that row. Do not leave the old assumed number next to it.
