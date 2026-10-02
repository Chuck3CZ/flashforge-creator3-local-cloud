# FlashForge Creator 3 – local cloud & control

*🇬🇧 English · [🇨🇿 Čeština](README.cs.md)*

Replace FlashForge's official (cloud-based) software for the **Creator 3** printer
with your own **local server**. The printer stops talking to the Chinese
`*.sz3dp.com` servers and instead reports its status, streams the camera and
accepts commands on a machine in your own network. Includes a web dashboard with
a live view and a control panel (jog, temperatures, print control).

> ⚠️ Unofficial project, not affiliated with FlashForge. Use at your own risk.
> The proprietary firmware is **not** bundled here – only a description of what's
> inside and where to download it.

Tested on Creator 3, firmware **`1.4.8 155 VC4.2.3 20221201`** (PID `000C`).

## Why it works

Reverse engineering the stock firmware (see
[docs/firmware-analysis.md](docs/firmware-analysis.md)) revealed three things
that make this whole project possible:

1. The firmware is **Linux** (i.MX, ARM) and updates are **not encrypted** –
   just a ZIP with `tar.xz` packages and an install shell script.
2. The cloud client **does not verify the TLS certificate**
   (`CURLOPT_SSL_VERIFYPEER=0`, `VERIFYHOST=0`) → a self-signed cert plus a DNS
   redirect is enough.
3. The printer has a **local control protocol on TCP port 8899** (G-code/M-code)
   for reading status and sending movement and commands.

## What's in the repo

| Path | What it is |
|------|-----------|
| [`cloud/ff_cloud.py`](cloud/ff_cloud.py) | Local "cloud" + dashboard + control (Python stdlib only) |
| [`cloud/start-isolated.sh`](cloud/start-isolated.sh) | Brings up an isolated network (host as DHCP+DNS) and the server |
| [`usb/flashforge_init.sh`](usb/flashforge_init.sh) | Backup/recon script run from USB as root |
| [`orca-profile/`](orca-profile/) | **OrcaSlicer vendor profile for Creator 3** — printer / filament / process JSONs plus `.gx` converter and IDEX mirror/replica post-processors |
| [`docs/firmware-analysis.md`](docs/firmware-analysis.md) | What's inside the firmware, how to unpack it |
| [`docs/cloud-protocol.md`](docs/cloud-protocol.md) | Reverse-engineered cloud protocol (register/status/update) |
| [`docs/protocol-8899.md`](docs/protocol-8899.md) | Local port 8899 command reference |

## Quick start (isolated network via switch / USB-LAN)

Wiring: `printer ── switch ── host USB-LAN adapter`. The host keeps internet on
its main interface and runs the isolated network on the USB adapter.

```bash
# macOS (dnsmasq from Homebrew); Linux is analogous
brew install dnsmasq
sudo sh cloud/start-isolated.sh          # sets 192.168.50.1, DHCP+DNS, starts the cloud
```

The script redirects `*.sz3dp.com` to the host, the printer gets an IP over DHCP
and starts reporting. Open **http://localhost:8080**.

### Variant with your own DNS (Pi-hole / UniFi / router)

You don't need the isolated network – just point `cloud.sz3dp.com`,
`hz.sz3dp.com` (and optionally `update.sz3dp.com`) at the host running
`python3 cloud/ff_cloud.py`. Details in [cloud/README.md](cloud/README.md).

## Dashboard

- live camera image (`Snapshot` from the printer, ~2 s refresh),
- print status, progress, both nozzle temps and the bed,
- controls: **Home, jog X/Y/Z, temperatures, fan, pause/resume/cancel,
  emergency STOP and a raw command box** (over port 8899).

Server endpoints: `GET /` (dashboard), `GET /state` (status JSON),
`GET /snapshot.jpg` (latest frame), `POST /control` (`{"cmds":[...]}`).

## Status & roadmap

- [x] Custom cloud – register + status, nothing leaves the network
- [x] Dashboard with camera and telemetry
- [x] Control over 8899 (movement, temperatures, print)
- [ ] Assisted bed leveling from the dashboard
- [ ] Root/SSH via the USB init script (buzzer, `/opt/play`, MQTT to Home Assistant)
- [ ] Home Assistant integration

## License

MIT, see [LICENSE](LICENSE). FlashForge trademarks and firmware belong to their
respective owners.
