from fastapi import FastAPI, Request, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from utils.utils import AWSClient, TavusClient, SupabaseClient, Utils
from openai import OpenAI
import whisper
import uvicorn

import os

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Initialize clients
aws_client = AWSClient()
tavus_client = TavusClient()
supabase_client = SupabaseClient()

# For simplicity, we'll mock user authentication
def get_current_user(request: Request):
    # Implement your actual authentication logic here
    # For this example, we'll use a dummy user_id
    return "user123"


@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(None),
    description: str = Form(None),
    user_id: str = Depends(get_current_user)
):
    if not user_id:
        return RedirectResponse("/login", status_code=302)

    if file:
        # Save file to S3
        try:
            file_url = aws_client.upload_file_to_s3(file, user_id)
            # Create a record in Supabase
            supabase_client.create_upload_record(user_id=user_id, file_url=file_url, description=None)
            content = f"File uploaded: {file.filename}"
        except Exception as e:
            return {"error": f"File upload failed: {str(e)}"}
    elif description:
        # Save description to S3
        try:
            file_url = aws_client.save_text_to_s3(description, user_id)
            # Create a record in Supabase
            supabase_client.create_upload_record(user_id=user_id, file_url=file_url, description=description)
            content = description
        except Exception as e:
            return {"error": f"Text upload failed: {str(e)}"}
    else:
        return {"error": "No file or description provided"}

    # Optionally, you can retrieve the content from S3 if needed
    # For this example, we'll use the content directly

    # Create conversation with Tavus AI
    try:
        conversation_url = tavus_client.create_conversation(context=content, callback_url="https://yourwebsite.com/webhook")
        # Create a record in Supabase
        supabase_client.create_conversation_record(user_id=user_id, conversation_url=conversation_url, context=content)
    except Exception as e:
        return {"error": f"Conversation creation failed: {str(e)}"}

    if not conversation_url:
        return {"error": "Failed to retrieve conversation URL."}

    # Redirect to /live with the conversation URL
    response = RedirectResponse("/live", status_code=302)
    # It's better to use session or a more secure method instead of cookies for sensitive data
    response.set_cookie(key="conversation_url", value=conversation_url, httponly=True, secure=True, samesite="Lax")
    return response


@app.get("/live", response_class=HTMLResponse)
async def live(request: Request):
    conversation_url = request.cookies.get("conversation_url")
    if not conversation_url:
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("live.html", {"request": request, "conversation_url": conversation_url})

@app.post("/record")
async def record(
    request: Request,
    file: UploadFile = File(...),
    description: str = Form(""),
    user_id: str = Depends(get_current_user)
):
    # Save the uploaded file temporarily
    temp_file_path = f"temp_{user_id}.webm"
    try:
        with open(temp_file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Transcribe the audio using Whisper
        model = whisper.load_model("base")
        result = model.transcribe(temp_file_path)
        transcription = result["text"]
        print('Transcription: ', transcription)
        
        # Process with ChatGPT
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are analyzing a video transcription."},
                {"role": "user", "content": transcription}
            ]
        )
        
        analysis = response.choices[0].message.content
        
        # Clean up temp file
        os.remove(temp_file_path)
        
        return {"transcription": transcription, "analysis": analysis}
        
    except Exception as e:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)