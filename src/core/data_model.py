from dataclasses import dataclass, field
from typing import List, Tuple

@dataclass
class FontInfo:
    name: str; size: float; color: str; is_bold: bool; is_italic: bool

@dataclass
class TextSpan:
    id: str; text: str; font: FontInfo; bbox: Tuple[float, float, float, float]; translated_text: str = ""

@dataclass
class TextBlock:
    id: str; bbox: Tuple[float, float, float, float]; final_bbox: Tuple[float, float, float, float] = None; spans: List[TextSpan] = field(default_factory=list)

@dataclass
class PageObject:
    page_number: int; dimensions: Tuple[float, float]; text_blocks: List[TextBlock] = field(default_factory=list)
