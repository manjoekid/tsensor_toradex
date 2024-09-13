FILESEXTRAPATHS:prepend := "${THISDIR}/${BPN}:"

SRC_URI:append = " \
    file://sudoers.torizon \
"

# We explicitly require pam
inherit features_check

REQUIRED_DISTRO_FEATURES = "pam"

do_install:append () {
    install -m 0755 -d ${D}${sysconfdir}/sudoers.d
    install -m 0440 ${WORKDIR}/sudoers.torizon ${D}${sysconfdir}/sudoers.d/50-torizon
    chmod 4755 ${D}${bindir}/sudo
    # Append the udev line to sudoers file if it's not already present
    sed -i '$a udev ALL=(ALL) NOPASSWD: /usr/bin/restart_gpsd.sh' ${D}/${sysconfdir}/sudoers
    sed -i '$a udev ALL=(ALL) NOPASSWD: /bin/systemctl restart gpsd' ${D}/${sysconfdir}/sudoers

}


