# main.py
import os
import logging
from fastapi import FastAPI, Request, UploadFile, File, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from utils.utils import AWSClient, TavusClient, SupabaseClient, Utils

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    logger.info("Rendering index page")
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(None),
    description: str = Form(None),
    user_id: str = Depends(get_current_user)
):
    logger.info("Received upload request from user: %s", user_id)

    if not user_id:
        logger.warning("User not authenticated")
        return RedirectResponse("/login", status_code=302)

    if file:
        logger.info("Processing file upload: %s", file.filename)
        # Save file to S3
        try:
            file_url = aws_client.upload_file_to_s3(file, user_id)
            logger.info("File uploaded to S3: %s", file_url)
            # Create a record in Supabase
            supabase_client.create_upload_record(user_id=user_id, file_url=file_url, description=None)
            logger.info("Upload record created in Supabase")
            content = f"File uploaded: {file.filename}"
        except Exception as e:
            logger.error("File upload failed: %s", str(e))
            return {"error": f"File upload failed: {str(e)}"}
    elif description:
        logger.info("Processing text description")
        # Save description to S3
        try:
            file_url = aws_client.save_text_to_s3(description, user_id)
            logger.info("Text saved to S3: %s", file_url)
            # Create a record in Supabase
            supabase_client.create_upload_record(user_id=user_id, file_url=file_url, description=description)
            logger.info("Upload record created in Supabase")
            content = description
        except Exception as e:
            logger.error("Text upload failed: %s", str(e))
            return {"error": f"Text upload failed: {str(e)}"}
    else:
        logger.warning("No file or description provided in the request")
        return {"error": "No file or description provided"}

    # Create conversation with Tavus AI
    try:
        logger.info("Creating conversation with Tavus AI")
        conversation_url = tavus_client.create_conversation(context=content, callback_url="https://yourwebsite.com/webhook")
        logger.info("Conversation created: %s", conversation_url)
        # Create a record in Supabase
        supabase_client.create_conversation_record(user_id=user_id, conversation_url=conversation_url, context=content)
        logger.info("Conversation record created in Supabase")
    except Exception as e:
        logger.error("Conversation creation failed: %s", str(e))
        return {"error": f"Conversation creation failed: {str(e)}"}

    if not conversation_url:
        logger.error("Failed to retrieve conversation URL")
        return {"error": "Failed to retrieve conversation URL."}

    # Redirect to /live with the conversation URL
    response = RedirectResponse("/live", status_code=302)
    # Use secure cookie settings
    response.set_cookie(key="conversation_url", value=conversation_url, httponly=True, secure=True, samesite="Lax")
    logger.info("Redirecting to /live")
    return response


@app.get("/live", response_class=HTMLResponse)
async def live(request: Request):
    conversation_url = request.cookies.get("conversation_url")
    if not conversation_url:
        logger.warning("No conversation URL found in cookies, redirecting to home")
        return RedirectResponse("/", status_code=302)
    logger.info("Rendering live conversation page")
    return templates.TemplateResponse("live.html", {"request": request, "conversation_url": conversation_url})


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting application")
    uvicorn.run(app, host="127.0.0.1", port=8000)
