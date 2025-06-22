#!/bin/bash

echo "Stopping backend (assistant.py)..."
taskkill //IM python.exe //F 2> /dev/null

echo "Stopping all node (npm run dev) processes..."
taskkill //IM node.exe //F 2> /dev/null

echo "All services stopped."
