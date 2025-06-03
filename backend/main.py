from fastapi import FastAPI, UploadFile, File
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import os, io, uuid, pandas as pd
from openai import OpenAI
from mavparse import parse_bin_to_df
from chat_state import push_msg, history
from prompts import build_prompt

app = FastAPI()

# Add CORS middleware to allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

TELEMETRY_DIR = os.path.join(os.path.dirname(__file__), "_telemetry") #create a directory for the telemetry data
os.makedirs(TELEMETRY_DIR, exist_ok=True)

@app.get("/ping")
async def ping(): #check if we have a connection to the server
    return {"pong": True}

@app.post("/upload-log")
async def upload_log(file: UploadFile = File(...)): #upload a log file
    """Receive a .bin file, parse, store per-session parquet, return session_id."""
    session_id = str(uuid.uuid4())
    raw = await file.read()
    df = parse_bin_to_df(io.BytesIO(raw))
    df_path = os.path.join(TELEMETRY_DIR, f"{session_id}.parquet") #save the file to the telemetry directory
    df.to_parquet(df_path, index=False) #save the file to the telemetry directory
    return {
        "session_id": session_id,
        "rows": len(df),
        "columns": list(df.columns),
    } #return the session id, the number of rows and the columns

@app.post("/chat/{session_id}")
async def chat(session_id: str, payload: dict): #chat with the server
    user_msg = payload.get("message", "") #get the user message
    df_path = os.path.join(TELEMETRY_DIR, f"{session_id}.parquet") #check if the session id is valid
    if not os.path.exists(df_path):
        return {"error": "invalid session_id"}

    df = pd.read_parquet(df_path)

    msgs = history(session_id)
    push_msg(session_id, "user", user_msg)
    msgs.append({"role": "user", "content": user_msg})

    system_msg = build_prompt(df, msgs) #build the system message

    # Use new OpenAI v1.0+ API syntax
    stream = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[system_msg, *msgs],
        temperature=0.2,
        stream=True,
    )

    async def gen(): #generate the response
        full = []
        sentence_buffer = []  # Buffer tokens into sentences
        
        for chunk in stream: #for each chunk in the stream
            # New v1.0+ streaming response format
            if chunk.choices[0].delta.content is not None:
                token = chunk.choices[0].delta.content
                full.append(token) #append the token to the full response
                sentence_buffer.append(token)
                
                # Check if we hit a sentence boundary
                if any(punct in token for punct in ['.', '!', '?', '\n\n']):
                    # Send the complete sentence
                    complete_sentence = ''.join(sentence_buffer)
                    yield f"data:{complete_sentence}\n\n"
                    sentence_buffer = []  # Reset buffer
                    
        # Send any remaining tokens at the end
        if sentence_buffer:
            remaining_text = ''.join(sentence_buffer)
            yield f"data:{remaining_text}\n\n"
            
        # save assistant reply
        push_msg(session_id, "assistant", "".join(full))

    return StreamingResponse(gen(), media_type="text/event-stream") #return the response
