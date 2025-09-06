#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Extracteur de texte pour traduction
Génère un fichier XLIFF à partir du DOM de la page.
"""
import logging
from typing import List
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
from core.data_model import PageObject

class TextExtractor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def create_xliff(self, pages: List[PageObject], source_lang: str, target_lang: str) -> str:
        self.logger.info(f"Création du fichier XLIFF de '{source_lang}' vers '{target_lang}' (Jalon 2 - Mode Paragraphe)")
        xliff = Element('xliff', attrib={'version': '1.2', 'xmlns': 'urn:oasis:names:tc:xliff:document:1.2'})
        file_elem = SubElement(xliff, 'file', attrib={'source-language': source_lang, 'target-language': target_lang, 'datatype': 'plaintext', 'original': 'pdf-document'})
        body = SubElement(file_elem, 'body')
        
        # [JALON 2] Itération sur la nouvelle structure de paragraphes
        for page in pages:
            for block in page.text_blocks:
                for paragraph in block.paragraphs:
                    # Concaténer le texte de tous les spans du paragraphe pour former une seule phrase
                    paragraph_text = "".join([span.text for span in paragraph.spans])
                    
                    if paragraph_text and paragraph_text.strip():
                        # Utiliser l'ID du paragraphe pour l'unité de traduction
                        trans_unit = SubElement(body, 'trans-unit', attrib={'id': paragraph.id})
                        source = SubElement(trans_unit, 'source')
                        source.text = paragraph_text
                        SubElement(trans_unit, 'target')
        
        xml_str = tostring(xliff, 'utf-8')
        parsed_str = minidom.parseString(xml_str)
        return parsed_str.toprettyxml(indent="  ", encoding="utf-8").decode('utf-8')
