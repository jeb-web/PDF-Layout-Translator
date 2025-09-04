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
    """Extrait et formate le texte pour la traduction."""

    def __init__(self):
        """Initialise l'extracteur de texte."""
        self.logger = logging.getLogger(__name__)
        self.logger.info("TextExtractor initialisé")

    def extract_for_translation(self, analysis_data: Dict[str, Any], 
                                source_lang: str = "auto", target_lang: str = "en") -> Dict[str, Any]:
        """
        Extrait les éléments textuels pertinents pour la traduction.

        Args:
            analysis_data: Données complètes de l'analyseur PDF.
            source_lang: Langue source.
            target_lang: Langue cible.

        Returns:
            Dictionnaire structuré contenant les éléments à traduire.
        """
        self.logger.info("Début de l'extraction pour traduction")
        
        translation_elements = []
        translatable_count = 0

        for element in analysis_data.get('text_elements', []):
            original_text = element.get('content', '').strip()
            
            # Déterminer si l'élément est traduisible
            is_translatable = self._is_translatable(original_text)
            
            if is_translatable:
                translatable_count += 1

            translation_elements.append({
                'id': element['id'],
                'original_text': original_text,
                'page_number': element['page_number'],
                'content_type': element['content_type'],
                'is_translatable': is_translatable,
                'context': f"Élément de type '{element['content_type']}' sur la page {element['page_number']}",
                'notes': "" # Pour des notes futures
            })

        self.logger.info(f"{len(translation_elements)} éléments extraits, dont {translatable_count} traduisibles.")

        return {
            "session_info": {
                "source_language": source_lang,
                "target_language": target_lang,
                "total_pages": analysis_data.get('document_info', {}).get('page_count', 0),
                "total_elements": len(translation_elements),
                "translatable_elements": translatable_count,
            },
            "translation_elements": translation_elements
        }

    def _is_translatable(self, text: str) -> bool:
        """
        Détermine si une chaîne de texte est probablement traduisible.
        Ignore les chaînes courtes composées uniquement de chiffres ou de symboles.
        """
        if not text:
            return False
        
        # Si le texte contient au moins une lettre, il est traduisible
        if re.search(r'\w', text):
            return True
            
        # S'il ne contient que des chiffres, des espaces et de la ponctuation simple
        if re.fullmatch(r'[\d\s.,!?;:%$€£"\'()\[\]{}]+', text):
            return False

        # Par défaut, considérer comme traduisible
        return True

    def create_export_package(self, extraction_data: Dict[str, Any], export_dir: Path) -> Dict[str, Path]:
        """
        Crée les fichiers d'export pour la traduction (ex: Markdown).

        Args:
            extraction_data: Données extraites prêtes pour la traduction.
            export_dir: Répertoire où sauvegarder les fichiers.

        Returns:
            Dictionnaire des fichiers créés {type: chemin}.
        """
        export_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Création du package d'export dans {export_dir}")

        markdown_content = self._generate_markdown_export(extraction_data)
        
        # Sauvegarder le fichier Markdown
        md_file_path = export_dir / "traduction_ia.md"
        try:
            with open(md_file_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            self.logger.info(f"Fichier Markdown généré: {md_file_path}")
        except IOError as e:
            self.logger.error(f"Erreur lors de l'écriture du fichier Markdown: {e}")
            raise

        return {"markdown": md_file_path}

    def _generate_markdown_export(self, extraction_data: Dict[str, Any]) -> str:
        """
        Génère le contenu du fichier Markdown pour l'IA.

        Args:
            extraction_data: Données extraites.

        Returns:
            Contenu formaté en Markdown.
        """
        info = extraction_data['session_info']
        source_lang = info['source_language']
        target_lang = info['target_language']
        
        # Instructions pour l'IA
        header = f"""---
# PROMPT DE TRADUCTION DE DOCUMENT PDF
# Source Lang: {source_lang}
# Target Lang: {target_lang}
---

**INSTRUCTIONS IMPORTANTES :**

1.  **Traduisez** le texte de `{source_lang}` vers `{target_lang}`.
2.  **NE MODIFIEZ JAMAIS** les identifiants comme `**[ID:T001|Page:1|Type:Title]**`. Conservez-les exactement tels quels.
3.  **CONSERVEZ LA STRUCTURE** : La traduction doit suivre immédiatement son identifiant.
4.  Répondez **UNIQUEMENT** avec la liste des traductions. N'ajoutez aucun commentaire, en-tête ou pied de page.

**Exemple de réponse attendue :**

```markdown
**[ID:T001|Page:1|Type:Title]**
This is the translated title.

**[ID:T002|Page:1|Type:Paragraph]**
This is the first translated paragraph, containing multiple sentences.
```

---
**TEXTE À TRADUIRE CI-DESSOUS :**
---
"""
        
        body_parts = []
        for element in extraction_data['translation_elements']:
            if element['is_translatable']:
                element_md = (
                    f"**[ID:{element['id']}|Page:{element['page_number']}|Type:{element['content_type'].title()}]**\n"
                    f"{element['original_text']}\n"
                )
                body_parts.append(element_md)

        return header + "\n" + "\n".join(body_parts)
