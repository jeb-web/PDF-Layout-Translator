#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Gestionnaire de polices
Gestion des polices, détection, remplacement et installation

Auteur: L'OréalGPT
Version: 1.0.0
"""

import os
import shutil
import logging
import platform
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from fontTools.ttLib import TTFont
import json
from datetime import datetime

@dataclass
class FontMapping:
    original_font: str
    replacement_font: str
    mapping_type: str  # 'automatic', 'user_choice', 'fallback'

class FontManager:
    """Gestionnaire de polices système et personnalisées."""
    
    def __init__(self, app_data_dir: Path):
        self.logger = logging.getLogger(__name__)
        self.app_data_dir = Path(app_data_dir)
        self.font_mappings_file = self.app_data_dir / "config" / "font_mappings.json"
        
        self.system_fonts: Dict[str, Path] = {}
        self.font_mappings: Dict[str, FontMapping] = {}
        
        self._scan_system_fonts()
        self._load_font_mappings()
        
        self.logger.info(f"FontManager initialisé: {len(self.system_fonts)} polices système trouvées.")
    
    def _get_system_font_directories(self) -> List[Path]:
        system = platform.system().lower()
        if system == 'windows':
            return [Path(os.environ.get('WINDIR', 'C:\\Windows')) / 'Fonts']
        elif system == 'darwin': # macOS
            return [Path('/System/Library/Fonts'), Path('/Library/Fonts'), Path.home() / 'Library' / 'Fonts']
        else: # Linux
            return [Path('/usr/share/fonts'), Path('/usr/local/share/fonts'), Path.home() / '.fonts']
    
    def _scan_system_fonts(self):
        self.logger.info("Scanning des polices système...")
        font_extensions = {'.ttf', '.otf', '.ttc'}
        for font_dir in self._get_system_font_directories():
            if font_dir.exists():
                for font_file in font_dir.rglob('*'):
                    if font_file.suffix.lower() in font_extensions:
                        try:
                            # Utiliser le nom du fichier comme clé simplifiée
                            self.system_fonts[font_file.stem] = font_file
                        except Exception:
                            continue
    
    def get_all_available_fonts(self) -> List[str]:
        return sorted(list(self.system_fonts.keys()))

    def check_fonts_availability(self, required_fonts: List[str]) -> Dict[str, Any]:
        available_system_fonts_lower = {name.lower(): name for name in self.system_fonts.keys()}
        missing_fonts = []
        
        for font_name in set(required_fonts):
            # Ignorer les polices PDF de base qui n'ont pas besoin de remplacement
            if font_name.lower() in ["helvetica", "times", "courier", "symbol", "zapfdingbats"]:
                continue
            
            if font_name.lower() not in available_system_fonts_lower:
                missing_fonts.append(font_name)
        
        suggestions = {font: self._suggest_alternatives(font) for font in missing_fonts}
        
        return {
            'missing_fonts': missing_fonts,
            'suggestions': suggestions,
            'all_available': len(missing_fonts) == 0
        }

    def _suggest_alternatives(self, missing_font: str) -> List[Dict[str, Any]]:
        # Logique de suggestion simple pour l'instant
        suggestions = []
        missing_lower = missing_font.lower()
        
        # Suggestion basée sur le style
        if 'bold' in missing_lower: suggestions.append({'font_name': 'Arial Bold', 'confidence': 0.7})
        elif 'italic' in missing_lower: suggestions.append({'font_name': 'Arial Italic', 'confidence': 0.7})
        
        # Suggestion par défaut
        suggestions.append({'font_name': 'Arial', 'confidence': 0.5})
        
        return suggestions

    def create_font_mapping(self, original_font: str, replacement_font: str, mapping_type: str = 'user_choice'):
        mapping = FontMapping(
            original_font=original_font,
            replacement_font=replacement_font,
            mapping_type=mapping_type,
        )
        self.font_mappings[original_font] = mapping
        self._save_font_mappings()

    def get_replacement_font(self, original_font: str) -> str:
        # 1. Vérifier les mappings choisis par l'utilisateur
        if original_font in self.font_mappings:
            return self.font_mappings[original_font].replacement_font
        
        # 2. Logique de fallback (très simplifiée)
        if 'bold' in original_font.lower(): return 'Arial Bold'
        if 'italic' in original_font.lower(): return 'Arial Italic'
        return 'Arial' # Fallback ultime

    def _load_font_mappings(self):
        if self.font_mappings_file.exists():
            try:
                with open(self.font_mappings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for original, mapping_data in data.items():
                        self.font_mappings[original] = FontMapping(**mapping_data)
                self.logger.info(f"{len(self.font_mappings)} correspondances chargées.")
            except Exception as e:
                self.logger.error(f"Erreur chargement mappings: {e}")

    def _save_font_mappings(self):
        self.font_mappings_file.parent.mkdir(parents=True, exist_ok=True)
        data_to_save = {key: value.__dict__ for key, value in self.font_mappings.items()}
        with open(self.font_mappings_file, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, indent=2)
