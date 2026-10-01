from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class TraceRequest(BaseModel):
    code: str
    language: str = "python"
    input_data: Optional[str] = None
    generate_flowchart: bool = False

class TraceStep(BaseModel):
    line_number: int
    executed_code: str
    variables: Dict[str, str] = Field(default_factory=dict)
    output: Optional[str] = None

class TraceResponse(BaseModel):
    success: bool
    language: str
    steps: List[TraceStep] = Field(default_factory=list)
    flowchart: Optional[str] = None
    error: Optional[str] = None
