#!/bin/sh
# FlashForge Creator 3 (PID 000C) - root recon, run from USB by /opt/auto_run.sh.
# Changes NOTHING on the printer. Writes what it finds to the USB stick, fast
# (seconds), so we can first confirm code execution works before any backup.
#
# Trigger: FAT32 (MBR) stick with these two files in the root:
#   000C                (empty marker file)
#   flashforge_init.sh  (this script)
# Power the printer off, insert the stick, power on. auto_run runs it as root.
#
# Optional marker files (empty) placed in the stick root:
#   DO_BACKUP     -> also dump the whole eMMC (slow; needs free space on stick)
#   DO_TELNET     -> start a root shell on tcp/2323 until next reboot (if telnetd)

# directory this script runs from = the mounted stick
DIR=$(cd "$(dirname "$0")" 2>/dev/null && pwd)
[ -z "$DIR" ] && DIR=/mnt
OUT="$DIR/ff_recon"
mkdir -p "$OUT" 2>/dev/null
LOG="$OUT/recon.txt"

{
  echo "=== FF Creator 3 recon @ $(date 2>/dev/null) ==="
  echo "--- id ---";            id 2>&1
  echo "--- uname -a ---";      uname -a 2>&1
  echo "--- cat /proc/version ---"; cat /proc/version 2>&1
  echo "--- cpuinfo ---";       cat /proc/cpuinfo 2>&1
  echo "--- meminfo ---";       head -5 /proc/meminfo 2>&1
  echo "--- mounts ---";        cat /proc/mounts 2>&1
  echo "--- df ---";            df -h 2>&1
  echo "--- partitions ---";    cat /proc/partitions 2>&1
  echo "--- mtd ---";           cat /proc/mtd 2>&1
  echo "--- cmdline ---";       cat /proc/cmdline 2>&1
  echo "--- block devices ---"; ls -l /dev/mmcblk* /dev/sd* /dev/mtd* 2>&1
  echo "--- /bin ---";          ls -la /bin 2>&1
  echo "--- /sbin ---";         ls -la /sbin 2>&1
  echo "--- /usr/bin ---";      ls -la /usr/bin 2>&1
  echo "--- /usr/sbin ---";     ls -la /usr/sbin 2>&1
  echo "--- busybox applets ---"; busybox 2>&1 | head -40
  echo "--- tools present ---"
  for t in sh ash bash telnetd dropbear sshd ssh python python3 lua perl \
           nc netcat socket inetd tcpsvd mosquitto curl wget scp tftp \
           vi nano dd gzip tar mount; do
    p=$(command -v $t 2>/dev/null); [ -n "$p" ] && echo "  $t -> $p"
  done
  echo "--- listening / network ---"; (netstat -ltnp 2>&1 || netstat -tnl 2>&1) | head -20
  echo "--- ifconfig ---";      ifconfig 2>&1
  echo "--- ps ---";            (ps w 2>&1 || ps 2>&1) | head -60
  echo "--- init.d ---";        ls -la /etc/init.d 2>&1
  echo "--- rcS ---";           cat /etc/init.d/rcS 2>&1
  echo "--- passwd ---";        cat /etc/passwd 2>&1
  echo "--- /opt ---";          ls -la /opt 2>&1
  echo "--- /opt/Printer ---";  ls -la /opt/Printer 2>&1
  echo "--- settings.conf ---"; cat /opt/Printer/settings.conf 2>&1
  echo "--- /data ---";         ls -la /data 2>&1
  echo "=== end recon ==="
} > "$LOG" 2>&1

# small, useful copies (config only; no big binaries)
cp /opt/Printer/settings.conf "$OUT/" 2>/dev/null
cp /etc/passwd "$OUT/" 2>/dev/null
cp /proc/mtd "$OUT/mtd.txt" 2>/dev/null
tar -czf "$OUT/etc.tgz" /etc 2>/dev/null

# optional: start a root shell on the network until reboot
if [ -f "$DIR/DO_TELNET" ]; then
  if command -v telnetd >/dev/null 2>&1; then
    telnetd -p 2323 -l /bin/sh 2>>"$LOG" &
    echo "telnetd started on 2323" >> "$LOG"
  elif busybox telnetd --help >/dev/null 2>&1; then
    busybox telnetd -p 2323 -l /bin/sh 2>>"$LOG" &
    echo "busybox telnetd started on 2323" >> "$LOG"
  else
    echo "no telnetd available" >> "$LOG"
  fi
fi

# optional: full eMMC image, per partition, gzipped (slow)
if [ -f "$DIR/DO_BACKUP" ]; then
  echo "backup start $(date)" >> "$LOG"
  for p in /dev/mmcblk0 /dev/mmcblk0p1 /dev/mmcblk0p2 /dev/mmcblk0p3 /dev/mmcblk0p4; do
    [ -b "$p" ] || continue
    n=$(basename "$p")
    dd if="$p" bs=1M 2>>"$LOG" | gzip -1 > "$OUT/$n.img.gz" 2>>"$LOG"
    echo "dumped $p" >> "$LOG"
  done
  echo "backup done $(date)" >> "$LOG"
fi

sync
echo OK > "$OUT/DONE"
sync
# do NOT halt; let the printer boot normally
exit 0
