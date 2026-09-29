#!/bin/sh
# Izolovana sit pro FlashForge Creator 3 na USB LAN adapteru.
# Mac = brana (192.168.50.1) + DHCP + DNS. cloud.sz3dp.com -> Mac.
# Internet Macu (en0/Wi-Fi) zustava netknuty.
#
# Pouziti:  sudo sh start-isolated.sh [rozhrani]
# napr.:    sudo sh start-isolated.sh en3
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
IP=192.168.50.1
MASK=255.255.255.0
DM=/opt/homebrew/opt/dnsmasq/sbin/dnsmasq

# --- vyber rozhrani (USB LAN) ---
IFACE="$1"
if [ -z "$IFACE" ]; then
    # najdi aktivni en* rozhrani, ktere ma jen self-assigned 169.254 (nebo zadnou
    # IP) = izolovana sit se switchem. Rozhrani s realnou IP (internet) preskoc.
    for i in $(ifconfig -l | tr ' ' '\n' | grep '^en'); do
        ifconfig "$i" | grep -q 'status: active' || continue
        ip=$(ifconfig "$i" | awk '/inet /{print $2}')
        if [ -z "$ip" ] || echo "$ip" | grep -q '^169\.254\.'; then
            IFACE="$i"; break
        fi
    done
fi
[ -z "$IFACE" ] && { echo "Nenalezeno USB LAN rozhrani, zadej ho: sudo sh start-isolated.sh en3"; exit 1; }
echo ">> rozhrani: $IFACE   IP: $IP"

# --- staticka IP na tom rozhrani ---
ifconfig "$IFACE" inet "$IP" netmask "$MASK" up

# --- dnsmasq config (jen na tomto rozhrani) ---
CONF="$DIR/dnsmasq-ff.conf"
cat > "$CONF" <<EOF
interface=$IFACE
bind-interfaces
no-resolv
no-hosts
dhcp-authoritative
dhcp-range=192.168.50.50,192.168.50.150,$MASK,12h
dhcp-option=3,$IP
dhcp-option=6,$IP
address=/sz3dp.com/$IP
log-queries
log-dhcp
EOF

echo ">> test dnsmasq configu"
"$DM" --test -C "$CONF"

echo ">> spoustim dnsmasq (DHCP+DNS) na $IFACE"
"$DM" --keep-in-foreground -C "$CONF" &
DPID=$!
trap 'echo; echo "koncim, uklizim..."; kill $DPID 2>/dev/null; ifconfig '"$IFACE"' inet delete 2>/dev/null' EXIT INT TERM

sleep 1
echo ">> spoustim vlastni cloud (ff_cloud.py)"
echo ">> Zapoj tiskarnu do $IFACE. Az nabehne, koukni do requests.log."
python3 "$DIR/ff_cloud.py"
