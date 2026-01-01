import logging
from dotenv import load_dotenv
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)
load_dotenv()


def create_ollama_llm(model_name: str = "phi4-mini:3.8b", temperature: float = 0.7):
    try:
        llm = ChatOllama(
            model=model_name,
            temperature=temperature
        )
        # logger.info(f"Successfully initialized {model_name}")
        return llm
    except Exception as e:
        logger.error(f"Error initializing Ollama LLM INnstance: {e}")
        raise

def create_openrouter_llm(model_name: str = "openai/gpt-oss-120b:free", temperature: float = 0.7):
    try:
        os.environ["OPENAI_API_KEY"] = os.getenv("OPENROUTER_API_KEY")
        os.environ["OPENAI_BASE_URL"] = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

        llm = ChatOpenAI(
            model=model_name,
            temperature=temperature
        )
        # logger.info(f"Successfully initialized {model_name}")
        return llm
    except Exception as e:
        logger.error(f"Error initializing Ollama LLM INnstance: {e}")
        raise

def create_gemini_llm(model_name: str = "gemini-2.5-flash", temperature: float = 0.7) -> ChatGoogleGenerativeAI:
    try:
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=temperature,
            convert_system_message_to_human=True
        )
        # logger.info(f"Successfully initialized {model_name}")
        return llm
    except Exception as e:
        logger.error(f"Error initializing Gemini: {e}")
        raise

