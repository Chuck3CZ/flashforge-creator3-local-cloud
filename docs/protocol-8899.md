# Local port 8899 protocol (FlashForge Creator 3)

*🇬🇧 English · [🇨🇿 Čeština](protocol-8899.cs.md)*

The printer's control interface on TCP port `8899` (class `ServerListener`), also
used by FlashPrint over the network. Text commands prefixed with `~`, terminated
by `\r\n`.

## Handshake

```
~M601 S0\r\n     # take control  -> "Control Success V2.1."
... commands ...
~M602\r\n        # release control -> "Control Release."
```

Every reply ends with `ok`.

## Supported commands

Derived from the `ServerListener::cmd_*` symbols:

```
G1 G28 G90 G91 G92
M17 M18 M104 M105 M106 M107 M108 M112 M114 M115 M119 M140
M144 M145 M146 M154 M155
M23 M24 M25 M26 M27 M28 M29
M601 M602 M610 M612 M650 M651 M652 M653 M654 M661 M662 M663
```

| Command | Meaning |
|---------|---------|
| `G1 X.. Y.. Z.. F..` | move (relative with `G91`) |
| `G28` | home – **does not work over the network on Creator 3** (touchscreen wizard only) |
| `G90` / `G91` | absolute / relative coordinates |
| `G92` | set current position |
| `M17` / `M18` | enable / disable motors |
| `M104 S<t> T<0/1>` | nozzle temperature (T0 left, T1 right) |
| `M140 S<t>` | bed temperature |
| `M106` / `M107` | fan on / off |
| `M112` | emergency stop |
| `M105` | temperatures: `T0:c/t T1:c/t B:c/t` |
| `M114` | position: `X1:.. X2:.. Y:.. Z:.. A:.. B:..` (X1/X2 = the two IDEX axes) |
| `M115` | machine info (type, FW, SN, MAC…) |
| `M119` | status + endstops, `MachineStatus`, `MoveMode`, `CurrentFile` |
| `M27` | SD print progress |
| `M23` | select/start printing a file (`0:/user/<name>`) |
| `M24` / `M25` / `M26` | resume / pause / cancel print |
| `M28` / `M29` | begin / end file write (upload) |
| `M146` | LED (color) |
| `M661` / `M662` | file list / file thumbnail |

Machine states: `READY, BUILDING, BUILDING_FROM_SD, PAUSED, CANCEL_BUILD,
BUILDING_ONBOARD, HEAT_SHUTDOWN`.

## Examples

```bash
# position and temperatures
printf '~M601 S0\r\n~M114\r\n~M105\r\n~M602\r\n' | nc <IP> 8899

# jog Z by -1 mm (bed up on Creator 3), relative
printf '~M601 S0\r\n~G91\r\n~G1 Z-1 F600\r\n~G90\r\n~M602\r\n' | nc <IP> 8899

# heat the left nozzle to 210 °C
printf '~M601 S0\r\n~M104 S210 T0\r\n~M602\r\n' | nc <IP> 8899
```

The server in this repo (`cloud/ff_cloud.py`) wraps this into the endpoint
`POST /control` with body `{"cmds": ["G91", "G1 Z-1 F600", "G90"]}`.

## Notes on Creator 3 geometry

- IDEX: two independent X axes (`X1` left, `X2` right).
- The **bed** moves in Z; a smaller Z means the bed is closer to the nozzle
  (Z ≈ 0 = contact). Approach zero carefully.
- Volume: 300 × 250 × 200 mm. Leveling: two adjustment screws at the front, fixed
  at the back.
