from src.llm_client import LLMClient
from src.config import get_settings

settings = get_settings()
print(f"Provider: {settings.llm_provider}")
print(f"Model: {settings.ollama_model}")

client = LLMClient(settings)
print("Sending test prompt to Ollama...")
response = client.generate("Hello, are you ready to trade?")
if response:
    print(f"Response received: {response.text}")
else:
    print("No response received.")
