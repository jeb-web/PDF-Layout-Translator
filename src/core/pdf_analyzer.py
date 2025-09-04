#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Analyseur de PDF
Analyse approfondie de la structure et du contenu des documents PDF

Auteur: L'OréalGPT
Version: 1.0.0
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime  # <-- FIX 1: Importation ajoutée
import fitz  # PyMuPDF

class ContentType(Enum):
    """Types de contenu identifiés"""
    TITLE = "title"
    SUBTITLE = "subtitle"
    PARAGRAPH = "paragraph"
    LIST_ITEM = "list_item"
    CAPTION = "caption"
    FOOTER = "footer"
    HEADER = "header"
    TABLE_CELL = "table_cell"
    QUOTE = "quote"
    CODE = "code"
    UNKNOWN = "unknown"

@dataclass
class FontInfo:
    """Informations sur une police"""
    name: str
    size: float
    flags: int
    is_bold: bool
    is_italic: bool
    is_mono: bool
    encoding: str

@dataclass
class TextElement:
    """Élément de texte extrait"""
    id: str
    content: str
    page_number: int
    bbox: Tuple[float, float, float, float]  # x0, y0, x1, y1
    font_info: FontInfo
    content_type: ContentType
    reading_order: int
    line_height: float
    char_spacing: float
    confidence: float

class PDFAnalyzer:
    """Analyseur de documents PDF"""
    
    def __init__(self):
        """Initialise l'analyseur PDF"""
        self.logger = logging.getLogger(__name__)
        self.doc: Optional[fitz.Document] = None
        
        # Seuils pour la classification du contenu
        self.title_size_threshold = 16.0
        self.subtitle_size_threshold = 14.0
        self.paragraph_min_words = 3
        
        # Patterns pour la détection de listes
        self.list_patterns = [
            r'^[\s]*[•·‣⁃]\s+',  # Puces
            r'^[\s]*[\d]+[.)]\s+',  # Numérotation
            r'^[\s]*[a-zA-Z][.)]\s+',  # Lettres
            r'^[\s]*[-*+]\s+',  # Tirets/astérisques
        ]
        
        self.logger.info("PDFAnalyzer initialisé")
    
    def analyze_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Analyse complète d'un document PDF
        
        Args:
            pdf_path: Chemin vers le fichier PDF
            
        Returns:
            Dictionnaire contenant l'analyse complète
        """
        try:
            self.logger.info(f"Début de l'analyse de {pdf_path}")
            
            # Ouvrir le document
            self.doc = fitz.open(pdf_path)
            
            if self.doc.is_encrypted:
                raise ValueError("Document PDF chiffré non supporté")
            
            # Analyse complète
            analysis_result = {
                'document_info': self._analyze_document_info(),
                'page_structure': self._analyze_page_structure(),
                'text_elements': self._extract_text_elements(),
                'fonts_used': self._analyze_fonts(),
                'layout_info': self._analyze_layout(),
                'metadata': self._extract_metadata(),
                # --- FIX 2: Remplacement de fitz.get_current_time() ---
                'analysis_timestamp': datetime.now().isoformat()
            }
            
            # Statistiques
            analysis_result['statistics'] = self._calculate_statistics(analysis_result)
            
            self.logger.info(f"Analyse terminée: {len(analysis_result['text_elements'])} éléments trouvés")
            
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'analyse PDF: {e}")
            raise
        finally:
            if self.doc:
                self.doc.close()
                self.doc = None
    
    def _analyze_document_info(self) -> Dict[str, Any]:
        """Analyse les informations générales du document"""
        return {
            'page_count': len(self.doc),
            'pdf_version': self.doc.metadata.get('format', 'Inconnue'),
            'is_pdf_a': self.doc.is_pdf,
            'needs_password': self.doc.needs_pass,
            'is_dirty': self.doc.is_dirty,
            'has_links': any(page.get_links() for page in self.doc),
            'has_annotations': any(page.annots() for page in self.doc),
            'has_forms': any(page.widgets() for page in self.doc)
        }
    
    def _analyze_page_structure(self) -> Dict[int, Dict[str, Any]]:
        """Analyse la structure de chaque page"""
        page_structure = {}
        
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            
            # Dimensions de la page
            rect = page.rect
            
            # Contenu de la page
            text_blocks = page.get_text("dict")
            images = page.get_images()
            drawings = page.get_drawings()
            
            page_structure[page_num + 1] = {
                'dimensions': {
                    'width': rect.width,
                    'height': rect.height,
                    'rotation': page.rotation
                },
                'text_blocks_count': len(text_blocks.get('blocks', [])),
                'images_count': len(images),
                'drawings_count': len(drawings),
                'has_text': bool(page.get_text().strip()),
                'text_density': self._calculate_text_density(page),
                'content_bounds': self._get_content_bounds(page)
            }
        
        return page_structure
    
    def _extract_text_elements(self) -> List[Dict[str, Any]]:
        """Extrait tous les éléments de texte avec leurs propriétés"""
        text_elements = []
        element_counter = 0
        
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            
            # Extraire les blocs de texte avec détails
            text_dict = page.get_text("dict")
            
            for block in text_dict.get("blocks", []):
                if "lines" not in block:  # Ignorer les blocs d'images
                    continue
                
                for line in block["lines"]:
                    for span in line["spans"]:
                        if not span["text"].strip():
                            continue
                        
                        element_counter += 1
                        
                        # Créer l'élément de texte
                        font_info = self._extract_font_info(span)
                        content_type = self._classify_content(span["text"], font_info)
                        
                        text_element = {
                            'id': f"T{element_counter:03d}",
                            'content': span["text"],
                            'page_number': page_num + 1,
                            'bbox': span["bbox"],  # (x0, y0, x1, y1)
                            'font_info': {
                                'name': font_info.name,
                                'size': font_info.size,
                                'flags': font_info.flags,
                                'is_bold': font_info.is_bold,
                                'is_italic': font_info.is_italic,
                                'is_mono': font_info.is_mono,
                                'encoding': font_info.encoding
                            },
                            'content_type': content_type.value,
                            'reading_order': element_counter,
                            'line_height': self._calculate_line_height(span),
                            'char_spacing': span.get("size", 0) * 0.1,  # Estimation
                            'confidence': self._calculate_confidence(span, content_type),
                            'text_direction': self._detect_text_direction(span["text"]),
                            'color': span.get("color", 0),
                            'origin': span.get("origin", [0, 0])
                        }
                        
                        text_elements.append(text_element)
        
        # Trier par ordre de lecture (page, puis position verticale, puis horizontale)
        text_elements.sort(key=lambda x: (x['page_number'], -x['bbox'][1], x['bbox'][0]))
        
        # Réassigner les numéros d'ordre
        for i, element in enumerate(text_elements):
            element['reading_order'] = i + 1
        
        return text_elements
    
    def _extract_font_info(self, span: Dict[str, Any]) -> FontInfo:
        """Extrait les informations de police d'un span"""
        font_name = span.get("font", "Unknown")
        font_size = span.get("size", 12.0)
        font_flags = span.get("flags", 0)
        
        # Analyser les flags de police
        is_bold = bool(font_flags & 2**4)
        is_italic = bool(font_flags & 2**1)
        is_mono = bool(font_flags & 2**0)
        
        return FontInfo(
            name=font_name,
            size=font_size,
            flags=font_flags,
            is_bold=is_bold,
            is_italic=is_italic,
            is_mono=is_mono,
            encoding=span.get("encoding", "utf-8")
        )
    
    def _classify_content(self, text: str, font_info: FontInfo) -> ContentType:
        """Classifie le type de contenu d'un élément texte"""
        text_clean = text.strip()
        word_count = len(text_clean.split())
        
        # Vérifier si c'est une liste
        for pattern in self.list_patterns:
            if re.match(pattern, text_clean):
                return ContentType.LIST_ITEM
        
        # Classification par taille de police et style
        if font_info.size >= self.title_size_threshold:
            if font_info.is_bold or word_count <= 6:
                return ContentType.TITLE
        elif font_info.size >= self.subtitle_size_threshold:
            if font_info.is_bold or word_count <= 8:
                return ContentType.SUBTITLE
        
        # Détection d'en-tête/pied de page par position (sera amélioré avec contexte)
        if word_count <= 10 and (font_info.size < 10 or text_clean.isdigit()):
            return ContentType.FOOTER
        
        # Détection de citation (texte en italique)
        if font_info.is_italic and word_count >= 3:
            return ContentType.QUOTE
        
        # Détection de code (police monospace)
        if font_info.is_mono:
            return ContentType.CODE
        
        # Paragraphe par défaut
        if word_count >= self.paragraph_min_words:
            return ContentType.PARAGRAPH
        
        # Légende ou texte court
        if word_count < self.paragraph_min_words:
            return ContentType.CAPTION
        
        return ContentType.UNKNOWN
    
    def _analyze_fonts(self) -> List[Dict[str, Any]]:
        """Analyse toutes les polices utilisées dans le document"""
        fonts_info = []
        font_usage = {}
        
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            font_list = page.get_fonts()
            
            for font_ref in font_list:
                font_name = font_ref[3]  # Nom de la police
                font_type = font_ref[1]  # Type de police
                
                if font_name not in font_usage:
                    font_usage[font_name] = {
                        'pages': set(),
                        'type': font_type,
                        'is_embedded': font_ref[2] != '',
                        'reference': font_ref[0]
                    }
                
                font_usage[font_name]['pages'].add(page_num + 1)
        
        # Convertir en liste avec statistiques
        for font_name, usage in font_usage.items():
            fonts_info.append({
                'name': font_name,
                'type': usage['type'],
                'is_embedded': usage['is_embedded'],
                'pages_used': sorted(list(usage['pages'])),
                'page_count': len(usage['pages']),
                'is_system_font': self._is_system_font(font_name),
                'font_family': self._extract_font_family(font_name)
            })
        
        # Trier par utilisation (nombre de pages)
        fonts_info.sort(key=lambda x: x['page_count'], reverse=True)
        
        return fonts_info
    
    def _analyze_layout(self) -> Dict[str, Any]:
        """Analyse la mise en page générale du document"""
        layout_info = {
            'text_columns': [],
            'margins': {},
            'text_alignment': {},
            'line_spacing': {},
            'layout_type': 'unknown'
        }
        
        # Analyser quelques pages représentatives
        sample_pages = min(3, len(self.doc))
        
        for page_num in range(sample_pages):
            page = self.doc[page_num]
            
            # Analyser les colonnes de texte
            columns = self._detect_text_columns(page)
            layout_info['text_columns'].append(columns)
            
            # Analyser les marges
            margins = self._calculate_margins(page)
            layout_info['margins'][page_num + 1] = margins
        
        # Déterminer le type de mise en page dominant
        layout_info['layout_type'] = self._determine_layout_type(layout_info)
        
        return layout_info
    
    def _extract_metadata(self) -> Dict[str, Any]:
        """Extrait les métadonnées du document"""
        metadata = self.doc.metadata
        
        return {
            'title': metadata.get('title', ''),
            'author': metadata.get('author', ''),
            'subject': metadata.get('subject', ''),
            'creator': metadata.get('creator', ''),
            'producer': metadata.get('producer', ''),
            'creation_date': metadata.get('creationDate', ''),
            'modification_date': metadata.get('modDate', ''),
            'keywords': metadata.get('keywords', ''),
            'language': self._detect_document_language()
        }
    
    def _calculate_statistics(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Calcule les statistiques générales de l'analyse"""
        text_elements = analysis_result['text_elements']
        
        # Statistiques par type de contenu
        content_type_stats = {}
        for element in text_elements:
            content_type = element['content_type']
            if content_type not in content_type_stats:
                content_type_stats[content_type] = 0
            content_type_stats[content_type] += 1
        
        # Statistiques de texte
        total_chars = sum(len(element['content']) for element in text_elements)
        total_words = sum(len(element['content'].split()) for element in text_elements)
        
        # Statistiques de police
        font_stats = {}
        for element in text_elements:
            font_name = element['font_info']['name']
            if font_name not in font_stats:
                font_stats[font_name] = 0
            font_stats[font_name] += 1
        
        return {
            'total_text_elements': len(text_elements),
            'total_characters': total_chars,
            'total_words': total_words,
            'average_words_per_element': total_words / max(1, len(text_elements)),
            'content_type_distribution': content_type_stats,
            'font_usage_distribution': font_stats,
            'pages_with_text': len([p for p in analysis_result['page_structure'].values() if p['has_text']]),
            'translation_complexity': self._assess_translation_complexity(text_elements)
        }
    
    # Méthodes utilitaires
    
    def _calculate_text_density(self, page) -> float:
        """Calcule la densité de texte d'une page"""
        text_area = 0
        page_area = page.rect.width * page.rect.height
        
        text_dict = page.get_text("dict")
        for block in text_dict.get("blocks", []):
            if "lines" in block:
                bbox = block["bbox"]
                block_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
                text_area += block_area
        
        return text_area / page_area if page_area > 0 else 0
    
    def _get_content_bounds(self, page) -> Dict[str, float]:
        """Obtient les limites du contenu d'une page"""
        text_dict = page.get_text("dict")
        
        if not text_dict.get("blocks"):
            return {'x0': 0, 'y0': 0, 'x1': 0, 'y1': 0}
        
        x0 = float('inf')
        y0 = float('inf')
        x1 = 0
        y1 = 0
        
        for block in text_dict["blocks"]:
            if "lines" in block:
                bbox = block["bbox"]
                x0 = min(x0, bbox[0])
                y0 = min(y0, bbox[1])
                x1 = max(x1, bbox[2])
                y1 = max(y1, bbox[3])
        
        return {'x0': x0, 'y0': y0, 'x1': x1, 'y1': y1}
    
    def _calculate_line_height(self, span: Dict[str, Any]) -> float:
        """Calcule la hauteur de ligne d'un span"""
        bbox = span["bbox"]
        return bbox[3] - bbox[1]  # y1 - y0
    
    def _calculate_confidence(self, span: Dict[str, Any], content_type: ContentType) -> float:
        """Calcule un score de confiance pour la classification"""
        base_confidence = 0.8
        
        # Augmenter la confiance pour certains types
        if content_type in [ContentType.TITLE, ContentType.SUBTITLE]:
            base_confidence += 0.1
        
        # Réduire pour les classifications incertaines
        if content_type == ContentType.UNKNOWN:
            base_confidence = 0.5
        
        return min(1.0, base_confidence)
    
    def _detect_text_direction(self, text: str) -> str:
        """Détecte la direction du texte"""
        # Détection simple RTL pour arabe/hébreu
        rtl_chars = sum(1 for char in text if ord(char) >= 0x590)
        return "rtl" if rtl_chars > len(text) * 0.3 else "ltr"
    
    def _is_system_font(self, font_name: str) -> bool:
        """Vérifie si une police est une police système standard"""
        system_fonts = {
            'Arial', 'Times-Roman', 'Helvetica', 'Courier',
            'Times New Roman', 'Calibri', 'Verdana', 'Georgia'
        }
        return any(sys_font.lower() in font_name.lower() for sys_font in system_fonts)
    
    def _extract_font_family(self, font_name: str) -> str:
        """Extrait la famille de police du nom complet"""
        # Supprimer les modificateurs courants
        family = re.sub(r'[,-](Bold|Italic|Regular|Light|Medium).*', '', font_name)
        return family.strip()
    
    def _detect_text_columns(self, page) -> int:
        """Détecte le nombre de colonnes de texte"""
        # Simplification : analyser la distribution horizontale des blocs de texte
        text_dict = page.get_text("dict")
        x_positions = []
        
        for block in text_dict.get("blocks", []):
            if "lines" in block:
                x_positions.append(block["bbox"][0])  # Position x gauche
        
        if not x_positions:
            return 0
        
        # Clustering simple des positions x
        x_positions.sort()
        clusters = 1
        threshold = 50  # pixels
        
        for i in range(1, len(x_positions)):
            if x_positions[i] - x_positions[i-1] > threshold:
                clusters += 1
        
        return min(clusters, 3)  # Maximum 3 colonnes détectées
    
    def _calculate_margins(self, page) -> Dict[str, float]:
        """Calcule les marges approximatives d'une page"""
        content_bounds = self._get_content_bounds(page)
        page_rect = page.rect
        
        return {
            'left': content_bounds['x0'],
            'top': content_bounds['y0'],
            'right': page_rect.width - content_bounds['x1'],
            'bottom': page_rect.height - content_bounds['y1']
        }
    
    def _determine_layout_type(self, layout_info: Dict[str, Any]) -> str:
        """Détermine le type de mise en page dominant"""
        # Analyser le nombre de colonnes moyen
        avg_columns = sum(layout_info['text_columns']) / max(1, len(layout_info['text_columns']))
        
        if avg_columns >= 2.5:
            return "multi_column"
        elif avg_columns >= 1.5:
            return "two_column"
        else:
            return "single_column"
    
    def _detect_document_language(self) -> str:
        """Détecte la langue du document (basique)"""
        # Extraction d'un échantillon de texte
        sample_text = ""
        for page_num in range(min(3, len(self.doc))):
            page = self.doc[page_num]
            sample_text += page.get_text()[:1000]
        
        # Détection basique par caractères
        if any(ord(char) >= 0x4e00 and ord(char) <= 0x9fff for char in sample_text):
            return "zh"  # Chinois
        elif any(ord(char) >= 0x0600 and ord(char) <= 0x06ff for char in sample_text):
            return "ar"  # Arabe
        elif any(ord(char) >= 0x0590 and ord(char) <= 0x05ff for char in sample_text):
            return "he"  # Hébreu
        else:
            return "unknown"
    
    def _assess_translation_complexity(self, text_elements: List[Dict[str, Any]]) -> str:
        """Évalue la complexité de traduction du document"""
        total_elements = len(text_elements)
        
        if total_elements == 0:
            return "none"
        
        # Facteurs de complexité
        complex_types = sum(1 for elem in text_elements 
                          if elem['content_type'] in ['table_cell', 'list_item'])
        
        avg_font_size = sum(elem['font_info']['size'] for elem in text_elements) / total_elements
        
        unique_fonts = len(set(elem['font_info']['name'] for elem in text_elements))
        
        # Classification
        complexity_score = 0
        complexity_score += complex_types / total_elements * 0.4
        complexity_score += min(unique_fonts / 10, 1) * 0.3
        complexity_score += (1 if avg_font_size < 10 else 0) * 0.3
        
        if complexity_score > 0.7:
            return "high"
        elif complexity_score > 0.4:
            return "medium"
        else:
            return "low"
