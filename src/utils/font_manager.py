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

# Spécifique à Windows pour la lecture du registre
if platform.system() == "Windows":
    import winreg

@dataclass
class FontStyle:
    path: Path
    
@dataclass
class FontFamily:
    name: str
    styles: Dict[str, FontStyle]

@dataclass
class FontMapping:
    original_font: str
    replacement_font: str

class FontManager:
    """Gestionnaire de polices système et personnalisées."""
    
    def __init__(self, app_data_dir: Path):
        self.logger = logging.getLogger(__name__)
        self.app_data_dir = Path(app_data_dir)
        self.font_mappings_file = self.app_data_dir / "config" / "font_mappings.json"
        
        self.font_families: Dict[str, FontFamily] = {}
        self.font_mappings: Dict[str, FontMapping] = {}
        self._scanned_files = set() # Pour éviter de traiter un fichier deux fois
        
        self._scan_system_fonts()
        self._load_font_mappings()
        
        self.logger.info(f"FontManager initialisé: {len(self.font_families)} familles de polices trouvées.")
    
    def _scan_system_fonts(self):
        """Scanne les polices système de manière exhaustive."""
        self.logger.info("Scanning exhaustif des polices système...")
        if platform.system() == "Windows":
            self._scan_fonts_from_registry()
        # Toujours scanner les dossiers en complément ou pour les autres OS
        self._scan_fonts_from_folders()

    def _scan_fonts_from_registry(self):
        """Méthode Windows: lit les polices depuis le registre pour une fiabilité maximale."""
        self.logger.debug("Scan des polices depuis le registre Windows...")
        font_dir = Path(os.environ.get('WINDIR', 'C:\\Windows')) / 'Fonts'
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts") as key:
                i = 0
                while True:
                    try:
                        _, file_name, _ = winreg.EnumValue(key, i)
                        # Le chemin peut être absolu ou relatif au dossier Fonts
                        font_path = Path(file_name)
                        if not font_path.is_absolute():
                            font_path = font_dir / file_name
                        
                        if font_path.exists() and font_path not in self._scanned_files:
                            self._process_font_file(font_path)
                            self._scanned_files.add(font_path)
                        i += 1
                    except OSError:
                        break # Fin de la liste
        except Exception as e:
            self.logger.error(f"Erreur d'accès au registre, le scan sera moins complet: {e}")

    def _scan_fonts_from_folders(self):
        """Scanne les dossiers de polices connus."""
        self.logger.debug("Scan des polices depuis les dossiers système...")
        font_extensions = {'.ttf', '.otf', '.ttc'}
        for font_dir in self._get_system_font_directories():
            if font_dir.exists():
                for font_file in font_dir.rglob('*'):
                    if font_file.suffix.lower() in font_extensions and font_file not in self._scanned_files:
                        self._process_font_file(font_file)
                        self._scanned_files.add(font_file)

    def _get_system_font_directories(self) -> List[Path]:
        dirs = []
        if platform.system() == 'Windows':
            dirs.append(Path(os.environ.get('WINDIR', 'C:\\Windows')) / 'Fonts')
            dirs.append(Path.home() / 'AppData' / 'Local' / 'Microsoft' / 'Windows' / 'Fonts')
        elif platform.system() == 'darwin': # macOS
            dirs.extend([Path('/System/Library/Fonts'), Path('/Library/Fonts'), Path.home() / 'Library' / 'Fonts'])
        else: # Linux
            dirs.extend([Path('/usr/share/fonts'), Path('/usr/local/share/fonts'), Path.home() / '.fonts'])
        
        return [d for d in dirs if d.exists()]

    def _process_font_file(self, font_path: Path):
        """Ouvre un fichier de police, lit ses métadonnées et l'ajoute à la structure."""
        try:
            font = TTFont(font_path, lazy=True)
            if 'ttc' in str(font_path).lower():
                for i in range(len(font.reader.fonts)):
                    sub_font = TTFont(font_path, fontNumber=i, lazy=True)
                    self._add_font_from_metadata(sub_font, font_path)
            else:
                self._add_font_from_metadata(font, font_path)
        except (TTLibError, Exception) as e:
            self.logger.debug(f"Impossible de traiter le fichier de police {font_path}: {e}")

    def _add_font_from_metadata(self, font: TTFont, font_path: Path):
        name_table = font['name']
        family_name, style_name = None, None
        
        for record in name_table.names:
            if record.nameID == 1: family_name = record.toUnicode()
            elif record.nameID == 2: style_name = record.toUnicode()

        if family_name and style_name:
            if family_name not in self.font_families:
                self.font_families[family_name] = FontFamily(name=family_name, styles={})
            self.font_families[family_name].styles[style_name] = FontStyle(path=font_path)

    def get_all_available_fonts(self) -> List[str]:
        full_font_names = []
        for family in self.font_families.values():
            for style in family.styles.keys():
                full_font_names.append(f"{family.name} {style}")
        return sorted(full_font_names)

    def check_fonts_availability(self, required_fonts: List[str]) -> Dict[str, Any]:
        available_fonts_list = self.get_all_available_fonts()
        available_fonts_lower = {name.lower() for name in available_fonts_list}
        missing_fonts = []
        
        for font_name in set(required_fonts):
            if font_name.lower() not in available_fonts_lower:
                missing_fonts.append(font_name)
        
        suggestions = {font: self._suggest_alternatives(font) for font in missing_fonts}
        
        return {'missing_fonts': missing_fonts, 'suggestions': suggestions, 'all_available': len(missing_fonts) == 0}

    def _suggest_alternatives(self, missing_font: str) -> List[Dict[str, Any]]:
        missing_lower = missing_font.lower()
        if 'bold' in missing_lower and "Arial Bold" in self.get_all_available_fonts(): return [{'font_name': "Arial Bold"}]
        if 'italic' in missing_lower and "Arial Italic" in self.get_all_available_fonts(): return [{'font_name': "Arial Italic"}]
        if "Arial" in self.get_all_available_fonts(): return [{'font_name': "Arial"}]
        return [{'font_name': "Helvetica"}]

    def create_font_mapping(self, original_font: str, replacement_font: str):
        self.font_mappings[original_font] = FontMapping(original_font, replacement_font)
        self._save_font_mappings()
        self.logger.info(f"Correspondance de police sauvegardée: '{original_font}' -> '{replacement_font}'")

    def get_replacement_font(self, original_font: str) -> str:
        if original_font in self.font_mappings:
            return self.font_mappings[original_font].replacement_font
        return self._suggest_alternatives(original_font)[0]['font_name']

    def _load_font_mappings(self):
        if self.font_mappings_file.exists():
            try:
                with open(self.font_mappings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for original, mapping_data in data.items():
                        self.font_mappings[original] = FontMapping(mapping_data['original_font'], mapping_data['replacement_font'])
            except Exception as e:
                self.logger.error(f"Erreur chargement mappings: {e}")

    def _save_font_mappings(self):
        self.font_mappings_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            data_to_save = {key: {'original_font': value.original_font, 'replacement_font': value.replacement_font} for key, value in self.font_mappings.items()}
            with open(self.font_mappings_file, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Erreur lors de la sauvegarde des mappings: {e}")
