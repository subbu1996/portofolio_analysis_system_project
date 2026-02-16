import logging
from langchain_community.utilities.twilio import TwilioAPIWrapper
from langchain_google_community import GmailToolkit
from langchain_google_community.gmail.utils import (
    build_resource_service,
    get_gmail_credentials,
)
from langchain_core.tools import tool

logger = logging.getLogger(__name__)



# --- Gmail Tools ---
def get_gmail_tools():
    """
    Initializes and returns the Gmail toolkit tools.
    Expects credentials.json to be present or authentication to be configured.
    """
    try:
        credentials = get_gmail_credentials(
            token_file="token.json",
            scopes=["https://mail.google.com/"],
            client_sercret_file="credentials.json",
        )
        api_resource = build_resource_service(credentials=credentials)
        toolkit = GmailToolkit(api_resource=api_resource)
        return toolkit.get_tools()
    except Exception as e:
        logger.error(f"Failed to initialize GmailToolkit: {e}")
        # Return empty list to prevent crash if credentials are missing
        return []

gmail_tools = get_gmail_tools()

# --- WhatsApp Tool (via Twilio)---
@tool
def send_whatsapp_message(message: str, to_number: str) -> str:
    """
    Sends a WhatsApp message to a specific user number.
    
    Args:
        message: The content of the message to send.
        to_number: The recipient's phone number (e.g., '+919999999999'). 
                   The tool will automatically add the 'whatsapp:' prefix if missing.
    """
    try:
        # Initialize Twilio Wrapper (looks for env vars: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER)
        twilio = TwilioAPIWrapper()
        
        # Ensure correct formatting for WhatsApp
        if not to_number.startswith("whatsapp:"):
            to_number = f"whatsapp:{to_number}"
            
        # Note: TwilioAPIWrapper.run uses the 'from_number' from env vars. 
        # Ensure TWILIO_FROM_NUMBER in .env is also formatted as 'whatsapp:+1...'
        result = twilio.run(message, to_number)
        return f"WhatsApp message sent successfully: {result}"
    except Exception as e:
        logger.error(f"Failed to send WhatsApp message: {e}")
        return f"Error sending WhatsApp message: {str(e)}"
