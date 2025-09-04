#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Gestionnaire de polices
Gestion des polices, détection, remplacement et installation

Auteur: L'OréalGPT
Version: 1.0.0
"""

import os
import logging
import platform
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from fontTools.ttLib import TTFont, TTLibError
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
        
        # --- MODIFICATION: Le dictionnaire stocke maintenant {VraiNom: CheminFichier} ---
        self.system_fonts: Dict[str, Path] = {}
        self.font_mappings: Dict[str, FontMapping] = {}
        
        self._scan_system_fonts()
        self._load_font_mappings()
        
        self.logger.info(f"FontManager initialisé: {len(self.system_fonts)} polices système trouvées.")
    
    def _get_system_font_directories(self) -> List[Path]:
        system = platform.system().lower()
        dirs = []
        if system == 'windows':
            dirs.append(Path(os.environ.get('WINDIR', 'C:\\Windows')) / 'Fonts')
        elif system == 'darwin': # macOS
            dirs.extend([Path('/System/Library/Fonts'), Path('/Library/Fonts'), Path.home() / 'Library' / 'Fonts'])
        else: # Linux
            dirs.extend([Path('/usr/share/fonts'), Path('/usr/local/share/fonts'), Path.home() / '.fonts'])
        
        return [d for d in dirs if d.exists()]

    def _get_font_real_name(self, font_path: Path) -> Optional[str]:
        """
        Ouvre un fichier de police et lit son vrai nom depuis les métadonnées.
        """
        try:
            with TTFont(font_path, lazy=True) as font:
                # La table 'name' contient les métadonnées de la police
                name_table = font['name']
                full_name = None
                family_name = None

                for record in name_table.names:
                    # nameID 4 est le "Full Font Name", c'est le plus fiable
                    if record.nameID == 4:
                        full_name = record.toUnicode()
                    # nameID 1 est la famille (ex: "Arial")
                    elif record.nameID == 1:
                        family_name = record.toUnicode()

                # Retourner le nom complet si disponible, sinon la famille, sinon None
                return full_name if full_name else family_name
        except (TTLibError, Exception) as e:
            # Gérer les fichiers de police corrompus ou illisibles
            self.logger.debug(f"Impossible de lire le nom de la police {font_path}: {e}")
            return None
    
    def _scan_system_fonts(self):
        self.logger.info("Scanning des polices système (lecture des métadonnées)...")
        font_extensions = {'.ttf', '.otf', '.ttc'}
        
        for font_dir in self._get_system_font_directories():
            for font_file in font_dir.rglob('*'):
                if font_file.suffix.lower() in font_extensions:
                    real_name = self._get_font_real_name(font_file)
                    if real_name and real_name not in self.system_fonts:
                        # --- MODIFICATION: Utilisation du vrai nom comme clé ---
                        self.system_fonts[real_name] = font_file

    def get_all_available_fonts(self) -> List[str]:
        return sorted(list(self.system_fonts.keys()))

    def check_fonts_availability(self, required_fonts: List[str]) -> Dict[str, Any]:
        available_system_fonts_lower = {name.lower(): name for name in self.system_fonts.keys()}
        missing_fonts = []
        
        for font_name in set(required_fonts):
            # Normaliser le nom de la police requise
            normalized_font_name = font_name.replace('-', ' ').replace('_', ' ')
            
            # Vérifier s'il existe une correspondance (insensible à la casse)
            found = False
            for available_font_lower in available_system_fonts_lower:
                if normalized_font_name.lower() in available_font_lower:
                    found = True
                    break
            if not found:
                missing_fonts.append(font_name)
        
        suggestions = {font: self._suggest_alternatives(font) for font in missing_fonts}
        
        return {
            'missing_fonts': missing_fonts,
            'suggestions': suggestions,
            'all_available': len(missing_fonts) == 0
        }

    def _suggest_alternatives(self, missing_font: str) -> List[Dict[str, Any]]:
        suggestions = []
        missing_lower = missing_font.lower()
        
        if 'bold' in missing_lower: suggestions.append({'font_name': 'Arial Bold', 'confidence': 0.7})
        elif 'italic' in missing_lower: suggestions.append({'font_name': 'Arial Italic', 'confidence': 0.7})
        
        suggestions.append({'font_name': 'Arial', 'confidence': 0.5})
        
        # Filtrer pour ne suggérer que des polices réellement disponibles
        available_fonts = self.get_all_available_fonts()
        return [s for s in suggestions if s['font_name'] in available_fonts]

    def create_font_mapping(self, original_font: str, replacement_font: str, mapping_type: str = 'user_choice'):
        mapping = FontMapping(
            original_font=original_font,
            replacement_font=replacement_font,
            mapping_type=mapping_type,
        )
        self.font_mappings[original_font] = mapping
        self._save_font_mappings()
        self.logger.info(f"Correspondance de police sauvegardée: '{original_font}' -> '{replacement_font}'")

    def get_replacement_font(self, original_font: str) -> str:
        if original_font in self.font_mappings:
            return self.font_mappings[original_font].replacement_font
        
        if 'bold' in original_font.lower(): return 'Arial Bold'
        if 'italic' in original_font.lower(): return 'Arial Italic'
        return 'Arial'

    def _load_font_mappings(self):
        if self.font_mappings_file.exists():
            try:
                with open(self.font_mappings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for original, mapping_data in data.items():
                        self.font_mappings[original] = FontMapping(**mapping_data)
                self.logger.info(f"{len(self.font_mappings)} correspondances de polices chargées.")
            except Exception as e:
                self.logger.error(f"Erreur lors du chargement des mappings: {e}")

    def _save_font_mappings(self):
        self.font_mappings_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            data_to_save = {key: value.__dict__ for key, value in self.font_mappings.items()}
            with open(self.font_mappings_file, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Erreur lors de la sauvegarde des mappings: {e}")
