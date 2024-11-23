from daily import Daily, EventHandler, CallClient

call_client = None

class RoomHandler(EventHandler):
    def __init__(self):
        super().__init__()
    
    def on_app_message(self, message, sender: str) -> None:
        print(f"Incoming app message from {sender}: {message}")

class DailyClient:
    def __init__(self):
        self.call_client = None

    def join_room(self, url):
        try:
            Daily.init()
            output_handler = RoomHandler()
            self.call_client = CallClient(event_handler=output_handler)
            self.call_client.join(url)
        except Exception as e:
            print(f"Error joining room: {e}")
            raise

    def send_message(self, conversation_id, context):
        message = {
            "message_type": "conversation",
            "event_type": "conversation.overwrite_llm_context",
            "conversation_id": conversation_id,
            "properties": {
                "context": context
            }
        }
        self.call_client.send_app_message(message)
