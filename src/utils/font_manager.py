#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Gestionnaire de polices
Gestion des polices, détection, remplacement et installation

Auteur: L'OréalGPT
Version: 1.0.0
"""

import os
import sys
import shutil
import logging
import platform
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass
from fontTools.ttLib import TTFont
from fontTools.fontBuilder import FontBuilder
import json

@dataclass
class FontInfo:
    """Informations détaillées sur une police"""
    name: str
    family: str
    style: str
    file_path: Optional[Path]
    is_system_font: bool
    is_embedded: bool
    is_available: bool
    license_info: str
    alternatives: List[str]

@dataclass
class FontMapping:
    """Mapping entre police originale et remplacement"""
    original_font: str
    replacement_font: str
    mapping_type: str  # 'automatic', 'user_choice', 'fallback'
    confidence: float
    created_at: str

class FontManager:
    """Gestionnaire de polices système et personnalisées"""
    
    def __init__(self, app_data_dir: Path):
        """
        Initialise le gestionnaire de polices
        
        Args:
            app_data_dir: Répertoire de données de l'application
        """
        self.logger = logging.getLogger(__name__)
        self.app_data_dir = Path(app_data_dir)
        self.custom_fonts_dir = self.app_data_dir / "fonts" / "custom_fonts"
        self.custom_fonts_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache des polices système
        self.system_fonts: Dict[str, FontInfo] = {}
        self.custom_fonts: Dict[str, FontInfo] = {}
        self.font_mappings: Dict[str, FontMapping] = {}
        
        # Répertoires de polices selon l'OS
        self.system_font_dirs = self._get_system_font_directories()
        
        # Polices de fallback par catégorie
        self.fallback_fonts = {
            'serif': ['Times New Roman', 'Times', 'Georgia', 'serif'],
            'sans-serif': ['Arial', 'Helvetica', 'Verdana', 'Calibri', 'sans-serif'],
            'monospace': ['Courier New', 'Courier', 'Consolas', 'Monaco', 'monospace'],
            'script': ['Comic Sans MS', 'Brush Script MT', 'cursive'],
            'fantasy': ['Impact', 'Arial Black', 'fantasy']
        }
        
        # Equivalences de polices courantes
        self.common_equivalents = {
            'Arial': ['Helvetica', 'Liberation Sans', 'DejaVu Sans'],
            'Times New Roman': ['Times', 'Liberation Serif', 'DejaVu Serif'],
            'Courier New': ['Courier', 'Liberation Mono', 'DejaVu Sans Mono'],
            'Helvetica': ['Arial', 'Liberation Sans', 'DejaVu Sans'],
            'Times': ['Times New Roman', 'Liberation Serif', 'DejaVu Serif'],
            'Courier': ['Courier New', 'Liberation Mono', 'DejaVu Sans Mono']
        }
        
        # Charger les données existantes
        self._load_font_mappings()
        
        # Scanner les polices au démarrage
        self._scan_system_fonts()
        self._scan_custom_fonts()
        
        self.logger.info(f"FontManager initialisé: {len(self.system_fonts)} polices système, "
                        f"{len(self.custom_fonts)} polices personnalisées")
    
    def _get_system_font_directories(self) -> List[Path]:
        """Retourne les répertoires de polices système selon l'OS"""
        system = platform.system().lower()
        font_dirs = []
        
        if system == 'windows':
            font_dirs = [
                Path(os.environ.get('WINDIR', 'C:\\Windows')) / 'Fonts',
                Path.home() / 'AppData' / 'Local' / 'Microsoft' / 'Windows' / 'Fonts'
            ]
        elif system == 'darwin':  # macOS
            font_dirs = [
                Path('/System/Library/Fonts'),
                Path('/Library/Fonts'),
                Path.home() / 'Library' / 'Fonts'
            ]
        else:  # Linux et autres Unix
            font_dirs = [
                Path('/usr/share/fonts'),
                Path('/usr/local/share/fonts'),
                Path.home() / '.fonts',
                Path.home() / '.local' / 'share' / 'fonts'
            ]
        
        # Filtrer les répertoires existants
        return [d for d in font_dirs if d.exists()]
    
    def _scan_system_fonts(self):
        """Scanne les polices système disponibles"""
        self.logger.info("Scanning des polices système...")
        
        font_extensions = {'.ttf', '.otf', '.woff', '.woff2'}
        
        for font_dir in self.system_font_dirs:
            try:
                for font_file in font_dir.rglob('*'):
                    if font_file.suffix.lower() in font_extensions:
                        try:
                            font_info = self._extract_font_info(font_file, is_system=True)
                            if font_info:
                                self.system_fonts[font_info.name] = font_info
                        except Exception as e:
                            self.logger.debug(f"Erreur lecture police {font_file}: {e}")
                            
            except Exception as e:
                self.logger.warning(f"Erreur scanning {font_dir}: {e}")
        
        self.logger.info(f"{len(self.system_fonts)} polices système trouvées")
    
    def _scan_custom_fonts(self):
        """Scanne les polices personnalisées installées"""
        self.logger.info("Scanning des polices personnalisées...")
        
        font_extensions = {'.ttf', '.otf'}
        
        try:
            for font_file in self.custom_fonts_dir.rglob('*'):
                if font_file.suffix.lower() in font_extensions:
                    try:
                        font_info = self._extract_font_info(font_file, is_system=False)
                        if font_info:
                            self.custom_fonts[font_info.name] = font_info
                    except Exception as e:
                        self.logger.debug(f"Erreur lecture police personnalisée {font_file}: {e}")
                        
        except Exception as e:
            self.logger.warning(f"Erreur scanning polices personnalisées: {e}")
        
        self.logger.info(f"{len(self.custom_fonts)} polices personnalisées trouvées")
    
    def _extract_font_info(self, font_file: Path, is_system: bool) -> Optional[FontInfo]:
        """
        Extrait les informations d'un fichier de police
        
        Args:
            font_file: Chemin vers le fichier de police
            is_system: True si c'est une police système
            
        Returns:
            Informations de la police ou None si erreur
        """
        try:
            # Utiliser fontTools pour lire les métadonnées
            font = TTFont(font_file)
            
            # Extraire le nom de la police
            name_table = font['name']
            font_name = None
            font_family = None
            font_style = "Regular"
            
            # Chercher le nom complet (nameID 4) et la famille (nameID 1)
            for record in name_table.names:
                if record.nameID == 4:  # Nom complet
                    font_name = record.toUnicode()
                elif record.nameID == 1:  # Famille
                    font_family = record.toUnicode()
                elif record.nameID == 2:  # Style
                    font_style = record.toUnicode()
            
            if not font_name:
                font_name = font_family or font_file.stem
            
            if not font_family:
                font_family = font_name
            
            # Trouver des polices alternatives
            alternatives = self._find_alternatives(font_name, font_family)
            
            font.close()
            
            return FontInfo(
                name=font_name,
                family=font_family,
                style=font_style,
                file_path=font_file,
                is_system_font=is_system,
                is_embedded=False,  # Les polices fichier ne sont pas embedded
                is_available=True,
                license_info=self._get_license_info(font_file),
                alternatives=alternatives
            )
            
        except Exception as e:
            self.logger.debug(f"Impossible de lire {font_file}: {e}")
            return None
    
    def _find_alternatives(self, font_name: str, font_family: str) -> List[str]:
        """Trouve des polices alternatives"""
        alternatives = []
        
        # Vérifier les équivalences connues
        for known_font, equivalents in self.common_equivalents.items():
            if known_font.lower() in font_name.lower():
                alternatives.extend(equivalents)
            elif font_name in equivalents:
                alternatives.append(known_font)
        
        # Ajouter des polices de la même famille
        family_lower = font_family.lower()
        for font_info in self.system_fonts.values():
            if (font_info.family.lower() == family_lower and 
                font_info.name != font_name):
                alternatives.append(font_info.name)
        
        # Supprimer les doublons et limiter
        return list(dict.fromkeys(alternatives))[:5]
    
    def _get_license_info(self, font_file: Path) -> str:
        """Obtient les informations de licence d'une police"""
        try:
            font = TTFont(font_file)
            name_table = font['name']
            
            # Chercher les informations de licence (nameID 13 ou 14)
            for record in name_table.names:
                if record.nameID in [13, 14]:  # License info
                    license_text = record.toUnicode()
                    font.close()
                    return license_text[:100] + "..." if len(license_text) > 100 else license_text
            
            font.close()
            return "Licence inconnue"
            
        except Exception:
            return "Impossible de lire la licence"
    
    def check_fonts_availability(self, required_fonts: List[str]) -> Dict[str, Any]:
        """
        Vérifie la disponibilité des polices requises
        
        Args:
            required_fonts: Liste des noms de polices requises
            
        Returns:
            Rapport de disponibilité des polices
        """
        available_fonts = []
        missing_fonts = []
        suggestions = {}
        
        all_fonts = {**self.system_fonts, **self.custom_fonts}
        
        for font_name in required_fonts:
            if self._is_font_available(font_name):
                available_fonts.append(font_name)
            else:
                missing_fonts.append(font_name)
                suggestions[font_name] = self._suggest_alternatives(font_name)
        
        return {
            'total_required': len(required_fonts),
            'available_count': len(available_fonts),
            'missing_count': len(missing_fonts),
            'available_fonts': available_fonts,
            'missing_fonts': missing_fonts,
            'suggestions': suggestions,
            'all_available': len(missing_fonts) == 0
        }
    
    def _is_font_available(self, font_name: str) -> bool:
        """Vérifie si une police est disponible"""
        # Vérification exacte
        if font_name in self.system_fonts or font_name in self.custom_fonts:
            return True
        
        # Vérification insensible à la casse
        font_name_lower = font_name.lower()
        all_fonts = {**self.system_fonts, **self.custom_fonts}
        
        for available_font in all_fonts:
            if available_font.lower() == font_name_lower:
                return True
        
        # Vérification partielle (contient le nom)
        for available_font in all_fonts:
            if font_name_lower in available_font.lower():
                return True
        
        return False
    
    def _suggest_alternatives(self, missing_font: str) -> List[Dict[str, Any]]:
        """Suggère des alternatives pour une police manquante"""
        suggestions = []
        missing_lower = missing_font.lower()
        
        # 1. Vérifier les équivalences connues
        for known_font, equivalents in self.common_equivalents.items():
            if (known_font.lower() == missing_lower or 
                missing_font in equivalents):
                for equiv in [known_font] + equivalents:
                    if self._is_font_available(equiv):
                        suggestions.append({
                            'font_name': equiv,
                            'confidence': 0.9,
                            'reason': 'Équivalence connue'
                        })
        
        # 2. Recherche par famille
        all_fonts = {**self.system_fonts, **self.custom_fonts}
        for font_name, font_info in all_fonts.items():
            if missing_lower in font_info.family.lower():
                suggestions.append({
                    'font_name': font_name,
                    'confidence': 0.8,
                    'reason': 'Même famille'
                })
        
        # 3. Recherche par similarité de nom
        for font_name in all_fonts:
            similarity = self._calculate_name_similarity(missing_font, font_name)
            if similarity > 0.6:
                suggestions.append({
                    'font_name': font_name,
                    'confidence': similarity,
                    'reason': 'Nom similaire'
                })
        
        # 4. Fallback par catégorie
        font_category = self._categorize_font(missing_font)
        if font_category in self.fallback_fonts:
            for fallback in self.fallback_fonts[font_category]:
                if self._is_font_available(fallback):
                    suggestions.append({
                        'font_name': fallback,
                        'confidence': 0.5,
                        'reason': f'Fallback {font_category}'
                    })
        
        # Trier par confiance et supprimer les doublons
        seen = set()
        unique_suggestions = []
        for suggestion in sorted(suggestions, key=lambda x: x['confidence'], reverse=True):
            if suggestion['font_name'] not in seen:
                seen.add(suggestion['font_name'])
                unique_suggestions.append(suggestion)
        
        return unique_suggestions[:5]  # Limiter à 5 suggestions
    
    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Calcule la similarité entre deux noms de police"""
        name1_lower = name1.lower()
        name2_lower = name2.lower()
        
        # Similarité simple basée sur les mots communs
        words1 = set(name1_lower.split())
        words2 = set(name2_lower.split())
        
        if not words1 or not words2:
            return 0.0
        
        common_words = words1 & words2
        total_words = words1 | words2
        
        return len(common_words) / len(total_words)
    
    def _categorize_font(self, font_name: str) -> str:
        """Catégorise une police selon son type"""
        font_lower = font_name.lower()
        
        # Mots-clés pour chaque catégorie
        serif_keywords = ['times', 'garamond', 'georgia', 'serif']
        sans_serif_keywords = ['arial', 'helvetica', 'verdana', 'calibri', 'sans']
        monospace_keywords = ['courier', 'console', 'mono', 'code']
        script_keywords = ['script', 'brush', 'comic']
        
        for keyword in serif_keywords:
            if keyword in font_lower:
                return 'serif'
        
        for keyword in sans_serif_keywords:
            if keyword in font_lower:
                return 'sans-serif'
        
        for keyword in monospace_keywords:
            if keyword in font_lower:
                return 'monospace'
        
        for keyword in script_keywords:
            if keyword in font_lower:
                return 'script'
        
        return 'sans-serif'  # Défaut
    
    def install_custom_font(self, font_file_path: Path) -> Dict[str, Any]:
        """
        Installe une police personnalisée
        
        Args:
            font_file_path: Chemin vers le fichier de police
            
        Returns:
            Résultat de l'installation
        """
        try:
            if not font_file_path.exists():
                return {'success': False, 'error': 'Fichier introuvable'}
            
            # Vérifier l'extension
            if font_file_path.suffix.lower() not in ['.ttf', '.otf']:
                return {'success': False, 'error': 'Format de police non supporté'}
            
            # Extraire les informations de la police
            font_info = self._extract_font_info(font_file_path, is_system=False)
            if not font_info:
                return {'success': False, 'error': 'Impossible de lire la police'}
            
            # Vérifier si elle existe déjà
            if font_info.name in self.custom_fonts:
                return {'success': False, 'error': 'Police déjà installée'}
            
            # Copier le fichier dans le répertoire des polices personnalisées
            destination = self.custom_fonts_dir / font_file_path.name
            
            # Éviter les conflits de noms
            counter = 1
            while destination.exists():
                name_part = font_file_path.stem
                ext_part = font_file_path.suffix
                destination = self.custom_fonts_dir / f"{name_part}_{counter}{ext_part}"
                counter += 1
            
            shutil.copy2(font_file_path, destination)
            
            # Mettre à jour les informations
            font_info.file_path = destination
            self.custom_fonts[font_info.name] = font_info
            
            self.logger.info(f"Police installée: {font_info.name}")
            
            return {
                'success': True,
                'font_name': font_info.name,
                'font_family': font_info.family,
                'destination': str(destination)
            }
            
        except Exception as e:
            self.logger.error(f"Erreur installation police: {e}")
            return {'success': False, 'error': str(e)}
    
    def create_font_mapping(self, original_font: str, replacement_font: str,
                          mapping_type: str = 'user_choice') -> bool:
        """
        Crée un mapping entre une police originale et son remplacement
        
        Args:
            original_font: Nom de la police originale
            replacement_font: Nom de la police de remplacement
            mapping_type: Type de mapping ('automatic', 'user_choice', 'fallback')
            
        Returns:
            True si le mapping a été créé
        """
        try:
            # Vérifier que la police de remplacement est disponible
            if not self._is_font_available(replacement_font):
                self.logger.warning(f"Police de remplacement non disponible: {replacement_font}")
                return False
            
            # Calculer un score de confiance
            confidence = self._calculate_mapping_confidence(original_font, replacement_font, mapping_type)
            
            # Créer le mapping
            mapping = FontMapping(
                original_font=original_font,
                replacement_font=replacement_font,
                mapping_type=mapping_type,
                confidence=confidence,
                created_at=datetime.now().isoformat()
            )
            
            self.font_mappings[original_font] = mapping
            self._save_font_mappings()
            
            self.logger.info(f"Mapping créé: {original_font} -> {replacement_font}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur création mapping: {e}")
            return False
    
    def _calculate_mapping_confidence(self, original: str, replacement: str, mapping_type: str) -> float:
        """Calcule la confiance d'un mapping de police"""
        base_confidence = {
            'user_choice': 0.9,
            'automatic': 0.7,
            'fallback': 0.5
        }.get(mapping_type, 0.5)
        
        # Ajuster selon la similarité
        similarity = self._calculate_name_similarity(original, replacement)
        confidence = base_confidence + (similarity * 0.1)
        
        return min(1.0, confidence)
    
    def get_font_mapping(self, original_font: str) -> Optional[str]:
        """
        Récupère le mapping d'une police
        
        Args:
            original_font: Nom de la police originale
            
        Returns:
            Nom de la police de remplacement ou None
        """
        if original_font in self.font_mappings:
            return self.font_mappings[original_font].replacement_font
        return None
    
    def _load_font_mappings(self):
        """Charge les mappings de polices depuis le fichier"""
        mappings_file = self.app_data_dir / "config" / "font_mappings.json"
        
        try:
            if mappings_file.exists():
                with open(mappings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for original_font, mapping_data in data.items():
                    if isinstance(mapping_data, str):
                        # Ancien format simple
                        mapping = FontMapping(
                            original_font=original_font,
                            replacement_font=mapping_data,
                            mapping_type='user_choice',
                            confidence=0.8,
                            created_at=datetime.now().isoformat()
                        )
                    else:
                        # Nouveau format complet
                        mapping = FontMapping(**mapping_data)
                    
                    self.font_mappings[original_font] = mapping
                
                self.logger.info(f"{len(self.font_mappings)} mappings de polices chargés")
                
        except Exception as e:
            self.logger.error(f"Erreur chargement mappings polices: {e}")
    
    def _save_font_mappings(self):
        """Sauvegarde les mappings de polices"""
        mappings_file = self.app_data_dir / "config" / "font_mappings.json"
        mappings_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Convertir en dictionnaire sérialisable
            data = {}
            for original_font, mapping in self.font_mappings.items():
                data[original_font] = {
                    'original_font': mapping.original_font,
                    'replacement_font': mapping.replacement_font,
                    'mapping_type': mapping.mapping_type,
                    'confidence': mapping.confidence,
                    'created_at': mapping.created_at
                }
            
            with open(mappings_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self.logger.error(f"Erreur sauvegarde mappings polices: {e}")
    
    def remove_font_mapping(self, original_font: str) -> bool:
        """Supprime un mapping de police"""
        if original_font in self.font_mappings:
            del self.font_mappings[original_font]
            self._save_font_mappings()
            self.logger.info(f"Mapping supprimé: {original_font}")
            return True
        return False
    
    def get_all_available_fonts(self) -> List[str]:
        """Retourne la liste de toutes les polices disponibles"""
        all_fonts = list(self.system_fonts.keys()) + list(self.custom_fonts.keys())
        return sorted(set(all_fonts))
    
    def get_font_info(self, font_name: str) -> Optional[FontInfo]:
        """Récupère les informations détaillées d'une police"""
        return self.system_fonts.get(font_name) or self.custom_fonts.get(font_name)
    
    def validate_font_licensing(self, font_names: List[str]) -> Dict[str, str]:
        """
        Valide les licences des polices pour usage commercial
        
        Args:
            font_names: Liste des noms de polices à vérifier
            
        Returns:
            Dictionnaire {font_name: license_status}
        """
        license_status = {}
        
        for font_name in font_names:
            font_info = self.get_font_info(font_name)
            
            if not font_info:
                license_status[font_name] = 'Police non trouvée'
            elif font_info.is_system_font:
                license_status[font_name] = 'Police système - Vérifier licence OS'
            elif 'free' in font_info.license_info.lower():
                license_status[font_name] = 'Licence libre'
            elif 'commercial' in font_info.license_info.lower():
                license_status[font_name] = 'Usage commercial possible'
            else:
                license_status[font_name] = 'Licence à vérifier'
        
        return license_status
    
    def export_font_report(self, required_fonts: List[str]) -> Dict[str, Any]:
        """
        Génère un rapport complet sur les polices
        
        Args:
            required_fonts: Liste des polices requises
            
        Returns:
            Rapport détaillé
        """
        availability = self.check_fonts_availability(required_fonts)
        licensing = self.validate_font_licensing(required_fonts)
        
        return {
            'summary': {
                'total_fonts': len(required_fonts),
                'available_fonts': availability['available_count'],
                'missing_fonts': availability['missing_count'],
                'mappings_available': len([f for f in availability['missing_fonts'] 
                                         if f in self.font_mappings])
            },
            'availability': availability,
            'licensing': licensing,
            'mappings': {font: mapping.replacement_font 
                        for font, mapping in self.font_mappings.items() 
                        if font in required_fonts},
            'recommendations': self._generate_font_recommendations(availability)
        }
    
    def _generate_font_recommendations(self, availability: Dict[str, Any]) -> List[str]:
        """Génère des recommandations basées sur la disponibilité des polices"""
        recommendations = []
        
        missing_count = availability['missing_count']
        total_count = availability['total_required']
        
        if missing_count == 0:
            recommendations.append("✅ Toutes les polices sont disponibles")
        elif missing_count < total_count * 0.3:
            recommendations.append("⚠️ Quelques polices manquantes - mappings recommandés")
        else:
            recommendations.append("❌ Beaucoup de polices manquantes - installation recommandée")
        
        # Recommandations spécifiques
        for font, suggestions in availability['suggestions'].items():
            if suggestions:
                best_suggestion = suggestions[0]
                recommendations.append(
                    f"💡 Pour '{font}': utiliser '{best_suggestion['font_name']}' "
                    f"({best_suggestion['reason']})"
                )
        
        return recommendations