import torch
from qdrant_client import QdrantClient
from transformers import AutoTokenizer, AutoModel

MODEL_NAME = "BAAI/bge-small-en-v1.5"
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
embed_model = AutoModel.from_pretrained(MODEL_NAME)

def generate_local_embedding(text: str) -> list:
    inputs = tokenizer(text, padding=True, truncation=True, return_tensors="pt", max_length=512)
    with torch.no_grad():
        outputs = embed_model(**inputs)
        embeddings = outputs.last_hidden_state.mean(dim=1)
        embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
    return embeddings[0].tolist()

def retrieve_matching_jds(cv_text: str, top_k: int = 3):
    """Searches Qdrant for top matching job descriptions for the CV."""
    qdrant = QdrantClient(path="./vectorstore/qdrant_db")

    cv_embedding = generate_local_embedding(cv_text)

    search_result = qdrant.query_points(
        collection_name="company_job_descriptions",
        query=cv_embedding,
        limit=top_k
    )

    matched_jds = [hit.payload for hit in search_result.points]
    qdrant.close()
    return matched_jds