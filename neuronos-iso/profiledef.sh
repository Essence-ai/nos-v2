#!/usr/bin/env bash
# shellcheck disable=SC2034

# NeuronOS ISO Profile Definition
# Based on Archiso releng profile

iso_name="neuronos"
iso_label="NEURONOS_$(date --date="@${SOURCE_DATE_EPOCH:-$(date +%s)}" +%Y%m)"
iso_publisher="NeuronOS Project <https://github.com/neuronos>"
iso_application="NeuronOS Live/Install ISO"
iso_version="$(date --date="@${SOURCE_DATE_EPOCH:-$(date +%s)}" +%Y.%m.%d)"
install_dir="neuronos"
buildmodes=('iso')
bootmodes=('bios.syslinux'
           'uefi.systemd-boot')
arch="x86_64"
pacman_conf="pacman.conf"
airootfs_image_type="squashfs"
airootfs_image_tool_options=('-comp' 'xz' '-Xbcj' 'x86' '-b' '1M' '-Xdict-size' '1M')
bootstrap_tarball_compression=('zstd' '-c' '-T0' '--auto-threads=logical' '--long' '-19')
file_permissions=(
  ["/etc/shadow"]="0:0:400"
  ["/etc/sudoers.d/liveuser"]="0:0:440"
  ["/etc/libvirt/hooks/qemu"]="0:0:755"
  ["/root"]="0:0:750"
  ["/root/.automated_script.sh"]="0:0:755"
  ["/root/.gnupg"]="0:0:700"
  ["/home/liveuser"]="1000:1000:750"
  ["/home/liveuser/Desktop"]="1000:1000:755"
  ["/home/liveuser/Desktop/install-neuronos.desktop"]="1000:1000:755"
  ["/usr/local/bin/neuronos-live-setup"]="0:0:755"
  ["/usr/bin/neuronos-welcome"]="0:0:755"
  ["/usr/bin/neuronos-vmmanager"]="0:0:755"
  ["/usr/bin/neuronos-onboarding"]="0:0:755"
  ["/usr/bin/looking-glass-client"]="0:0:755"
  ["/usr/bin/scream"]="0:0:755"
  ["/usr/bin/scream-receiver"]="0:0:755"
  ["/usr/bin/neuron-hwdetect"]="0:0:755"
  ["/usr/bin/neuronvm"]="0:0:755"
  ["/usr/bin/neuronvm-launch"]="0:0:755"
  ["/usr/lib/neuronos"]="0:0:755"
  ["/usr/lib/neuronos/neuronos-firstboot.sh"]="0:0:755"
  ["/usr/lib/neuronos/vm-setup.py"]="0:0:755"
  ["/usr/lib/neuronos/install-to-target.sh"]="0:0:755"
  ["/usr/bin/calamares"]="0:0:755"
)
