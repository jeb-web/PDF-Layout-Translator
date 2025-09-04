#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Reconstructeur de PDF
Reconstruction du PDF final avec texte traduit et mise en page ajustée

Auteur: L'OréalGPT
Version: 1.0.0
"""

import logging
import fitz  # PyMuPDF
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import json
import tempfile
import shutil

@dataclass
class ReconstructionResult:
    """Résultat de la reconstruction"""
    success: bool
    output_path: Optional[Path]
    processing_time: float
    pages_processed: int
    elements_processed: int
    errors: List[str]
    warnings: List[str]
    quality_score: float
    file_size_original: int
    file_size_output: int

class PDFReconstructor:
    """Reconstructeur de PDF avec texte traduit"""
    
    def __init__(self, config_manager=None, font_manager=None):
        """
        Initialise le reconstructeur PDF
        
        Args:
            config_manager: Gestionnaire de configuration (optionnel)
            font_manager: Gestionnaire de polices (optionnel)
        """
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager
        self.font_manager = font_manager
        
        # Configuration par défaut
        self.preserve_images = True
        self.preserve_drawings = True
        self.preserve_annotations = True
        self.preserve_forms = False  # Les formulaires peuvent poser problème
        self.embed_fonts = True
        self.optimize_output = True
        self.compression_level = 70  # 0-100
        
        # Configuration depuis le gestionnaire si disponible
        if config_manager:
            self.preserve_images = config_manager.get('export.preserve_images', True)
            self.preserve_drawings = config_manager.get('export.preserve_drawings', True)
            self.embed_fonts = config_manager.get('fonts.embed_fonts', True)
            self.optimize_output = config_manager.get('export.optimize_output', True)
            self.compression_level = config_manager.get('export.compression_level', 70)
        
        # Marges de sécurité pour le placement de texte
        self.text_margin = 2.0  # pixels
        
        self.logger.info("PDFReconstructor initialisé")
    
    def reconstruct_pdf(self, original_pdf_path: Path, layout_data: Dict[str, Any],
                       validated_translations: Dict[str, Any], output_path: Path,
                       preserve_original: bool = True) -> ReconstructionResult:
        """
        Reconstruit le PDF avec les traductions et ajustements de mise en page
        
        Args:
            original_pdf_path: Chemin vers le PDF original
            layout_data: Données de mise en page du layout_processor
            validated_translations: Traductions validées
            output_path: Chemin de sortie du PDF
            preserve_original: Créer une sauvegarde de l'original
            
        Returns:
            Résultat de la reconstruction
        """
        start_time = datetime.now()
        self.logger.info(f"Début de la reconstruction: {original_pdf_path} -> {output_path}")
        
        errors = []
        warnings = []
        pages_processed = 0
        elements_processed = 0
        
        try:
            # Créer une sauvegarde si demandé
            if preserve_original:
                self._create_backup(original_pdf_path)
            
            # Ouvrir le document original
            original_doc = fitz.open(original_pdf_path)
            original_size = original_pdf_path.stat().st_size
            
            # Créer le nouveau document
            output_doc = fitz.open()
            
            # Traiter chaque page
            for page_num in range(len(original_doc)):
                try:
                    page_result = self._process_page(
                        original_doc[page_num], 
                        output_doc, 
                        page_num + 1,
                        layout_data,
                        validated_translations
                    )
                    
                    pages_processed += 1
                    elements_processed += page_result['elements_processed']
                    warnings.extend(page_result['warnings'])
                    
                except Exception as e:
                    error_msg = f"Erreur page {page_num + 1}: {str(e)}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)
            
            # Copier les métadonnées
            self._copy_metadata(original_doc, output_doc)
            
            # Optimiser si demandé
            if self.optimize_output:
                self._optimize_document(output_doc)
            
            # Sauvegarder le document final
            output_doc.save(output_path, 
                           garbage=4,  # Nettoyage maximal
                           deflate=True,  # Compression
                           clean=True)  # Nettoyage des objets non utilisés
            
            output_size = output_path.stat().st_size
            
            # Fermer les documents
            original_doc.close()
            output_doc.close()
            
            # Calculer le score de qualité
            quality_score = self._calculate_quality_score(
                pages_processed, len(original_doc), elements_processed, errors, warnings
            )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            result = ReconstructionResult(
                success=len(errors) == 0,
                output_path=output_path if len(errors) == 0 else None,
                processing_time=processing_time,
                pages_processed=pages_processed,
                elements_processed=elements_processed,
                errors=errors,
                warnings=warnings,
                quality_score=quality_score,
                file_size_original=original_size,
                file_size_output=output_size if output_path.exists() else 0
            )
            
            self.logger.info(f"Reconstruction terminée: {result.success}, "
                           f"{result.pages_processed} pages, {result.elements_processed} éléments")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la reconstruction: {e}")
            errors.append(str(e))
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return ReconstructionResult(
                success=False,
                output_path=None,
                processing_time=processing_time,
                pages_processed=pages_processed,
                elements_processed=elements_processed,
                errors=errors,
                warnings=warnings,
                quality_score=0.0,
                file_size_original=0,
                file_size_output=0
            )
    
    def _create_backup(self, original_path: Path):
        """Crée une sauvegarde du fichier original"""
        try:
            backup_dir = original_path.parent / "backups"
            backup_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{original_path.stem}_backup_{timestamp}{original_path.suffix}"
            backup_path = backup_dir / backup_name
            
            shutil.copy2(original_path, backup_path)
            self.logger.info(f"Sauvegarde créée: {backup_path}")
            
        except Exception as e:
            self.logger.warning(f"Impossible de créer la sauvegarde: {e}")
    
    def _process_page(self, original_page, output_doc, page_number: int,
                     layout_data: Dict[str, Any], validated_translations: Dict[str, Any]) -> Dict[str, Any]:
        """
        Traite une page individuelle
        
        Args:
            original_page: Page originale PyMuPDF
            output_doc: Document de sortie
            page_number: Numéro de page
            layout_data: Données de mise en page
            validated_translations: Traductions validées
            
        Returns:
            Résultats du traitement de la page
        """
        warnings = []
        elements_processed = 0
        
        # Créer la nouvelle page avec les mêmes dimensions
        new_page = output_doc.new_page(width=original_page.rect.width,
                                     height=original_page.rect.height)
        
        # Copier les éléments non-textuels d'abord
        if self.preserve_images:
            elements_processed += self._copy_images(original_page, new_page, warnings)
        
        if self.preserve_drawings:
            elements_processed += self._copy_drawings(original_page, new_page, warnings)
        
        if self.preserve_annotations:
            elements_processed += self._copy_annotations(original_page, new_page, warnings)
        
        # Placer le texte traduit
        text_elements = self._get_page_text_elements(page_number, layout_data)
        for element_layout in text_elements:
            try:
                self._place_translated_text(new_page, element_layout, validated_translations)
                elements_processed += 1
            except Exception as e:
                warning = f"Erreur placement texte {element_layout['element_id']}: {str(e)}"
                warnings.append(warning)
                self.logger.warning(warning)
        
        return {
            'elements_processed': elements_processed,
            'warnings': warnings
        }
    
    def _copy_images(self, original_page, new_page, warnings: List[str]) -> int:
        """Copie les images de la page originale"""
        images_copied = 0
        
        try:
            image_list = original_page.get_images()
            
            for img_index, img in enumerate(image_list):
                try:
                    # Récupérer l'image
                    xref = img[0]
                    base_image = original_page.parent.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    
                    # Récupérer la position de l'image
                    image_rects = original_page.get_image_rects(xref)
                    
                    for rect in image_rects:
                        # Insérer l'image dans la nouvelle page
                        new_page.insert_image(rect, stream=image_bytes)
                        images_copied += 1
                        
                except Exception as e:
                    warning = f"Erreur copie image {img_index}: {str(e)}"
                    warnings.append(warning)
                    
        except Exception as e:
            warning = f"Erreur lors de la copie des images: {str(e)}"
            warnings.append(warning)
        
        return images_copied
    
    def _copy_drawings(self, original_page, new_page, warnings: List[str]) -> int:
        """Copie les éléments de dessin (formes, lignes, etc.)"""
        drawings_copied = 0
        
        try:
            drawings = original_page.get_drawings()
            
            for drawing in drawings:
                try:
                    # Reconstruire le chemin de dessin
                    for item in drawing["items"]:
                        if item[0] == "l":  # ligne
                            p1, p2 = item[1], item[2]
                            new_page.draw_line(p1, p2)
                            drawings_copied += 1
                        elif item[0] == "re":  # rectangle
                            rect = item[1]
                            new_page.draw_rect(rect)
                            drawings_copied += 1
                        elif item[0] == "c":  # courbe
                            # Gérer les courbes si nécessaire
                            pass
                            
                except Exception as e:
                    warning = f"Erreur copie dessin: {str(e)}"
                    warnings.append(warning)
                    
        except Exception as e:
            warning = f"Erreur lors de la copie des dessins: {str(e)}"
            warnings.append(warning)
        
        return drawings_copied
    
    def _copy_annotations(self, original_page, new_page, warnings: List[str]) -> int:
        """Copie les annotations (commentaires, liens, etc.)"""
        annotations_copied = 0
        
        try:
            # Copier les liens
            links = original_page.get_links()
            for link in links:
                try:
                    new_page.insert_link(link)
                    annotations_copied += 1
                except Exception as e:
                    warning = f"Erreur copie lien: {str(e)}"
                    warnings.append(warning)
            
            # Copier les annotations
            for annot in original_page.annots():
                try:
                    # Créer une nouvelle annotation de même type
                    annot_dict = annot.info
                    new_annot = new_page.add_text_annot(annot.rect.tl, annot_dict.get("title", ""))
                    new_annot.set_info(annot_dict)
                    annotations_copied += 1
                except Exception as e:
                    warning = f"Erreur copie annotation: {str(e)}"
                    warnings.append(warning)
                    
        except Exception as e:
            warning = f"Erreur lors de la copie des annotations: {str(e)}"
            warnings.append(warning)
        
        return annotations_copied
    
    def _get_page_text_elements(self, page_number: int, layout_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Récupère les éléments de texte pour une page donnée"""
        page_elements = []
        
        for element_layout in layout_data.get('element_layouts', []):
            # Déterminer la page depuis l'ID ou les données d'origine
            # Ici on assume que page_number est dans les métadonnées
            if self._element_belongs_to_page(element_layout, page_number):
                page_elements.append(element_layout)
        
        return page_elements
    
    def _element_belongs_to_page(self, element_layout: Dict[str, Any], page_number: int) -> bool:
        """Détermine si un élément appartient à une page donnée"""
        # Cette méthode devrait utiliser les données originales pour déterminer la page
        # Pour simplifier, on assume que l'information est disponible
        # Dans une implémentation réelle, il faudrait croiser avec les données d'extraction
        return True  # Placeholder - à implémenter selon la structure des données
    
    def _place_translated_text(self, page, element_layout: Dict[str, Any], 
                             validated_translations: Dict[str, Any]):
        """
        Place le texte traduit sur la page
        
        Args:
            page: Page PyMuPDF
            element_layout: Layout de l'élément
            validated_translations: Traductions validées
        """
        element_id = element_layout['element_id']
        
        # Récupérer la traduction
        if element_id not in validated_translations['translations']:
            return
        
        translation_data = validated_translations['translations'][element_id]
        translated_text = translation_data['translated_text']
        
        # Récupérer la position et la police
        bbox = element_layout['new_bbox']  # Utiliser la bbox ajustée
        font_size = element_layout['new_font_size']
        
        # Convertir la bbox en rectangle PyMuPDF
        rect = fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])
        
        # Déterminer la police à utiliser
        font_name = self._determine_font_for_element(element_id, validated_translations)
        
        # Préparer les options de texte
        text_options = {
            'fontsize': font_size,
            'color': (0, 0, 0),  # Noir par défaut
            'align': fitz.TEXT_ALIGN_LEFT  # Alignement par défaut
        }
        
        # Ajuster l'alignement selon le type de contenu
        content_type = self._get_element_content_type(element_id, validated_translations)
        if content_type == 'title':
            text_options['align'] = fitz.TEXT_ALIGN_CENTER
        elif content_type == 'subtitle':
            text_options['align'] = fitz.TEXT_ALIGN_LEFT
        
        # Gérer les polices personnalisées
        if self.font_manager and font_name:
            font_info = self.font_manager.get_font_info(font_name)
            if font_info and font_info.file_path:
                try:
                    # Utiliser une police personnalisée si disponible
                    text_options['font'] = fitz.Font(fontfile=str(font_info.file_path))
                except Exception as e:
                    self.logger.warning(f"Impossible d'utiliser la police {font_name}: {e}")
        
        # Insérer le texte
        try:
            # Ajuster le rectangle pour éviter les débordements
            adjusted_rect = self._adjust_text_rect(rect, translated_text, text_options)
            
            # Insérer le texte avec gestion des retours à la ligne
            text_rect = page.insert_textbox(
                adjusted_rect,
                translated_text,
                **text_options
            )
            
            # Vérifier si le texte a été tronqué
            if text_rect.y1 > adjusted_rect.y1:
                self.logger.warning(f"Texte possiblement tronqué pour {element_id}")
            
        except Exception as e:
            # Fallback: utiliser une méthode plus simple
            self.logger.warning(f"Erreur insertion textbox pour {element_id}: {e}")
            try:
                page.insert_text(
                    rect.tl,  # Point en haut à gauche
                    translated_text,
                    fontsize=font_size,
                    color=(0, 0, 0)
                )
            except Exception as e2:
                self.logger.error(f"Erreur fallback insertion texte pour {element_id}: {e2}")
                raise
    
    def _determine_font_for_element(self, element_id: str, validated_translations: Dict[str, Any]) -> str:
        """Détermine la police à utiliser pour un élément"""
        # Récupérer les informations de police originales
        # et appliquer les mappings si disponibles
        
        if self.font_manager:
            # Logique de détermination de police avec le gestionnaire
            # Pour l'instant, retourner une police par défaut
            return "Arial"
        
        return "Arial"  # Fallback
    
    def _get_element_content_type(self, element_id: str, validated_translations: Dict[str, Any]) -> str:
        """Récupère le type de contenu d'un élément"""
        # Cette information devrait être disponible dans les données d'origine
        # Pour l'instant, retourner un type par défaut
        return "paragraph"
    
    def _adjust_text_rect(self, rect: fitz.Rect, text: str, text_options: Dict[str, Any]) -> fitz.Rect:
        """Ajuste le rectangle de texte pour éviter les débordements"""
        
        # Ajouter une marge de sécurité
        adjusted_rect = fitz.Rect(
            rect.x0 + self.text_margin,
            rect.y0 + self.text_margin,
            rect.x1 - self.text_margin,
            rect.y1 - self.text_margin
        )
        
        # S'assurer que le rectangle reste valide
        if adjusted_rect.width <= 0:
            adjusted_rect.x1 = adjusted_rect.x0 + 10
        if adjusted_rect.height <= 0:
            adjusted_rect.y1 = adjusted_rect.y0 + 10
        
        return adjusted_rect
    
    def _copy_metadata(self, source_doc, target_doc):
        """Copie les métadonnées du document source vers le document cible"""
        try:
            metadata = source_doc.metadata.copy()
            
            # Ajouter des informations sur la traduction
            metadata['subject'] = f"Traduit par PDF Layout Translator - {datetime.now().strftime('%Y-%m-%d')}"
            metadata['creator'] = "PDF Layout Translator"
            metadata['producer'] = "PDF Layout Translator v1.0.0"
            
            target_doc.set_metadata(metadata)
            
        except Exception as e:
            self.logger.warning(f"Erreur lors de la copie des métadonnées: {e}")
    
    def _optimize_document(self, doc):
        """Optimise le document PDF pour réduire sa taille"""
        try:
            # Nettoyage des objets non utilisés
            doc.scrub()
            
            # Compression des images si possible
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Optimiser les images de la page
                for img_index in range(len(page.get_images())):
                    try:
                        # Récompresser les images avec le niveau souhaité
                        # Cette fonctionnalité dépend de la version de PyMuPDF
                        pass
                    except:
                        pass
            
            self.logger.info("Optimisation du document terminée")
            
        except Exception as e:
            self.logger.warning(f"Erreur lors de l'optimisation: {e}")
    
    def _calculate_quality_score(self, pages_processed: int, total_pages: int,
                               elements_processed: int, errors: List[str], 
                               warnings: List[str]) -> float:
        """Calcule un score de qualité pour la reconstruction"""
        
        if total_pages == 0:
            return 0.0
        
        # Score basé sur le pourcentage de pages traitées avec succès
        page_success_rate = pages_processed / total_pages
        
        # Pénalité pour les erreurs et avertissements
        error_penalty = min(0.5, len(errors) * 0.1)
        warning_penalty = min(0.2, len(warnings) * 0.02)
        
        # Score final
        quality_score = page_success_rate - error_penalty - warning_penalty
        quality_score = max(0.0, min(1.0, quality_score))
        
        return quality_score
    
    def create_comparison_pdf(self, original_path: Path, translated_path: Path,
                            output_path: Path) -> bool:
        """
        Crée un PDF de comparaison côte à côte
        
        Args:
            original_path: PDF original
            translated_path: PDF traduit
            output_path: PDF de comparaison
            
        Returns:
            True si succès
        """
        try:
            original_doc = fitz.open(original_path)
            translated_doc = fitz.open(translated_path)
            comparison_doc = fitz.open()
            
            max_pages = max(len(original_doc), len(translated_doc))
            
            for page_num in range(max_pages):
                # Créer une nouvelle page plus large
                if page_num < len(original_doc):
                    orig_page = original_doc[page_num]
                    page_width = orig_page.rect.width
                    page_height = orig_page.rect.height
                else:
                    page_width = 595  # A4 par défaut
                    page_height = 842
                
                # Nouvelle page avec double largeur
                new_page = comparison_doc.new_page(width=page_width * 2 + 20, height=page_height)
                
                # Ajouter la page originale à gauche
                if page_num < len(original_doc):
                    orig_page = original_doc[page_num]
                    pix = orig_page.get_pixmap()
                    new_page.insert_image(fitz.Rect(0, 0, page_width, page_height), pixmap=pix)
                
                # Ajouter la page traduite à droite
                if page_num < len(translated_doc):
                    trans_page = translated_doc[page_num]
                    pix = trans_page.get_pixmap()
                    new_page.insert_image(fitz.Rect(page_width + 20, 0, page_width * 2 + 20, page_height), pixmap=pix)
                
                # Ajouter une ligne de séparation
                new_page.draw_line(
                    fitz.Point(page_width + 10, 0),
                    fitz.Point(page_width + 10, page_height),
                    color=(0.5, 0.5, 0.5),
                    width=2
                )
                
                # Ajouter des labels
                new_page.insert_text(
                    fitz.Point(10, 30),
                    "ORIGINAL",
                    fontsize=12,
                    color=(0, 0, 1)
                )
                new_page.insert_text(
                    fitz.Point(page_width + 30, 30),
                    "TRADUIT",
                    fontsize=12,
                    color=(1, 0, 0)
                )
            
            comparison_doc.save(output_path)
            
            # Fermer les documents
            original_doc.close()
            translated_doc.close()
            comparison_doc.close()
            
            self.logger.info(f"PDF de comparaison créé: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur création PDF de comparaison: {e}")
            return False
    
    def extract_text_for_validation(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Extrait le texte du PDF reconstruit pour validation
        
        Args:
            pdf_path: Chemin vers le PDF
            
        Returns:
            Dictionnaire avec le texte extrait
        """
        try:
            doc = fitz.open(pdf_path)
            extracted_text = {}
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_text = page.get_text()
                extracted_text[f"page_{page_num + 1}"] = {
                    'text': page_text,
                    'word_count': len(page_text.split()),
                    'char_count': len(page_text)
                }
            
            doc.close()
            
            return {
                'pages': extracted_text,
                'total_pages': len(extracted_text),
                'total_words': sum(page['word_count'] for page in extracted_text.values()),
                'total_chars': sum(page['char_count'] for page in extracted_text.values())
            }
            
        except Exception as e:
            self.logger.error(f"Erreur extraction texte pour validation: {e}")
            return {}
    
    def generate_reconstruction_report(self, result: ReconstructionResult,
                                     layout_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Génère un rapport détaillé de la reconstruction
        
        Args:
            result: Résultat de la reconstruction
            layout_data: Données de mise en page utilisées
            
        Returns:
            Rapport détaillé
        """
        report = {
            'reconstruction_summary': {
                'success': result.success,
                'processing_time': result.processing_time,
                'pages_processed': result.pages_processed,
                'elements_processed': result.elements_processed,
                'quality_score': result.quality_score
            },
            'file_information': {
                'output_path': str(result.output_path) if result.output_path else None,
                'original_size_mb': result.file_size_original / 1024 / 1024,
                'output_size_mb': result.file_size_output / 1024 / 1024,
                'size_change_percent': ((result.file_size_output - result.file_size_original) / 
                                       max(1, result.file_size_original)) * 100
            },
            'issues': {
                'errors': result.errors,
                'warnings': result.warnings,
                'error_count': len(result.errors),
                'warning_count': len(result.warnings)
            },
            'layout_statistics': {
                'total_elements': len(layout_data.get('element_layouts', [])),
                'elements_with_issues': len([e for e in layout_data.get('element_layouts', []) 
                                           if e.get('issues_count', 0) > 0]),
                'solutions_applied': sum(e.get('solutions_applied', 0) 
                                       for e in layout_data.get('element_layouts', []))
            },
            'recommendations': self._generate_reconstruction_recommendations(result, layout_data),
            'timestamp': datetime.now().isoformat()
        }
        
        return report
    
    def _generate_reconstruction_recommendations(self, result: ReconstructionResult,
                                               layout_data: Dict[str, Any]) -> List[str]:
        """Génère des recommandations basées sur les résultats"""
        recommendations = []
        
        if result.success:
            recommendations.append("✅ Reconstruction réussie.")
        else:
            recommendations.append("❌ Reconstruction échouée. Vérifiez les erreurs.")
        
        if result.quality_score >= 0.9:
            recommendations.append("🌟 Excellente qualité de reconstruction.")
        elif result.quality_score >= 0.7:
            recommendations.append("✅ Bonne qualité de reconstruction.")
        elif result.quality_score >= 0.5:
            recommendations.append("⚠️ Qualité acceptable avec quelques problèmes.")
        else:
            recommendations.append("❌ Qualité de reconstruction problématique.")
        
        # Recommandations sur la taille du fichier
        if result.file_size_output > 0 and result.file_size_original > 0:
            size_ratio = result.file_size_output / result.file_size_original
            if size_ratio > 1.5:
                recommendations.append("📁 Fichier de sortie significativement plus volumineux.")
            elif size_ratio < 0.5:
                recommendations.append("📁 Fichier de sortie réduit, vérifiez que tout le contenu est présent.")
        
        # Recommandations sur les erreurs
        if len(result.errors) > 0:
            recommendations.append(f"🔍 {len(result.errors)} erreur(s) à résoudre.")
        
        if len(result.warnings) > 5:
            recommendations.append(f"⚠️ Nombreux avertissements ({len(result.warnings)}). Révision recommandée.")
        
        return recommendations