#!/usr/bin/env bash
set -euo pipefail

MIN_PYTHON="3.12"

err() { echo "holix-link install: $*" >&2; exit 1; }

find_python() {
  for cmd in python3.14 python3.13 python3.12 python3; do
    if command -v "$cmd" >/dev/null 2>&1; then
      version=$("$cmd" -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
      if "$cmd" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)"; then
        echo "$cmd"
        return 0
      fi
    fi
  done
  return 1
}

PYTHON=$(find_python) || err "Python ${MIN_PYTHON}+ is required."

if ! command -v pipx >/dev/null 2>&1; then
  echo "Installing pipx..."
  "$PYTHON" -m pip install --user pipx
  "$PYTHON" -m pipx ensurepath || true
fi

pipx install Holix-Link || pipx upgrade Holix-Link

echo ""
echo "Holix Link installed. Try:"
echo "  holix-link --help"
echo "  holix-link pair LINK-CODE --folder ~/your-folder"