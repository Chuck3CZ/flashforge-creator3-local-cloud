# USB skript (root přístup / záloha)

`/opt/auto_run.sh` v tiskárně při každém startu prohledá USB. Když v kořeni
FAT32 flashky najde **prázdný soubor `000C`** (PID Creatoru 3) a
**`flashforge_init.sh`**, spustí ten skript **jako root**.

`flashforge_init.sh` v této složce je průzkumný/zálohovací: uloží na flašku do
`ff_dump/` info o systému, `/etc`, `/opt`, `/data` a (volitelně) kompletní obraz
eMMC. Nic v tiskárně nemění a nakonec ji nechá normálně nabootovat.

## Použití
1. Flashka FAT32 (MBR), do kořene zkopíruj `000C` a `flashforge_init.sh`.
2. Tiskárnu vypni, zasuň flašku, zapni. Boot potrvá déle (záloha).
3. Hotovo, když v `ff_dump/` je soubor `DONE`.

Přepínače (prázdné soubory v kořeni flašky):
- `SKIP_EMMC` – vynechá plný obraz eMMC
- `ENABLE_TELNET` – dočasný root shell na portu 2323 (do restartu; jen když je
  ve firmwaru `telnetd`)

> Bez zálohy hrozí zničení tiskárny. Recovery režimy FlashForge nejsou veřejně
> zdokumentované – před přepisem systému si udělej obraz eMMC.
