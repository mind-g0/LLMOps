import os
from pathlib import Path
import torch
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from transformers import AutoTokenizer, AutoModel

load_dotenv()

MODEL_NAME = "BAAI/bge-small-en-v1.5"
_tokenizer = None
_embed_model = None

def get_embedding_model():
    """Caches and returns the model and tokenizer to prevent duplicate weight loading."""
    global _tokenizer, _embed_model
    if _tokenizer is None or _embed_model is None:
        _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        _embed_model = AutoModel.from_pretrained(MODEL_NAME)
        _embed_model.eval()
    return _tokenizer, _embed_model

def generate_local_embedding(text: str) -> list:
    """Generates a 384-dimensional vector locally."""
    tokenizer, embed_model = get_embedding_model()
    inputs = tokenizer(text, padding=True, truncation=True, return_tensors="pt", max_length=512)
    with torch.no_grad():
        outputs = embed_model(**inputs)
        embeddings = outputs.last_hidden_state.mean(dim=1)
        embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
    return embeddings[0].tolist()

def seed_vectorstore_from_rag_data():
    """Reads Markdown job descriptions in rag_data/ and embeds them into Qdrant."""
    qdrant = QdrantClient(path="./vectorstore/qdrant_db")
    collection_name = "company_job_descriptions"

    if qdrant.collection_exists(collection_name):
        qdrant.delete_collection(collection_name)

    qdrant.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE)
    )

    rag_data_dir = Path("rag_data")
    points = []

    for idx, file_path in enumerate(rag_data_dir.glob("*.md"), start=1):
        with open(file_path, "r", encoding="utf-8") as f:
            md_content = f.read()

        embedding = generate_local_embedding(md_content)

        jd_payload = {
            "title": file_path.stem.replace("_", " ").title(),
            "description": md_content
        }

        points.append(
            PointStruct(id=idx, vector=embedding, payload=jd_payload)
        )

    if points:
        qdrant.upsert(collection_name=collection_name, points=points)
        print(f"Successfully seeded {len(points)} Markdown job description(s) into Qdrant.")

    qdrant.close()