#!/bin/bash
# Render build script for maplemeta-web
set -e

echo === Installing Python dependencies ===
pip install -r backend/requirements.txt

echo === Installing Node.js via fnm ===
export HOME=/home/jamin
if [ ! -f /home/jamin/.fnm/fnm ]; then
  curl -fsSL https://fnm.vercel.app/install | bash
fi

export PATH=/home/jamin/.fnm:/home/jamin/.local/bin:/home/jamin/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin:/snap/bin
eval 

fnm install 20 --log-level quiet
fnm use 20

echo Node.js: 
echo npm: 

echo === Building React frontend ===
cd frontend
npm install
npm run build

echo === Build complete! ===
ls -la ../backend/static/
