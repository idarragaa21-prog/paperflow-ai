#!/usr/bin/env bash
# Renders every out/slide-*.html to a 1080x1350 PNG at 2x (2160x2700), Instagram-ready.
# Usage: bash render.sh
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1) install the bundled serif fonts (Montserrat is embedded as base64 in the CSS)
mkdir -p "$HOME/.fonts"
cp "$HERE"/fonts/*.ttf "$HOME/.fonts/" 2>/dev/null || true
fc-cache -f >/dev/null 2>&1 || true

# 2) locate the preinstalled Chromium (Playwright's build in this environment)
CHROME="$(ls /opt/pw-browsers/chromium-*/chrome-linux/chrome 2>/dev/null | head -1)"
[ -z "$CHROME" ] && CHROME="$(command -v chromium || command -v chromium-browser || command -v google-chrome || true)"
[ -z "$CHROME" ] && { echo "No Chromium found"; exit 1; }

# 3) render each slide
cd "$HERE/out"
n=0
for f in slide-*.html; do
  [ -e "$f" ] || continue
  "$CHROME" --headless=new --no-sandbox --disable-gpu --hide-scrollbars \
    --force-device-scale-factor=2 --window-size=1080,1350 \
    --screenshot="${f%.html}.png" "$f" >/dev/null 2>&1
  n=$((n+1))
done
echo "rendered $n slides -> $HERE/out/*.png"
