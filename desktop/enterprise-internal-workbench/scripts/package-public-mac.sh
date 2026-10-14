#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_PATH="$ROOT_DIR/release/mac-arm64/enterprise-internal-workbench.app"
ZIP_PATH="$ROOT_DIR/release/enterprise-internal-workbench-darwin-arm64.zip"
SIGN_DIR="/tmp/enterprise-internal-workbench-mac-sign"
SIGN_APP_PATH="$SIGN_DIR/enterprise-internal-workbench.app"

cd "$ROOT_DIR"

export VITE_API_BASE_URL="${VITE_API_BASE_URL:-http://175.178.225.8/api}"

npm run build
npx electron-builder --mac zip --arm64

if [[ ! -d "$APP_PATH" ]]; then
  echo "mac app not found: $APP_PATH" >&2
  exit 1
fi

rm -rf "$SIGN_DIR"
mkdir -p "$SIGN_DIR"
ditto --norsrc "$APP_PATH" "$SIGN_APP_PATH"

xattr -cr "$SIGN_APP_PATH" || true
find "$SIGN_APP_PATH" -name ".DS_Store" -delete
find "$SIGN_APP_PATH" -exec xattr -d com.apple.FinderInfo {} \; 2>/dev/null || true
find "$SIGN_APP_PATH" -exec xattr -d "com.apple.fileprovider.fpfs#P" {} \; 2>/dev/null || true
find "$SIGN_APP_PATH" -exec xattr -d com.apple.provenance {} \; 2>/dev/null || true

# For local interview demos without an Apple Developer ID, avoid hardened runtime.
# Hardened runtime with ad-hoc signatures can make Electron's framework fail dyld Team ID checks.
codesign --force --deep --sign - "$SIGN_APP_PATH"
codesign --verify --deep --strict --verbose=2 "$SIGN_APP_PATH"

rm -f "$ZIP_PATH"
ditto -c -k --sequesterRsrc --keepParent "$SIGN_APP_PATH" "$ZIP_PATH"

echo "Created $ZIP_PATH"
