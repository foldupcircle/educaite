# utils/utils.py

import os
import uuid
import random
import string
import boto3
import requests
from botocore.exceptions import NoCredentialsError
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Utils:
    @staticmethod
    def get_random_string(length: int) -> str:
        """Generate a random string of given length."""
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
            file_url = f"s3://{self.bucket_name}/{unique_filename}"
            return file_url
        except NoCredentialsError:
            print("AWS credentials not available.")
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
            file_url = f"s3://{self.bucket_name}/{unique_filename}"
            return file_url
        except NoCredentialsError:
            print("AWS credentials not available.")
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
