#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Parseur de traductions
Parse et valide les traductions retournées par l'utilisateur

Auteur: L'OréalGPT
Version: 1.0.0
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class ValidationLevel(Enum):
    """Niveaux de validation"""
    STRICT = "strict"
    MODERATE = "moderate"
    PERMISSIVE = "permissive"

class ParseResult(Enum):
    """Résultats de parsing"""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"

@dataclass
class TranslationValidation:
    """Résultat de validation d'une traduction"""
    element_id: str
    is_valid: bool
    original_text: str
    translated_text: str
    expansion_factor: float
    issues: List[str]
    confidence: float

@dataclass
class ParseReport:
    """Rapport de parsing complet"""
    result: ParseResult
    total_elements: int
    parsed_elements: int
    missing_elements: List[str]
    extra_elements: List[str]
    invalid_elements: List[str]
    validations: List[TranslationValidation]
    overall_expansion_factor: float
    processing_time: float
    recommendations: List[str]

class TranslationParser:
    """Parseur de traductions retournées"""
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.MODERATE):
        """
        Initialise le parseur de traductions
        
        Args:
            validation_level: Niveau de validation à appliquer
        """
        self.logger = logging.getLogger(__name__)
        self.validation_level = validation_level
        
        # Pattern pour identifier les éléments traduits
        self.element_pattern = re.compile(
            r'\*\*\[ID:([^|]+)\|Page:(\d+)\|Type:([^\]]+)\]\*\*[^\n]*\n(.*?)(?=\n\*\*\[ID:|$)',
            re.DOTALL | re.MULTILINE
        )
        
        # Patterns de nettoyage
        self.cleanup_patterns = [
            (r'<!--.*?-->', ''),  # Supprimer les commentaires HTML
            (r'\n\s*\n\s*\n', '\n\n'),  # Normaliser les sauts de ligne multiples
            (r'^\s+|\s+$', ''),  # Espaces début/fin
        ]
        
        # Seuils de validation
        self.max_expansion_factor = 3.0  # Texte 3x plus long que l'original
        self.min_expansion_factor = 0.2  # Texte 5x plus court que l'original
        self.suspicious_expansion_threshold = 2.0  # Seuil d'alerte
        
        self.logger.info(f"TranslationParser initialisé (niveau: {validation_level.value})")
    
    def parse_translated_content(self, translated_content: str, 
                               original_extraction_data: Dict[str, Any]) -> ParseReport:
        """
        Parse le contenu traduit retourné par l'utilisateur
        
        Args:
            translated_content: Contenu traduit avec identifiants
            original_extraction_data: Données d'extraction originales
            
        Returns:
            Rapport de parsing complet
        """
        start_time = datetime.now()
        self.logger.info("Début du parsing des traductions")
        
        try:
            # Nettoyer le contenu d'entrée
            cleaned_content = self._clean_input_content(translated_content)
            
            # Extraire les éléments originaux
            original_elements = {
                elem['id']: elem for elem in original_extraction_data['translation_elements']
                if elem['is_translatable']
            }
            
            # Parser les éléments traduits
            parsed_translations = self._parse_elements(cleaned_content)
            
            # Valider les traductions
            validations = self._validate_translations(parsed_translations, original_elements)
            
            # Analyser les résultats
            analysis = self._analyze_results(validations, original_elements, parsed_translations)
            
            # Calculer les métriques
            metrics = self._calculate_metrics(validations)
            
            # Générer les recommandations
            recommendations = self._generate_recommendations(analysis, metrics)
            
            # Créer le rapport final
            processing_time = (datetime.now() - start_time).total_seconds()
            
            report = ParseReport(
                result=analysis['result'],
                total_elements=len(original_elements),
                parsed_elements=len(parsed_translations),
                missing_elements=analysis['missing_elements'],
                extra_elements=analysis['extra_elements'],
                invalid_elements=analysis['invalid_elements'],
                validations=validations,
                overall_expansion_factor=metrics['avg_expansion_factor'],
                processing_time=processing_time,
                recommendations=recommendations
            )
            
            self.logger.info(f"Parsing terminé: {report.result.value} "
                           f"({report.parsed_elements}/{report.total_elements} éléments)")
            
            return report
            
        except Exception as e:
            self.logger.error(f"Erreur lors du parsing: {e}")
            raise
    
    def _clean_input_content(self, content: str) -> str:
        """Nettoie le contenu d'entrée"""
        cleaned = content
        
        # Appliquer les patterns de nettoyage
        for pattern, replacement in self.cleanup_patterns:
            cleaned = re.sub(pattern, replacement, cleaned)
        
        return cleaned
    
    def _parse_elements(self, content: str) -> Dict[str, str]:
        """
        Parse les éléments traduits du contenu
        
        Args:
            content: Contenu traduit nettoyé
            
        Returns:
            Dictionnaire {element_id: translated_text}
        """
        parsed_elements = {}
        
        # Rechercher tous les éléments avec le pattern
        matches = self.element_pattern.findall(content)
        
        for match in matches:
            element_id, page_num, content_type, translated_text = match
            
            # Nettoyer le texte traduit
            cleaned_translation = self._clean_translated_text(translated_text)
            
            if cleaned_translation:
                parsed_elements[element_id] = cleaned_translation
                self.logger.debug(f"Élément parsé: {element_id}")
            else:
                self.logger.warning(f"Traduction vide pour {element_id}")
        
        # Fallback: essayer un parsing plus permissif si peu d'éléments trouvés
        if len(parsed_elements) < 5:
            backup_elements = self._permissive_parse(content)
            if len(backup_elements) > len(parsed_elements):
                self.logger.info("Utilisation du parsing permissif")
                parsed_elements = backup_elements
        
        return parsed_elements
    
    def _clean_translated_text(self, text: str) -> str:
        """Nettoie le texte traduit"""
        # Supprimer les sauts de ligne excessifs
        cleaned = re.sub(r'\n+', ' ', text).strip()
        
        # Supprimer les espaces multiples
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        return cleaned
    
    def _permissive_parse(self, content: str) -> Dict[str, str]:
        """
        Parsing plus permissif pour gérer les variations de format
        
        Args:
            content: Contenu à parser
            
        Returns:
            Dictionnaire des éléments parsés
        """
        elements = {}
        
        # Pattern plus flexible
        flexible_pattern = re.compile(
            r'(?:\*\*)?(?:\[)?ID:([^|\]]+)(?:\|[^\]]*)?(?:\])?(?:\*\*)?[^\n]*\n(.*?)(?=(?:\*\*)?(?:\[)?ID:|$)',
            re.DOTALL | re.MULTILINE
        )
        
        matches = flexible_pattern.findall(content)
        
        for element_id, translated_text in matches:
            cleaned_id = element_id.strip()
            cleaned_text = self._clean_translated_text(translated_text)
            
            if cleaned_text:
                elements[cleaned_id] = cleaned_text
        
        return elements
    
    def _validate_translations(self, parsed_translations: Dict[str, str],
                             original_elements: Dict[str, Dict[str, Any]]) -> List[TranslationValidation]:
        """
        Valide les traductions parsées
        
        Args:
            parsed_translations: Traductions parsées
            original_elements: Éléments originaux
            
        Returns:
            Liste des validations
        """
        validations = []
        
        for element_id, original_data in original_elements.items():
            original_text = original_data['original_text']
            translated_text = parsed_translations.get(element_id, '')
            
            validation = self._validate_single_translation(
                element_id, original_text, translated_text, original_data
            )
            
            validations.append(validation)
        
        return validations
    
    def _validate_single_translation(self, element_id: str, original_text: str,
                                   translated_text: str, original_data: Dict[str, Any]) -> TranslationValidation:
        """
        Valide une traduction individuelle
        
        Args:
            element_id: ID de l'élément
            original_text: Texte original
            translated_text: Texte traduit
            original_data: Données originales de l'élément
            
        Returns:
            Validation de la traduction
        """
        issues = []
        is_valid = True
        confidence = 1.0
        
        # Vérifier si la traduction existe
        if not translated_text:
            issues.append("Traduction manquante")
            is_valid = False
            confidence = 0.0
        else:
            # Calculer le facteur d'expansion
            expansion_factor = len(translated_text) / max(1, len(original_text))
            
            # Vérifications selon le niveau de validation
            if self.validation_level == ValidationLevel.STRICT:
                is_valid, validation_issues = self._strict_validation(
                    original_text, translated_text, expansion_factor, original_data
                )
                issues.extend(validation_issues)
            elif self.validation_level == ValidationLevel.MODERATE:
                is_valid, validation_issues = self._moderate_validation(
                    original_text, translated_text, expansion_factor, original_data
                )
                issues.extend(validation_issues)
            else:  # PERMISSIVE
                is_valid, validation_issues = self._permissive_validation(
                    original_text, translated_text, expansion_factor
                )
                issues.extend(validation_issues)
            
            # Ajuster la confiance selon les problèmes
            confidence = max(0.1, 1.0 - (len(issues) * 0.2))
        
        return TranslationValidation(
            element_id=element_id,
            is_valid=is_valid,
            original_text=original_text,
            translated_text=translated_text,
            expansion_factor=len(translated_text) / max(1, len(original_text)),
            issues=issues,
            confidence=confidence
        )
    
    def _strict_validation(self, original: str, translated: str, expansion_factor: float,
                          original_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validation stricte"""
        issues = []
        is_valid = True
        
        # Vérifier le facteur d'expansion
        if expansion_factor > self.max_expansion_factor:
            issues.append(f"Expansion excessive: {expansion_factor:.2f}x")
            is_valid = False
        elif expansion_factor < self.min_expansion_factor:
            issues.append(f"Contraction excessive: {expansion_factor:.2f}x")
            is_valid = False
        
        # Vérifier la préservation de la structure pour les listes
        if original_data['content_type'] == 'list_item':
            if not self._preserves_list_structure(original, translated):
                issues.append("Structure de liste non préservée")
                is_valid = False
        
        # Vérifier la longueur pour les titres
        if original_data['content_type'] in ['title', 'subtitle']:
            if len(translated.split()) > len(original.split()) * 2:
                issues.append("Titre trop long après traduction")
                is_valid = False
        
        return is_valid, issues
    
    def _moderate_validation(self, original: str, translated: str, expansion_factor: float,
                           original_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validation modérée"""
        issues = []
        is_valid = True
        
        # Vérifications plus souples
        if expansion_factor > self.max_expansion_factor * 1.5:
            issues.append(f"Expansion très importante: {expansion_factor:.2f}x")
            is_valid = False
        elif expansion_factor < self.min_expansion_factor * 0.5:
            issues.append(f"Contraction très importante: {expansion_factor:.2f}x")
            is_valid = False
        elif expansion_factor > self.suspicious_expansion_threshold:
            issues.append(f"Expansion élevée: {expansion_factor:.2f}x")
        
        # Vérifier la cohérence de base
        if len(translated.strip()) < 2:
            issues.append("Traduction trop courte")
            is_valid = False
        
        return is_valid, issues
    
    def _permissive_validation(self, original: str, translated: str, 
                             expansion_factor: float) -> Tuple[bool, List[str]]:
        """Validation permissive"""
        issues = []
        is_valid = True
        
        # Vérifications minimales
        if not translated.strip():
            issues.append("Traduction vide")
            is_valid = False
        elif expansion_factor > 5.0:
            issues.append(f"Expansion extrême: {expansion_factor:.2f}x")
        elif expansion_factor < 0.1:
            issues.append(f"Contraction extrême: {expansion_factor:.2f}x")
        
        return is_valid, issues
    
    def _preserves_list_structure(self, original: str, translated: str) -> bool:
        """Vérifie si la structure de liste est préservée"""
        original_has_bullet = bool(re.search(r'^[\s]*[•·‣⁃\-\*\+]', original.strip()))
        translated_has_bullet = bool(re.search(r'^[\s]*[•·‣⁃\-\*\+]', translated.strip()))
        
        return original_has_bullet == translated_has_bullet
    
    def _analyze_results(self, validations: List[TranslationValidation],
                        original_elements: Dict[str, Dict[str, Any]],
                        parsed_translations: Dict[str, str]) -> Dict[str, Any]:
        """Analyse les résultats de validation"""
        
        original_ids = set(original_elements.keys())
        parsed_ids = set(parsed_translations.keys())
        
        missing_elements = list(original_ids - parsed_ids)
        extra_elements = list(parsed_ids - original_ids)
        
        invalid_elements = [
            v.element_id for v in validations 
            if not v.is_valid and v.element_id in parsed_ids
        ]
        
        valid_count = sum(1 for v in validations if v.is_valid)
        total_count = len(original_elements)
        
        # Déterminer le résultat global
        if valid_count == total_count and not missing_elements:
            result = ParseResult.SUCCESS
        elif valid_count >= total_count * 0.8:  # 80% de réussite
            result = ParseResult.PARTIAL
        else:
            result = ParseResult.FAILED
        
        return {
            'result': result,
            'missing_elements': missing_elements,
            'extra_elements': extra_elements,
            'invalid_elements': invalid_elements,
            'valid_count': valid_count,
            'total_count': total_count,
            'success_rate': valid_count / max(1, total_count)
        }
    
    def _calculate_metrics(self, validations: List[TranslationValidation]) -> Dict[str, float]:
        """Calcule les métriques de traduction"""
        valid_validations = [v for v in validations if v.translated_text]
        
        if not valid_validations:
            return {
                'avg_expansion_factor': 1.0,
                'min_expansion_factor': 1.0,
                'max_expansion_factor': 1.0,
                'avg_confidence': 0.0
            }
        
        expansion_factors = [v.expansion_factor for v in valid_validations]
        confidences = [v.confidence for v in validations]
        
        return {
            'avg_expansion_factor': sum(expansion_factors) / len(expansion_factors),
            'min_expansion_factor': min(expansion_factors),
            'max_expansion_factor': max(expansion_factors),
            'avg_confidence': sum(confidences) / len(confidences)
        }
    
    def _generate_recommendations(self, analysis: Dict[str, Any], 
                                metrics: Dict[str, float]) -> List[str]:
        """Génère des recommandations basées sur l'analyse"""
        recommendations = []
        
        # Recommandations basées sur le taux de réussite
        if analysis['success_rate'] < 0.5:
            recommendations.append(
                "❌ Taux de réussite faible. Vérifiez que l'IA a bien conservé tous les identifiants."
            )
        elif analysis['success_rate'] < 0.8:
            recommendations.append(
                "⚠️ Quelques éléments manquants ou invalides. Vérification recommandée."
            )
        else:
            recommendations.append(
                "✅ Bonne qualité de traduction. Vous pouvez procéder à l'étape suivante."
            )
        
        # Recommandations sur l'expansion
        if metrics['avg_expansion_factor'] > 1.5:
            recommendations.append(
                f"📏 Expansion moyenne importante ({metrics['avg_expansion_factor']:.1f}x). "
                "La mise en page pourrait nécessiter des ajustements."
            )
        elif metrics['avg_expansion_factor'] < 0.7:
            recommendations.append(
                f"📏 Contraction moyenne ({metrics['avg_expansion_factor']:.1f}x). "
                "Vérifiez que les traductions sont complètes."
            )
        
        # Recommandations sur les éléments manquants
        if analysis['missing_elements']:
            count = len(analysis['missing_elements'])
            recommendations.append(
                f"🔍 {count} élément(s) manquant(s). Demandez à l'IA de reprendre ces éléments."
            )
        
        # Recommandations sur les éléments extra
        if analysis['extra_elements']:
            count = len(analysis['extra_elements'])
            recommendations.append(
                f"➕ {count} élément(s) supplémentaire(s) détecté(s). Vérifiez les identifiants."
            )
        
        return recommendations
    
    def get_missing_elements_prompt(self, report: ParseReport,
                                  original_extraction_data: Dict[str, Any]) -> str:
        """
        Génère un prompt pour récupérer les éléments manquants
        
        Args:
            report: Rapport de parsing
            original_extraction_data: Données d'extraction originales
            
        Returns:
            Prompt pour récupérer les éléments manquants
        """
        if not report.missing_elements:
            return ""
        
        # Récupérer les éléments manquants
        original_elements = {
            elem['id']: elem for elem in original_extraction_data['translation_elements']
        }
        
        missing_texts = []
        for element_id in report.missing_elements:
            if element_id in original_elements:
                elem = original_elements[element_id]
                missing_texts.append(
                    f"**[ID:{elem['id']}|Page:{elem['page_number']}|Type:{elem['content_type'].title()}]**\n"
                    f"{elem['original_text']}"
                )
        
        prompt = f"""Il manque {len(report.missing_elements)} élément(s) dans votre traduction. 

Veuillez traduire ces éléments manquants en conservant exactement les identifiants :

{chr(10).join(missing_texts)}

Répondez uniquement avec les traductions de ces éléments manquants, en conservant le format exact des identifiants.
"""
        
        return prompt
    
    def merge_translations(self, original_translations: Dict[str, str],
                         additional_translations: str) -> Dict[str, str]:
        """
        Fusionne des traductions supplémentaires avec les originales
        
        Args:
            original_translations: Traductions déjà parsées
            additional_translations: Traductions supplémentaires à ajouter
            
        Returns:
            Traductions fusionnées
        """
        additional_parsed = self._parse_elements(additional_translations)
        
        merged = original_translations.copy()
        merged.update(additional_parsed)
        
        self.logger.info(f"Fusion: {len(additional_parsed)} nouveaux éléments ajoutés")
        
        return merged
    
    def export_validated_translations(self, report: ParseReport) -> Dict[str, Any]:
        """
        Exporte les traductions validées pour la phase suivante
        
        Args:
            report: Rapport de parsing
            
        Returns:
            Données de traduction validées
        """
        validated_translations = {}
        
        for validation in report.validations:
            if validation.is_valid and validation.translated_text:
                validated_translations[validation.element_id] = {
                    'original_text': validation.original_text,
                    'translated_text': validation.translated_text,
                    'expansion_factor': validation.expansion_factor,
                    'confidence': validation.confidence
                }
        
        return {
            'translations': validated_translations,
            'statistics': {
                'total_elements': report.total_elements,
                'translated_elements': len(validated_translations),
                'overall_expansion_factor': report.overall_expansion_factor,
                'processing_timestamp': datetime.now().isoformat()
            },
            'quality_metrics': {
                'success_rate': len(validated_translations) / max(1, report.total_elements),
                'avg_confidence': sum(v['confidence'] for v in validated_translations.values()) / max(1, len(validated_translations))
            }
        }