# Xiaomi Air Fryer

Control your Xiaomi, Careli, Silencare or Viomi air fryer from Home Assistant —
locally, over the miIO protocol.

**Not just sensors.** Set the target time and temperature with sliders, pick a
recipe by name, toggle preheat, and pause or resume, straight from a dashboard.

## Setting up

The setup dialog offers three ways to get the device token:

- **Scan a QR code** — signs in to the Xiaomi cloud and reads it for you. Any QR
  scanner works, the Mi Home app is not required.
- **A Mi Home app backup** — reads the token locally, nothing is sent to Xiaomi.
- **By hand** — if you already know the address and token.

Afterwards everything runs on your own network.

## Good to know

- 28 models supported; the property mappings are transcribed from the published
  MIoT specifications
- Entity names, their states and the setup dialog are translated into 14 languages
- Sensors report as unavailable while the fryer is unplugged and recover on their
  own; the controls stay usable and keep the last known setting
- Power consumption cannot be read — no model measures it

## Credits

Builds on [python-miio](https://github.com/rytilahti/python-miio) by Teemu
Rytilahti for the protocol, on
[Xiaomi-cloud-tokens-extractor](https://github.com/PiotrMachowski/Xiaomi-cloud-tokens-extractor)
by Piotr Machowski for the QR sign-in, and continues
[XiaomiAirFryer](https://github.com/tsunglung/XiaomiAirFryer) by tsunglung.

Unofficial and community built. Not affiliated with Xiaomi or Home Assistant.
