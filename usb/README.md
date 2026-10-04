# USB root access (recon + backup)

`/opt/auto_run.sh` on the printer scans USB at every boot. If the root of a
**FAT32 (MBR)** stick holds an empty **`000C`** file and **`flashforge_init.sh`**,
it runs that script **as root**.

`flashforge_init.sh` here is a fast, read-only recon: it writes what the printer
contains (tools, partitions, init, settings, network) to `ff_recon/` on the
stick and exits. It changes nothing. Done when `ff_recon/DONE` exists.

## Steps
1. Format a USB stick FAT32 with an MBR/DOS partition table.
2. Copy `000C` and `flashforge_init.sh` into its root.
3. Power the printer OFF, insert the stick, power ON.
4. Wait ~1 min, power off, read `ff_recon/recon.txt` on the stick.

## Optional markers (empty files in the stick root)
- `DO_TELNET` — start a root shell on tcp/2323 until the next reboot (only if
  the printer ships `telnetd`; the recon lists what is available).
- `DO_BACKUP` — also dump the whole eMMC per partition (gzip). Slow; needs free
  space on the stick. **Do a full backup before changing anything on the printer.**

## Troubleshooting (if `ff_recon/` never appears)
- The stick must be **FAT32 + MBR** (not exFAT, not GPT).
- Both files must be in the **root**, names exact (`000C`, `flashforge_init.sh`).
- Insert the stick **before powering on** (auto_run only scans at boot).
- Try a different/smaller stick; some are not enumerated as `/dev/sda`.
