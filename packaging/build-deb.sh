#!/usr/bin/env bash
# Build the Fierce-NG .deb on Debian/Kali.
#
#   sudo apt-get install -y debhelper dh-python python3-all python3-setuptools \
#        python3-dnspython python3-typer python3-rich python3-requests devscripts
#   ./packaging/build-deb.sh
#
# The resulting .deb is written to the parent directory.
set -euo pipefail
cd "$(dirname "$0")/.."

if ! command -v dpkg-buildpackage >/dev/null 2>&1; then
  echo "dpkg-buildpackage not found. Install build deps first (see header)." >&2
  exit 1
fi

chmod +x debian/rules
dpkg-buildpackage -us -uc -b
echo "Done. See ../fierce-ng_*.deb"
