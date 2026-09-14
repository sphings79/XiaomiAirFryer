# Xiaomi Air Fryer

Home Assistant integration for Xiaomi, Careli, Silencare and Viomi air fryers.
Runs entirely on your network — the cloud is only used once, to look up the
device token, and can be skipped altogether.

**[Deutsche Fassung](README.de.md)**

---

## Setting up

<img src="docs/setup.svg" alt="Three ways to obtain the device token: scan a QR code, read it from a Mi Home backup, or enter it by hand" width="100%">

A Xiaomi device only answers to whoever holds its token. There are three ways
to get one, and the integration asks which you would like at the start.

**Scan a QR code.** The integration signs in to the Xiaomi cloud and reads the
token off your account, so nothing has to be typed. Any QR scanner works — your
phone's camera opens Xiaomi's sign-in page in the browser — and the Mi Home app
works too.

**From a Mi Home backup.** Upload an Android `.ab` backup, an already extracted
`miio2.db`, or the database out of an iOS backup. Nothing leaves your network.
Useful if you would rather not sign in, or if the sign-in ever stops working.

**By hand.** If you already know the address and the 32 character token, enter
them directly.

Whichever route you take, the token is stored once and everything afterwards
happens locally over the miIO protocol.

---

## What you get

<img src="docs/entities.svg" alt="Sensors for reading the fryer's state, and number, select, switch and button entities for operating it" width="100%">

Entities are only created where the model supports them, so a fryer without a
delayed start does not get a delayed start box.

Alongside the entities, eleven services cover the same ground for automations:
`start`, `stop`, `pause`, `resume`, `start_custom`, `preheat`, `recipe_id`,
`food_quanty`, `appoint_time`, `target_time` and `target_temperature`.

### Languages

Entity names, their states and the whole setup dialog are translated into
fourteen languages:

Czech · Danish · Dutch · English · French · German · Greek · Italian ·
Polish · Portuguese · Russian · Spanish · Swedish · Traditional Chinese

That includes the values themselves — a German dashboard reads *Gart* and
*Kein Wenden nötig* rather than `Cooking` and `NotTurnPot`. Recipes show as
*French fries* or *Chicken wings* instead of `M1` and `M2`, where the model's
recipe slots are known.

---

## Supported devices

| Name | Model |
|------|-------|
| Mi Smart Air Fryer | `careli.fryer.maf01` |
| Mi Smart Air Fryer | `careli.fryer.maf02` |
| Mi Smart Air Fryer 3.5L | `careli.fryer.maf03` |
| Xiaomi Smart Air Fryer Pro 4L | `careli.fryer.maf05a` |
| Mi Smart Air Fryer | `careli.fryer.maf06` |
| Mijia Smart Air Fryer 4.5L | `careli.fryer.maf06a` |
| Mijia Smart Air Fryer 4.5L | `careli.fryer.maf06b` |
| Mi Smart Air Fryer 3.5L Global | `careli.fryer.maf07` |
| Mijia Smart Air Fryer 5.5L | `careli.fryer.maf07c` |
| Youban Mijia Smart Air Fryer 6.5L | `careli.fryer.maf09a` |
| Xiaomi Smart Air Fryer 6.5L | `careli.fryer.maf10` |
| Mi Smart Air Fryer EU 6.5L | `careli.fryer.maf10a` |
| Upany Air Fryer YB-02208DTW | `careli.fryer.ybaf01` |
| Youban Smart Air Fryer 2208DTW | `careli.fryer.ybaf02` |
| Youban KitchenMi Smart Air Fryer 6007WA | `careli.fryer.ybaf03` |
| Youban KitchenMi Smart Air Fryer 6007WAB | `careli.fryer.ybaf04` |
| Xiaomi Smart Air Fryer 4.5L Global | `xiaomi.fryer.maf14` |
| Xiaomi Smart Air Fryer 4.5L | `xiaomi.fryer.maf15` |
| Xiaomi Smart Air Fryer | `xiaomi.fryer.maf16` |
| Xiaomi Smart Air Fryer | `xiaomi.fryer.maf07d` |
| Silencare Air Fryer 1.8L | `silen.fryer.sck501` |
| Silencare Silent Smart Air Fryer | `silen.fryer.sck505` |
| Viomi Smart Air Fryer Pro 6L | `viomi.fryer.v3` |
| Mi Smart Air Fryer | `miot.fryer.534` |

Property mappings are taken from the published MIoT specs rather than guessed.
If your model is missing, open an issue with its model name — visible in the
Mi Home app under device info — and a link to its spec on
[miot-spec.org](https://miot-spec.org).

---

## Installing

**Through HACS.** HACS → Integrations → ⋯ → Custom repositories →
`sphings79/XiaomiAirFryer`, category *Integration*. Install, then restart Home
Assistant.

**By hand.** Copy the `custom_components/xiaomi_airfryer` folder into your
config folder and restart.

Then add it under Settings → Devices & Services → Add Integration → *Xiaomi
AirFryer*.

---

## Notes

**The fryer is usually unplugged between uses.** Sensors report as unavailable
when it cannot be reached and recover on their own once it is back — no restart
needed. The controls stay usable and keep showing the last known setting, so
they do not clutter a dashboard with unavailable rows.

**Power consumption cannot be read.** None of these fryers measure it; their
MIoT specs carry no electrical values at all. A metering smart plug is the only
way to get real figures.

**Recipes live in the app, not the appliance.** The device reports which slot is
selected (`M1`, `M2`, …) but not what it holds, and its `recipe_name` stays on a
placeholder. The slot names in this integration were established by watching a
device while its recipes were selected one after another. Contributions for
other models are welcome — the table is per model, and unknown slots are passed
through unchanged.

---

## About this project

This is an independently maintained continuation of
[tsunglung/XiaomiAirFryer](https://github.com/tsunglung/XiaomiAirFryer), which
has not answered an issue since November 2024. It carries a working cloud
sign-in after the original one stopped functioning, a rewritten update path,
translations, controls, and fixes for a number of long-standing reports.

Original work © 2021 tsunglung, MIT licensed. The miIO protocol implementation
comes from [python-miio](https://github.com/rytilahti/python-miio) by Teemu
Rytilahti. The cloud sign-in follows the approach of
[Xiaomi-cloud-tokens-extractor](https://github.com/PiotrMachowski/Xiaomi-cloud-tokens-extractor)
by Piotr Machowski, also MIT licensed.
