# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [2.0.1] - 2026-09-14

### Fixed

- The "Unsupported device found" message pointed at the upstream issue tracker,
  so reports about missing models never reached this repository.

## [2.0.0] - 2026-09-14

First release of the independently maintained continuation of
[tsunglung/XiaomiAirFryer](https://github.com/tsunglung/XiaomiAirFryer).

### Added

- **Controls.** Number entities for target time, temperature and delayed start;
  selects for recipe and food quantity; switches for preheat and the turn-food
  reminder; buttons for pause and resume. Each only where the model supports it.
- **QR code sign-in** replacing the cloud login, which stopped working when
  Xiaomi changed its API. Any QR scanner can be used.
- **Token from a Mi Home app backup**, for setting up without the cloud at all.
- **Fourteen languages** for entity names, their states, and the setup dialog.
- **Named recipes** — slot `M1` shows as "French fries" where the model's recipe
  order is known.
- `careli.fryer.maf10` and `xiaomi.fryer.maf16`.
- A remaining-time-in-percent sensor.
- Firmware version in the device registry.
- `icons.json`, brand assets, and issue templates.

### Fixed

- **Re-adding a configured fryer destroyed its config entry**, leaving it unable
  to load with "Invalid FryerMiot model: None".
- **An unreachable device during setup produced an HTTP 500** instead of a
  message, because the exception classes being caught were local stand-ins
  rather than the ones actually raised.
- **Sensors froze on their last values** when the fryer stopped answering, and
  recovery needed a Home Assistant restart.
- **A second fryer crashed the switch platform** with a `KeyError`.
- Six sensors read attributes that were never defined and always reported
  unknown.
- Zeroconf discovery never ran; the service type was missing from the manifest.
- `appoint_time` was offered as a 1–24 field but sent as minutes.
- `recipe_name` and `recipe_sync` were mapped the wrong way round on
  `xiaomi.fryer.maf14`.
- Passing an `input_number` into the numeric services failed validation.
- Service calls against an unreachable fryer raised instead of reporting.

### Changed

- Polling moved to a `DataUpdateCoordinator`: one request per interval shared by
  all entities, with consistent availability.
- Entity names come from translations rather than being hard-coded English.
  Existing entities keep their IDs; new installations follow the user's language.
- `micloud` dropped from the requirements.
