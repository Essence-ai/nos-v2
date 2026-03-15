#!/usr/bin/env bash
# NeuronOS ISO Profile Definition

iso_name="neuronos"
iso_label="NEURONOS_$(date +%Y%m)"
iso_publisher="NeuronOS Project <https://github.com/neuronos>"
iso_application="NeuronOS Live/Install ISO"
iso_version="$(date +%Y.%m.%d)"
install_dir="neuronos"
buildmodes=('iso')
bootmodes=('bios.syslinux.mbr' 'bios.syslinux.eltorito'
           'uefi-ia32.grub.esp' 'uefi-x64.grub.esp'
           'uefi-ia32.grub.eltorito' 'uefi-x64.grub.eltorito')
arch="x86_64"
pacman_conf="pacman.conf"
airootfs_image_type="squashfs"
airootfs_image_tool_options=('-comp' 'xz' '-Xbcj' 'x86' '-b' '1M' '-Xdict-size' '1M')
file_permissions=(
  ["/etc/shadow"]="0:0:400"
  ["/root"]="0:0:750"
  ["/root/.automated_script.sh"]="0:0:755"
  ["/usr/local/bin/"]="0:0:755"
)
