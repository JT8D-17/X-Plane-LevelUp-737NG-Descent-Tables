#!/bin/sh
cd "$(dirname "$0")" || exit 1

for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1; then
    if "$candidate" -c "import tkinter" >/dev/null 2>&1; then
      exec "$candidate" LevelUpVNAVInstaller.pyw
    fi
  fi
done

echo "Python 3 with Tkinter is required."
echo "Install Python from https://www.python.org/downloads/ and run this launcher again."
