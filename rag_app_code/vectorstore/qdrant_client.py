import json
import os
from pathlib import Path
import torch
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from transformers import AutoTokenizer, AutoModel

load_dotenv()

# Load local embedding model
MODEL_NAME = "BAAI/bge-small-en-v1.5"
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
embed_model = AutoModel.from_pretrained(MODEL_NAME)

def generate_local_embedding(text: str) -> list:
    """Generates a 384-dimensional vector locally."""
    inputs = tokenizer(text, padding=True, truncation=True, return_tensors="pt", max_length=512)
    with torch.no_grad():
        outputs = embed_model(**inputs)
        embeddings = outputs.last_hidden_state.mean(dim=1)
        embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
    return embeddings[0].tolist()

def seed_vectorstore_from_rag_data():
    """Reads job descriptions from rag_data/ and embeds them into Qdrant."""
    qdrant = QdrantClient(path="./vectorstore/qdrant_db")
    collection_name = "company_job_descriptions"

    # Recreate collection to enforce 384 dimensions
    if qdrant.collection_exists(collection_name):
        qdrant.delete_collection(collection_name)

    qdrant.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE)
    )

    rag_data_dir = Path("rag_data")
    points = []

    for idx, file_path in enumerate(rag_data_dir.glob("*.json"), start=1):
        with open(file_path, "r", encoding="utf-8") as f:
            jd_payload = json.load(f)

        text_to_embed = jd_payload.get("summary_text", jd_payload.get("description", ""))
        embedding = generate_local_embedding(text_to_embed)

        points.append(
            PointStruct(id=idx, vector=embedding, payload=jd_payload)
        )

    if points:
        qdrant.upsert(collection_name=collection_name, points=points)
        print(f"Successfully seeded {len(points)} job description(s) into Qdrant.")

    qdrant.close()

if __name__ == "__main__":
    seed_vectorstore_from_rag_data()