import io
import os
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import openai
import time  # Add this import at the top

load_dotenv()

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB

openai.api_key = os.getenv('OPENAI_API_KEY')

@app.route('/api/test-openai', methods=['GET'])
def test_openai():
    try:
        models = openai.models.list()
        return jsonify({'success': True, 'models': [m.id for m in models['data']]})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/process-audio', methods=['POST'])
def process_audio():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
    file = request.files['audio']


    # In your process_audio function, replace the filename line with:
    filename = secure_filename(f"audio-{int(time.time())}-{file.filename}")
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    try:
        with open(filepath, "rb") as audio_file:
            transcription = openai.audio.transcriptions.create(
                file=audio_file,
                model="whisper-1",
                response_format="text"
            )
        os.remove(filepath)
        return jsonify({'transcript': transcription})
    except Exception as e:
        if os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({'error': 'Server error processing audio'}), 500

@app.route('/api/get-ai-response', methods=['POST'])
def get_ai_response():
    data = request.get_json()
    message = data.get('message')
    if not message:
        return jsonify({'error': 'No message provided'}), 400
    try:
        completion = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are Sam, an experienced interviewer conducting a mock interview. Your role is to ask relevant questions based on the candidate's responses and provide a realistic interview experience. Keep your responses concise and professional."
                },
                {
                    "role": "user",
                    "content": message
                }
            ],
            max_tokens=150,
            temperature=0.7
        )
        response = completion.choices[0].message.content
        return jsonify({'response': response})
    except Exception as e:
        return jsonify({'error': 'Server error getting AI response'}), 500

@app.route('/api/generate-speech', methods=['POST'])
def generate_speech():
    data = request.get_json()
    text = data.get('text')
    if not text:
        return jsonify({'error': 'Text is required'}), 400
    try:
        speech_response = openai.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=text,
        )
        audio_bytes = speech_response.content
        return send_file(
            io.BytesIO(audio_bytes),
            mimetype='audio/mpeg',
            as_attachment=False,
            download_name='speech.mp3'
        )
    except Exception as e:
        return jsonify({'error': 'Failed to generate speech'}), 500

if __name__ == '__main__':
    app.run(host='localhost', port=3001)