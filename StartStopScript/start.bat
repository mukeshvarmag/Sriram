@echo off
cd backend
start cmd /k python main.py
cd ..
timeout /t 5
cd frontend
start cmd /k npm run dev
cd ..


# In local development, you can run the following commands to start and stop the servers:
# .\StartStopScript\start.bat
# .\StartStopScript\stop.bat