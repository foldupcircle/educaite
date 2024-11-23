from fastapi import FastAPI, Request, UploadFile, File, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from utils import s3_client, tavus_client, auth

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")

# Dependency for authentication
def get_current_user(request: Request):
    # Implement your authentication logic here
    # For simplicity, we'll assume a user_id in session
    return request.session.get('user_id')

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
        file_url = s3_client.upload_file_to_s3(file, user_id)
        content = f"File uploaded: {file.filename}"
    elif description:
        # Save description to S3 or database
        content = description
        s3_client.save_text_to_s3(description, user_id)
    else:
        return {"error": "No file or description provided"}

    # Create conversation with Tavus AI
    conversation_url = tavus_client.create_conversation(content)

    # Redirect to /live
    response = RedirectResponse("/live", status_code=302)
    response.set_cookie(key="conversation_url", value=conversation_url)
    return response

@app.get("/live", response_class=HTMLResponse)
async def live(request: Request):
    conversation_url = request.cookies.get("conversation_url")
    return templates.TemplateResponse("live.html", {"request": request, "conversation_url": conversation_url})
