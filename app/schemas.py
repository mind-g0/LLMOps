from typing import Dict, Any
from pydantic import BaseModel

class SingleRouteRequest(BaseModel):
    task_type: str  # Must be "llm" or "ocr"
    payload: Dict[str, Any]