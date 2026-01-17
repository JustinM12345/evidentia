import openrouter
import os
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Get OpenRouter API key from environment variables
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Check if the API key is loaded correctly
if OPENROUTER_API_KEY is None:
    raise ValueError("OpenRouter API key is not set in the .env file")

def call_llm_extract(text: str) -> dict:
    # Call the LLM to analyze the policy text
    try:
        result = openrouter.call(
            model="openai/gpt-4o-mini",  # You can change this model if needed
            prompt=text,
            api_key=OPENROUTER_API_KEY
        )
        return result
    except Exception as e:
        return {"error": str(e)}  # Return error message if the LLM call fails
