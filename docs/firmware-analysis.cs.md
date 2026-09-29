# Rozbor firmwaru FlashForge Creator 3

*[🇬🇧 English](firmware-analysis.md) · 🇨🇿 Čeština*

Poznámky z reverse engineeringu firmwaru `1.4.8 155 VC4.2.3 20221201` (PID `000C`).
Firmware sám tu **není** – stáhneš ho z oficiálního
[FlashForge Download Center → Creator Series](https://www.flashforge.com/blogs/download-center-1/creator-series).

## Platforma

- **SoC:** Freescale/NXP i.MX, ARM `armv5tejl`, kernel Linux `3.10.32`
- **GUI:** Qt 4.8.6 aplikace `creator3-arm` (dynamicky linkovaná, **neostripovaná,
  s debug_info** → dobře se reverzuje v Ghidře/objdump)
- **Pohybová deska:** samostatný **STM32** (Cortex-M3, flash `0x08000000`),
  Linux s ním mluví přes `/dev/ttyS8`. Flashuje se z Linuxu nástrojem
  `ISPFinderPlusISP` (STM32 UART bootloader, BOOT0 přes GPIO267) – lze přehrát
  bez otevírání tiskárny.
- **Kamera:** `mjpg-streamer` (spouští se, když je připojená)

## Formát aktualizace

ZIP (nešifrovaný) s obsahem:

```
000C                     # PID marker (spouštěč aktualizace)
flashforge_init.sh       # instalační skript (běží jako root)
kernel-*.tar.xz          # uImage jádra
control-*.tar.xz         # firmware STM32 (Creator3.hex) + ISPFinderPlusISP
software-*.tar.xz        # Qt aplikace creator3-arm + auto_run.sh + ffstartup
library-*.tar.xz         # Qt, openssl 1.0.2, curl, tslib, mjpg-streamer
*.bmp                    # obrazovky (start/complete/failed)
```

Balíky se ověřují jen přes `md5sum.list` (žádný podpis).

## Boot / vstupní bod (root)

Při **každém** startu `/opt/auto_run.sh` prohledá USB (`/dev/sda1..4`). Pokud
v kořeni FAT32 flashky najde soubor `000C` a `flashforge_init.sh`, spustí ten
skript **jako root**. Odtud jde získat plný přístup k systému (viz
[`usb/flashforge_init.sh`](../usb/flashforge_init.sh)).

Poznámka: síťový `G28` (home) přes 8899 nedělá nic – domování jede jen přes
dotykový wizard. Pohybové příkazy (`G1`, jog) ale fungují.

## Klíčová zjištění pro síť

- Cloud běží na `cloud.sz3dp.com` (443) a `hz.sz3dp.com:11002`, aktualizace na
  `update.sz3dp.com:10443`.
- V `NetworkManager` je TLS ověřování **vypnuté**:
  `curl_easy_setopt(h, CURLOPT_SSL_VERIFYPEER(64), 0)` a
  `CURLOPT_SSL_VERIFYHOST(81), 0`. Ve firmwaru není žádný CA bundle. →
  self-signed certifikát projde.
- „Send log" ve firmwaru má natvrdo zadané SMTP přihlašovací údaje k účtu na
  `smtp.163.com` (patří FlashForge, ne uživateli).

## Jak se to rozbaluje

```bash
unzip <firmware>.zip -d fw
cd fw
for t in *.tar.xz; do mkdir -p "x/${t%.tar.xz}"; tar -xJf "$t" -C "x/${t%.tar.xz}"; done
# hlavni binarka:
file x/software-*/creator3-arm
arm-none-eabi-objdump -d x/software-*/creator3-arm   # disassembly
strings -n 4 x/software-*/creator3-arm | less        # retezce
```
