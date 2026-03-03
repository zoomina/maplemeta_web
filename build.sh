#!/bin/bash
# Render build script for maplemeta-web
set -e

echo "=== Installing Python dependencies ==="
pip install -r backend/requirements.txt

echo "=== Setting up Node.js ==="
# Check if Node.js 18+ already available
NODE_MAJOR=0
if command -v node &>/dev/null; then
  NODE_MAJOR=$(node --version | cut -d. -f1 | tr -d 'v')
fi

if [ "$NODE_MAJOR" -ge 18 ] 2>/dev/null; then
  echo "Node.js already available: $(node --version)"
else
  echo "Installing Node.js via fnm..."
  curl -fsSL https://fnm.vercel.app/install | bash -s -- --install-dir "$HOME/.fnm" --skip-shell
  export PATH="$HOME/.fnm:$PATH"
  "$HOME/.fnm/fnm" install 20
  "$HOME/.fnm/fnm" use 20
  FNM_ENV=$("$HOME/.fnm/fnm" env --shell bash)
  eval "$FNM_ENV"
fi

echo "Node.js: $(node --version)"
echo "npm: $(npm --version)"

echo "=== Building React frontend ==="
cd frontend
npm install
npm run build

echo "=== Build complete! ==="
ls -la ../backend/static/
