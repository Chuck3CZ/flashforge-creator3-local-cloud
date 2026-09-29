#!/bin/sh
# Creator 3 – průzkum + záloha. NIC NEMĚNÍ na tiskárně.
# Spouští ho /opt/auto_run.sh při bootu, když je na USB soubor 000C.
# Výstup jde na flashku do složky ff_dump/.

USB=/mnt
OUT=$USB/ff_dump
mkdir -p $OUT
LOG=$OUT/dump.log
exec >>$LOG 2>&1
set -x
date

# --- info o systému ---
uname -a                         > $OUT/uname.txt
cat /proc/cpuinfo                > $OUT/cpuinfo.txt
cat /proc/meminfo                > $OUT/meminfo.txt
cat /proc/partitions             > $OUT/partitions.txt
cat /proc/mtd                    > $OUT/mtd.txt 2>/dev/null
cat /proc/cmdline                > $OUT/cmdline.txt
mount                            > $OUT/mount.txt
df -k                            > $OUT/df.txt
ps                               > $OUT/ps.txt 2>/dev/null || ps -ef > $OUT/ps.txt
ls -la /bin /sbin /usr/bin /usr/sbin > $OUT/bins.txt 2>&1
busybox                          > $OUT/busybox.txt 2>&1
ifconfig -a                      > $OUT/ifconfig.txt 2>&1
ls -laR /opt                     > $OUT/opt_tree.txt 2>&1
ls -laR /data                    > $OUT/data_tree.txt 2>&1
ls -la /dev                      > $OUT/dev.txt 2>&1

# --- konfigurace (malé soubory) ---
mkdir -p $OUT/files
tar -cf $OUT/files/etc.tar /etc 2>/dev/null
tar -cf $OUT/files/opt_small.tar /opt/*.sh /opt/*.cfg /opt/Printer /opt/flashforge 2>/dev/null
tar -cf $OUT/files/data_small.tar --exclude='/data/pics' /data 2>/dev/null \
  || tar -cf $OUT/files/data_small.tar /data/log /data/*.txt 2>/dev/null

# --- plná záloha eMMC po oddílech (gzip, kvůli FAT32 limitu 4 GB) ---
if [ ! -f $USB/SKIP_EMMC ]; then
  for p in /dev/mmcblk0p*; do
    [ -b "$p" ] || continue
    n=$(basename $p)
    dd if=$p bs=64k 2>>$LOG | gzip -1 > $OUT/$n.img.gz
    md5sum $OUT/$n.img.gz >> $OUT/md5.txt
  done
  # boot oblast před prvním oddílem (bootloader), prvních 16 MB
  dd if=/dev/mmcblk0 bs=1M count=16 2>>$LOG | gzip -1 > $OUT/mmcblk0_first16M.img.gz
fi

# --- volitelně: dočasný shell po síti jen do restartu ---
# Vytvoř na flashce prázdný soubor ENABLE_TELNET a pak: telnet <IP> 2323
if [ -f $USB/ENABLE_TELNET ]; then
  if busybox telnetd --help >/dev/null 2>&1 || which telnetd; then
    (busybox telnetd -p 2323 -l /bin/sh || telnetd -p 2323 -l /bin/sh) &
    echo "telnetd started on 2323"
  else
    echo "telnetd not available"
  fi
fi

sync
echo DONE > $OUT/DONE
date
# žádný halt – tiskárna normálně dobootuje
exit 0
