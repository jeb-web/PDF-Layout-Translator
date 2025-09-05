#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Extracteur de texte pour traduction
Génère un fichier XLIFF à partir du DOM de la page.

Auteur: L'OréalGPT
Version: 2.0.0
"""
import logging
from typing import List
from xml.etree.ElementTree import Element, SubElement, ElementTree, tostring
from xml.dom import minidom
from .data_model import PageObject

class TextExtractor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def create_xliff(self, pages: List[PageObject], source_lang: str, target_lang: str) -> str:
        """Crée une chaîne de caractères au format XLIFF 1.2."""
        self.logger.info(f"Création du fichier XLIFF de '{source_lang}' vers '{target_lang}'")

        xliff = Element('xliff', attrib={'version': '1.2'})
        file_elem = SubElement(xliff, 'file', attrib={
            'source-language': source_lang,
            'target-language': target_lang,
            'datatype': 'plaintext',
            'original': 'pdf-document'
        })
        body = SubElement(file_elem, 'body')

        for page in pages:
            for block in page.text_blocks:
                for span in block.spans:
                    if span.text.strip():
                        trans_unit = SubElement(body, 'trans-unit', attrib={'id': span.id})
                        source = SubElement(trans_unit, 'source')
                        source.text = span.text
                        target = SubElement(trans_unit, 'target')
        
        # Pretty print
        xml_str = tostring(xliff, 'utf-8')
        parsed_str = minidom.parseString(xml_str)
        return parsed_str.toprettyxml(indent="  ", encoding="utf-8").decode('utf-8')```

#### **4. Fichier Modifié : `src/core/translation_parser.py`**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Parseur de traductions
Parse le fichier XLIFF retourné par l'utilisateur.

Auteur: L'OréalGPT
Version: 2.0.0
"""
import logging
from typing import Dict
from xml.etree import ElementTree

class TranslationParser:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def parse_xliff(self, xliff_content: str) -> Dict[str, str]:
        """Parse le contenu XLIFF et retourne un dictionnaire de traductions."""
        self.logger.info("Parsing du fichier XLIFF traduit.")
        translations = {}
        try:
            root = ElementTree.fromstring(xliff_content)
            ns = {'': 'urn:oasis:names:tc:xliff:document:1.2'} # Namespace for XLIFF 1.2

            for trans_unit in root.findall('.//trans-unit', ns):
                unit_id = trans_unit.get('id')
                target = trans_unit.find('target', ns)
                if unit_id and target is not None and target.text:
                    translations[unit_id] = target.text
        except ElementTree.ParseError as e:
            self.logger.error(f"Erreur de parsing XLIFF: {e}")
            raise ValueError("Le contenu fourni n'est pas un XML XLIFF valide.")
        
        self.logger.info(f"{len(translations)} traductions parsées avec succès.")
        return translations
