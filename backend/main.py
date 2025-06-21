import os
import logging
from logging.handlers import TimedRotatingFileHandler
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from livekit import api

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging setup
LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

log_file = os.path.join(LOG_DIR, 'app.log')

logger = logging.getLogger('app_logger')
logger.setLevel(logging.INFO)
handler = TimedRotatingFileHandler(log_file, when='midnight', backupCount=7)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Pydantic model for request body
class TokenRequest(BaseModel):
    identity: str = 'candidate'
    room: str = 'mock-interview'

@app.post('/api/get-livekit-token')
async def get_livekit_token(request: TokenRequest):
    logger.info(f"Token request received: identity={request.identity}, room={request.room}")
    try:
        token = api.AccessToken() \
            .with_identity(request.identity) \
            .with_grants(api.VideoGrants(
                room_join=True,
                room=request.room,
            )) \
            .to_jwt()
        logger.info(f"Token generated successfully for identity={request.identity}, room={request.room}")
        return {"token": token}
    except Exception as e:
        logger.error(f"Token generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate token: {str(e)}")

# To run the app, use:
# uvicorn filename:app --host localhost --port 3001
