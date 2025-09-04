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
from typing import Dict, List, Any, Optional, Tuple  # <-- FIX: Ajout de l'importation manquante
from dataclasses import dataclass, field
from fontTools.ttLib import TTFont, TTLibError
import json

if platform.system() == "Windows":
    import winreg

@dataclass
class FontStyle:
    path: Path
    
@dataclass
class FontFamily:
    name: str
    styles: Dict[str, FontStyle] = field(default_factory=dict)

@dataclass
class FontMapping:
    original_font: str
    replacement_font_name: str

class FontManager:
    def __init__(self, app_data_dir: Path):
        self.logger = logging.getLogger(__name__)
        self.app_data_dir = app_data_dir
        self.font_mappings_file = self.app_data_dir / "config" / "font_mappings.json"
        
        self.font_families: Dict[str, FontFamily] = {}
        self.font_mappings: Dict[str, FontMapping] = {}
        self._scanned_files = set()
        
        self._scan_system_fonts()
        self._load_font_mappings()
        
        self.logger.info(f"FontManager initialisé: {len(self.font_families)} familles de polices trouvées.")

    def _scan_system_fonts(self):
        """Scanne les polices système de manière exhaustive."""
        self.logger.info("Scanning exhaustif des polices système...")
        if platform.system() == "Windows":
            self._scan_fonts_from_registry()
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
                        font_path = Path(file_name) if Path(file_name).is_absolute() else font_dir / file_name
                        if font_path.exists() and font_path not in self._scanned_files:
                            self._process_font_file(font_path)
                            self._scanned_files.add(font_path)
                        i += 1
                    except OSError:
                        break
        except Exception as e:
            self.logger.error(f"Erreur d'accès au registre, le scan sera moins complet: {e}")

    def _scan_fonts_from_folders(self):
        """Scanne les dossiers de polices connus."""
        self.logger.debug("Scan des polices depuis les dossiers système...")
        font_extensions = {'.ttf', '.otf', '.ttc'}
        for font_dir in self._get_system_font_directories():
            for font_file in font_dir.rglob('*'):
                if font_file.suffix.lower() in font_extensions and font_file not in self._scanned_files:
                    self._process_font_file(font_file)
                    self._scanned_files.add(font_file)

    def _get_system_font_directories(self) -> List[Path]:
        dirs = []
        if platform.system() == 'Windows':
            dirs.extend([Path(os.environ.get('WINDIR', 'C:\\Windows')) / 'Fonts', 
                         Path.home() / 'AppData' / 'Local' / 'Microsoft' / 'Windows' / 'Fonts'])
        elif platform.system() == 'darwin':
            dirs.extend([Path('/System/Library/Fonts'), Path('/Library/Fonts'), Path.home() / 'Library' / 'Fonts'])
        else:
            dirs.extend([Path('/usr/share/fonts'), Path('/usr/local/share/fonts'), Path.home() / '.fonts'])
        return [d for d in dirs if d.exists()]

    def _process_font_file(self, font_path: Path):
        try:
            font_collection = TTFont(font_path, lazy=True)
            if hasattr(font_collection, 'reader') and 'ttc' in font_collection.reader.file.name.lower():
                for i in range(len(font_collection.reader.fonts)):
                    font = TTFont(font_path, fontNumber=i, lazy=True)
                    self._add_font_from_metadata(font, font_path)
            else:
                self._add_font_from_metadata(font_collection, font_path)
        except (TTLibError, Exception):
            pass

    def _add_font_from_metadata(self, font: TTFont, font_path: Path):
        name_table = font['name']
        family_name, style_name = None, None
        for record in name_table.names:
            if record.nameID == 1: family_name = record.toUnicode()
            elif record.nameID == 2: style_name = record.toUnicode()
        if family_name and style_name:
            if family_name not in self.font_families:
                self.font_families[family_name] = FontFamily(name=family_name)
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
        missing_fonts = set()
        for font_name in set(required_fonts):
            if font_name.lower() not in available_fonts_lower:
                missing_fonts.add(font_name)
        suggestions = {font: self._suggest_alternatives(font) for font in missing_fonts}
        return {'missing_fonts': list(missing_fonts), 'suggestions': suggestions, 'all_available': not missing_fonts}

    def _suggest_alternatives(self, missing_font: str) -> List[Dict[str, Any]]:
        if 'bold' in missing_font.lower() and "Arial Bold" in self.get_all_available_fonts(): return [{'font_name': "Arial Bold"}]
        if 'italic' in missing_font.lower() and "Arial Italic" in self.get_all_available_fonts(): return [{'font_name': "Arial Italic"}]
        if "Arial" in self.get_all_available_fonts(): return [{'font_name': "Arial"}]
        return [{'font_name': "Helvetica"}]

    def create_font_mapping(self, original_font: str, replacement_font_name: str):
        self.font_mappings[original_font] = FontMapping(original_font, replacement_font_name)
        self._save_font_mappings()
        self.logger.info(f"Mapping sauvegardé: '{original_font}' -> '{replacement_font_name}'")

    def get_replacement_font_path(self, original_font_name: str) -> Optional[Path]:
        if original_font_name in self.font_mappings:
            replacement_name = self.font_mappings[original_font_name].replacement_font_name
            family, style = self._split_font_name(replacement_name)
            if family in self.font_families and style in self.font_families[family].styles:
                return self.font_families[family].styles[style].path

        fallback_name = self._suggest_alternatives(original_font_name)[0]['font_name']
        family, style = self._split_font_name(fallback_name)
        if family in self.font_families and style in self.font_families[family].styles:
            return self.font_families[family].styles[style].path
        
        return None

    def _split_font_name(self, full_name: str) -> Tuple[str, str]:
        for family_name in sorted(self.font_families.keys(), key=len, reverse=True):
            if full_name.startswith(family_name):
                style = full_name[len(family_name):].strip()
                return family_name, style if style else "Regular"
        return full_name, "Regular"

    def _load_font_mappings(self):
        if self.font_mappings_file.exists():
            try:
                with open(self.font_mappings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for original, mapping_data in data.items():
                        self.font_mappings[original] = FontMapping(
                            original_font=mapping_data['original_font'],
                            replacement_font_name=mapping_data['replacement_font_name']
                        )
            except Exception: pass

    def _save_font_mappings(self):
        self.font_mappings_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.font_mappings_file, 'w', encoding='utf-8') as f:
                json.dump({k: v.__dict__ for k, v in self.font_mappings.items()}, f, indent=2)
        except Exception: pass
