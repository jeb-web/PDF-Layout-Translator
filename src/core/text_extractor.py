#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Extracteur de texte
Extrait et prépare le texte pour la traduction par une IA externe

Auteur: L'OréalGPT
Version: 1.0.0
"""

import logging
from typing import Dict, List, Any
from pathlib import Path
import re

class TextExtractor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.info("TextExtractor initialisé")

    def extract_for_translation(self, analysis_data: Dict[str, Any], 
                                source_lang: str = "auto", target_lang: str = "en") -> Dict[str, Any]:
        self.logger.info("Début de l'extraction pour traduction")
        
        translation_elements = []
        for element in analysis_data.get('text_elements', []):
            is_translatable = self._is_translatable(element.get('content', ''))
            translation_elements.append({
                'id': element['id'],
                'original_text': element['content'],
                'page_number': element['page_number'],
                'content_type': element['content_type'],
                'is_translatable': is_translatable,
            })
        
        return {
            "session_info": { "source_language": source_lang, "target_language": target_lang },
            "translation_elements": translation_elements
        }

    def _is_translatable(self, text: str) -> bool:
        return bool(text and re.search(r'\w', text))

    def create_export_package(self, extraction_data: Dict[str, Any], export_dir: Path) -> Dict[str, Path]:
        export_dir.mkdir(parents=True, exist_ok=True)
        markdown_content = self._generate_markdown_export(extraction_data)
        md_file_path = export_dir / "traduction_ia.md"
        with open(md_file_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        return {"markdown": md_file_path}

    def _generate_markdown_export(self, extraction_data: Dict[str, Any]) -> str:
        info = extraction_data['session_info']
        source_lang = info['source_language']
        target_lang = info['target_language']
        
        header = f"""---
# PROMPT DE TRADUCTION DE DOCUMENT PDF
# Source Lang: {source_lang}
# Target Lang: {target_lang}
---

**INSTRUCTIONS TRÈS IMPORTANTES :**

1.  **Traduisez** le texte de `{source_lang}` vers `{target_lang}`.
2.  **NE MODIFIEZ JAMAIS** les identifiants comme `**[ID:T001|...]**`.
3.  **CONSERVEZ LE FORMATAGE MARKDOWN** : Si un texte est en gras (`**gras**`) ou en italique (`*italique*`), appliquez le même style aux mots correspondants dans votre traduction.
4.  Répondez **UNIQUEMENT** avec la liste des traductions. N'ajoutez aucun commentaire.

---
**TEXTE À TRADUIRE CI-DESSOUS :**
---
"""
        
        body_parts = [
            f"**[ID:{elem['id']}|Page:{elem['page_number']}|Type:{elem['content_type'].title()}]**\n{elem['original_text']}\n"
            for elem in extraction_data['translation_elements'] if elem['is_translatable']
        ]

        return header + "\n" + "\n".join(body_parts)
