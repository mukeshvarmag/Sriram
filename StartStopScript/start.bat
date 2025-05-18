@echo off
cd backend
start cmd /k python main.py
cd ..
timeout /t 5
cd frontend
start cmd /k npm run dev
cd ..