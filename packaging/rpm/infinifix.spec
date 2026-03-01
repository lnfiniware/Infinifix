Name:           infinifix
Version:        0.2.0
Release:        0.beta.1%{?dist}
Summary:        Huawei Linux Doctor
License:        MIT
URL:            https://github.com/lnfiniware/Infinifix
BuildRequires:  cmake gcc-c++ make python3
Requires:       python3 python3-rich fwupd alsa-utils pciutils usbutils

%description
InfiniFix is a terminal-first doctor for Huawei and Honor laptops on Linux.
It provides safe diagnostics, fix planning, apply mode, and rollback.

%prep
%autosetup -n %{name}-%{version}

%build
cmake -S src/cpp -B build/cpp
cmake --build build/cpp

%install
mkdir -p %{buildroot}%{_bindir}
mkdir -p %{buildroot}%{_datadir}/infinifix
mkdir -p %{buildroot}%{_libexecdir}/infinifix
mkdir -p %{buildroot}%{_datadir}/applications
mkdir -p %{buildroot}%{_datadir}/icons/hicolor/scalable/apps
mkdir -p %{buildroot}%{_datadir}/metainfo
mkdir -p %{buildroot}%{_mandir}/man1

cp -a src/infinifix %{buildroot}%{_datadir}/infinifix/
install -Dm755 build/cpp/probe %{buildroot}%{_libexecdir}/infinifix/probe
install -Dm644 assets/icon-h.svg %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/infinifix.svg
install -Dm644 packaging/desktop/infinifix.desktop %{buildroot}%{_datadir}/applications/infinifix.desktop
install -Dm644 packaging/desktop/infinifix.appdata.xml %{buildroot}%{_datadir}/metainfo/infinifix.appdata.xml
install -Dm644 packaging/man/infinifix.1 %{buildroot}%{_mandir}/man1/infinifix.1

cat > %{buildroot}%{_bindir}/infinifix <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
export INFINIFIX_PROBE_PATH=%{_libexecdir}/infinifix/probe
export PYTHONPATH=%{_datadir}/infinifix:${PYTHONPATH:-}
exec python3 -m infinifix.main "$@"
EOF
chmod 0755 %{buildroot}%{_bindir}/infinifix

%files
%{_bindir}/infinifix
%{_libexecdir}/infinifix/probe
%{_datadir}/infinifix
%{_datadir}/applications/infinifix.desktop
%{_datadir}/metainfo/infinifix.appdata.xml
%{_datadir}/icons/hicolor/scalable/apps/infinifix.svg
%{_mandir}/man1/infinifix.1*

%changelog
* Mon Mar 02 2026 lnfiniware <lnfiniware@users.noreply.github.com> - 0.2.0-0.beta.1
- v0.2 beta release: automation flags, report sanitization, lock safety
