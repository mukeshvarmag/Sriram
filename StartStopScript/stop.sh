#!/bin/bash
echo "Stopping Flask (python) server..."
pkill -f "python3 main.py"
echo "Stopping React (npm) server..."
pkill -f "npm run dev"
echo "All servers stopped."