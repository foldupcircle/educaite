# main.py

from fastapi import FastAPI, Request, UploadFile, File, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from utils.utils import AWSClient, TavusClient, SupabaseClient, Utils
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)