# Change Log - Geyserwala Connect - Python Bindings

## [0.0.8] - 2023-12-22

Allow for custom values. Condensed accessors.

### Added
- `subscribe()`, `unsubscribe()`
- `get_value()`, `set_value()`

### Changed
- `update_status()` -> `update()`

### Removed
- All value key accessors except `id`, `name`, `version`, `status`, `mode`, `tank_temp`, `element_demand`

## [0.0.7] - 2023-12-09

Migrate to persistent latch signals, with programmable hold time

### Added
- `external-disable` signal, accepts integer of number or seconds to latch, or true (defaults to 24 hours). Zero/false will clear.

### Changed
- `external-demand` signal, accepts integer of number of seconds to latch, or true (defaults to 24 hours). Zero/false will clear.

### Removed
- `lowpower-enable` replaced by `external-disable`.

## [0.0.6] - 2023-08-08

Initial development
