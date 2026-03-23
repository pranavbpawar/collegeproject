#!/bin/bash
# TBAPS — Stop all local services
echo "▶  Stopping TBAPS services..."
fuser -k 8000/tcp 2>/dev/null && echo "   ✅ Backend stopped"  || echo "   (backend was not running)"
fuser -k 5173/tcp 2>/dev/null && echo "   ✅ Frontend stopped" || echo "   (frontend was not running)"
echo "Done."
