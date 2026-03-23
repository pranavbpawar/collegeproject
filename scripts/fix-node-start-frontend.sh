#!/bin/bash
# Install Node.js 20 via nvm and start the frontend
set -e

# Install nvm if not present
if [ ! -d "$HOME/.nvm" ]; then
    echo "▶  Installing nvm..."
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
fi

# Load nvm
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

# Install Node.js 20
echo "▶  Installing Node.js 20..."
nvm install 20
nvm use 20
echo "Node version: $(node --version)"

# Remove old node_modules and reinstall with new Node
echo "▶  Reinstalling frontend deps with Node 20..."
cd /mnt/r/MACHINE/MACHINE/frontend
rm -rf node_modules package-lock.json
npm install --silent

# Start frontend
echo "▶  Starting frontend on http://localhost:5173 ..."
nohup npx vite --host 0.0.0.0 --port 5173 > /tmp/tbaps-frontend.log 2>&1 &
echo "Frontend PID: $!"

sleep 6
echo "=== Frontend Log ==="
cat /tmp/tbaps-frontend.log
