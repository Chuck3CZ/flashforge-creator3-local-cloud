# Cloudový protokol FlashForge Creator 3 (reverzovaný)

*[🇬🇧 English](cloud-protocol.md) · 🇨🇿 Čeština*

HTTPS + JSON. Certifikát se neověřuje, takže stačí namířit DNS domén `*.sz3dp.com`
na vlastní server se self-signed certifikátem.

## Endpointy

| Metoda | URL | Kdy |
|--------|-----|-----|
| POST | `https://update.sz3dp.com:10443/update` | kontrola firmwaru po startu |
| POST | `https://cloud.sz3dp.com/printer/register` | registrace (opakuje, dokud neuspěje) |
| POST | `https://cloud.sz3dp.com/printer/status` | periodické hlášení stavu + kamera |

## `/update` (kontrola firmwaru)

Request nese verze (`ControlVersion`, `KernelVersion`, `LibraryVersion`,
`SoftwareVersion`, `HardwareVersion`, `Name`, `PID`, `VID`, `SN`).
Pro „žádná aktualizace" stačí odpovědět:

```json
{ "ErrorCode": 200, "Message": "OK", "SessionID": "<echo>" }
```

## `/printer/register`

Request:

```json
{
  "RegistrationCode": "XXXXXX", "SN": "...", "MAC": "...",
  "PrinterType": "Flashforge Creator 3", "PrinterName": "",
  "Measure": "300X250X200", "ExtruderCount": 2, "ExtruderSepCount": 2,
  "Version": "1.4.8 155 VC4.2.3 20221201", "Vid": "2B71", "Pid": "000C",
  "AuthToken": ""
}
```

**Podmínka úspěchu** (ověřeno v `CloudClient::registerPrinter`): odpověď musí mít
`ErrorCode == 200` **a** obsahovat `RegistrationCode` (string). Bez `RegistrationCode`
firmware zaloguje `regisgter: no RegistrationCode` a registraci **opakuje dokola**.
`ErrorCode: 0` je bráno jako chyba. `AuthToken` a `PrinterName` jsou volitelné a
tiskárna si je uloží.

Funkční odpověď:

```json
{
  "ErrorCode": 200, "Message": "OK",
  "RegistrationCode": "<stejný jako v requestu>",
  "AuthToken": "cokoliv", "PrinterName": "Creator3"
}
```

Po úspěchu firmware volá `setConnectionStatus(true)` → displej ukáže „připojeno".

## `/printer/status`

Request (periodicky), zkráceně:

```json
{
  "SN": "...", "MAC": "...", "RegistrationCode": "...", "AuthToken": "...",
  "ErrorCode": 0, "Message": "",
  "Detail": {
    "JobStatus": "", "PrintProgress": 0.0, "JobID": "", "JobErrorCode": 0,
    "GcodeName": "", "GcodePath": "", "TmpModel": "", "Support": "",
    "CurTemps": [19, 19], "TargetTemps": [0, 0],
    "PlatformCurTemp": 18, "PlatformTargetTemp": 0,
    "Filament": 0, "CumulativeFilament": 0.0,
    "Duration": 0, "EstimateTime": 0.0,
    "EstimateLengthLeft": 0.0, "EstimateLengthRight": 0.0,
    "DownloadProgress": 0.0, "Door": 0,
    "FirmwareVersion": "1.4.8 155 VC4.2.3 20221201",
    "IPAddress": "192.168.x.y", "Measure": "300X250X200",
    "PrinterType": "Flashforge Creator 3", "PrinterName": ""
  },
  "Snapshot": "<base64 JPEG z kamery>"
}
```

Odpověď: `{"ErrorCode": 200, "Message": "OK"}`. Do odpovědi lze vložit příkaz
pro tiskárnu:

```json
{ "ErrorCode": 200, "Message": "OK", "Command": "pause", "Data": {} }
```

Známé cloudové příkazy: `newjob`, `pause`, `resume`, `opencamera`, `closecamera`.
Pro reálné ovládání je ale praktičtější lokální port 8899 – viz
[protocol-8899.md](protocol-8899.md).
