# FlashForge Creator 3 — OrcaSlicer profile

OrcaSlicer sám o sobě **nemá** profil pro FlashForge Creator 3 a existující
Orca-Flashforge fork taky ne (podporuje Adventurer-řadu a AD5X). Tenhle
balík přidá:

- machine profile (300×250×200 mm, IDEX, dvě 0.4 trysky)
- generické filament profily (PLA, PETG, ABS, PVA pro supporty)
- tři process profily (0.10 / 0.20 / 0.30 mm)
- post-processing skript `gx_converter.py`, který převede `.gcode` z Orcy
  do `.gx` binárního formátu, který tiskárna umí tisknout z USB/SD a který
  umí přijmout tvůj [lokální cloud](https://github.com/Chuck3CZ/flashforge-creator3-local-cloud)

## Instalace (macOS)

```bash
cd ~/creator3-mod/orca-profile
./scripts/install_macos.sh
```

Skript nakopíruje `FlashForge.json` a adresář `FlashForge/` do
`/Applications/OrcaSlicer.app/Contents/Resources/profiles/`. Případné
existující soubory zazálohuje s příponou `.bak-YYYYMMDD-HHMMSS`. Po
instalaci OrcaSlicer restartuj.

Odinstalace: `./scripts/install_macos.sh --uninstall`.

Po update OrcaSlicer je potřeba instalaci spustit znovu — bundled profily
se při update přepíšou.

## Instalace (Windows)

Nemám k dispozici Windows, ale postup je ekvivalentní:

1. Zavři OrcaSlicer.
2. Zkopíruj `FlashForge.json` do
   `C:\Program Files\OrcaSlicer\resources\profiles\`.
3. Zkopíruj adresář `FlashForge/` (s `machine/`, `process/`, `filament/`)
   do stejné cesty.
4. Spusť OrcaSlicer znovu.

## Zapnutí post-processingu

OrcaSlicer → **Settings → Others → Post-processing scripts**:

```
python3 "/Users/Martin/creator3-mod/orca-profile/scripts/gx_converter.py"
```

OrcaSlicer po sliceování automaticky zavolá skript, předá mu cestu
k `.gcode` souboru a výsledkem bude `.gx` soubor ve stejném adresáři.
Původní `.gcode` zůstane pro inspekci; chceš-li ho smazat, nastav v shellu
`GX_KEEP_GCODE=0`.

Pokud používáš dashboard z lokálního cloudu, `.gx` nahraj přes jeho
upload endpoint nebo prostě na SD kartu / přes `scp` na tiskárnu.

## IDEX režimy — tisk na levé / pravé hlavě

Creator 3 má **independent dual extruder** (IDEX). OrcaSlicer to řeší přes
"Extruder" picker u jednotlivých objektů / modifikátorů:

### 1. Pouze pravá hlava (T0)

- V levém panelu klikni na objekt → **Objects → Extruder → 1**.
- Prime tower zapnutý není potřeba, ale neuškodí (nižší risk zaschnutí
  druhé trysky).
- Po slice export → `.gx` → **detect_extruder_usage()** v konvertoru
  nastaví flag na 0 → tiskárna předehřeje jen T0.

### 2. Pouze levá hlava (T1)

- Objekt → **Extruder → 2** (OrcaSlicer indexuje od 1, tzn. 2 = T1).
- Konvertor nastaví flag na 1.

### 3. Dva filamenty / barvy (dual-head)

- V horní liště **"Add Filament"** přidej druhý filament (např. PLA
  černý + PLA bílý).
- Na každý objekt / modifikátor přiřaď filament 1 nebo 2.
- Prime tower **musí být zapnutý** (`enable_prime_tower = 1`, defaultně
  je, 35 mm široký ve standardním procesu).
- Flush volumes jsou v profilu nastavené na 140 mm³ (konzervativní,
  u čistých barev stačí 80, přechod bílá→černá chce 200+).

### 4. Duplicate mode (dvě stejné kopie současně)

OrcaSlicer stock to zatím **neumí** elegantně pro Creator 3 (jen pro
Snapmaker J1 přes "Printer settings → Printable area → Duplicate mode").
Workaround: slice jako single-extruder (T0), potom v `gx_converter.py`
před spuštěním nastav environment proměnnou `GX_IDEX_MODE=duplicate`
(TODO: v této verzi ještě není, přijde až budu mít referenční `.gx` ze
stock FlashPrint 5 s duplicate módem — jeho start sekvence posílá
specifický M-code, který neznám bez vzorku).

### 5. Mirror mode (zrcadlená kopie)

Stejná situace jako duplicate — čeká na vzorek z FlashPrintu 5.

## Co je ověřené proti oficiálnímu FlashForge Cura setupu

Hodnoty v tomto profilu jsou sladěné s oficiálním návodem *"Cura Setup
for Flashforge Creator 3/Creator 3 Pro"* (en.fss.flashforge.com, PDF):

- **Bed:** 300×250×200, origin at CENTER (souřadnice -150…+150 v X,
  -125…+125 v Y). Pozor, start gcode používá záporné souřadnice —
  pokud by firmware odmítal, ověřit v displeji tiskárny.
- **G-code flavor:** Marlin
- **Material:** 1.75 mm
- **Nozzle offset:** 0,0 (offset řeší firmware)
- **Start gcode:** `G90` / `G1 Z50 F420` (zvedne lože dolů = Z nahoru)
  / `M651 S255` (FlashForge M-code pro zapnutí LED komory)
- **End gcode:** `M104 S0` / `M140 S0` / `G162 Z F1800`
  (FlashForge-specifický home Z na maximum) / `M652` (LED off) /
  `G91` / `M18`
- **Extruder select:** `M108 T0` nebo `M108 T1` (FlashForge-specifický,
  musí předcházet standardnímu `T0`/`T1`)

### Pozor: oficiální FlashForge přiznání

> *"Note: Cura currently does not support slicing files for dual extruder
> printers. The Extruder 1 on Machine Settings window refers to the right
> extruder."*

To znamená, že **oficiální Cura setup umí jen single-extruder tisk**
(buď levá, nebo pravá hlava, ne obě zároveň). Dual-material je exkluzivita
FlashPrintu 5.

OrcaSlicer má lepší IDEX podporu než Cura (díky Snapmaker J1), takže
dual-material by měl v OrcaSlicer teoreticky fungovat, ale je to
**experimentální** a chce test. Pokud dual-material selhává, přepni se
na single-material a vyber si levou nebo pravou hlavu — to funguje
spolehlivě.

## Co ještě chybí

- **Reálný dual-head start/end G-code z FlashPrintu 5.** Pokud chceš
  tisknout dvěma materiály najednou, FlashPrint má specifickou start
  sekvenci pro priming obou trysek a parkování neaktivní hlavy. Pošli
  mi jeden `.gx` z FlashPrintu 5 (dual-head kostka 20×20×20 mm v PLA)
  a vytáhnu z něj přesné sekvence pro OrcaSlicer.
- **Duplicate / mirror mód** — stock OrcaSlicer to umí jen pro Snapmaker
  J1 a chce specifický M-code na začátku. Z reference `.gx` bych vytáhl
  i tohle.
- **Bed model `.stl`** a texture `.png` — kosmetika pro náhled v Orca.
- **Nozzle X-offset** pro IDEX. Teď je `extruder_offset = [0x0, 0x0]`,
  což OrcaSlicer bere jako "ovládá to firmware". Pokud by druhá hlava
  tiskla s posunem, nastavit zde skutečný offset podle kalibračních
  testů.

## Testování

1. V OrcaSlicer načti referenční model (20mm kostku).
2. Vyber vendor **FlashForge**, printer **Creator 3**.
3. Slice, over "Preview" zkontroluj, že se používá správný extruder.
4. Export vyrobí `.gcode` + konvertor vytvoří `.gx`.
5. `.gx` nahraj na SD / přes lokální cloud a vytiskni.
6. Pokud něco neseděsní (teploty, časy v displeji tiskárny, předehřev
   druhé trysky, kterou nepotřebuješ) → nahlás, co displeja ukazuje
   proti tomu, co má být, a dám to do pořádku.

## Interní struktura

```
orca-profile/
├── FlashForge.json              # vendor index
├── machine/
│   ├── FlashForge_Creator3.json       # printer settings
│   └── FlashForge_Creator3_model.json # machine_model (vizuál)
├── filament/
│   ├── FlashForge_Generic_PLA_Creator3.json
│   ├── FlashForge_Generic_PETG_Creator3.json
│   ├── FlashForge_Generic_ABS_Creator3.json
│   └── FlashForge_Generic_PVA_Creator3.json
├── process/
│   ├── 0.10mm_Fine_Creator3.json
│   ├── 0.20mm_Standard_Creator3.json
│   └── 0.30mm_Draft_Creator3.json
├── scripts/
│   ├── gx_converter.py           # .gcode → .gx post-processing
│   └── install_macos.sh
└── README.md
```
