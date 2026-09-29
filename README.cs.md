# FlashForge Creator 3 – lokální cloud & ovládání

*[🇬🇧 English](README.md) · 🇨🇿 Čeština*

Náhrada oficiálního (cloudového) softwaru FlashForge pro tiskárnu **Creator 3**
vlastním **lokálním serverem**. Tiskárna přestane komunikovat s čínskými servery
`*.sz3dp.com` a místo toho hlásí stav, posílá obraz z kamery a přijímá příkazy
na počítač ve vlastní síti. Součástí je webový dashboard s živým náhledem a
ovládacím panelem (jog, teploty, řízení tisku).

> ⚠️ Neoficiální projekt, není spojený s FlashForge. Používáš na vlastní
> nebezpečí. Do repozitáře **není** přibalený proprietární firmware – jen popis,
> co je uvnitř, a odkaz, kde ho stáhnout.

Testováno na Creator 3, firmware **`1.4.8 155 VC4.2.3 20221201`** (PID `000C`).

## Proč to jde

Rozbor originálního firmwaru (viz [docs/firmware-analysis.md](docs/firmware-analysis.md))
ukázal tři věci, které celý projekt umožňují:

1. Firmware je **Linux** (i.MX, ARM) a aktualizace **nejsou šifrované** –
   obyčejný ZIP s `tar.xz` balíky a instalačním shell skriptem.
2. Cloudový klient **neověřuje TLS certifikát** (`CURLOPT_SSL_VERIFYPEER=0`,
   `VERIFYHOST=0`) → stačí self-signed certifikát a přesměrování DNS.
3. Tiskárna má **lokální řídicí protokol na TCP portu 8899** (G-code/M-code),
   přes který jde číst stav i posílat pohyb a příkazy.

## Co je v repu

| Cesta | Co to je |
|-------|----------|
| [`cloud/ff_cloud.py`](cloud/ff_cloud.py) | Lokální „cloud" + dashboard + ovládání (jen stdlib Pythonu) |
| [`cloud/start-isolated.sh`](cloud/start-isolated.sh) | Rozjede izolovanou síť (Mac jako DHCP+DNS) a server |
| [`usb/flashforge_init.sh`](usb/flashforge_init.sh) | Zálohovací/průzkumný skript spouštěný z USB jako root |
| [`docs/firmware-analysis.md`](docs/firmware-analysis.md) | Co je uvnitř firmwaru, jak se rozbaluje |
| [`docs/cloud-protocol.md`](docs/cloud-protocol.md) | Reverzovaný cloudový protokol (register/status/update) |
| [`docs/protocol-8899.md`](docs/protocol-8899.md) | Příkazy lokálního rozhraní na portu 8899 |

## Rychlý start (izolovaná síť přes switch/USB-LAN)

Zapojení: `tiskárna ── switch ── USB-LAN adaptér počítače`. Počítač si drží
internet na svém hlavním rozhraní, izolovanou síť dělá na USB adaptéru.

```bash
# macOS (dnsmasq z Homebrew), Linux obdobně
brew install dnsmasq
sudo sh cloud/start-isolated.sh          # nastaví 192.168.50.1, DHCP+DNS, spustí cloud
```

Skript přesměruje `*.sz3dp.com` na počítač, tiskárna dostane IP z DHCP a začne
se hlásit. Otevři **http://localhost:8080**.

### Varianta s vlastním DNS (Pi-hole/UniFi/router)

Nemusíš dělat izolovanou síť – stačí v DNS nasměrovat `cloud.sz3dp.com`,
`hz.sz3dp.com` (a případně `update.sz3dp.com`) na IP počítače, kde běží
`python3 cloud/ff_cloud.py`. Detaily v [cloud/README.md](cloud/README.md).

## Dashboard

- živý obraz z kamery (`Snapshot` z tiskárny, aktualizace ~2 s),
- stav tisku, průběh, teploty obou trysek a podložky,
- ovládání: **Domů, jog X/Y/Z, teploty, větrák, pauza/pokračovat/zrušit,
  nouzové STOP a pole na vlastní příkaz** (přes port 8899).

Endpointy serveru: `GET /` (dashboard), `GET /state` (JSON stavu),
`GET /snapshot.jpg` (poslední fotka), `POST /control` (`{"cmds":[...]}`).

## Stav a plány

- [x] Vlastní cloud – registrace i status, nic neodchází ven
- [x] Dashboard s kamerou a telemetrií
- [x] Ovládání přes 8899 (pohyb, teploty, tisk)
- [ ] Asistované vyrovnání podložky z dashboardu
- [ ] Root/SSH přes USB init skript (bzučák, `/opt/play`, MQTT do Home Assistanta)
- [ ] Napojení na Home Assistant

## Licence

MIT, viz [LICENSE](LICENSE). Značky a firmware FlashForge patří jejich vlastníkům.
