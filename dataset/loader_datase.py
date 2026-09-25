import os
import json
from deepeval.dataset import EvaluationDataset
from deepeval.dataset import Golden


def carregar_dataset():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(BASE_DIR, "goldendataset_voabank.json")

    with open(json_path, "r", encoding="utf-8") as f:
        dados = json.load(f)

    if isinstance(dados, dict):
        dados = [dados]

    dataset = EvaluationDataset()

    for item in dados:
        entrada = item["input"]

  
        if isinstance(entrada, list):
            linhas = []
            for t in entrada:
                if isinstance(t, dict):
                    texto = t.get("usuario") or t.get("bot") or ""
                    if texto:
                        linhas.append(texto)
            input_str = "\n".join(linhas)
        else:
            input_str = entrada

        dataset.add_golden(Golden(
            input=input_str,
            expected_output=item["expected_output"],
            retrieval_context=item.get("retrieval_context", []),
        ))

    return dataset