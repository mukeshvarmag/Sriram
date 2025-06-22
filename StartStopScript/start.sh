#!/bin/bash

# Start backend (assumes assistant.py is in backend folder)
echo "Starting backend (assistant.py)..."
(cd ../backend && python assistant.py start) &
BACK_PID=$!

# Start frontend
echo "Starting frontend (npm run dev)..."
(cd ../frontend && npm run dev) &
FRONT_PID=$!

# Start playground
echo "Starting playground (npm run dev)..."
(cd ../playground && npm run dev) &
PLAY_PID=$!

echo "All services started."
echo "Backend PID: $BACK_PID"
echo "Frontend PID: $FRONT_PID"
echo "Playground PID: $PLAY_PID"
