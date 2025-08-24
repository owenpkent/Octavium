from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class KeyDef(BaseModel):
    label: str
    note: int
    width: float = 1.0
    height: float = 1.0
    velocity: int = 100
    channel: int = 0
    color: Optional[str] = None

class RowDef(BaseModel):
    keys: List[KeyDef]

class Layout(BaseModel):
    name: str
    rows: List[RowDef]
    columns: int = Field(ge=1, default=12)
    gap: int = 4
    base_octave: int = 4
    allow_poly: bool = True
    quantize_scale: Optional[Literal["chromatic","major","minor","pentatonic","custom"]] = "chromatic"
    custom_scale: Optional[List[int]] = None
