# RPM spec: wraps the PyInstaller folder (dist/drevo-light) built beforehand.
# Built by packaging/build_rpm.sh inside a Fedora container.
%global debug_package %{nil}
%global __strip /bin/true
%global __brp_strip %{nil}
%global __brp_strip_static_archive %{nil}
%global __brp_strip_comment_note %{nil}
%global __brp_check_rpaths %{nil}
%global __requires_exclude_from ^/usr/lib/drevo-light/.*$
%global __provides_exclude_from ^/usr/lib/drevo-light/.*$
AutoReqProv: no

Name:           drevo-light
Version:        %{?app_version}%{!?app_version:1.1}
Release:        1%{?dist}
Summary:        Lighting editor for the Drevo Tyrfing V2 keyboard
License:        GPL-3.0-or-later
URL:            https://github.com/tolgalen/Drevo
BuildArch:      x86_64
Requires:       systemd-udev

%description
Drevo Light paints keys, manages profiles and starts the built-in effects of
the Drevo Tyrfing V2 keyboard without the official software. Self-contained
build (bundles Python and Qt); installs a udev rule so the logged-in user can
access the keyboard.

%prep
%build

%install
install -d %{buildroot}/usr/lib/drevo-light %{buildroot}%{_bindir}
cp -a %{_sourcedir}/drevo-light/. %{buildroot}/usr/lib/drevo-light/
ln -s ../lib/drevo-light/drevo-light %{buildroot}%{_bindir}/drevo-light
install -Dm644 %{_sourcedir}/70-drevo-tyrfing.rules %{buildroot}/usr/lib/udev/rules.d/70-drevo-tyrfing.rules
install -Dm644 %{_sourcedir}/icon.png %{buildroot}%{_datadir}/icons/hicolor/256x256/apps/drevo-light.png
install -Dm644 %{_sourcedir}/drevo-light.desktop %{buildroot}%{_datadir}/applications/drevo-light.desktop
sed -i 's#^Exec=.*#Exec=drevo-light#' %{buildroot}%{_datadir}/applications/drevo-light.desktop

install -Dm644 %{_sourcedir}/LICENSE %{buildroot}%{_licensedir}/%{name}/LICENSE

%post
udevadm control --reload >/dev/null 2>&1 || :
udevadm trigger --subsystem-match=hidraw --subsystem-match=usb >/dev/null 2>&1 || :

%files
%license %{_licensedir}/%{name}/LICENSE
/usr/lib/drevo-light
%{_bindir}/drevo-light
/usr/lib/udev/rules.d/70-drevo-tyrfing.rules
%{_datadir}/icons/hicolor/256x256/apps/drevo-light.png
%{_datadir}/applications/drevo-light.desktop

%changelog
* Sun Nov 08 2026 candion <candion@gmail.com> - 1.1-1
- Release 1.1
