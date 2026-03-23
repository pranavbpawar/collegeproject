#!/bin/bash
cd /mnt/r/MACHINE/MACHINE/frontend
nohup npx vite --host 0.0.0.0 --port 5173 > /tmp/tbaps-frontend.log 2>&1 &
echo "Frontend PID: $!"
sleep 6
echo "=== Frontend Log ==="
cat /tmp/tbaps-frontend.log
