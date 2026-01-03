"""FastAPI application with Google ADK Agents."""
import os
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.adk import Runner
from google.adk.sessions.sqlite_session_service import SqliteSessionService
import google.genai as genai
from agents import root_agent
from database import create_tables

# Create database tables on startup (optional - will fail gracefully if DB not available)
try:
    create_tables()
    print("✅ Database connection successful")
except Exception as e:
    print(f"⚠️  Database connection failed (will retry when needed): {e}")

# Create session service once (reused across requests)
session_service = SqliteSessionService(db_path='sessions.db')

# Create global Runner instance (singleton - reused across all requests)
APP_NAME = 'agentic_workflow'
runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=session_service)

app = FastAPI(title="Agentic AI Workflow API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    """Chat request model."""
    message: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Chat response model."""
    response: str
    session_id: Optional[str] = None


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Agentic AI Workflow API",
        "framework": "Google ADK",
        "agents": ["WeatherAgent", "DocAgent", "MeetingAgent", "SQLAgent"],
        "status": "running"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat endpoint using Google ADK Runner.
    
    The root_agent coordinates between specialized capabilities:
    - Weather intelligence
    - Document RAG + Web search
    - Meeting scheduling with reasoning
    - NL2SQL queries
    """
    try:
        # Step 1: Set user_id and session_id
        user_id = request.user_id or "default_user"
        session_id = request.session_id or "default_session"
        
        # Step 2: Explicitly Check/Create Session (Get or Create Pattern)
        # Try to retrieve existing session (returns None if not found)
        existing_session = await session_service.get_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id
        )
        
        if existing_session is None:
            # Session doesn't exist, create it in the SQLite DB
            await session_service.create_session(
                app_name=APP_NAME,
                user_id=user_id,
                session_id=session_id
            )
        
        # Step 3: Create Content object for the message
        user_message = genai.types.Content(
            role='user',
            parts=[genai.types.Part(text=request.message)]
        )
        
        # Step 4: Run the agent asynchronously (Runner is global singleton)
        response_parts = []
        event_count = 0
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=user_message
        ):
            event_count += 1
            
            # Collect response from events - try multiple ways to extract text
            text_found = False
            
            # Method 1: Check event.content (Content object)
            if hasattr(event, 'content') and event.content:
                # If content is a string
                if isinstance(event.content, str):
                    response_parts.append(event.content)
                    text_found = True
                # If content has parts attribute
                elif hasattr(event.content, 'parts') and event.content.parts:
                    for part in event.content.parts:
                        # Part can be Part object with .text attribute
                        try:
                            part_text = getattr(part, 'text', None)
                            if part_text:
                                response_parts.append(str(part_text).strip())
                                text_found = True
                                continue
                        except:
                            pass
                        # Or part can be a string
                        if isinstance(part, str) and part.strip():
                            response_parts.append(part.strip())
                            text_found = True
                            continue
                        # Or part can be a dict
                        if isinstance(part, dict) and 'text' in part:
                            part_text = part['text']
                            if part_text:
                                response_parts.append(str(part_text).strip())
                                text_found = True
                                continue
                # If content has text attribute directly
                elif hasattr(event.content, 'text'):
                    response_parts.append(str(event.content.text))
                    text_found = True
            
            # Method 2: Check event.text directly
            if not text_found and hasattr(event, 'text') and event.text:
                response_parts.append(str(event.text))
                text_found = True
            
            # Method 3: Try string conversion if nothing else works
            if not text_found and event_count == 1:
                # For first event, try to extract any readable text
                event_str = str(event)
                if len(event_str) < 500:  # Only if reasonable size
                    # Try to find text patterns
                    if 'text' in event_str.lower():
                        response_parts.append(event_str)
        
        # Join all response parts
        if response_parts:
            response_text = " ".join(response_parts).strip()
        else:
            response_text = "No response received. The agent may be taking longer than expected or encountered an error."
        
        return ChatResponse(
            response=response_text,
            session_id=request.session_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=8000)
