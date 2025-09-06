#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Extracteur de texte pour traduction
Génère un fichier XLIFF à partir du DOM de la page, en préservant les styles via HTML.
"""
import logging
from typing import List, Dict, Any
from lxml import etree
from dataclasses import asdict
from core.data_model import PageObject, FontInfo

class CDATA(etree.CDATA):
    pass

class TextExtractor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.styles: Dict[str, FontInfo] = {}
        self.style_map: Dict[tuple, str] = {}
        self.style_counter = 1

    def _get_style_class(self, font_info: FontInfo) -> str:
        """Crée ou récupère un nom de classe pour un style de police donné."""
        style_key = (font_info.name, round(font_info.size, 2), font_info.color, font_info.is_bold, font_info.is_italic)
        if style_key in self.style_map:
            return self.style_map[style_key]
        
        class_name = f"c{self.style_counter}"
        self.styles[class_name] = font_info
        self.style_map[style_key] = class_name
        self.style_counter += 1
        return class_name

    def create_xliff(self, pages: List[PageObject], source_lang: str, target_lang: str) -> Dict[str, Any]:
        self.styles.clear(); self.style_map.clear(); self.style_counter = 1

        # Pré-peupler la feuille de style pour garantir la cohérence
        for page in pages:
            for block in page.text_blocks:
                for para in block.paragraphs:
                    for span in para.spans:
                        self._get_style_class(span.font)

        root = etree.Element('xliff', version='1.2', xmlns='urn:oasis:names:tc:xliff:document:1.2')
        file_elem = etree.SubElement(root, 'file', **{'source-language': source_lang, 'target-language': target_lang, 'datatype': 'plaintext', 'original': 'pdf-document'})
        body = etree.SubElement(file_elem, 'body')

        for page in pages:
            for block in page.text_blocks:
                for paragraph in block.paragraphs:
                    p_element = etree.Element('p')
                    for span in paragraph.spans:
                        # [MODIFICATION FINALE] Ajouter l'ID du span comme une ancre dans le HTML
                        # C'est la clé pour la réconciliation après la traduction.
                        span_element = etree.SubElement(p_element, 'span', attrib={
                            'class': self._get_style_class(span.font),
                            'id': span.id
                        })
                        span_element.text = span.text
                    
                    para_html_str = etree.tostring(p_element, encoding='unicode', method='html')
                    if para_html_str.strip():
                        trans_unit = etree.SubElement(body, 'trans-unit', id=paragraph.id)
                        source = etree.SubElement(trans_unit, 'source')
                        source.text = CDATA(para_html_str)
                        etree.SubElement(trans_unit, 'target')
        
        xliff_string = etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='utf-8').decode('utf-8')
        
        # Renvoyer la feuille de style avec le XLIFF est crucial
        return { 
            "xliff": xliff_string, 
            "styles": {name: asdict(font) for name, font in self.styles.items()} 
        }
