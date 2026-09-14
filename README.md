<div align="center">
  <img src="assets/banner.svg" alt="Xiaomi Air Fryer for Home Assistant — local miIO control with sensors, sliders and recipe selection, no cloud after setup" width="100%">

  # Xiaomi Air Fryer — Local Control for Home Assistant

  **Set time, temperature and recipe on your Xiaomi air fryer straight from Home Assistant.**
  Works over the local miIO protocol; the cloud is only touched once, to look up the device token, and can be skipped entirely.

  [![HACS](https://img.shields.io/badge/HACS-Custom-41BDF5?style=for-the-badge)](https://hacs.xyz)
  [![Release](https://img.shields.io/github/v/release/sphings79/XiaomiAirFryer?style=for-the-badge&color=3DDC97)](https://github.com/sphings79/XiaomiAirFryer/releases)
  [![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.6%2B-41BDF5?style=for-the-badge)](https://www.home-assistant.io)
  [![License](https://img.shields.io/github/license/sphings79/XiaomiAirFryer?style=for-the-badge&color=7C7CF5)](LICENSE)

  [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=sphings79&repository=XiaomiAirFryer&category=integration)

  **English** &#183; [Deutsch](README.de.md)

  If this saves you some fiddling, a ⭐ on the repository helps other people find it.
</div>

---

## Table of contents

- [What this integration does](#what-this-integration-does)
- [Entities you get](#entities-you-get)
- [Supported models](#supported-models)
- [Installation](#installation)
- [Setting it up](#setting-it-up)
- [Automation examples](#automation-examples)
- [Languages](#languages)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)
- [Credits](#credits)
- [Disclaimer](#disclaimer)
- [Contributing](#contributing)
- [License](#license)

---

## What this integration does

Xiaomi, Careli, Silencare and Viomi air fryers speak the local **miIO protocol**, the same
one the Mi Home app uses on your own network. This integration talks to them directly:
once it knows the device token, nothing leaves your network any more.

You get the state of the appliance as sensors — what it is doing, how long is left, which
recipe is selected — **and you can operate it**: set the temperature, pick a recipe, start
and pause it, all from a dashboard or an automation.

<img src="assets/setup.svg" alt="Three ways to obtain the device token: scan a QR code with any scanner, upload a Mi Home app backup, or enter the address and token by hand — afterwards everything runs locally" width="100%">

---

## Entities you get

<img src="assets/entities.svg" alt="Home Assistant entities: sensors reporting status, remaining time and recipe on the left; on the right sliders for temperature and time, dropdowns for recipe and quantity, switches for preheat and turn reminder, and pause and resume buttons" width="100%">

### Reading

| Entity | Example | Notes |
|---|---|---|
| `sensor.<device>_status` | `Cooking` | Translated into your language |
| `sensor.<device>_remaining` | `12` min | Minutes left |
| `sensor.<device>_remaining_percent` | `80` % | Works well with timer cards |
| `sensor.<device>_target_time` | `15` min | |
| `sensor.<device>_target_temperature` | `180` °C | |
| `sensor.<device>_recipe_id` | `French fries` | Named where the model's slots are known |
| `sensor.<device>_food_quanty` | `Double portion` | |
| `sensor.<device>_preheat_phase` | `Off` | |
| `sensor.<device>_turn_pot` | `Turn the food` | Prompt from the appliance |
| `sensor.<device>_appoint_time_left` | `0` min | Time until a delayed start |

### Operating

| Entity | Type | What it does |
|---|---|---|
| `number.<device>_target_temperature` | number | 40–200 °C |
| `number.<device>_target_time` | number | 1–1440 minutes |
| `number.<device>_appoint_time` | number | Delayed start, in minutes |
| `select.<device>_recipe_id` | select | Pick a recipe by name |
| `select.<device>_food_quanty` | select | Single, double, half, full |
| `switch.<device>` | switch | Start and cancel cooking |
| `switch.<device>_preheat` | switch | Preheat before cooking |
| `switch.<device>_turn_pot_config` | switch | Reminder to turn the food |
| `button.<device>_pause` | button | Pause |
| `button.<device>_resume` | button | Resume |

Eleven services cover the same ground for automations: `start`, `stop`, `pause`, `resume`,
`start_custom`, `preheat`, `recipe_id`, `food_quanty`, `appoint_time`, `target_time` and
`target_temperature`.

> Entity IDs follow your Home Assistant language, because Home Assistant derives them from
> the translated entity name. A German instance gets `sensor.<device>_zieltemperatur`.

---

## Supported models

Twenty-eight models. Property mappings are transcribed from the **published MIoT
specifications**, not guessed — which is also why the table below can say exactly what
each model supports.

| Model | ID | Baskets | Time | Temp. | Delay | Quantity | Preheat | Named recipes |
|---|---|---|---|---|---|---|---|---|
| Mi Smart Air Fryer | `careli.fryer.maf01` | 1 | ✅ | ✅ | ✅ | ✅ | ✅ | ☆ |
| Mi Smart Air Fryer | `careli.fryer.maf02` | 1 | ✅ | ✅ | ✅ | ✅ | ✅ | ☆ |
| Mi Smart Air Fryer 3.5L | `careli.fryer.maf03` | 1 | ✅ | ✅ | ✅ | ✅ | ✅ | ☆ |
| Xiaomi Smart Air Fryer Pro 4L | `careli.fryer.maf05a` | 1 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ 11 |
| Mi Smart Air Fryer | `careli.fryer.maf06` | 1 | ✅ | ✅ | ✅ | ✅ | ✅ | ☆ |
| Mijia Smart Air Fryer 4.5L | `careli.fryer.maf06a` | 1 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ 6 |
| Mijia Smart Air Fryer 4.5L | `careli.fryer.maf06b` | 1 | ✅ | ✅ | — | — | — | ✅ 6 |
| Mi Smart Air Fryer 3.5L Global | `careli.fryer.maf07` | 1 | ✅ | ✅ | ✅ | ✅ | ✅ | ☆ |
| Mijia Smart Air Fryer 5.5L | `careli.fryer.maf07c` | 1 | ✅ | ✅ | ✅ | ✅ | — | ✅ 13 |
| Youban Mijia Smart Air Fryer 6.5L | `careli.fryer.maf09a` | 1 | ✅ | ✅ | ✅ | ✅ | — | ✅ 13 |
| Xiaomi Smart Air Fryer 6.5L | `careli.fryer.maf10` | 1 | ✅ | ✅ | ✅ | ✅ | ✅ | ☆ |
| Mi Smart Air Fryer EU 6.5L | `careli.fryer.maf10a` | 1 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ 13 |
| Upany Air Fryer YB-02208DTW | `careli.fryer.ybaf01` | 1 | ✅ | ✅ | — | — | — | ☆ |
| Youban Smart Air Fryer 2208DTW | `careli.fryer.ybaf02` | 1 | ✅ | ✅ | ✅ | ✅ | ✅ | ☆ |
| Youban KitchenMi 6007WA | `careli.fryer.ybaf03` | 1 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ 23 |
| Youban KitchenMi 6007WAB | `careli.fryer.ybaf04` | 1 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ 23 |
| Mi Smart Air Fryer | `miot.fryer.534` | 1 | ✅ | ✅ | — | ✅ | ✅ | ☆ |
| Silencare Air Fryer 1.8L | `silen.fryer.sck501` | 1 | ✅ | ✅ | — | — | — | ☆ |
| Silencare Silent Smart Air Fryer | `silen.fryer.sck505` | 1 | ✅ | ✅ | — | — | — | ☆ |
| Viomi Smart Air Fryer Pro 6L | `viomi.fryer.v3` | 1 | ✅ | ✅ | — | — | — | ☆ |
| Xiaomi Smart Double Stack Air Fryer 12L | `xiaomi.fryer.jl12` | 2 | ✅ | ✅ | ✅ | — | — | ✅ 17 |
| Xiaomi Smart Double Stack Air Fryer 12L | `xiaomi.fryer.jl12w` | 2 | ✅ | ✅ | ✅ | — | — | ✅ 17 |
| Xiaomi Smart Air Fryer | `xiaomi.fryer.maf07d` | 1 | ✅ | ✅ | ✅ | ✅ | — | ✅ 13 |
| Xiaomi Smart Air Fryer 4.5L Global | `xiaomi.fryer.maf14` | 1 | ✅ | ✅ | ✅ | ✅ | — | ✅ 11 |
| Xiaomi Smart Air Fryer 4.5L | `xiaomi.fryer.maf15` | 1 | ✅ | ✅ | ✅ | ✅ | — | ✅ 11 |
| Xiaomi Smart Air Fryer | `xiaomi.fryer.maf16` | 1 | ✅ | ✅ | ✅ | ✅ | — | ✅ 13 |
| Xiaomi Smart Air Fryer 6.5L | `xiaomi.fryer.maf65` | 1 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ 13 |
| Mijia Smart Steam Air Fryer 7L | `xiaomi.fryer.st701o` | 1 | ✅ | ✅ | ✅ | ✅ | — | ✅ 37 |

✅ supported · — not available on this model · ☆ recipe slots not mapped yet
**Baskets** is how many cooking chambers the appliance has; the `jl12` models have two and
get a full set of entities per basket.
**Named recipes** shows how many slots are mapped — `✅ 13` means thirteen dishes appear by
name instead of `M1`.

> [!WARNING]
> **☆ means the recipe slots of that model are not mapped.** The fryer only ever reports
> `M1`, `M2` and so on; which dish that is comes from the Mi Home app, not from the
> device. Those models show the raw slot.
>
> For four of them — `maf01`, `maf02`, `maf03` and `maf07` — there is nothing to map: they
> fetch their recipes from the cloud at runtime, so the list differs per account. For the
> rest, the table can be worked out on a real appliance: pick the recipes one by one in
> the Mi Home app, note which `M` number appears in `sensor.…_recipe_id`, and open an
> issue with the list. It takes five minutes and turns a ☆ into a ✅ for everyone with
> that fryer. See [Contributing](#contributing).

Missing your fryer? Open a
[model request](https://github.com/sphings79/XiaomiAirFryer/issues/new?template=model_request.yml)
with its model name and a link to its spec on [miot-spec.org](https://miot-spec.org).

---

## Installation

### Through HACS

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=sphings79&repository=XiaomiAirFryer&category=integration)

Or by hand: HACS → Integrations → ⋯ → Custom repositories →
`sphings79/XiaomiAirFryer`, category *Integration*. Install it, then restart Home
Assistant.

### Manually

Copy `custom_components/xiaomi_airfryer` into your `config/custom_components` folder and
restart Home Assistant.

---

## Setting it up

Settings → Devices & Services → **Add Integration** → *Xiaomi AirFryer*. The dialog opens
with a choice of three ways to get the device token:

**Scan a QR code.** The integration signs in to the Xiaomi cloud and reads the token off
your account. Any QR scanner works — your phone's camera opens Xiaomi's sign-in page in
the browser — and the Mi Home app works too. Nothing has to be typed.

**From a Mi Home backup.** Upload an Android `.ab` backup, an extracted `miio2.db`, or the
database out of an iOS backup. Nothing is sent to Xiaomi.

**By hand.** Enter the IP address and the 32 character token directly.

Give the fryer a fixed IP address in your router while you are at it — the integration
follows an address change over mDNS, but a reservation saves it the trouble.

---

## Automation examples

Notify when cooking finishes:

```yaml
automation:
  - alias: Air fryer is done
    triggers:
      - trigger: state
        entity_id: sensor.kitchen_air_fryer_status
        to: cooked
    actions:
      - action: notify.mobile_app_phone
        data:
          message: The air fryer is finished.
```

Remind you to turn the food:

```yaml
automation:
  - alias: Turn the food
    triggers:
      - trigger: state
        entity_id: sensor.kitchen_air_fryer_turn_pot
        to: turn_pot
    actions:
      - action: notify.mobile_app_phone
        data:
          message: Time to turn the food over.
```

Preheat to a temperature from a helper:

```yaml
script:
  preheat_air_fryer:
    sequence:
      - action: number.set_value
        target:
          entity_id: number.kitchen_air_fryer_target_temperature
        data:
          value: "{{ states('input_number.fryer_temperature') | int }}"
      - action: switch.turn_on
        target:
          entity_id: switch.kitchen_air_fryer_preheat
      - action: switch.turn_on
        target:
          entity_id: switch.kitchen_air_fryer
```

> An automation matches the **raw state** (`cooked`, `turn_pot`), not the translation.
> Home Assistant always stores the raw value and translates only for display.

---

## Languages

Entity names, their **states**, and the whole setup dialog are translated into fourteen
languages:

🇨🇿 Czech · 🇩🇰 Danish · 🇳🇱 Dutch · 🇬🇧 English · 🇫🇷 French · 🇩🇪 German · 🇬🇷 Greek ·
🇮🇹 Italian · 🇵🇱 Polish · 🇵🇹 Portuguese · 🇷🇺 Russian · 🇪🇸 Spanish · 🇸🇪 Swedish ·
🇹🇼 Traditional Chinese

That includes the values themselves. A German dashboard reads *Gart* and *Kein Wenden
nötig* rather than `cooking` and `not_turn_pot`, and recipes show as *Pommes frites*
instead of `M1`.

---

## Troubleshooting

**Everything is unavailable.** The fryer is probably unplugged — that is its normal state
between uses. Sensors recover on their own once it answers again, no restart needed. The
controls stay usable throughout and keep showing the last known setting.

**Setup fails with "Could not reach the air fryer".** Give the appliance a few seconds
after switching it on; it does not answer immediately. Check that the IP address is right
and that nothing blocks UDP port 54321 between Home Assistant and the fryer.

**Two Home Assistant instances, one fryer.** That does not work. The miIO protocol is
session based, and two pollers interfere with each other until neither gets a reply.

**The token stopped working.** A token changes when the device is removed from Mi Home and
paired again. Remove the integration and set it up once more.

---

## FAQ

### Do I need a Xiaomi account?

Only if you want the QR sign-in to fetch the token for you. The backup route and entering
the token by hand both work without one, and nothing contacts Xiaomi after setup either
way.

### Does this work without an internet connection?

Yes, once it is set up. The integration talks to the fryer over your own network. Only the
initial token lookup needs the internet, and even that can be avoided.

### Can I see how much electricity the fryer uses?

No. None of these models measure it — their MIoT specifications carry no electrical values
at all. A metering smart plug is the only way to get real figures.

### Why are the recipes called M1 and M2 on my fryer?

The appliance only reports which slot is selected, not what it holds; the recipe list
lives in the Mi Home app. Where the slot order is known for a model, the integration shows
proper names. For other models, see [Contributing](#contributing) — it takes about five
minutes to work out.

### Can I change the time while it is cooking?

Yes. The controls are not locked during a cooking cycle, the same way the app allows it.
If the appliance refuses a value, Home Assistant shows the error.

### Does it work with two air fryers?

Yes, as long as each is set up in one Home Assistant instance only.

---

## Credits

Built on the work of others:

- [python-miio](https://github.com/rytilahti/python-miio) by Teemu Rytilahti — the miIO
  protocol implementation this relies on
- [Xiaomi-cloud-tokens-extractor](https://github.com/PiotrMachowski/Xiaomi-cloud-tokens-extractor)
  by Piotr Machowski — the approach used for the QR code sign-in
- [XiaomiAirFryer](https://github.com/tsunglung/XiaomiAirFryer) by tsunglung — the original
  integration this continues, MIT licensed
- Device property mappings come from the MIoT specifications published at
  [miot-spec.org](https://miot-spec.org)

If this is useful to you: [buy me a coffee](https://buymeacoffee.com/sphings) ☕

---

## Disclaimer

Unofficial and community built. Not affiliated with, endorsed by, or supported by Xiaomi,
Careli, Silencare, Viomi, or the Home Assistant project. Product names are trademarks of
their respective owners.

---

## Contributing

Particularly useful:

- **Recipe slot orders.** Open your fryer's recipe list in the Mi Home app and note the
  order. Slot `M1` is the first entry, `M2` the second, and so on. Open an issue with the
  list and your model name and it can be named properly for everyone.
- **New models.** A link to the model's spec on [miot-spec.org](https://miot-spec.org) is
  enough to add it — the mapping is transcribed from there rather than guessed.
- **Translation corrections.** One file per language under
  `custom_components/xiaomi_airfryer/translations/`.

---

## License

MIT — see [LICENSE](LICENSE). Original work © 2021 tsunglung, continued work © 2026
sphings79. Attribution details are in [NOTICE](NOTICE).

---

<sub>
Home Assistant Xiaomi air fryer integration · Mi Smart Air Fryer Home Assistant · Xiaomi
Smart Air Fryer Pro 4L · careli.fryer · miIO local control · air fryer without cloud ·
HACS custom integration · Mijia Heißluftfritteuse Home Assistant · Viomi air fryer ·
Silencare air fryer · Xiaomi air fryer token
</sub>
