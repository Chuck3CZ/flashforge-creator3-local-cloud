# Lokální protokol port 8899 (FlashForge Creator 3)

*[🇬🇧 English](protocol-8899.md) · 🇨🇿 Čeština*

Řídicí rozhraní tiskárny na TCP portu `8899` (třída `ServerListener`). Používá ho
i FlashPrint po síti. Textové příkazy s prefixem `~`, ukončené `\r\n`.

## Handshake

```
~M601 S0\r\n     # převzít řízení  -> "Control Success V2.1."
... příkazy ...
~M602\r\n        # uvolnit řízení  -> "Control Release."
```

Každou odpověď zakončuje `ok`.

## Podporované příkazy

Zjištěno z `ServerListener::cmd_*` symbolů:

```
G1 G28 G90 G91 G92
M17 M18 M104 M105 M106 M107 M108 M112 M114 M115 M119 M140
M144 M145 M146 M154 M155
M23 M24 M25 M26 M27 M28 M29
M601 M602 M610 M612 M650 M651 M652 M653 M654 M661 M662 M663
```

| Příkaz | Význam |
|--------|--------|
| `G1 X.. Y.. Z.. F..` | pohyb (s `G91` relativně) |
| `G28` | domů – **přes síť u Creatoru 3 nefunguje** (jen dotykový wizard) |
| `G90` / `G91` | absolutní / relativní souřadnice |
| `G92` | nastavit aktuální polohu |
| `M17` / `M18` | zapnout / vypnout motory |
| `M104 S<t> T<0/1>` | teplota trysky (T0 levá, T1 pravá) |
| `M140 S<t>` | teplota podložky |
| `M106` / `M107` | větrák zap / vyp |
| `M112` | nouzové zastavení |
| `M105` | teploty: `T0:c/t T1:c/t B:c/t` |
| `M114` | poloha: `X1:.. X2:.. Y:.. Z:.. A:.. B:..` (X1/X2 = dvě osy IDEX) |
| `M115` | info o stroji (typ, FW, SN, MAC…) |
| `M119` | stav + koncové spínače, `MachineStatus`, `MoveMode`, `CurrentFile` |
| `M27` | průběh SD tisku |
| `M23` | vybrat/spustit tisk souboru (`0:/user/<jméno>`) |
| `M24` / `M25` / `M26` | pokračovat / pauza / zrušit tisk |
| `M28` / `M29` | začátek / konec zápisu souboru (upload) |
| `M146` | LED (barva) |
| `M661` / `M662` | seznam souborů / náhled souboru |

Stavy stroje: `READY, BUILDING, BUILDING_FROM_SD, PAUSED, CANCEL_BUILD,
BUILDING_ONBOARD, HEAT_SHUTDOWN`.

## Příklady

```bash
# poloha a teploty
printf '~M601 S0\r\n~M114\r\n~M105\r\n~M602\r\n' | nc <IP> 8899

# jog Z o -1 mm (podložka nahoru u Creatoru 3), relativně
printf '~M601 S0\r\n~G91\r\n~G1 Z-1 F600\r\n~G90\r\n~M602\r\n' | nc <IP> 8899

# nahřát levou trysku na 210 °C
printf '~M601 S0\r\n~M104 S210 T0\r\n~M602\r\n' | nc <IP> 8899
```

Server v tomto repu (`cloud/ff_cloud.py`) to obaluje do endpointu
`POST /control` s tělem `{"cmds": ["G91", "G1 Z-1 F600", "G90"]}`.

## Poznámky ke geometrii Creatoru 3

- IDEX: dvě nezávislé osy X (`X1` levá, `X2` pravá).
- V ose Z se pohybuje **podložka**; menší Z = podložka blíž k trysce
  (Z ≈ 0 = kontakt). K nule se přibližuj opatrně.
- Rozměr: 300 × 250 × 200 mm. Vyrovnání: dva stavěcí šrouby vepředu, vzadu napevno.
