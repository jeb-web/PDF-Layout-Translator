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
from typing import Dict, List, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class ValidationLevel(Enum):
    STRICT = "strict"
    MODERATE = "moderate"
    PERMISSIVE = "permissive"

class ParseResult(Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"

@dataclass
class TranslationValidation:
    element_id: str
    is_valid: bool
    original_text: str
    translated_text: str
    expansion_factor: float
    issues: List[str]
    confidence: float

@dataclass
class ParseReport:
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
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.MODERATE):
        self.logger = logging.getLogger(__name__)
        self.validation_level = validation_level
        
        # --- FIX: Regex corrigé pour capturer correctement le texte après l'identifiant ---
        self.element_pattern = re.compile(
            r'\*\*\[ID:([^|]+)\|Page:(\d+)\|Type:([^\]]+)\]\*\*(.*?)(?=\s*\*\*\[ID:|$)',
            re.DOTALL
        )
        
        self.max_expansion_factor = 3.0
        self.min_expansion_factor = 0.2
        
        self.logger.info(f"TranslationParser initialisé (niveau: {validation_level.value})")
    
    def parse_translated_content(self, translated_content: str, 
                               original_extraction_data: Dict[str, Any]) -> ParseReport:
        start_time = datetime.now()
        
        original_elements = {
            elem['id']: elem for elem in original_extraction_data.get('translation_elements', [])
            if elem.get('is_translatable', True)
        }
        
        parsed_translations = self._parse_elements(translated_content)
        validations = self._validate_translations(parsed_translations, original_elements)
        analysis = self._analyze_results(validations, original_elements, parsed_translations)
        metrics = self._calculate_metrics(validations)
        recommendations = self._generate_recommendations(analysis)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return ParseReport(
            result=analysis['result'],
            total_elements=len(original_elements),
            parsed_elements=len(parsed_translations),
            missing_elements=analysis['missing_elements'],
            extra_elements=analysis['extra_elements'],
            invalid_elements=analysis['invalid_elements'],
            validations=validations,
            overall_expansion_factor=metrics.get('avg_expansion_factor', 1.0),
            processing_time=processing_time,
            recommendations=recommendations
        )
    
    def _parse_elements(self, content: str) -> Dict[str, str]:
        parsed_elements = {}
        matches = self.element_pattern.findall(content)
        
        for match in matches:
            element_id, _, _, raw_text = match
            cleaned_text = self._clean_translated_text(raw_text)
            parsed_elements[element_id] = cleaned_text
        
        return parsed_elements
    
    def _clean_translated_text(self, text: str) -> str:
        # Cette fonction est cruciale pour enlever les sauts de ligne et espaces
        # avant et après le texte capturé.
        return re.sub(r'\s+', ' ', text).strip()
    
    def _validate_translations(self, parsed_translations: Dict[str, str],
                             original_elements: Dict[str, Dict[str, Any]]) -> List[TranslationValidation]:
        validations = []
        for element_id, original_data in original_elements.items():
            original_text = original_data.get('original_text', '')
            translated_text = parsed_translations.get(element_id, '')
            validations.append(self._validate_single_translation(element_id, original_text, translated_text))
        return validations
    
    def _validate_single_translation(self, element_id: str, original_text: str, translated_text: str) -> TranslationValidation:
        issues = []
        is_valid = True
        
        if not translated_text:
            issues.append("Traduction manquante")
            is_valid = False
            expansion_factor = 0.0
        else:
            expansion_factor = len(translated_text) / max(1, len(original_text))
            if self.validation_level == ValidationLevel.MODERATE:
                if expansion_factor > (self.max_expansion_factor * 2) or expansion_factor < (self.min_expansion_factor / 2):
                    issues.append("Facteur d'expansion extrême")
                    is_valid = False # Une expansion trop extrême est une erreur
            elif self.validation_level == ValidationLevel.STRICT:
                if expansion_factor > self.max_expansion_factor or expansion_factor < self.min_expansion_factor:
                    issues.append("Facteur d'expansion hors limites strictes")
                    is_valid = False

        return TranslationValidation(
            element_id=element_id,
            is_valid=is_valid,
            original_text=original_text,
            translated_text=translated_text,
            expansion_factor=expansion_factor,
            issues=issues,
            confidence=1.0 if is_valid else 0.2
        )
    
    def _analyze_results(self, validations: List[TranslationValidation],
                        original_elements: Dict[str, Dict[str, Any]],
                        parsed_translations: Dict[str, str]) -> Dict[str, Any]:
        
        original_ids = set(original_elements.keys())
        parsed_ids = set(parsed_translations.keys())
        
        missing_elements = list(original_ids - parsed_ids)
        extra_elements = list(parsed_ids - original_ids)
        invalid_elements = [v.element_id for v in validations if not v.is_valid and v.element_id in parsed_ids]
        
        valid_count = sum(1 for v in validations if v.is_valid)
        total_count = len(original_elements)
        
        if valid_count > 0 and not missing_elements and len(invalid_elements) < (total_count * 0.1):
             result = ParseResult.SUCCESS
        elif valid_count > 0:
             result = ParseResult.PARTIAL
        else:
             result = ParseResult.FAILED
        
        return {
            'result': result,
            'missing_elements': missing_elements,
            'extra_elements': extra_elements,
            'invalid_elements': invalid_elements
        }
    
    def _calculate_metrics(self, validations: List[TranslationValidation]) -> Dict[str, float]:
        factors = [v.expansion_factor for v in validations if v.translated_text]
        if not factors:
            return {'avg_expansion_factor': 1.0}
        return {'avg_expansion_factor': sum(factors) / len(factors)}
    
    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        recs = []
        if analysis['result'] == ParseResult.FAILED:
            recs.append("❌ Échec critique. Vérifiez le format du texte collé.")
        if analysis['missing_elements']:
            recs.append(f"🔍 {len(analysis['missing_elements'])} élément(s) manquant(s).")
        if analysis['invalid_elements']:
            recs.append(f"⚠️ {len(analysis['invalid_elements'])} traduction(s) invalide(s).")
        return recs

    def export_validated_translations(self, report: ParseReport) -> Dict[str, Any]:
        validated = {}
        for validation in report.validations:
            if validation.is_valid and validation.translated_text:
                validated[validation.element_id] = {
                    'original_text': validation.original_text,
                    'translated_text': validation.translated_text,
                    'expansion_factor': validation.expansion_factor,
                    'confidence': validation.confidence
                }
        return {
            'translations': validated,
            'statistics': {
                'total_elements': report.total_elements,
                'translated_elements': len(validated),
                'overall_expansion_factor': report.overall_expansion_factor
            }
        }
