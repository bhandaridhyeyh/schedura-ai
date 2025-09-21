import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime
import tools
from typing import List, Dict

# --- INITIALIZATION ---
load_dotenv()

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# OpenAI client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    default_headers={"HTTP-Referer": os.getenv("OPENROUTER_SITE_NAME")},
)

# --- UPDATED DATA MODELS ---
class Message(BaseModel):
    sender: str
    text: str

class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    session_id: str

# --- TOOL MAPPING ---
AVAILABLE_TOOLS = {
    "get_available_services": tools.get_available_services,
    "get_available_slots": tools.get_available_slots,
    "book_appointment": tools.book_appointment,
}

# --- UPDATED API ENDPOINT ---
@app.post("/chat")
async def chat(request: ChatRequest):
    conversation_history = request.messages
    
    try:
        with open('config.json', 'r') as f: config = json.load(f)
        business_name = config.get("business_name", "your business")

        # --- 1. IMPROVED SYSTEM PROMPT ---
        system_prompt = f"""
        You are Schedura AI, a friendly and efficient booking assistant for {business_name}.
        Your primary goal is to help users book appointments. Use the conversation history for context.

        --- CRITICAL FLOW ---
        1. Greet the user and ask how you can help.
        2. If the user asks to see services, use the `get_available_services` tool.
        3. **After the user selects a service, DO NOT offer the services again.** Your next step is to ask for the desired date.
        4. After getting a date, use the `get_available_slots` tool.
        5. After the user selects a slot and provides their details (name, email), use the `book_appointment` tool.
        6. If you are missing information (like name or email), ask for it. Do not re-ask for information already in the chat history.

        --- CONTEXT ---
        - Today’s date is {datetime.now().strftime('%Y-%m-%d')}.
        """

        messages_for_llm = [{"role": "system", "content": system_prompt}]
        for msg in conversation_history:
            role = "user" if msg['sender'] == 'user' else "assistant"
            messages_for_llm.append({"role": role, "content": msg['text']})

        response = client.chat.completions.create(
            model="x-ai/grok-4-fast:free",
            messages=messages_for_llm,
            tools=[
                {
                    "type": "function", 
                    "function": {
                        "name": "get_available_services", 
                        # --- 2. REFINED TOOL DESCRIPTION ---
                        "description": "Use this tool ONLY when the user asks to see a list of all available services. Do NOT use it if they select a specific service to book.",
                        "parameters": { "type": "object", "properties": {} }
                    }
                },
                {
                    "type": "function", 
                    "function": {
                        "name": "get_available_slots", 
                        "description": "Find available appointment slots for a given date.", 
                        "parameters": {"type": "object", "properties": {"date_str": {"type": "string", "description": "The date to check, in YYYY-MM-DD format."}}}
                    }
                },
                {
                    "type": "function", 
                    "function": {
                        "name": "book_appointment", 
                        "description": "Book a service for a user once all details (service, date, time, name, email) are confirmed.", 
                        "parameters": {"type": "object", "properties": {"service_name": {"type": "string"}, "date_str": {"type": "string"}, "time_str": {"type": "string"}, "user_name": {"type": "string"}, "user_email": {"type": "string"}}}
                    }
                }
            ],
            tool_choice="auto"
        )
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        if tool_calls:
            tool_call = tool_calls[0]
            function_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)

            if function_name == "get_available_services":
                services = tools.get_available_services()
                return {"type": "service_options", "text": "Of course! Here are the services we offer:", "data": services}
            
            if function_name == "get_available_slots":
                date_str = args.get("date_str")
                if not date_str:
                    return {"type": "date_request", "text": "Perfect. Now, please pick a date for your appointment."}
                
                slots = tools.get_available_slots(date_str)
                if slots:
                    return {"type": "slot_options", "text": f"Here are the available slots for {date_str}:", "data": slots}
                else:
                    return {"type": "text", "text": f"Sorry, no slots are available on {date_str}. Please try another date."}
            
            if function_name == "book_appointment":
                messages_for_llm.append(response_message)
                confirmation_message = tools.book_appointment(**args)
                messages_for_llm.append({"tool_call_id": tool_call.id, "role": "tool", "name": function_name, "content": confirmation_message})

                final_response = client.chat.completions.create(model="x-ai/grok-4-fast:free", messages=messages_for_llm)
                return {"type": "text", "text": final_response.choices[0].message.content}

        return {"type": "text", "text": response_message.content}

    except Exception as e:
        print(f"[ERROR] Chat endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))