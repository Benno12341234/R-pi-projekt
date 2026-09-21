#!/usr/bin/env bash
# One-time setup: turns the Pi's USB-C port into a USB gadget (Ethernet-over-USB),
# so when it's plugged into a computer via USB-C, that computer sees a network
# link to the Pi instead of just a power draw. Run this ON THE PI, then reboot.
#
# Only works on Pi models with a USB-C/OTG-capable data port (Pi Zero 2 W,
# Pi 4, Pi 5) - and only when using that port, not a plain USB-A port.

set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
    echo "run as root (sudo $0)" >&2
    exit 1
fi

BOOT_DIR=/boot/firmware
[ -d "$BOOT_DIR" ] || BOOT_DIR=/boot   # older Raspberry Pi OS layout

CONFIG_TXT="$BOOT_DIR/config.txt"
CMDLINE_TXT="$BOOT_DIR/cmdline.txt"

if ! grep -q '^dtoverlay=dwc2' "$CONFIG_TXT"; then
    echo "dtoverlay=dwc2" >> "$CONFIG_TXT"
    echo "added dtoverlay=dwc2 to $CONFIG_TXT"
fi

if ! grep -q 'modules-load=dwc2,g_ether' "$CMDLINE_TXT"; then
    sed -i 's/\brootwait\b/rootwait modules-load=dwc2,g_ether/' "$CMDLINE_TXT"
    echo "added modules-load=dwc2,g_ether to $CMDLINE_TXT"
fi

mkdir -p /etc/systemd/network
cat > /etc/systemd/network/80-usb-gadget.network <<'EOF'
[Match]
Name=usb0

[Network]
Address=192.168.7.2/24
EOF

systemctl enable systemd-networkd

echo
echo "Done. Reboot the Pi, then plug the USB-C data port into a computer."
echo "The Pi will show up on the host as a network device, reachable at 192.168.7.2."
