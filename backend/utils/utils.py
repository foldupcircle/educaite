# utils/utils.py

import os
import uuid
import random
import string
import boto3
import requests
from botocore.exceptions import NoCredentialsError, ClientError
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

class Utils:
    @staticmethod
    def get_random_string(length: int) -> str:
        """Generate a random alphanumeric string of the specified length."""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


class AWSClient:
    def __init__(self):
        """Initialize the AWS S3 client with credentials from environment variables."""
        self.aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
        self.aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        self.bucket_name = os.getenv('AWS_BUCKET_NAME')
        self.region_name = os.getenv('AWS_REGION', 'us-east-1')  # Default region if not specified

        if not all([self.aws_access_key_id, self.aws_secret_access_key, self.bucket_name]):
            raise ValueError("AWS credentials or bucket name not set in environment variables.")

        self.s3 = boto3.client(
            's3',
            region_name=self.region_name,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key
        )

    def upload_file_to_s3(self, file, user_id: str) -> str:
        """
        Upload a file to S3 under a user-specific directory.

        :param file: UploadFile object from FastAPI
        :param user_id: ID of the authenticated user
        :return: S3 file URL
        """
        file_extension = file.filename.split('.')[-1]
        unique_filename = f"{user_id}/{uuid.uuid4()}.{file_extension}"
        try:
            self.s3.upload_fileobj(
                file.file,
                self.bucket_name,
                unique_filename,
                ExtraArgs={'ACL': 'private'}
            )
            file_url = f"s3://{self.bucket_name}/educaite/{unique_filename}"
            return file_url
        except NoCredentialsError:
            print("AWS credentials not available.")
            raise
        except ClientError as e:
            print(f"Failed to upload file to S3: {e}")
            raise

    def save_text_to_s3(self, text: str, user_id: str) -> str:
        """
        Save a text string as a .txt file in S3 under a user-specific directory.

        :param text: Text content to save
        :param user_id: ID of the authenticated user
        :return: S3 file URL
        """
        unique_filename = f"{user_id}/{uuid.uuid4()}.txt"
        try:
            self.s3.put_object(
                Bucket=self.bucket_name,
                Key=unique_filename,
                Body=text.encode('utf-8'),
                ACL='private'
            )
            file_url = f"s3://{self.bucket_name}/educaite/{unique_filename}"
            return file_url
        except NoCredentialsError:
            print("AWS credentials not available.")
            raise
        except ClientError as e:
            print(f"Failed to save text to S3: {e}")
            raise


class TavusClient:
    def __init__(self):
        """Initialize the Tavus API client with credentials from environment variables."""
        self.api_key = os.getenv('TAVUS_API_KEY')
        self.replica_id = os.getenv('REPLICA_ID')
        self.persona_id = os.getenv('PERSONA_ID')
        self.base_url = "https://tavusapi.com/v2"

        if not all([self.api_key, self.replica_id, self.persona_id]):
            raise ValueError("Tavus API credentials not set in environment variables.")

        self.headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

    def create_conversation(self, context: str, callback_url: str = None, conversation_name: str = "User Conversation") -> str:
        """
        Create a conversation with Tavus AI.

        :param context: Conversational context derived from user input
        :param callback_url: Optional callback URL for webhooks
        :param conversation_name: Name of the conversation
        :return: URL to join the conversation
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
                # Add other properties as needed
            }
        }

        if callback_url:
            payload["callback_url"] = callback_url

        try:
            response = requests.post(url, json=payload, headers=self.headers)
            response.raise_for_status()  # Raise an exception for HTTP errors
            data = response.json()
            return data.get("conversation_url")
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred while creating conversation: {http_err}")
            print(f"Response: {response.text}")
            raise
        except Exception as err:
            print(f"An error occurred while creating conversation: {err}")
            raise

    def get_replica(self, replica_id: str = None, verbose: bool = False) -> dict:
        """
        Retrieve information about a specific replica.

        :param replica_id: ID of the replica (if None, use self.replica_id)
        :param verbose: If True, include additional replica data
        :return: Replica information as a dictionary
        """
        replica_id = replica_id or self.replica_id
        url = f"{self.base_url}/replicas/{replica_id}"
        params = {"verbose": str(verbose).lower()}  # 'true' or 'false'

        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred while fetching replica: {http_err}")
            print(f"Response: {response.text}")
            raise
        except Exception as err:
            print(f"An error occurred while fetching replica: {err}")
            raise


class SupabaseClient:
    def __init__(self):
        """Initialize the Supabase client with credentials from environment variables."""
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_KEY')

        if not all([self.supabase_url, self.supabase_key]):
            raise ValueError("Supabase credentials not set in environment variables.")

        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)

    def create_upload_record(self, user_id: str, file_url: str, description: str = None) -> dict:
        """
        Create a record for an uploaded file or text.

        :param user_id: ID of the authenticated user
        :param file_url: URL of the uploaded file in S3
        :param description: Optional text description
        :return: Inserted record
        """
        try:
            data = {
                "user_id": user_id,
                "file_url": file_url,
                "description": description
            }
            response = self.supabase.table("uploads").insert(data).execute()
            if response.status_code == 201:
                return response.data
            else:
                print(f"Failed to create upload record: {response.error}")
                raise Exception(response.error)
        except Exception as e:
            print(f"An error occurred while creating upload record: {e}")
            raise

    def create_conversation_record(self, user_id: str, conversation_url: str, context: str) -> dict:
        """
        Create a record for a conversation.

        :param user_id: ID of the authenticated user
        :param conversation_url: URL to join the conversation
        :param context: Context provided to the Tavus AI agent
        :return: Inserted record
        """
        try:
            data = {
                "user_id": user_id,
                "conversation_url": conversation_url,
                "context": context
            }
            response = self.supabase.table("conversations").insert(data).execute()
            if response.status_code == 201:
                return response.data
            else:
                print(f"Failed to create conversation record: {response.error}")
                raise Exception(response.error)
        except Exception as e:
            print(f"An error occurred while creating conversation record: {e}")
            raise

    def get_user_uploads(self, user_id: str) -> list:
        """
        Retrieve all uploads for a specific user.

        :param user_id: ID of the authenticated user
        :return: List of upload records
        """
        try:
            response = self.supabase.table("uploads").select("*").eq("user_id", user_id).execute()
            if response.status_code == 200:
                return response.data
            else:
                print(f"Failed to retrieve uploads: {response.error}")
                raise Exception(response.error)
        except Exception as e:
            print(f"An error occurred while retrieving uploads: {e}")
            raise

    def get_user_conversations(self, user_id: str) -> list:
        """
        Retrieve all conversations for a specific user.

        :param user_id: ID of the authenticated user
        :return: List of conversation records
        """
        try:
            response = self.supabase.table("conversations").select("*").eq("user_id", user_id).execute()
            if response.status_code == 200:
                return response.data
            else:
                print(f"Failed to retrieve conversations: {response.error}")
                raise Exception(response.error)
        except Exception as e:
            print(f"An error occurred while retrieving conversations: {e}")
            raise
