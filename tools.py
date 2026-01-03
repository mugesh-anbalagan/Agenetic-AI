"""Tools for the ADK agents - Weather, Document RAG, SQL, and Search."""
import os
import requests
from typing import Dict, Any, List, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import google.generativeai as genai
from dotenv import load_dotenv

# Note: Using Gemini API directly for document querying (no LlamaIndex/embeddings needed)
# This avoids embedding compatibility issues and uses only Gemini API key

# Load environment variables from .env file
load_dotenv()

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/meetings_db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Gemini API key for document querying
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


def get_weather(city: str, date: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch real-time or historical weather data from OpenWeatherMap API.
    
    Args:
        city: City name
        date: Optional date (YYYY-MM-DD). If None, returns current weather.
    
    Returns:
        Dictionary containing weather data
    """
    api_key = os.getenv("OPENWEATHERMAP_API_KEY", "")
    if not api_key:
        return {"error": "OPENWEATHERMAP_API_KEY not set"}
    
    # For current weather
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        return {
            "city": data.get("name"),
            "temperature": data["main"]["temp"],
            "description": data["weather"][0]["description"],
            "condition": data["weather"][0]["main"],
            "humidity": data["main"]["humidity"],
            "wind_speed": data.get("wind", {}).get("speed", 0)
        }
    except Exception as e:
        return {"error": f"Failed to fetch weather: {str(e)}"}


def query_document(query: str) -> str:
    """
    Query documents using Gemini API directly (no embeddings required).
    Searches resume.pdf in the /data folder using Gemini's native document understanding.
    
    Args:
        query: Natural language query
    
    Returns:
        Answer from the document
    """
    if not GEMINI_API_KEY:
        return "Error: GEMINI_API_KEY not set. Please configure it in your .env file."
    
    data_dir = "./data"
    if not os.path.exists(data_dir):
        return "Error: /data folder not found. Please ensure resume.pdf is in the /data folder."
    
    try:
        # Find PDF files in data directory
        pdf_files = [f for f in os.listdir(data_dir) if f.lower().endswith('.pdf')]
        if not pdf_files:
            return "Error: No PDF files found in /data folder. Please ensure resume.pdf exists."
        
        pdf_path = os.path.join(data_dir, pdf_files[0])
        
        # Use Gemini API directly to read and query the PDF
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Upload PDF file to Gemini
        pdf_file = genai.upload_file(path=pdf_path)
        
        try:
            # Query the document
            prompt = f"""Please answer the following question based ONLY on the content of this document.

Question: {query}

IMPORTANT: 
- Answer ONLY if the information is clearly in the document
- If the information is NOT in the document, respond with exactly: "NOT_IN_DOCUMENT"
- Do not guess or infer information not in the document
- Be strict - if it's not explicitly in the document, return "NOT_IN_DOCUMENT"

Provide a clear and concise answer if found, or "NOT_IN_DOCUMENT" if not found."""
            
            response = model.generate_content([pdf_file, prompt])
            
            # Extract text from response
            if response and response.text:
                answer = response.text.strip()
                # Check if answer indicates info not in document
                if "NOT_IN_DOCUMENT" in answer.upper() or "not available" in answer.lower() or "not in the document" in answer.lower():
                    return "NOT_IN_DOCUMENT"
                return answer
            else:
                return "NOT_IN_DOCUMENT"
                
        finally:
            # Clean up uploaded file
            try:
                genai.delete_file(pdf_file.name)
            except:
                pass  # File may already be deleted
        
    except Exception as e:
        error_msg = str(e)
        # If document query fails, suggest using web search
        return f"Error querying document: {error_msg}. If information is not in the document, the agent can use Google Search instead. Please rephrase your question or ask the agent to search the web."


def google_search(query: str) -> str:
    """
    Perform Google Search using Gemini's grounding (built-in tool).
    This is a placeholder - Gemini's grounding will be handled by the agent.
    
    Args:
        query: Search query
    
    Returns:
        Search results (Note: Actual grounding happens via Gemini's built-in tool)
    """
    # Note: Gemini models have built-in Google Search grounding
    # This function is here for documentation, but the agent should use
    # Gemini's native grounding capabilities
    return f"Use Gemini's built-in Google Search grounding for query: {query}"


def execute_sql(sql_query: str) -> Dict[str, Any]:
    """
    Execute SQL query on PostgreSQL database.
    This is read-only - only SELECT queries are allowed.
    INSERT operations should use the insert_meeting tool instead.
    
    Args:
        sql_query: SQL query string (must be SELECT)
    
    Returns:
        Query results or error message
    """
    # Safety check - only SELECT queries allowed (read-only mode)
    sql_query_upper = sql_query.strip().upper()
    if not sql_query_upper.startswith("SELECT"):
        return {"error": "Read-only mode: Only SELECT queries are allowed. Use insert_meeting tool for INSERT operations."}
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql_query))
            rows = result.fetchall()
            columns = result.keys()
            return {
                "columns": list(columns),
                "rows": [dict(zip(columns, row)) for row in rows]
            }
    except Exception as e:
        return {"error": f"SQL execution error: {str(e)}"}


def insert_meeting(title: str, meeting_date: str, meeting_time: Optional[str] = None, reasoning: str = "") -> Dict[str, Any]:
    """
    Insert a new meeting into the database.
    This tool is specifically for the MeetingAgent.
    
    Args:
        title: Meeting title
        meeting_date: Date in YYYY-MM-DD format
        meeting_time: Optional time in HH:MM:SS format
        reasoning: Reasoning text (e.g., weather conditions)
    
    Returns:
        Success or error message
    """
    try:
        with engine.connect() as conn:
            query = text("""
                INSERT INTO meetings (title, meeting_date, meeting_time, reasoning)
                VALUES (:title, :meeting_date, :meeting_time, :reasoning)
            """)
            conn.execute(query, {
                "title": title,
                "meeting_date": meeting_date,
                "meeting_time": meeting_time,
                "reasoning": reasoning
            })
            conn.commit()
            return {"success": True, "message": f"Meeting '{title}' scheduled for {meeting_date}"}
    except Exception as e:
        return {"error": f"Failed to insert meeting: {str(e)}"}


def check_schedule_conflicts(meeting_date: str, meeting_time: Optional[str] = None) -> Dict[str, Any]:
    """
    Check for scheduling conflicts on a given date/time.
    
    Args:
        meeting_date: Date in YYYY-MM-DD format
        meeting_time: Optional time in HH:MM:SS format
    
    Returns:
        List of conflicting meetings or empty list
    """
    try:
        with engine.connect() as conn:
            if meeting_time:
                query = text("""
                    SELECT id, title, meeting_date, meeting_time, reasoning
                    FROM meetings
                    WHERE meeting_date = :meeting_date AND meeting_time = :meeting_time
                """)
                result = conn.execute(query, {"meeting_date": meeting_date, "meeting_time": meeting_time})
            else:
                query = text("""
                    SELECT id, title, meeting_date, meeting_time, reasoning
                    FROM meetings
                    WHERE meeting_date = :meeting_date
                """)
                result = conn.execute(query, {"meeting_date": meeting_date})
            
            conflicts = result.fetchall()
            if conflicts:
                return {
                    "has_conflicts": True,
                    "conflicts": [dict(zip(result.keys(), row)) for row in conflicts]
                }
            else:
                return {"has_conflicts": False, "conflicts": []}
    except Exception as e:
        return {"error": f"Failed to check schedule: {str(e)}"}

