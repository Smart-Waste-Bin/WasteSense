# SmartBin Bill of Materials (DEV-01)

Order: 2 bins + 1 spare set (3 sets). Prices in GHS.
Status: DRAFT. "Est." prices come from the project BOM document. Replace them with real quotes when suppliers reply.

## A. Parts per bin unit (x3 sets)

| # | Part | What to ask for | Qty | Est. unit | Est. total | Quoted unit | Supplier | Link | Notes |
|---|------|-----------------|-----|-----------|------------|-------------|----------|------|-------|
| 1 | ESP32 DevKit V1 | ESP32-WROOM-32, 30 pins, CP2102 or CH340 USB chip | 3 | 110 | 330 | | | | Note USB type (Micro-USB or USB-C) |
| 2 | JSN-SR04T ultrasonic sensor | v2.0 or v3.0, 5 V, separate probe, 2.5 m cable | 3 | 150 | 450 | | | | Blind zone about 25 cm |
| 3 | Resistors 1 kΩ and 2 kΩ | 1/4 W metal film, small assortment pack | 6 pcs (3 of each) | 1 | 6 | | | | Buy a few extra |
| 4 | Status LED 5 mm green + 220 Ω resistor | | 3 | 2 | 6 | | | | |
| 5 | USB cable, 2 m | Data cable (not charge-only), matches ESP32 port | 3 | 25 | 75 | | | | |
| 6 | USB wall adapter 5 V 2 A | Good brand, USB-A port | 3 | 40 | 120 | | | | Cheap adapters give noisy readings |
| 7 | IP65 junction box | ABS, about 100 x 68 x 50 mm, screw lid | 3 | 50 | 150 | | | | Check the ESP32 fits |
| 8 | Perfboard 5 x 7 cm | Double-sided, 2.54 mm pitch | 3 | 10 | 30 | | | | |
| 9 | Female header strip 1 x 40 | 2.54 mm, single row | 3 | 8 | 24 | | | | |
| 10 | Cable glands (to confirm size) | Fit probe cable and power cable | 6 | TBD | TBD | | | | 2 per bin |

Subtotal parts (estimated, items 1 to 9): GHS 1,191 (GHS 397 per unit)
Cost per bin unit: GHS 397 + cable glands. Target (NFR-20): under GHS 600.

## B. Shared items (one set for the team)

| # | Part | What to ask for | Qty | Est. unit | Est. total | Quoted unit | Supplier | Link |
|---|------|-----------------|-----|-----------|------------|-------------|----------|------|
| 11 | Breadboard | 830 points | 1 | 25 | 25 | | | |
| 12 | Jumper wire set | Male-male, male-female, female-female, 40 of each | 1 | 30 | 30 | | | |
| 13 | Solder wire 0.8 mm | 60/40 tin-lead, flux core, about 100 g | 1 | 40 | 40 | | | |

Subtotal shared (estimated): GHS 95

## C. Tools (borrow from lab or university if possible)

| # | Tool | Est. price | Borrowed? |
|---|------|------------|-----------|
| 14 | Digital multimeter | 120 | |
| 15 | Soldering iron kit, 60 W | 120 | |
| 16 | Test waste bin with lid, 60 to 80 L | 150 | |

Subtotal tools if bought (estimated): GHS 390

## Totals (estimated)

| Group | GHS |
|-------|-----|
| A. Parts, 3 sets | 1,191 |
| B. Shared items | 95 |
| A + B | 1,286 |
| C. Tools (only if not borrowed) | 390 |
| Everything | 1,676 |

## Order record

- Order placed on: ____
- Supplier(s): ____
- Expected delivery date: ____ (also log in Jira)
- Final cost per bin unit: ____ (record against NFR-20)

## Open points

- Confirm whether a spare junction box is needed (a spare set may only need electronics).
- Confirm cable gland size once the probe cable thickness is known.
- Check ESP32 USB type before buying cables.
