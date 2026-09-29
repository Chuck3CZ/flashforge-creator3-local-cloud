# Vlastní cloud pro FlashForge Creator 3

Náhrada za `*.sz3dp.com`. Tiskárna neověřuje TLS certifikát
(`CURLOPT_SSL_VERIFYPEER=0`, `VERIFYHOST=0` v `NetworkManager`), takže stačí
self-signed cert + DNS přesměrování. Do firmwaru se nesahá.

## Endpointy, které tiskárna volá
- `POST https://cloud.sz3dp.com/printer/register` — registrace
  pole: `RegistrationCode, PrinterName, PrinterType, ExtruderCount, Version, AuthToken`
- `POST https://cloud.sz3dp.com/printer/status` — opakovaně, stav tisku
  pole: `FirmwareVersion, IPAddress, Door, Filament, CumulativeFilament, JobID,
  JobStatus, JobErrorCode, GcodePath, GcodeName, PrintProgress, Duration,
  PlatformCurTemp/TargetTemp, CurTemps, TargetTemps, DownloadProgress,
  EstimateTime, EstimateLengthLeft/Right, Snapshot(base64 foto), Status`
- Odpověď může nést `Command` + `Data`: `newjob, pause, resume, opencamera, closecamera`
- `update.sz3dp.com:10443/update` — kontrola aktualizací (necháme mlčet)

## Krok 1 – odchycení (běží teď)
1. Na serveru (Mac 192.168.16.168 / Pi / NAS):
       python3 ff_cloud.py
2. DNS: `cloud.sz3dp.com` a `hz.sz3dp.com` → 192.168.16.168
   - Pi-hole/AdGuard: Local DNS → add A record
   - dnsmasq: `address=/cloud.sz3dp.com/192.168.16.168`
   - router s local DNS: statický záznam
3. Na tiskárně vypni a znovu zapni cloud (Settings → Network), ať se přeregistruje.
4. Sleduj `requests.log` — uvidíme přesný formát JSONu.

## Krok 2 – doladění odpovědí
Podle zachyceného `register`/`status` upravíme odpovědi v `ff_cloud.py` tak, aby
tiskárna hlásila „připojeno". Pak přidáme trvalé úložiště stavu + web/HA.

## Poslání příkazu tiskárně
    echo '{"Command":"pause","Data":{}}' > cmd.json
Vloží se do odpovědi na příští `/printer/status`.

## Poznámky
- Porty: HTTPS 10443 i 443 mohou být potřeba (sz3dp používá :10443 pro update,
  cloud běží na standardním 443 — případně přidáme listener na 443).
- Alternativa bez cloudu: lokální LAN protokol na TCP **8899** (M105/M119/M27…)
  — pro Home Assistant jednodušší, ale bez vzdáleného přístupu a bez kamery push.
