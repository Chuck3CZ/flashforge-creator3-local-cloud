# FlashForge Creator 3 cloud protocol (reverse-engineered)

*🇬🇧 English · [🇨🇿 Čeština](cloud-protocol.cs.md)*

HTTPS + JSON. The certificate is not verified, so it's enough to point the DNS of
the `*.sz3dp.com` domains at your own server with a self-signed certificate.

## Endpoints

| Method | URL | When |
|--------|-----|------|
| POST | `https://update.sz3dp.com:10443/update` | firmware check after boot |
| POST | `https://cloud.sz3dp.com/printer/register` | registration (retries until it succeeds) |
| POST | `https://cloud.sz3dp.com/printer/status` | periodic status + camera |

## `/update` (firmware check)

The request carries versions (`ControlVersion`, `KernelVersion`,
`LibraryVersion`, `SoftwareVersion`, `HardwareVersion`, `Name`, `PID`, `VID`,
`SN`). For "no update available" just answer:

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

**Success condition** (verified in `CloudClient::registerPrinter`): the response
must have `ErrorCode == 200` **and** contain `RegistrationCode` (string). Without
`RegistrationCode` the firmware logs `regisgter: no RegistrationCode` and
**retries forever**. `ErrorCode: 0` is treated as an error. `AuthToken` and
`PrinterName` are optional and the printer stores them.

Working response:

```json
{
  "ErrorCode": 200, "Message": "OK",
  "RegistrationCode": "<same as in the request>",
  "AuthToken": "anything", "PrinterName": "Creator3"
}
```

On success the firmware calls `setConnectionStatus(true)` → the screen shows
"connected".

## `/printer/status`

Request (periodic), abbreviated:

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
  "Snapshot": "<base64 JPEG from the camera>"
}
```

Response: `{"ErrorCode": 200, "Message": "OK"}`. A command for the printer can be
embedded in the response:

```json
{ "ErrorCode": 200, "Message": "OK", "Command": "pause", "Data": {} }
```

Known cloud commands: `newjob`, `pause`, `resume`, `opencamera`, `closecamera`.
For real control the local port 8899 is more practical – see
[protocol-8899.md](protocol-8899.md).
