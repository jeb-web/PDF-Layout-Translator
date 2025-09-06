#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Extracteur de texte pour traduction
Génère un fichier XLIFF à partir du DOM de la page, en préservant les styles via HTML.
"""
import logging
from typing import List, Dict, Any
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
from core.data_model import PageObject, FontInfo

class TextExtractor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.styles: Dict[str, FontInfo] = {}
        self.style_counter = 1

    def _get_style_class(self, font_info: FontInfo) -> str:
        """Crée ou récupère un nom de classe pour un style de police donné."""
        # Créer une clé unique pour le style
        style_key = (font_info.name, font_info.size, font_info.color, font_info.is_bold, font_info.is_italic)
        
        # Inverser le dictionnaire pour chercher par valeur
        for class_name, style in self.styles.items():
            if style == style_key:
                return class_name
        
        # Si le style n'existe pas, le créer
        class_name = f"c{self.style_counter}"
        self.styles[class_name] = style_key
        self.style_counter += 1
        return class_name

    def create_xliff(self, pages: List[PageObject], source_lang: str, target_lang: str) -> str:
        self.logger.info("Création du fichier XLIFF (Jalon 2 - Mode HTML Sémantique)")
        self.styles.clear()
        self.style_counter = 1

        xliff = Element('xliff', attrib={'version': '1.2', 'xmlns': 'urn:oasis:names:tc:xliff:document:1.2'})
        file_elem = SubElement(xliff, 'file', attrib={'source-language': source_lang, 'target-language': target_lang, 'datatype': 'plaintext', 'original': 'pdf-document'})
        
        # Stocker la feuille de style dans les métadonnées du fichier (facultatif mais propre)
        # Pour la simplicité, nous la stockons en mémoire pour l'instant.

        body = SubElement(file_elem, 'body')
        
        for page in pages:
            for block in page.text_blocks:
                for paragraph in block.paragraphs:
                    content_parts = []
                    
                    spans_on_line = []
                    for span in paragraph.spans:
                        spans_on_line.append(span)

                        # Détecter les sauts de ligne forcés (basé sur la géométrie)
                        is_last_span = (span == paragraph.spans[-1])
                        if not is_last_span:
                            next_span = paragraph.spans[paragraph.spans.index(span) + 1]
                            if abs(span.bbox[1] - next_span.bbox[1]) > 1: # Si le span suivant est sur une autre ligne
                                # C'est un saut de ligne forcé
                                text = "".join(s.text for s in spans_on_line)
                                class_name = self._get_style_class(spans_on_line[0].font) # Simplification: style du 1er span
                                content_parts.append(f'<span class="{class_name}">{text}</span><br/>')
                                spans_on_line = []

                    # Gérer la dernière ligne du paragraphe
                    if spans_on_line:
                        text = "".join(s.text for s in spans_on_line)
                        class_name = self._get_style_class(spans_on_line[0].font)
                        content_parts.append(f'<span class="{class_name}">{text}</span>')

                    para_content = "".join(content_parts)
                    
                    if para_content.strip():
                        trans_unit = SubElement(body, 'trans-unit', attrib={'id': paragraph.id})
                        source = SubElement(trans_unit, 'source')
                        # Important: encadrer le contenu dans un CDATA pour éviter les problèmes de parsing XML
                        source.text = f"<![CDATA[<p>{para_content}</p>]]>"
                        SubElement(trans_unit, 'target')

        xml_str = tostring(xliff, 'utf-8')
        parsed_str = minidom.parseString(xml_str)
        return parsed_str.toprettyxml(indent="  ", encoding="utf-8").decode('utf-8')
