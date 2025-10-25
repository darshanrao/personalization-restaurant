from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from llm import llm_service
from voice import voice_service

# Load environment variables
load_dotenv()

app = FastAPI(title="EchoEats Chat API")

# Configure CORS
allow_origin = os.getenv("ALLOW_ORIGIN", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[allow_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    sessionId: str = None

class ChatResponse(BaseModel):
    reply: str
    session_id: str
    message_count: int

class HealthResponse(BaseModel):
    status: str

class ChatHistoryResponse(BaseModel):
    session_id: str
    history: list

class VoiceChatRequest(BaseModel):
    message: str
    sessionId: str = None

class VoiceChatResponse(BaseModel):
    reply: str
    audio: str  # Base64 encoded audio
    session_id: str
    message_count: int

class SpeechToTextResponse(BaseModel):
    text: str
    success: bool

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(status="ok")

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat endpoint that processes messages with session management."""
    result = await llm_service.chat_once(request.message, request.sessionId)
    return ChatResponse(
        reply=result["reply"],
        session_id=result["session_id"],
        message_count=result["message_count"]
    )

@app.get("/chat/history/{session_id}", response_model=ChatHistoryResponse)
async def get_chat_history(session_id: str):
    """Get chat history for a specific session."""
    history = llm_service.get_chat_history(session_id)
    return ChatHistoryResponse(session_id=session_id, history=history)

@app.post("/voice/chat", response_model=VoiceChatResponse)
async def voice_chat(request: VoiceChatRequest):
    """Voice chat endpoint that processes messages and returns audio response."""
    # Get text response from LLM
    result = await llm_service.chat_once(request.message, request.sessionId)
    
    # Convert text to speech
    audio_base64 = await voice_service.text_to_speech(result["reply"])
    
    return VoiceChatResponse(
        reply=result["reply"],
        audio=audio_base64 or "",
        session_id=result["session_id"],
        message_count=result["message_count"]
    )

@app.post("/voice/stt", response_model=SpeechToTextResponse)
async def speech_to_text(audio_file: UploadFile = File(...)):
    """Convert speech to text using ElevenLabs STT API."""
    try:
        # Read audio file
        audio_data = await audio_file.read()
        
        # Convert to text using ElevenLabs STT
        text = await voice_service.speech_to_text(audio_data)
        
        if text:
            return SpeechToTextResponse(text=text, success=True)
        else:
            return SpeechToTextResponse(text="", success=False)
            
    except Exception as e:
        print(f"Error in STT endpoint: {e}")
        return SpeechToTextResponse(text="", success=False)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
