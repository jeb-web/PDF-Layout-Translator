#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Processeur de mise en page
Gestion des ajustements de mise en page pour le texte traduit

Auteur: L'OréalGPT
Version: 1.0.0
"""

import logging
import math
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

class LayoutIssueType(Enum):
    """Types de problèmes de mise en page"""
    OVERFLOW_HORIZONTAL = "overflow_horizontal"
    OVERFLOW_VERTICAL = "overflow_vertical"
    UNDERFLOW = "underflow"
    FONT_TOO_SMALL = "font_too_small"
    ELEMENT_COLLISION = "element_collision"
    MARGIN_VIOLATION = "margin_violation"
    ASPECT_RATIO_CHANGED = "aspect_ratio_changed"

class SolutionType(Enum):
    """Types de solutions de mise en page"""
    REDUCE_FONT_SIZE = "reduce_font_size"
    EXPAND_CONTAINER = "expand_container"
    MOVE_ELEMENTS = "move_elements"
    SPLIT_TEXT = "split_text"
    ADJUST_LINE_SPACING = "adjust_line_spacing"
    ADJUST_MARGINS = "adjust_margins"
    REFLOW_TEXT = "reflow_text"
    USE_ALTERNATIVE_FONT = "use_alternative_font"

@dataclass
class LayoutConstraints:
    """Contraintes de mise en page pour un élément"""
    min_font_size: float = 8.0
    max_font_size: float = 72.0
    min_line_height: float = 1.0
    max_line_height: float = 2.0
    preserve_aspect_ratio: bool = True
    allow_font_reduction: bool = True
    allow_container_expansion: bool = False
    max_font_reduction_percent: float = 20.0
    max_container_expansion_percent: float = 50.0
    min_margin: float = 5.0

@dataclass
class ElementLayout:
    """Layout d'un élément après traduction"""
    element_id: str
    original_bbox: Tuple[float, float, float, float]  # x0, y0, x1, y1
    new_bbox: Tuple[float, float, float, float]
    original_font_size: float
    new_font_size: float
    original_text: str
    translated_text: str
    expansion_factor: float
    layout_constraints: LayoutConstraints
    issues: List['LayoutIssue'] = field(default_factory=list)
    solutions: List['LayoutSolution'] = field(default_factory=list)

@dataclass
class LayoutIssue:
    """Problème de mise en page identifié"""
    issue_type: LayoutIssueType
    severity: float  # 0.0 à 1.0
    description: str
    affected_elements: List[str]
    overflow_amount: Optional[float] = None

@dataclass
class LayoutSolution:
    """Solution proposée pour un problème de mise en page"""
    solution_type: SolutionType
    confidence: float  # 0.0 à 1.0
    description: str
    parameters: Dict[str, Any]
    affected_elements: List[str]
    estimated_quality_impact: float  # 0.0 à 1.0 (0 = pas d'impact)

class LayoutProcessor:
    """Processeur de mise en page pour texte traduit"""
    
    def __init__(self, config_manager=None):
        """
        Initialise le processeur de mise en page
        
        Args:
            config_manager: Gestionnaire de configuration (optionnel)
        """
        self.logger = logging.getLogger(__name__)
        
        # Configuration par défaut
        self.default_constraints = LayoutConstraints()
        
        # Configuration depuis le gestionnaire si disponible
        if config_manager:
            self.default_constraints.allow_font_reduction = config_manager.get(
                'layout.prefer_font_size_reduction', True
            )
            self.default_constraints.max_font_reduction_percent = config_manager.get(
                'layout.max_font_size_reduction', 20.0
            )
            self.default_constraints.allow_container_expansion = config_manager.get(
                'layout.auto_expand_containers', False
            )
            self.default_constraints.min_margin = config_manager.get(
                'layout.min_margin', 5.0
            )
        
        # Facteurs de conversion pour estimation de taille de texte
        self.char_width_factor = 0.6  # Largeur moyenne d'un caractère par rapport à la taille de police
        self.line_height_factor = 1.2  # Hauteur de ligne par défaut
        
        # Seuils de qualité
        self.quality_thresholds = {
            'excellent': 0.95,
            'good': 0.85,
            'acceptable': 0.70,
            'poor': 0.50
        }
        
        self.logger.info("LayoutProcessor initialisé")
    
    def process_layout(self, validated_translations: Dict[str, Any],
                      original_extraction_data: Dict[str, Any],
                      font_mappings: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Traite la mise en page pour les traductions validées
        
        Args:
            validated_translations: Traductions validées
            original_extraction_data: Données d'extraction originales
            font_mappings: Mappings de polices (optionnel)
            
        Returns:
            Résultats du traitement de mise en page
        """
        self.logger.info("Début du traitement de mise en page")
        
        try:
            # Créer les layouts d'éléments
            element_layouts = self._create_element_layouts(
                validated_translations, original_extraction_data, font_mappings
            )
            
            # Détecter les problèmes de mise en page
            layout_issues = self._detect_layout_issues(element_layouts)
            
            # Générer des solutions
            solutions = self._generate_solutions(element_layouts, layout_issues)
            
            # Optimiser la mise en page globale
            optimized_layout = self._optimize_global_layout(element_layouts, solutions)
            
            # Calculer les métriques de qualité
            quality_metrics = self._calculate_quality_metrics(optimized_layout)
            
            # Créer le rapport final
            layout_result = {
                'element_layouts': self._serialize_layouts(optimized_layout),
                'layout_issues': self._serialize_issues(layout_issues),
                'applied_solutions': self._serialize_solutions(solutions),
                'quality_metrics': quality_metrics,
                'recommendations': self._generate_recommendations(quality_metrics, layout_issues),
                'processing_timestamp': datetime.now().isoformat(),
                'layout_changes_summary': self._create_changes_summary(element_layouts, optimized_layout)
            }
            
            self.logger.info(f"Traitement terminé: {len(element_layouts)} éléments traités")
            return layout_result
            
        except Exception as e:
            self.logger.error(f"Erreur lors du traitement de mise en page: {e}")
            raise
    
    def _create_element_layouts(self, validated_translations: Dict[str, Any],
                              original_extraction_data: Dict[str, Any],
                              font_mappings: Dict[str, str] = None) -> List[ElementLayout]:
        """Crée les layouts d'éléments avec les nouvelles dimensions"""
        element_layouts = []
        translations = validated_translations['translations']
        
        # Récupérer les éléments originaux
        original_elements = {
            elem['id']: elem for elem in original_extraction_data['translation_elements']
        }
        
        for element_id, translation_data in translations.items():
            if element_id not in original_elements:
                continue
            
            original_element = original_elements[element_id]
            
            # Créer le layout d'élément
            element_layout = self._create_single_element_layout(
                element_id, original_element, translation_data, font_mappings
            )
            
            element_layouts.append(element_layout)
        
        return element_layouts
    
    def _create_single_element_layout(self, element_id: str, original_element: Dict[str, Any],
                                    translation_data: Dict[str, Any],
                                    font_mappings: Dict[str, str] = None) -> ElementLayout:
        """Crée le layout pour un élément individuel"""
        
        # Informations originales
        original_text = translation_data['original_text']
        translated_text = translation_data['translated_text']
        original_bbox = tuple(original_element['position_info']['bbox'])
        original_font_info = original_element['font_info']
        original_font_size = original_font_info['size']
        
        # Calculer le facteur d'expansion
        expansion_factor = translation_data['expansion_factor']
        
        # Déterminer les contraintes selon le type de contenu
        constraints = self._get_constraints_for_content_type(original_element['content_type'])
        
        # Calculer les nouvelles dimensions nécessaires
        new_dimensions = self._calculate_new_dimensions(
            original_text, translated_text, original_bbox, original_font_size, constraints
        )
        
        # Déterminer la nouvelle taille de police
        new_font_size = self._calculate_optimal_font_size(
            translated_text, original_bbox, original_font_size, constraints
        )
        
        # Créer le layout d'élément
        element_layout = ElementLayout(
            element_id=element_id,
            original_bbox=original_bbox,
            new_bbox=new_dimensions,
            original_font_size=original_font_size,
            new_font_size=new_font_size,
            original_text=original_text,
            translated_text=translated_text,
            expansion_factor=expansion_factor,
            layout_constraints=constraints
        )
        
        return element_layout
    
    def _get_constraints_for_content_type(self, content_type: str) -> LayoutConstraints:
        """Détermine les contraintes selon le type de contenu"""
        constraints = LayoutConstraints()
        
        # Ajustements selon le type
        if content_type == 'title':
            constraints.min_font_size = 14.0
            constraints.max_font_reduction_percent = 15.0
            constraints.preserve_aspect_ratio = True
            constraints.allow_container_expansion = False
        elif content_type == 'subtitle':
            constraints.min_font_size = 12.0
            constraints.max_font_reduction_percent = 20.0
            constraints.allow_container_expansion = True
            constraints.max_container_expansion_percent = 30.0
        elif content_type == 'paragraph':
            constraints.min_font_size = 8.0
            constraints.max_font_reduction_percent = 25.0
            constraints.allow_container_expansion = True
            constraints.max_container_expansion_percent = 50.0
        elif content_type == 'list_item':
            constraints.min_font_size = 8.0
            constraints.preserve_aspect_ratio = False
            constraints.allow_container_expansion = True
        elif content_type == 'caption':
            constraints.min_font_size = 6.0
            constraints.max_font_reduction_percent = 30.0
            constraints.allow_container_expansion = True
        
        return constraints
    
    def _calculate_new_dimensions(self, original_text: str, translated_text: str,
                                original_bbox: Tuple[float, float, float, float],
                                font_size: float, constraints: LayoutConstraints) -> Tuple[float, float, float, float]:
        """Calcule les nouvelles dimensions nécessaires"""
        
        x0, y0, x1, y1 = original_bbox
        original_width = x1 - x0
        original_height = y1 - y0
        
        # Estimation de la largeur nécessaire
        char_count_original = len(original_text)
        char_count_translated = len(translated_text)
        
        if char_count_original > 0:
            width_factor = char_count_translated / char_count_original
        else:
            width_factor = 1.0
        
        # Calculer nouvelle largeur en tenant compte du facteur de largeur des caractères
        estimated_char_width = font_size * self.char_width_factor
        estimated_width = char_count_translated * estimated_char_width
        
        # Ajuster selon l'espace disponible
        if estimated_width > original_width:
            # Texte plus large - peut nécessiter plusieurs lignes
            lines_needed = math.ceil(estimated_width / original_width)
            new_width = min(estimated_width, original_width)
            new_height = original_height * lines_needed
        else:
            # Texte plus court
            new_width = estimated_width
            new_height = original_height
        
        # Appliquer les contraintes
        if not constraints.allow_container_expansion:
            new_width = min(new_width, original_width)
            new_height = min(new_height, original_height)
        else:
            max_expansion = 1 + (constraints.max_container_expansion_percent / 100)
            new_width = min(new_width, original_width * max_expansion)
            new_height = min(new_height, original_height * max_expansion)
        
        # Retourner la nouvelle bbox
        return (x0, y0, x0 + new_width, y0 + new_height)
    
    def _calculate_optimal_font_size(self, text: str, bbox: Tuple[float, float, float, float],
                                   original_font_size: float, constraints: LayoutConstraints) -> float:
        """Calcule la taille de police optimale"""
        
        x0, y0, x1, y1 = bbox
        available_width = x1 - x0
        available_height = y1 - y0
        
        # Estimation de la largeur du texte avec la police originale
        estimated_width = len(text) * original_font_size * self.char_width_factor
        
        # Si le texte déborde horizontalement
        if estimated_width > available_width:
            # Calculer la réduction nécessaire
            reduction_factor = available_width / estimated_width
            new_font_size = original_font_size * reduction_factor
        else:
            new_font_size = original_font_size
        
        # Appliquer les contraintes
        max_reduction_factor = 1 - (constraints.max_font_reduction_percent / 100)
        min_allowed_size = original_font_size * max_reduction_factor
        min_allowed_size = max(min_allowed_size, constraints.min_font_size)
        
        new_font_size = max(new_font_size, min_allowed_size)
        new_font_size = min(new_font_size, constraints.max_font_size)
        
        return new_font_size
    
    def _detect_layout_issues(self, element_layouts: List[ElementLayout]) -> List[LayoutIssue]:
        """Détecte les problèmes de mise en page"""
        issues = []
        
        for layout in element_layouts:
            # Vérifier les débordements
            overflow_issues = self._detect_overflow_issues(layout)
            issues.extend(overflow_issues)
            
            # Vérifier les problèmes de police
            font_issues = self._detect_font_issues(layout)
            issues.extend(font_issues)
        
        # Vérifier les collisions entre éléments
        collision_issues = self._detect_element_collisions(element_layouts)
        issues.extend(collision_issues)
        
        return issues
    
    def _detect_overflow_issues(self, layout: ElementLayout) -> List[LayoutIssue]:
        """Détecte les problèmes de débordement pour un élément"""
        issues = []
        
        orig_x0, orig_y0, orig_x1, orig_y1 = layout.original_bbox
        new_x0, new_y0, new_x1, new_y1 = layout.new_bbox
        
        # Débordement horizontal
        if new_x1 > orig_x1:
            overflow_amount = new_x1 - orig_x1
            severity = min(1.0, overflow_amount / (orig_x1 - orig_x0))
            
            issues.append(LayoutIssue(
                issue_type=LayoutIssueType.OVERFLOW_HORIZONTAL,
                severity=severity,
                description=f"Débordement horizontal de {overflow_amount:.1f}px",
                affected_elements=[layout.element_id],
                overflow_amount=overflow_amount
            ))
        
        # Débordement vertical
        if new_y1 > orig_y1:
            overflow_amount = new_y1 - orig_y1
            severity = min(1.0, overflow_amount / (orig_y1 - orig_y0))
            
            issues.append(LayoutIssue(
                issue_type=LayoutIssueType.OVERFLOW_VERTICAL,
                severity=severity,
                description=f"Débordement vertical de {overflow_amount:.1f}px",
                affected_elements=[layout.element_id],
                overflow_amount=overflow_amount
            ))
        
        return issues
    
    def _detect_font_issues(self, layout: ElementLayout) -> List[LayoutIssue]:
        """Détecte les problèmes liés à la police"""
        issues = []
        
        # Police trop petite
        if layout.new_font_size < layout.layout_constraints.min_font_size:
            severity = 1.0 - (layout.new_font_size / layout.layout_constraints.min_font_size)
            
            issues.append(LayoutIssue(
                issue_type=LayoutIssueType.FONT_TOO_SMALL,
                severity=severity,
                description=f"Police trop petite: {layout.new_font_size:.1f}pt (min: {layout.layout_constraints.min_font_size}pt)",
                affected_elements=[layout.element_id]
            ))
        
        return issues
    
    def _detect_element_collisions(self, element_layouts: List[ElementLayout]) -> List[LayoutIssue]:
        """Détecte les collisions entre éléments"""
        issues = []
        
        for i, layout1 in enumerate(element_layouts):
            for layout2 in element_layouts[i+1:]:
                if self._bboxes_overlap(layout1.new_bbox, layout2.new_bbox):
                    overlap_area = self._calculate_overlap_area(layout1.new_bbox, layout2.new_bbox)
                    
                    # Calculer la sévérité basée sur l'aire de chevauchement
                    area1 = self._calculate_bbox_area(layout1.new_bbox)
                    area2 = self._calculate_bbox_area(layout2.new_bbox)
                    min_area = min(area1, area2)
                    severity = overlap_area / min_area if min_area > 0 else 1.0
                    
                    issues.append(LayoutIssue(
                        issue_type=LayoutIssueType.ELEMENT_COLLISION,
                        severity=min(1.0, severity),
                        description=f"Collision entre éléments (aire: {overlap_area:.1f}px²)",
                        affected_elements=[layout1.element_id, layout2.element_id]
                    ))
        
        return issues
    
    def _bboxes_overlap(self, bbox1: Tuple[float, float, float, float],
                       bbox2: Tuple[float, float, float, float]) -> bool:
        """Vérifie si deux bounding boxes se chevauchent"""
        x1_0, y1_0, x1_1, y1_1 = bbox1
        x2_0, y2_0, x2_1, y2_1 = bbox2
        
        return not (x1_1 <= x2_0 or x2_1 <= x1_0 or y1_1 <= y2_0 or y2_1 <= y1_0)
    
    def _calculate_overlap_area(self, bbox1: Tuple[float, float, float, float],
                              bbox2: Tuple[float, float, float, float]) -> float:
        """Calcule l'aire de chevauchement entre deux bounding boxes"""
        x1_0, y1_0, x1_1, y1_1 = bbox1
        x2_0, y2_0, x2_1, y2_1 = bbox2
        
        overlap_x0 = max(x1_0, x2_0)
        overlap_y0 = max(y1_0, y2_0)
        overlap_x1 = min(x1_1, x2_1)
        overlap_y1 = min(y1_1, y2_1)
        
        if overlap_x1 <= overlap_x0 or overlap_y1 <= overlap_y0:
            return 0.0
        
        return (overlap_x1 - overlap_x0) * (overlap_y1 - overlap_y0)
    
    def _calculate_bbox_area(self, bbox: Tuple[float, float, float, float]) -> float:
        """Calcule l'aire d'une bounding box"""
        x0, y0, x1, y1 = bbox
        return (x1 - x0) * (y1 - y0)
    
    def _generate_solutions(self, element_layouts: List[ElementLayout],
                          layout_issues: List[LayoutIssue]) -> List[LayoutSolution]:
        """Génère des solutions pour les problèmes de mise en page"""
        solutions = []
        
        # Grouper les problèmes par élément
        issues_by_element = {}
        for issue in layout_issues:
            for element_id in issue.affected_elements:
                if element_id not in issues_by_element:
                    issues_by_element[element_id] = []
                issues_by_element[element_id].append(issue)
        
        # Générer des solutions pour chaque élément
        for element_id, element_issues in issues_by_element.items():
            element_layout = next((l for l in element_layouts if l.element_id == element_id), None)
            if element_layout:
                element_solutions = self._generate_element_solutions(element_layout, element_issues)
                solutions.extend(element_solutions)
        
        return solutions
    
    def _generate_element_solutions(self, layout: ElementLayout,
                                  issues: List[LayoutIssue]) -> List[LayoutSolution]:
        """Génère des solutions pour un élément spécifique"""
        solutions = []
        
        for issue in issues:
            if issue.issue_type == LayoutIssueType.OVERFLOW_HORIZONTAL:
                solutions.extend(self._solve_horizontal_overflow(layout, issue))
            elif issue.issue_type == LayoutIssueType.OVERFLOW_VERTICAL:
                solutions.extend(self._solve_vertical_overflow(layout, issue))
            elif issue.issue_type == LayoutIssueType.FONT_TOO_SMALL:
                solutions.extend(self._solve_font_too_small(layout, issue))
            elif issue.issue_type == LayoutIssueType.ELEMENT_COLLISION:
                solutions.extend(self._solve_element_collision(layout, issue))
        
        return solutions
    
    def _solve_horizontal_overflow(self, layout: ElementLayout,
                                 issue: LayoutIssue) -> List[LayoutSolution]:
        """Solutions pour débordement horizontal"""
        solutions = []
        
        # Solution 1: Réduire la taille de police
        if layout.layout_constraints.allow_font_reduction:
            font_reduction = issue.overflow_amount / (layout.new_bbox[2] - layout.new_bbox[0])
            new_font_size = layout.new_font_size * (1 - font_reduction)
            
            if new_font_size >= layout.layout_constraints.min_font_size:
                solutions.append(LayoutSolution(
                    solution_type=SolutionType.REDUCE_FONT_SIZE,
                    confidence=0.8,
                    description=f"Réduire la police à {new_font_size:.1f}pt",
                    parameters={'new_font_size': new_font_size},
                    affected_elements=[layout.element_id],
                    estimated_quality_impact=0.3
                ))
        
        # Solution 2: Expand container si autorisé
        if layout.layout_constraints.allow_container_expansion:
            solutions.append(LayoutSolution(
                solution_type=SolutionType.EXPAND_CONTAINER,
                confidence=0.6,
                description=f"Étendre le conteneur de {issue.overflow_amount:.1f}px",
                parameters={'width_increase': issue.overflow_amount},
                affected_elements=[layout.element_id],
                estimated_quality_impact=0.1
            ))
        
        # Solution 3: Reflow text (retour à la ligne)
        solutions.append(LayoutSolution(
            solution_type=SolutionType.REFLOW_TEXT,
            confidence=0.7,
            description="Réorganiser le texte sur plusieurs lignes",
            parameters={'enable_multiline': True},
            affected_elements=[layout.element_id],
            estimated_quality_impact=0.2
        ))
        
        return solutions
    
    def _solve_vertical_overflow(self, layout: ElementLayout,
                               issue: LayoutIssue) -> List[LayoutSolution]:
        """Solutions pour débordement vertical"""
        solutions = []
        
        # Solution 1: Ajuster l'espacement des lignes
        solutions.append(LayoutSolution(
            solution_type=SolutionType.ADJUST_LINE_SPACING,
            confidence=0.7,
            description="Réduire l'espacement entre les lignes",
            parameters={'line_height_factor': 0.9},
            affected_elements=[layout.element_id],
            estimated_quality_impact=0.2
        ))
        
        # Solution 2: Expand container verticalement
        if layout.layout_constraints.allow_container_expansion:
            solutions.append(LayoutSolution(
                solution_type=SolutionType.EXPAND_CONTAINER,
                confidence=0.6,
                description=f"Étendre le conteneur verticalement de {issue.overflow_amount:.1f}px",
                parameters={'height_increase': issue.overflow_amount},
                affected_elements=[layout.element_id],
                estimated_quality_impact=0.1
            ))
        
        return solutions
    
    def _solve_font_too_small(self, layout: ElementLayout,
                            issue: LayoutIssue) -> List[LayoutSolution]:
        """Solutions pour police trop petite"""
        solutions = []
        
        # Solution 1: Expand container pour permettre une police plus grande
        if layout.layout_constraints.allow_container_expansion:
            target_font_size = layout.layout_constraints.min_font_size
            scale_factor = target_font_size / layout.new_font_size
            
            solutions.append(LayoutSolution(
                solution_type=SolutionType.EXPAND_CONTAINER,
                confidence=0.8,
                description=f"Agrandir le conteneur pour police {target_font_size:.1f}pt",
                parameters={
                    'scale_factor': scale_factor,
                    'target_font_size': target_font_size
                },
                affected_elements=[layout.element_id],
                estimated_quality_impact=0.1
            ))
        
        # Solution 2: Utiliser une police alternative plus compacte
        solutions.append(LayoutSolution(
            solution_type=SolutionType.USE_ALTERNATIVE_FONT,
            confidence=0.5,
            description="Utiliser une police plus compacte",
            parameters={'font_style': 'condensed'},
            affected_elements=[layout.element_id],
            estimated_quality_impact=0.3
        ))
        
        return solutions
    
    def _solve_element_collision(self, layout: ElementLayout,
                               issue: LayoutIssue) -> List[LayoutSolution]:
        """Solutions pour collision d'éléments"""
        solutions = []
        
        # Solution: Déplacer les éléments
        solutions.append(LayoutSolution(
            solution_type=SolutionType.MOVE_ELEMENTS,
            confidence=0.6,
            description="Réorganiser la position des éléments",
            parameters={'collision_resolution': 'auto'},
            affected_elements=issue.affected_elements,
            estimated_quality_impact=0.4
        ))
        
        return solutions
    
    def _optimize_global_layout(self, element_layouts: List[ElementLayout],
                              solutions: List[LayoutSolution]) -> List[ElementLayout]:
        """Optimise la mise en page globale en appliquant les meilleures solutions"""
        
        # Trier les solutions par confiance et impact qualité
        sorted_solutions = sorted(solutions, 
                                key=lambda s: (s.confidence, -s.estimated_quality_impact), 
                                reverse=True)
        
        # Appliquer les solutions compatibles
        applied_solutions = []
        optimized_layouts = [layout for layout in element_layouts]  # Copie
        
        for solution in sorted_solutions:
            if self._can_apply_solution(solution, applied_solutions):
                optimized_layouts = self._apply_solution(solution, optimized_layouts)
                applied_solutions.append(solution)
        
        return optimized_layouts
    
    def _can_apply_solution(self, solution: LayoutSolution,
                          applied_solutions: List[LayoutSolution]) -> bool:
        """Vérifie si une solution peut être appliquée sans conflit"""
        
        # Vérifier les conflits avec les solutions déjà appliquées
        for applied in applied_solutions:
            # Même élément, types de solution incompatibles
            if (set(solution.affected_elements) & set(applied.affected_elements) and
                self._are_solutions_incompatible(solution.solution_type, applied.solution_type)):
                return False
        
        return True
    
    def _are_solutions_incompatible(self, type1: SolutionType, type2: SolutionType) -> bool:
        """Vérifie si deux types de solution sont incompatibles"""
        incompatible_pairs = [
            (SolutionType.REDUCE_FONT_SIZE, SolutionType.EXPAND_CONTAINER),
            (SolutionType.REFLOW_TEXT, SolutionType.MOVE_ELEMENTS)
        ]
        
        return (type1, type2) in incompatible_pairs or (type2, type1) in incompatible_pairs
    
    def _apply_solution(self, solution: LayoutSolution,
                       layouts: List[ElementLayout]) -> List[ElementLayout]:
        """Applique une solution aux layouts"""
        
        for layout in layouts:
            if layout.element_id in solution.affected_elements:
                if solution.solution_type == SolutionType.REDUCE_FONT_SIZE:
                    layout.new_font_size = solution.parameters['new_font_size']
                    # Recalculer les dimensions avec la nouvelle police
                    layout.new_bbox = self._recalculate_bbox_with_new_font(layout)
                
                elif solution.solution_type == SolutionType.EXPAND_CONTAINER:
                    x0, y0, x1, y1 = layout.new_bbox
                    if 'width_increase' in solution.parameters:
                        x1 += solution.parameters['width_increase']
                    if 'height_increase' in solution.parameters:
                        y1 += solution.parameters['height_increase']
                    layout.new_bbox = (x0, y0, x1, y1)
                
                # Ajouter la solution aux solutions appliquées
                layout.solutions.append(solution)
        
        return layouts
    
    def _recalculate_bbox_with_new_font(self, layout: ElementLayout) -> Tuple[float, float, float, float]:
        """Recalcule la bbox avec une nouvelle taille de police"""
        x0, y0, x1, y1 = layout.original_bbox
        
        # Estimation de la nouvelle largeur nécessaire
        char_count = len(layout.translated_text)
        estimated_width = char_count * layout.new_font_size * self.char_width_factor
        estimated_height = layout.new_font_size * self.line_height_factor
        
        # Limiter aux dimensions originales si nécessaire
        original_width = x1 - x0
        original_height = y1 - y0
        
        new_width = min(estimated_width, original_width)
        new_height = min(estimated_height, original_height)
        
        return (x0, y0, x0 + new_width, y0 + new_height)
    
    def _calculate_quality_metrics(self, layouts: List[ElementLayout]) -> Dict[str, Any]:
        """Calcule les métriques de qualité de la mise en page"""
        
        total_elements = len(layouts)
        if total_elements == 0:
            return {'overall_quality': 0.0}
        
        # Métriques individuelles
        font_size_preservation = sum(
            1.0 if layout.new_font_size >= layout.original_font_size * 0.9 else 
            layout.new_font_size / layout.original_font_size
            for layout in layouts
        ) / total_elements
        
        bbox_preservation = sum(
            1.0 if self._calculate_bbox_area(layout.new_bbox) <= self._calculate_bbox_area(layout.original_bbox) * 1.1
            else self._calculate_bbox_area(layout.original_bbox) / self._calculate_bbox_area(layout.new_bbox)
            for layout in layouts
        ) / total_elements
        
        issues_impact = 1.0 - (sum(len(layout.issues) for layout in layouts) / max(1, total_elements * 3))
        
        # Score global
        overall_quality = (font_size_preservation * 0.4 + 
                          bbox_preservation * 0.4 + 
                          issues_impact * 0.2)
        
        return {
            'overall_quality': overall_quality,
            'font_size_preservation': font_size_preservation,
            'bbox_preservation': bbox_preservation,
            'issues_impact': issues_impact,
            'elements_with_issues': sum(1 for layout in layouts if layout.issues),
            'total_solutions_applied': sum(len(layout.solutions) for layout in layouts),
            'quality_level': self._get_quality_level(overall_quality)
        }
    
    def _get_quality_level(self, quality_score: float) -> str:
        """Détermine le niveau de qualité"""
        for level, threshold in self.quality_thresholds.items():
            if quality_score >= threshold:
                return level
        return 'poor'
    
    def _generate_recommendations(self, quality_metrics: Dict[str, Any],
                                layout_issues: List[LayoutIssue]) -> List[str]:
        """Génère des recommandations basées sur les métriques"""
        recommendations = []
        
        quality_level = quality_metrics['quality_level']
        
        if quality_level == 'excellent':
            recommendations.append("✅ Excellente qualité de mise en page. Aucun ajustement nécessaire.")
        elif quality_level == 'good':
            recommendations.append("✅ Bonne qualité de mise en page. Ajustements mineurs possibles.")
        elif quality_level == 'acceptable':
            recommendations.append("⚠️ Qualité acceptable. Quelques ajustements recommandés.")
        else:
            recommendations.append("❌ Qualité de mise en page problématique. Révision recommandée.")
        
        # Recommandations spécifiques
        if quality_metrics['elements_with_issues'] > 0:
            recommendations.append(
                f"🔍 {quality_metrics['elements_with_issues']} élément(s) avec des problèmes détectés."
            )
        
        # Analyse des types de problèmes
        issue_types = {}
        for issue in layout_issues:
            issue_type = issue.issue_type.value
            if issue_type not in issue_types:
                issue_types[issue_type] = 0
            issue_types[issue_type] += 1
        
        for issue_type, count in issue_types.items():
            if issue_type == 'overflow_horizontal':
                recommendations.append(f"📏 {count} débordement(s) horizontal - considérer des polices plus compactes.")
            elif issue_type == 'font_too_small':
                recommendations.append(f"🔍 {count} police(s) trop petite(s) - agrandir les conteneurs si possible.")
        
        return recommendations
    
    def _serialize_layouts(self, layouts: List[ElementLayout]) -> List[Dict[str, Any]]:
        """Sérialise les layouts pour export JSON"""
        return [
            {
                'element_id': layout.element_id,
                'original_bbox': layout.original_bbox,
                'new_bbox': layout.new_bbox,
                'original_font_size': layout.original_font_size,
                'new_font_size': layout.new_font_size,
                'expansion_factor': layout.expansion_factor,
                'issues_count': len(layout.issues),
                'solutions_applied': len(layout.solutions)
            }
            for layout in layouts
        ]
    
    def _serialize_issues(self, issues: List[LayoutIssue]) -> List[Dict[str, Any]]:
        """Sérialise les problèmes pour export JSON"""
        return [
            {
                'issue_type': issue.issue_type.value,
                'severity': issue.severity,
                'description': issue.description,
                'affected_elements': issue.affected_elements,
                'overflow_amount': issue.overflow_amount
            }
            for issue in issues
        ]
    
    def _serialize_solutions(self, solutions: List[LayoutSolution]) -> List[Dict[str, Any]]:
        """Sérialise les solutions pour export JSON"""
        return [
            {
                'solution_type': solution.solution_type.value,
                'confidence': solution.confidence,
                'description': solution.description,
                'parameters': solution.parameters,
                'affected_elements': solution.affected_elements,
                'estimated_quality_impact': solution.estimated_quality_impact
            }
            for solution in solutions
        ]
    
    def _create_changes_summary(self, original_layouts: List[ElementLayout],
                              optimized_layouts: List[ElementLayout]) -> Dict[str, Any]:
        """Crée un résumé des changements appliqués"""
        
        font_size_changes = []
        bbox_changes = []
        
        for orig, opt in zip(original_layouts, optimized_layouts):
            if orig.new_font_size != opt.new_font_size:
                font_size_changes.append({
                    'element_id': orig.element_id,
                    'original_size': orig.new_font_size,
                    'new_size': opt.new_font_size,
                    'change_percent': (opt.new_font_size - orig.new_font_size) / orig.new_font_size * 100
                })
            
            if orig.new_bbox != opt.new_bbox:
                bbox_changes.append({
                    'element_id': orig.element_id,
                    'original_bbox': orig.new_bbox,
                    'new_bbox': opt.new_bbox
                })
        
        return {
            'font_size_changes': font_size_changes,
            'bbox_changes': bbox_changes,
            'total_changes': len(font_size_changes) + len(bbox_changes)
        }