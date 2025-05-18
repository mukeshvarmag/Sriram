#!/bin/bash
cd backend
gnome-terminal -- bash -c "python3 main.py; exec bash"
cd ..
sleep 5
cd frontend
gnome-terminal -- bash -c "npm run dev; exec bash"
cd ..