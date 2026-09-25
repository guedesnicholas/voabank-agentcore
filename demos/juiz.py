import os
import requests
import json
import asyncio
from deepeval.models import DeepEvalBaseLLM 



API_JUIZ_URL = "xxxxxxxxxxxxxxxxxxxxxxxx"



   
class JuizAPI(DeepEvalBaseLLM):
    """
    Juiz customizado que chama o Bedrock (Qwen) via API Gateway.
    """

    def __init__(self):
        pass

    def get_model_name(self) -> str:
        return "qwen-via-api-gateway"

    def load_model(self):
        return self

    def generate(self, prompt: str, schema: type = None) -> str:
      
        schema_str = None
        if schema is not None:
            schema_str = json.dumps(schema.model_json_schema())

        resp = requests.post(
            API_JUIZ_URL,
            json={"prompt": prompt, "schema": schema_str},
            timeout=120
        )
        resp.raise_for_status()
        return resp.json().get("resposta", "")

    async def a_generate(self, prompt: str, schema: type = None) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self.generate(prompt, schema))


def obter_juiz():
    """Função que o resto do projeto chama para obter o juiz."""
    provider = os.getenv("JUIZ_PROVIDER", "api").lower()

    if provider == "api":
        return JuizAPI()

    # Fallback opcional para Ollama
    if provider == "ollama":
        from deepeval.models import OllamaModel
        return OllamaModel(
            model=os.getenv("JUIZ_MODEL", "llama3.1:latest"),
            base_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
            temperature=0
        )

    raise ValueError(f"JUIZ_PROVIDER desconhecido: {provider}")