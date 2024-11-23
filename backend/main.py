# main.py
import os
import logging
import tempfile
from fastapi import FastAPI, Request, UploadFile, File, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from utils.utils import TavusClient, Utils

from langchain.document_loaders import PyPDFLoader
from langchain.chains.summarize import load_summarize_chain
from langchain.chat_models import ChatOpenAI  # Updated import
from langchain.text_splitter import CharacterTextSplitter

import concurrent.futures  # Import for concurrency

# Initialize LangChain components with ChatOpenAI
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)  # Use ChatOpenAI for chat models
summary_chain = load_summarize_chain(llm, chain_type="map_reduce")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log")
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Initialize Tavus client
tavus_client = TavusClient()

# Mock user authentication (replace with actual authentication logic)
def get_current_user(request: Request):
    return "user123"  # Dummy user ID

@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    logger.info("Rendering index page")
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload")
async def upload_document(
    request: Request,
    name: str = Form(...),
    file: UploadFile = File(None),
    user_id: str = Depends(get_current_user)
):
    logger.info("Received upload request from user: %s", user_id)

    if not user_id:
        logger.warning("User not authenticated")
        return RedirectResponse("/login", status_code=302)

    # Initialize context with user's name
    context = f"User Name: {name}\n"

    if file:
        logger.info("Processing uploaded file: %s", file.filename)
        try:
            if file.content_type == 'application/pdf':
                logger.info("File is a PDF. Processing with LangChain.")

                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(await file.read())
                    tmp_path = tmp.name
                logger.info("Temporary PDF saved at: %s", tmp_path)

                loader = PyPDFLoader(tmp_path)
                documents = loader.load()

                text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
                splits = text_splitter.split_documents(documents)

                logger.info(f"Number of text chunks created: {len(splits)}")

                # Concurrently invoke the summary chain on each split
                summaries = []
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future_to_split = {executor.submit(summary_chain.invoke, split): split for split in splits}
                    
                    for future in concurrent.futures.as_completed(future_to_split):
                        split = future_to_split[future]
                        try:
                            summary = future.result()
                            summaries.append(summary)
                            logger.debug("Summary for split %s: %s", split, summary)
                        except Exception as exc:
                            logger.error("Error summarizing split %s: %s", split, exc)

                # Optionally, you can further reduce the summaries if needed
                final_summary = "\n".join(summaries)

                logger.info("Summary generated for the PDF.")

                context += f"# Document Summary:\n{final_summary}"

                os.unlink(tmp_path)
                logger.info("Temporary PDF file deleted.")

            elif file.content_type.startswith('image/'):
                logger.info("Uploaded file is an image. No processing applied.")
                pass  # Do nothing for images

            else:
                logger.info("Uploaded file type is not supported for processing.")
                pass  # Do nothing for other file types

        except Exception as e:
            logger.error("Error processing the uploaded file: %s", str(e))
            return {"error": f"File processing failed: {str(e)}"}
    else:
        logger.info("No file uploaded. Proceeding with name only.")

    # Create a conversation with Tavus AI using the context
    try:
        logger.info("Creating conversation with Tavus AI.")
        conversation_url = tavus_client.create_conversation(
            context=context,
            callback_url="https://yourwebsite.com/webhook"
        )
        logger.info("Conversation created successfully: %s", conversation_url)
    except Exception as e:
        logger.error("Failed to create conversation with Tavus AI: %s", str(e))
        return {"error": f"Conversation creation failed: {str(e)}"}

    if not conversation_url:
        logger.error("Conversation URL retrieval failed.")
        return {"error": "Failed to retrieve conversation URL."}

    # Redirect the user to the live conversation page
    response = RedirectResponse("/live", status_code=302)
    response.set_cookie(
        key="conversation_url",
        value=conversation_url,
        httponly=True,
        secure=True,
        samesite="Lax"
    )
    logger.info("Redirecting user to /live page.")
    return response

@app.get("/live", response_class=HTMLResponse)
async def live(request: Request):
    conversation_url = request.cookies.get("conversation_url")
    if not conversation_url:
        logger.warning("No conversation URL found in cookies. Redirecting to home page.")
        return RedirectResponse("/", status_code=302)
    logger.info("Rendering live conversation page.")
    return templates.TemplateResponse("live.html", {"request": request, "conversation_url": conversation_url})

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting FastAPI application.")
    uvicorn.run(app, host="127.0.0.1", port=8000)
