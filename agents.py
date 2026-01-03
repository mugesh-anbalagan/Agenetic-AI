"""Google ADK Agent definitions - Weather, Document, Meeting Scheduler, and SQL Agents."""
import os
from google.adk import Agent
from google.adk.tools import FunctionTool
from tools import (
    get_weather,
    query_document,
    execute_sql,
    insert_meeting,
    check_schedule_conflicts
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
MODEL_NAME = "gemini-2.5-flash"  # Updated to available model

# Weather Agent Tools
weather_tool = FunctionTool(get_weather)

weather_agent = Agent(
    name="WeatherAgent",
    model=MODEL_NAME,
    tools=[weather_tool],
    instruction="You are a weather intelligence agent. Use the get_weather tool to fetch weather data. Always provide detailed weather information including temperature, conditions, and whether weather is suitable for outdoor activities."
)

# Document + Web Intelligence Agent Tools
doc_query_tool = FunctionTool(query_document)

doc_agent = Agent(
    name="DocAgent",
    model=MODEL_NAME,
    tools=[doc_query_tool],
    instruction="""You are a document intelligence agent with web search fallback capability.

WORKFLOW:
1. First, use the query_document tool to search the provided resume/PDF in the /data folder.
2. Check the response from query_document:
   - If it returns "NOT_IN_DOCUMENT" OR says information is not in the document
   - OR if it's a general knowledge question (like "Who is the CEO of Google?")
   - OR if it's about current events, company information, or anything not in a resume
   → Then use Gemini's built-in Google Search grounding to find the answer
3. For questions clearly not in a resume (company CEOs, current events, general knowledge), you may skip the document query and use Google Search directly.

EXAMPLES:
- "What is the leave policy?" → Try document first, if NOT_IN_DOCUMENT → Google Search
- "Who is the CEO of Google?" → This is NOT in a resume, use Google Search directly
- "What is my Python experience?" → Try document first (should be in resume)

Always provide a complete answer - either from the document OR from Google Search."""
)

# SQL Agent Tools
sql_tool = FunctionTool(execute_sql)

sql_agent = Agent(
    name="SQLAgent",
    model=MODEL_NAME,
    tools=[sql_tool],
    instruction="""You are an NL2SQL agent. Convert natural language queries to PostgreSQL SQL queries for the meetings table.
    The meetings table has columns: id, title, meeting_date, meeting_time, reasoning, created_at.
    
    IMPORTANT DATE HANDLING:
    - When user says "tomorrow": Calculate tomorrow's date as CURRENT_DATE + INTERVAL '1 day' OR use date format (YYYY-MM-DD)
    - When user says "today": Use CURRENT_DATE
    - When user says "next week": Use CURRENT_DATE + INTERVAL '7 days'
    - Always calculate dates automatically - NEVER ask the user for date format
    
    DATE EXAMPLES:
    - "Show all meetings scheduled tomorrow" → SELECT * FROM meetings WHERE meeting_date = CURRENT_DATE + INTERVAL '1 day';
    - "Do we have any meetings today?" → SELECT * FROM meetings WHERE meeting_date = CURRENT_DATE;
    - "List meetings next week" → SELECT * FROM meetings WHERE meeting_date >= CURRENT_DATE + INTERVAL '7 days' AND meeting_date < CURRENT_DATE + INTERVAL '14 days';
    
    Always use SELECT queries only. Return results in a clear, formatted way. Calculate dates automatically using PostgreSQL date functions."""
)

# Meeting Scheduler Agent Tools
check_conflicts_tool = FunctionTool(check_schedule_conflicts)
insert_meeting_tool = FunctionTool(insert_meeting)

meeting_agent = Agent(
    name="MeetingAgent",
    model=MODEL_NAME,
    tools=[check_conflicts_tool, insert_meeting_tool, weather_tool],
    instruction="""You are a meeting scheduler agent with multi-step reasoning capabilities.

    Workflow:
    1. First, use get_weather tool to check tomorrow's weather forecast for the user's city.
    2. Apply logic: If weather is clear or clouds AND temperature > 18°C, then is_weather_good = True.
    3. If is_weather_good is True:
       a. Use check_schedule_conflicts to check for conflicts on the requested date/time.
       b. If no conflicts, use insert_meeting to schedule the meeting.
       c. Include reasoning in the format: "Weather: [condition], [temperature]C"
    4. If weather is not good or conflicts exist, inform the user.

    Always use multi-step reasoning and coordinate tools as needed."""
)

# Root Agent (Supervisor) - Routes to appropriate agent
# For multi-agent coordination, use a single agent with all tools
all_tools = [weather_tool, doc_query_tool, sql_tool, check_conflicts_tool, insert_meeting_tool]

root_agent = Agent(
    name="Supervisor",
    model=MODEL_NAME,
    tools=all_tools,
    instruction="""You are the supervisor coordinating specialized agent capabilities:
    - Weather queries: Use get_weather tool directly
    - Document queries: Use query_document tool. For general knowledge questions (like "Who is Google CEO?"), use Gemini's built-in Google Search grounding
    - Meeting scheduling: Use get_weather, check_schedule_conflicts, and insert_meeting tools
    - Database queries: Use execute_sql tool (read-only SELECT queries)
    
    Route user queries to the appropriate tool(s) and coordinate multi-step workflows when needed.
    
    IMPORTANT INSTRUCTIONS:
    - For dates: When user says "tomorrow", calculate automatically - NEVER ask for date format
      * For SQL queries: Use PostgreSQL date functions (CURRENT_DATE + INTERVAL '1 day')
      * For other queries: Calculate as today + 1 day in YYYY-MM-DD format
    - For meeting scheduling: If city is not specified, use "Chennai" as default. Calculate tomorrow's date automatically.
    - For SQL queries: Use PostgreSQL date functions for date calculations - do NOT ask user for date format
    - For general knowledge questions not in documents: Use Gemini's built-in Google Search grounding capability
    - Be proactive: Don't ask for information you can infer or calculate - calculate dates automatically
    - Always provide complete answers - if a tool fails, explain clearly and suggest alternatives
    
    For meeting scheduling, follow the workflow: check weather → check conflicts → schedule if conditions are met."""
)
