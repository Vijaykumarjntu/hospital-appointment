from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from contextlib import asynccontextmanager

from src.config import settings
from src.database.connection import init_db, close_db, get_db, redis_client
from src.database.models import Patient, Doctor
from src.voice.free_voice_handler import FreeVoiceHandler

# Initialize free voice handler
voice_handler = FreeVoiceHandler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print(f"Starting {settings.APP_NAME}...")
    await init_db()
    
    # Test Redis
    await redis_client.set("test_key", "Redis is working!")
    test_value = await redis_client.get("test_key")
    print(f"✅ {test_value}")
    
    yield
    
    # Shutdown
    await close_db()
    print("👋 Shutdown complete")

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    lifespan=lifespan
)

@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "environment": settings.ENVIRONMENT,
        "voice_endpoints": {
            "websocket": "/ws/voice (for real-time audio)",
            "webhook": "/voice/webhook (for SIP integration)",
            "test_page": "/voice/test (browser testing)"
        }
    }

@app.get("/health")
async def health_check():
    # Check PostgreSQL
    try:
        async with AsyncSessionLocal() as session:
            await session.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {e}"
    
    # Check Redis
    try:
        await redis_client.ping()
        redis_status = "healthy"
    except Exception as e:
        redis_status = f"unhealthy: {e}"
    
    return {
        "status": "ok",
        "database": db_status,
        "redis": redis_status,
        "stt": "whisper (local)",
        "tts": "coqui (local)"
    }


# ========== FREE VOICE ENDPOINTS ==========

@app.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time voice"""
    await voice_handler.handle_websocket(websocket)

@app.post("/voice/webhook")
async def voice_webhook(request: Request):
    """Webhook endpoint for SIP integration"""
    return await voice_handler.handle_webhook(request)

@app.get("/voice/test")
async def voice_test_page():
    """Simple test page for voice in browser"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Voice Agent Test</title>
        <style>
            body { font-family: Arial; padding: 20px; }
            button { padding: 10px; margin: 5px; }
            #status { margin: 10px 0; padding: 10px; background: #f0f0f0; }
            #response { margin: 10px 0; padding: 10px; border: 1px solid #ccc; min-height: 50px; }
        </style>
    </head>
    <body>
        <h1>🎤 Voice Agent Test (100% Open Source)</h1>
        
        <div id="status">Disconnected</div>
        
        <button onclick="connect()">Connect</button>
        <button onclick="startRecording()" disabled id="recordBtn">Start Recording</button>
        <button onclick="stopRecording()" disabled id="stopBtn">Stop Recording</button>
        
        <div id="response"></div>
        <script>
            let ws = null;
            let mediaRecorder = null;
            let audioChunks = [];
            
            function connect() {
                ws = new WebSocket("ws://localhost:8000/ws/voice");
                
                ws.onopen = () => {
                    document.getElementById("status").innerHTML = "✅ Connected";
                    document.getElementById("recordBtn").disabled = false;
                };
                 ws.onmessage = (event) => {
                    // Play received audio
                    const audioBlob = new Blob([event.data], { type: 'audio/wav' });
                    const audioUrl = URL.createObjectURL(audioBlob);
                    const audio = new Audio(audioUrl);
                    audio.play();
                    
                    document.getElementById("response").innerHTML += "<br>🔊 Got response";
                };
                
                ws.onclose = () => {
                    document.getElementById("status").innerHTML = "❌ Disconnected";
                    document.getElementById("recordBtn").disabled = true;
                    document.getElementById("stopBtn").disabled = true;
                };
                }
            
            function startRecording() {
                navigator.mediaDevices.getUserMedia({ audio: true })
                    .then(stream => {
                        mediaRecorder = new MediaRecorder(stream);
                        mediaRecorder.ondataavailable = event => {
                            audioChunks.push(event.data);
                        };
                        
                        mediaRecorder.onstop = () => {
                            const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                            audioChunks = [];

                              // Send to server
                            const reader = new FileReader();
                            reader.onload = () => {
                                ws.send(reader.result);
                            };
                            reader.readAsArrayBuffer(audioBlob);
                        };
                        
                        mediaRecorder.start();
                        
                        document.getElementById("recordBtn").disabled = true;
                        document.getElementById("stopBtn").disabled = false;
                    });
            }
             function stopRecording() {
                mediaRecorder.stop();
                mediaRecorder.stream.getTracks().forEach(track => track.stop());
                
                document.getElementById("recordBtn").disabled = false;
                document.getElementById("stopBtn").disabled = true;
            }
        </script>
    </body>
    </html>
    """
    return Response(content=html, media_type="text/html")

    
@app.get("/patients")
async def get_patients(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Patient))
    patients = result.scalars().all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "phone": p.phone_number,
            "language": p.preferred_language
        }
        for p in patients
    ]

@app.get("/doctors/{doctor_id}/slots/{date}")
async def get_doctor_slots(
    doctor_id: int, 
    date: str,
    db: AsyncSession = Depends(get_db)
):
    """Get available slots for a doctor on a specific date"""
    from datetime import datetime
    
    target_date = datetime.strptime(date, "%Y-%m-%d").date()
    
    stmt = select(TimeSlot).where(
        TimeSlot.doctor_id == doctor_id,
        TimeSlot.slot_time.cast(Date) == target_date,
        TimeSlot.is_booked == False
    ).order_by(TimeSlot.slot_time)
    
    result = await db.execute(stmt)
    slots = result.scalars().all()
    
    return [
        {
            "id": s.id,
            "time": s.slot_time.strftime("%I:%M %p"),
            "datetime": s.slot_time.isoformat()
        }
        for s in slots
    ]

# Import for type hints
from sqlalchemy import Date
from src.database.connection import AsyncSessionLocal
from src.database.models import TimeSlot