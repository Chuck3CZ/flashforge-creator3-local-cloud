# FlashForge Creator 3 firmware analysis

*🇬🇧 English · [🇨🇿 Čeština](firmware-analysis.cs.md)*

Reverse-engineering notes for firmware `1.4.8 155 VC4.2.3 20221201` (PID `000C`).
The firmware itself is **not** here – download it from the official
[FlashForge Download Center → Creator Series](https://www.flashforge.com/blogs/download-center-1/creator-series).

## Platform

- **SoC:** Freescale/NXP i.MX, ARM `armv5tejl`, Linux kernel `3.10.32`
- **GUI:** Qt 4.8.6 app `creator3-arm` (dynamically linked, **not stripped, with
  debug_info** → easy to reverse in Ghidra/objdump)
- **Motion board:** separate **STM32** (Cortex-M3, flash `0x08000000`); Linux
  talks to it over `/dev/ttyS8`. Flashed from Linux via `ISPFinderPlusISP`
  (STM32 UART bootloader, BOOT0 via GPIO267) – can be reflashed without opening
  the printer.
- **Camera:** `mjpg-streamer` (started when a camera is attached)

## Update format

Unencrypted ZIP containing:

```
000C                     # PID marker (triggers the update)
flashforge_init.sh       # install script (runs as root)
kernel-*.tar.xz          # kernel uImage
control-*.tar.xz         # STM32 firmware (Creator3.hex) + ISPFinderPlusISP
software-*.tar.xz        # Qt app creator3-arm + auto_run.sh + ffstartup
library-*.tar.xz         # Qt, openssl 1.0.2, curl, tslib, mjpg-streamer
*.bmp                    # screens (start/complete/failed)
```

Packages are only checked against `md5sum.list` (no signature).

## Boot / entry point (root)

On **every** boot `/opt/auto_run.sh` scans the USB (`/dev/sda1..4`). If it finds
a file `000C` and `flashforge_init.sh` in the root of a FAT32 stick, it runs that
script **as root**. That's the way to gain full system access (see
[`usb/flashforge_init.sh`](../usb/flashforge_init.sh)).

Note: network `G28` (home) over 8899 does nothing – homing only works via the
touchscreen wizard. Movement commands (`G1`, jog) do work.

## Key networking findings

- Cloud runs on `cloud.sz3dp.com` (443) and `hz.sz3dp.com:11002`; updates on
  `update.sz3dp.com:10443`.
- TLS verification is **disabled** in `NetworkManager`:
  `curl_easy_setopt(h, CURLOPT_SSL_VERIFYPEER(64), 0)` and
  `CURLOPT_SSL_VERIFYHOST(81), 0`. There is no CA bundle anywhere in the
  firmware → a self-signed certificate is accepted.
- The "Send log" feature has hard-coded SMTP credentials for an account on
  `smtp.163.com` (belongs to FlashForge, not the user).

## How to unpack

```bash
unzip <firmware>.zip -d fw
cd fw
for t in *.tar.xz; do mkdir -p "x/${t%.tar.xz}"; tar -xJf "$t" -C "x/${t%.tar.xz}"; done
# main binary:
file x/software-*/creator3-arm
arm-none-eabi-objdump -d x/software-*/creator3-arm   # disassembly
strings -n 4 x/software-*/creator3-arm | less        # strings
```
