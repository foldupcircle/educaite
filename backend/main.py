# main.py
import os
import logging
import tempfile
import whisper
import uvicorn
from openai import OpenAI
from fastapi import FastAPI, Request, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from utils.utils import TavusClient, Utils, AWSClient, SupabaseClient
from utils.interactions import DailyClient

from langchain.document_loaders import PyPDFLoader
from langchain.chains import load_summarize_chain
from langchain_openai import ChatOpenAI  # Updated import
from langchain.text_splitter import CharacterTextSplitter
from langchain.prompts import PromptTemplate
import concurrent.futures  # Import for concurrency

map_prompt = PromptTemplate(
    template="Summarize this content:\n\n{text}",
    input_variables=["text"]
)

llm = ChatOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    model="gpt-4o-mini", 
    temperature=0
)  # Use ChatOpenAI for chat models

# summary_chain = load_summarize_chain(llm, chain_type="map_reduce", map_prompt=map_prompt)


async def format_text(text: str) -> str:
    try:
        response = llm.invoke(
            f"""Format this content so it is easier to read in plain text:
            {text}
            
            DO NOT CHANGE THE CONTENT OF THE TEXT. ONLY FORMAT IT SAFELY."""
        )
        return response.content
    except Exception as e:
        logger.error(f"Error formatting text: {e}")
        return ""

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
                
                logger.info("Formatting text...")
                context += "# Document Summary:\n"
                for i, document in enumerate(documents):
                    logger.info("Formatting text %d of %d", i, len(documents))
                    page_text = document.page_content
                    formatted_text = await format_text(page_text)
                    context += formatted_text

                # text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
                # splits = text_splitter.split_documents(documents)

                # logger.info(f"Number of text chunks created: {len(splits)}")

                # # Concurrently invoke the summary chain on each split
                # summaries = []
                # with concurrent.futures.ThreadPoolExecutor() as executor:
                #     logger.info("Summarizing splits concurrently")
                #     future_to_split = {executor.submit(summary_chain.invoke, split): split for split in splits}
                    
                #     for future in concurrent.futures.as_completed(future_to_split):
                #         split = future_to_split[future]
                #         try:
                #             summary = future.result()
                #             summaries.append(summary)
                #             logger.debug("Summary for split %s: %s", split, summary)
                #         except Exception as exc:
                #             logger.error("Error summarizing split %s: %s", split, exc)


                # Optionally, you can further reduce the summaries if needed
                # final_summary = "\n".join(summaries)

                # logger.info("Summary generated for the PDF.")

                # context += f"# Document Summary:\n{final_summary}"

                os.unlink(tmp_path)
                logger.info("Context: %s", context)
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

    return JSONResponse(content={"context": context}, status_code=200)


@app.post("/create_conversation")
async def create_conversation(request: Request):
    try:
        # Get the JSON body from the request
        body = await request.json()
        context = body.get('context')
        
        if not context:
            raise HTTPException(status_code=422, detail="Context is required")

        logger.info("Creating conversation with Tavus AI with context length: %d", len(context))
        conversation_url = tavus_client.create_conversation(
            context=context,
            callback_url="https://yourwebsite.com/webhook"
        )
        return JSONResponse(content={"conversation_url": conversation_url}, status_code=200)
    except ValueError as e:
        # Handle JSON parsing errors
        logger.error("Invalid JSON in request: %s", str(e))
        raise HTTPException(status_code=422, detail="Invalid JSON format")
    except Exception as e:
        logger.error("Error creating conversation: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))
    

@app.get("/live", response_class=HTMLResponse)
async def live(request: Request):
    conversation_url = request.cookies.get("conversation_url")
    if not conversation_url:
        logger.warning("No conversation URL found in cookies. Redirecting to home page.")
        return RedirectResponse("/", status_code=302)
    logger.info("Rendering live conversation page.")
    return templates.TemplateResponse("live.html", {"request": request, "conversation_url": conversation_url})


@app.post("/record")
async def record(
    request: Request,
    file: UploadFile = File(...),
    description: str = Form(""),
    user_id: str = Depends(get_current_user)
):
    print('Received record request from user: ', user_id)
    print('Description: ', description)
    # Save the uploaded file temporarily
    temp_file_path = f"temp_{user_id}.webm"
    try:
        with open(temp_file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        print('File saved to: ', temp_file_path)
        
        # Transcribe the audio using Whisper
        model = whisper.load_model("base")
        print('Transcribing...')
        result = model.transcribe(temp_file_path)
        print('Transcribed!')
        transcription = result["text"]
        print('Transcription: ', transcription)
        
        # Process with ChatGPT
        summary_prompt = PromptTemplate(
            template="""
                Summarize the student's situation based on the following criteria:
                1. What topic/subject they're studying
                2. Their current progress/understanding level
                3. Specific areas where they're struggling
                4. Their confidence level with the material
                Keep the response concise and empathetic and return in a cohesive paragraph.
                \n\n{text}
            """,
            input_variables=["text"]
        )
        print('Prompt: ', summary_prompt)
        print('LLM: ', llm)
        response = llm.invoke(summary_prompt.format(text=transcription))
        print('LLM Response:', response)

        # Clean up temp file
        os.remove(temp_file_path)
        
        return {"transcription": transcription, "analysis": response}
        
    except Exception as e:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    logger.info("Starting FastAPI application.")
    uvicorn.run(app, host="127.0.0.1", port=8000)
