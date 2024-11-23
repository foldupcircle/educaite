# utils/utils.py

import os
import uuid
import random
import string
import logging
import boto3
import requests
from botocore.exceptions import NoCredentialsError, ClientError
from dotenv import load_dotenv
from supabase import create_client, Client

# Configure logging
logger = logging.getLogger(__name__)

load_dotenv()

class Utils:
    @staticmethod
    def get_random_string(length: int) -> str:
        """Generate a random alphanumeric string of the specified length."""
        random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=length))
        logger.debug("Generated random string: %s", random_str)
        return random_str


class AWSClient:
    def __init__(self):
        """Initialize the AWS S3 client with credentials from environment variables."""
        self.aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
        self.aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        self.bucket_name = os.getenv('AWS_BUCKET_NAME')
        self.region_name = os.getenv('AWS_REGION', 'us-east-1')  # Default region if not specified

        if not all([self.aws_access_key_id, self.aws_secret_access_key, self.bucket_name]):
            logger.error("AWS credentials or bucket name not set in environment variables.")
            raise ValueError("AWS credentials or bucket name not set in environment variables.")

        self.s3 = boto3.client(
            's3',
            region_name=self.region_name,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key
        )
        logger.info("Initialized AWS S3 client")

    def upload_file_to_s3(self, file, user_id: str) -> str:
        """
        Upload a file to S3 under a user-specific directory.
        """
        file_extension = file.filename.split('.')[-1]
        unique_filename = f"{user_id}/{uuid.uuid4()}.{file_extension}"
        try:
            logger.info("Uploading file to S3: %s", unique_filename)
            self.s3.upload_fileobj(
                file.file,
                self.bucket_name,
                unique_filename,
                ExtraArgs={'ACL': 'private'}
            )
            file_url = f"s3://{self.bucket_name}/{unique_filename}"
            logger.info("File uploaded to S3 at: %s", file_url)
            return file_url
        except NoCredentialsError:
            logger.error("AWS credentials not available.")
            raise
        except ClientError as e:
            logger.error("Failed to upload file to S3: %s", e)
            raise

    def save_text_to_s3(self, text: str, user_id: str) -> str:
        """
        Save a text string as a .txt file in S3 under a user-specific directory.
        """
        unique_filename = f"{user_id}/{uuid.uuid4()}.txt"
        try:
            logger.info("Saving text to S3: %s", unique_filename)
            self.s3.put_object(
                Bucket=self.bucket_name,
                Key=unique_filename,
                Body=text.encode('utf-8'),
                ACL='private'
            )
            file_url = f"s3://{self.bucket_name}/{unique_filename}"
            logger.info("Text saved to S3 at: %s", file_url)
            return file_url
        except NoCredentialsError:
            logger.error("AWS credentials not available.")
            raise
        except ClientError as e:
            logger.error("Failed to save text to S3: %s", e)
            raise


class TavusClient:
    def __init__(self):
        """Initialize the Tavus API client with credentials from environment variables."""
        self.api_key = os.getenv('TAVUS_API_KEY')
        self.replica_id = os.getenv('REPLICA_ID')
        self.persona_id = os.getenv('PERSONA_ID')
        self.base_url = "https://tavusapi.com/v2"

        if not all([self.api_key, self.replica_id, self.persona_id]):
            logger.error("Tavus API credentials not set in environment variables.")
            raise ValueError("Tavus API credentials not set in environment variables.")

        self.headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        logger.info("Initialized Tavus API client")

    def create_conversation(self, context: str, callback_url: str = None, conversation_name: str = "User Conversation") -> str:
        """
        Create a conversation with Tavus AI.
        """
        url = f"{self.base_url}/conversations"
        payload = {
            "replica_id": self.replica_id,
            "persona_id": self.persona_id,
            "conversation_name": conversation_name,
            "conversational_context": context,
            "properties": {
                "enable_recording": False,
                "language": "english",
            }
        }

        if callback_url:
            payload["callback_url"] = callback_url

        try:
            logger.info("Creating conversation with Tavus AI")
            response = requests.post(url, json=payload, headers=self.headers)
            response.raise_for_status()  # Raise an exception for HTTP errors
            data = response.json()
            conversation_url = data.get("conversation_url")
            logger.info("Conversation created: %s", conversation_url)
            return conversation_url
        except requests.exceptions.HTTPError as http_err:
            logger.error("HTTP error occurred while creating conversation: %s", http_err)
            logger.error("Response: %s", response.text)
            raise
        except Exception as err:
            logger.error("An error occurred while creating conversation: %s", err)
            raise

    def get_replica(self, replica_id: str = None, verbose: bool = False) -> dict:
        """
        Retrieve information about a specific replica.
        """
        replica_id = replica_id or self.replica_id
        url = f"{self.base_url}/replicas/{replica_id}"
        params = {"verbose": str(verbose).lower()}  # 'true' or 'false'

        try:
            logger.info("Fetching replica information for: %s", replica_id)
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            logger.debug("Replica data: %s", data)
            return data
        except requests.exceptions.HTTPError as http_err:
            logger.error("HTTP error occurred while fetching replica: %s", http_err)
            logger.error("Response: %s", response.text)
            raise
        except Exception as err:
            logger.error("An error occurred while fetching replica: %s", err)
            raise


class SupabaseClient:
    def __init__(self):
        """Initialize the Supabase client with credentials from environment variables."""
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_KEY')

        if not all([self.supabase_url, self.supabase_key]):
            logger.error("Supabase credentials not set in environment variables.")
            raise ValueError("Supabase credentials not set in environment variables.")

        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        logger.info("Initialized Supabase client")

    def create_upload_record(self, user_id: str, file_url: str, description: str = None) -> dict:
        """
        Create a record for an uploaded file or text.
        """
        try:
            data = {
                "user_id": user_id,
                "file_url": file_url,
                "description": description
            }
            logger.info("Inserting upload record into Supabase: %s", data)
            response = self.supabase.table("uploads").insert(data).execute()
            logger.debug("Supabase response: %s", response)
            if response.status_code == 201:
                logger.info("Upload record created successfully")
                return response.data
            else:
                logger.error("Failed to create upload record: %s", response.error)
                raise Exception(response.error)
        except Exception as e:
            logger.error("An error occurred while creating upload record: %s", e)
            raise

    def create_conversation_record(self, user_id: str, conversation_url: str, context: str) -> dict:
        """
        Create a record for a conversation.
        """
        try:
            data = {
                "user_id": user_id,
                "conversation_url": conversation_url,
                "context": context
            }
            logger.info("Inserting conversation record into Supabase: %s", data)
            response = self.supabase.table("conversations").insert(data).execute()
            logger.debug("Supabase response: %s", response)
            if response.status_code == 201:
                logger.info("Conversation record created successfully")
                return response.data
            else:
                logger.error("Failed to create conversation record: %s", response.error)
                raise Exception(response.error)
        except Exception as e:
            logger.error("An error occurred while creating conversation record: %s", e)
            raise

    def get_user_uploads(self, user_id: str) -> list:
        """
        Retrieve all uploads for a specific user.
        """
        try:
            logger.info("Retrieving uploads for user: %s", user_id)
            response = self.supabase.table("uploads").select("*").eq("user_id", user_id).execute()
            logger.debug("Supabase response: %s", response)
            if response.status_code == 200:
                logger.info("Uploads retrieved successfully")
                return response.data
            else:
                logger.error("Failed to retrieve uploads: %s", response.error)
                raise Exception(response.error)
        except Exception as e:
            logger.error("An error occurred while retrieving uploads: %s", e)
            raise

    def get_user_conversations(self, user_id: str) -> list:
        """
        Retrieve all conversations for a specific user.
        """
        try:
            logger.info("Retrieving conversations for user: %s", user_id)
            response = self.supabase.table("conversations").select("*").eq("user_id", user_id).execute()
            logger.debug("Supabase response: %s", response)
            if response.status_code == 200:
                logger.info("Conversations retrieved successfully")
                return response.data
            else:
                logger.error("Failed to retrieve conversations: %s", response.error)
                raise Exception(response.error)
        except Exception as e:
            logger.error("An error occurred while retrieving conversations: %s", e)
            raise
