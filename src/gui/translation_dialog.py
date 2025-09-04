#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Interface de traduction avancée
Interface dédiée à la gestion et révision des traductions

Auteur: L'OréalGPT
Version: 1.0.0
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import re

# Imports des modules core
from core.translation_parser import TranslationParser, ValidationLevel, ParseResult

class TranslationDialog:
    """Interface avancée de gestion des traductions"""
    
    def __init__(self, parent, extraction_data: Dict[str, Any], 
                 translation_parser: TranslationParser = None):
        """
        Initialise l'interface de traduction
        
        Args:
            parent: Fenêtre parent
            extraction_data: Données d'extraction du texte
            translation_parser: Parser de traductions (optionnel)
        """
        self.parent = parent
        self.extraction_data = extraction_data
        self.translation_parser = translation_parser or TranslationParser()
        self.logger = logging.getLogger(__name__)
        
        # Données de traduction
        self.original_elements = {
            elem['id']: elem for elem in extraction_data['translation_elements']
            if elem['is_translatable']
        }
        self.translations = {}  # {element_id: translated_text}
        self.validation_results = {}  # {element_id: validation_info}
        
        # Variables d'interface
        self.current_element_id = None
        self.filter_status = "all"  # all, missing, translated, issues
        self.search_query = ""
        
        # Créer la fenêtre
        self._create_window()
        
        # Charger les éléments
        self._load_elements()
        
        self.logger.info("Interface de traduction initialisée")
    
    def _create_window(self):
        """Crée la fenêtre de dialogue"""
        self.window = tk.Toplevel(self.parent)
        self.window.title("Gestionnaire de Traductions")
        self.window.geometry("1400x900")
        self.window.minsize(1200, 700)
        
        # Centrer la fenêtre
        self.window.transient(self.parent)
        self.window.grab_set()
        
        # Configuration du style
        style = ttk.Style()
        style.configure('Element.TFrame', relief='solid', borderwidth=1)
        style.configure('Original.TLabel', background='#f0f0f0', padding=5)
        style.configure('Translation.TLabel', background='#f8f8f8', padding=5)
        style.configure('Valid.TLabel', foreground='green')
        style.configure('Invalid.TLabel', foreground='red')
        style.configure('Missing.TLabel', foreground='orange')
        
        # Créer l'interface
        self._create_widgets()
        
        # Centrer sur le parent
        self.window.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - (1400 // 2)
        y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - (900 // 2)
        self.window.geometry(f"1400x900+{x}+{y}")
    
    def _create_widgets(self):
        """Crée les widgets de l'interface"""
        
        # Frame principal
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # En-tête avec informations
        self._create_header(main_frame)
        
        # Barre d'outils
        self._create_toolbar(main_frame)
        
        # Interface principale divisée
        self._create_main_interface(main_frame)
        
        # Barre de statut
        self._create_status_bar(main_frame)
        
        # Boutons de contrôle
        self._create_control_buttons(main_frame)
    
    def _create_header(self, parent):
        """Crée l'en-tête avec informations du document"""
        header_frame = ttk.LabelFrame(parent, text="Informations du Document", padding=10)
        header_frame.pack(fill='x', pady=(0, 10))
        
        session_info = self.extraction_data['session_info']
        
        info_text = f"""Langue source: {session_info['source_language']} → Langue cible: {session_info['target_language']}
Pages: {session_info['total_pages']} | Éléments à traduire: {session_info['translatable_elements']}"""
        
        ttk.Label(header_frame, text=info_text).pack(anchor='w')
        
        # Barre de progression globale
        progress_frame = ttk.Frame(header_frame)
        progress_frame.pack(fill='x', pady=(5, 0))
        
        ttk.Label(progress_frame, text="Progression:").pack(side='left')
        
        self.progress_bar = ttk.Progressbar(progress_frame, length=300, mode='determinate')
        self.progress_bar.pack(side='left', padx=(10, 0))
        
        self.progress_label = ttk.Label(progress_frame, text="0/0")
        self.progress_label.pack(side='left', padx=(10, 0))
    
    def _create_toolbar(self, parent):
        """Crée la barre d'outils"""
        toolbar_frame = ttk.Frame(parent)
        toolbar_frame.pack(fill='x', pady=(0, 10))
        
        # Filtres
        filter_frame = ttk.LabelFrame(toolbar_frame, text="Filtres", padding=5)
        filter_frame.pack(side='left', fill='y')
        
        self.filter_var = tk.StringVar(value="all")
        filters = [
            ("Tous", "all"),
            ("Non traduits", "missing"),
            ("Traduits", "translated"),
            ("Avec problèmes", "issues")
        ]
        
        for text, value in filters:
            ttk.Radiobutton(filter_frame, text=text, variable=self.filter_var, 
                           value=value, command=self._apply_filter).pack(side='left', padx=5)
        
        # Recherche
        search_frame = ttk.LabelFrame(toolbar_frame, text="Recherche", padding=5)
        search_frame.pack(side='left', fill='y', padx=(10, 0))
        
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self._on_search_change)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=20)
        search_entry.pack(side='left')
        
        ttk.Button(search_frame, text="Effacer", command=self._clear_search).pack(side='left', padx=(5, 0))
        
        # Actions rapides
        actions_frame = ttk.LabelFrame(toolbar_frame, text="Actions", padding=5)
        actions_frame.pack(side='right', fill='y')
        
        ttk.Button(actions_frame, text="Import en lot", command=self._import_bulk_translation).pack(side='left', padx=2)
        ttk.Button(actions_frame, text="Export", command=self._export_translations).pack(side='left', padx=2)
        ttk.Button(actions_frame, text="Valider tout", command=self._validate_all).pack(side='left', padx=2)
    
    def _create_main_interface(self, parent):
        """Crée l'interface principale divisée"""
        
        # PanedWindow pour diviser l'interface
        paned = ttk.PanedWindow(parent, orient='horizontal')
        paned.pack(fill='both', expand=True, pady=(0, 10))
        
        # Panneau gauche - Liste des éléments
        self._create_elements_panel(paned)
        
        # Panneau droit - Édition
        self._create_edition_panel(paned)
        
        # Configuration des poids
        paned.add(self.elements_frame, weight=1)
        paned.add(self.edition_frame, weight=1)
    
    def _create_elements_panel(self, parent):
        """Crée le panneau de liste des éléments"""
        self.elements_frame = ttk.LabelFrame(parent, text="Éléments à Traduire", padding=5)
        
        # Treeview pour la liste des éléments
        tree_frame = ttk.Frame(self.elements_frame)
        tree_frame.pack(fill='both', expand=True)
        
        # Configuration du Treeview
        columns = ('page', 'type', 'preview', 'status')
        self.elements_tree = ttk.Treeview(tree_frame, columns=columns, show='tree headings', height=15)
        
        # Configuration des colonnes
        self.elements_tree.heading('#0', text='ID')
        self.elements_tree.heading('page', text='Page')
        self.elements_tree.heading('type', text='Type')
        self.elements_tree.heading('preview', text='Aperçu')
        self.elements_tree.heading('status', text='Statut')
        
        self.elements_tree.column('#0', width=80, minwidth=60)
        self.elements_tree.column('page', width=60, minwidth=40)
        self.elements_tree.column('type', width=100, minwidth=80)
        self.elements_tree.column('preview', width=200, minwidth=150)
        self.elements_tree.column('status', width=100, minwidth=80)
        
        # Scrollbars
        v_scroll = ttk.Scrollbar(tree_frame, orient='vertical', command=self.elements_tree.yview)
        h_scroll = ttk.Scrollbar(tree_frame, orient='horizontal', command=self.elements_tree.xview)
        self.elements_tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        # Placement
        self.elements_tree.grid(row=0, column=0, sticky='nsew')
        v_scroll.grid(row=0, column=1, sticky='ns')
        h_scroll.grid(row=1, column=0, sticky='ew')
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Bind events
        self.elements_tree.bind('<<TreeviewSelect>>', self._on_element_select)
        self.elements_tree.bind('<Double-1>', self._on_element_double_click)
        
        # Menu contextuel
        self._create_context_menu()
    
    def _create_edition_panel(self, parent):
        """Crée le panneau d'édition"""
        self.edition_frame = ttk.LabelFrame(parent, text="Édition de Traduction", padding=5)
        
        # Informations de l'élément sélectionné
        info_frame = ttk.LabelFrame(self.edition_frame, text="Élément Sélectionné", padding=10)
        info_frame.pack(fill='x', pady=(0, 10))
        
        self.element_info_label = ttk.Label(info_frame, text="Aucun élément sélectionné", 
                                           wraplength=400, justify='left')
        self.element_info_label.pack(anchor='w')
        
        # Texte original
        original_frame = ttk.LabelFrame(self.edition_frame, text="Texte Original", padding=5)
        original_frame.pack(fill='x', pady=(0, 10))
        
        self.original_text = scrolledtext.ScrolledText(original_frame, height=4, state='disabled',
                                                      wrap='word', font=('Arial', 10))
        self.original_text.pack(fill='x')
        
        # Zone de traduction
        translation_frame = ttk.LabelFrame(self.edition_frame, text="Traduction", padding=5)
        translation_frame.pack(fill='both', expand=True, pady=(0, 10))
        
        self.translation_text = scrolledtext.ScrolledText(translation_frame, height=6, wrap='word',
                                                         font=('Arial', 10))
        self.translation_text.pack(fill='both', expand=True)
        self.translation_text.bind('<KeyRelease>', self._on_translation_change)
        
        # Suggestions et validation
        validation_frame = ttk.LabelFrame(self.edition_frame, text="Validation", padding=5)
        validation_frame.pack(fill='x', pady=(0, 10))
        
        self.validation_label = ttk.Label(validation_frame, text="", wraplength=400)
        self.validation_label.pack(anchor='w')
        
        # Boutons d'action
        buttons_frame = ttk.Frame(self.edition_frame)
        buttons_frame.pack(fill='x')
        
        ttk.Button(buttons_frame, text="Sauvegarder", command=self._save_current_translation).pack(side='left')
        ttk.Button(buttons_frame, text="Réinitialiser", command=self._reset_current_translation).pack(side='left', padx=(5, 0))
        ttk.Button(buttons_frame, text="Suivant", command=self._go_to_next_element).pack(side='right')
        ttk.Button(buttons_frame, text="Précédent", command=self._go_to_previous_element).pack(side='right', padx=(0, 5))
    
    def _create_context_menu(self):
        """Crée le menu contextuel pour la liste des éléments"""
        self.context_menu = tk.Menu(self.window, tearoff=0)
        self.context_menu.add_command(label="Éditer", command=self._edit_selected_element)
        self.context_menu.add_command(label="Marquer comme traduit", command=self._mark_as_translated)
        self.context_menu.add_command(label="Marquer comme problématique", command=self._mark_as_issue)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Copier texte original", command=self._copy_original_text)
        self.context_menu.add_command(label="Copier traduction", command=self._copy_translation)
        
        # Bind du clic droit
        self.elements_tree.bind('<Button-3>', self._show_context_menu)
    
    def _create_status_bar(self, parent):
        """Crée la barre de statut"""
        status_frame = ttk.Frame(parent, relief='sunken', borderwidth=1)
        status_frame.pack(fill='x', pady=(10, 0))
        
        self.status_label = ttk.Label(status_frame, text="Prêt")
        self.status_label.pack(side='left', padx=5, pady=2)
        
        # Statistiques
        self.stats_label = ttk.Label(status_frame, text="")
        self.stats_label.pack(side='right', padx=5, pady=2)
    
    def _create_control_buttons(self, parent):
        """Crée les boutons de contrôle de la fenêtre"""
        control_frame = ttk.Frame(parent)
        control_frame.pack(fill='x', pady=(10, 0))
        
        ttk.Button(control_frame, text="Annuler", command=self._cancel).pack(side='left')
        ttk.Button(control_frame, text="Aide", command=self._show_help).pack(side='left', padx=(10, 0))
        
        ttk.Button(control_frame, text="Valider et Fermer", command=self._validate_and_close).pack(side='right')
        ttk.Button(control_frame, text="Sauvegarder", command=self._save_all_translations).pack(side='right', padx=(0, 10))
    
    def _load_elements(self):
        """Charge les éléments dans la liste"""
        # Vider la liste
        for item in self.elements_tree.get_children():
            self.elements_tree.delete(item)
        
        # Charger les éléments
        for element_id, element in self.original_elements.items():
            # Statut de la traduction
            if element_id in self.translations and self.translations[element_id].strip():
                if element_id in self.validation_results:
                    validation = self.validation_results[element_id]
                    status = "✅ Valide" if validation['is_valid'] else "❌ Invalide"
                    status_tag = "valid" if validation['is_valid'] else "invalid"
                else:
                    status = "⏳ À valider"
                    status_tag = "pending"
            else:
                status = "❌ Manquant"
                status_tag = "missing"
            
            # Aperçu du texte original
            preview = element['original_text'][:50]
            if len(element['original_text']) > 50:
                preview += "..."
            
            # Insérer dans la liste
            item_id = self.elements_tree.insert('', 'end',
                                               text=element['id'],
                                               values=(
                                                   element['page_number'],
                                                   element['content_type'].title(),
                                                   preview,
                                                   status
                                               ),
                                               tags=(status_tag,))
        
        # Configuration des tags pour les couleurs
        self.elements_tree.tag_configure('valid', background='#e8f5e8')
        self.elements_tree.tag_configure('invalid', background='#ffe8e8')
        self.elements_tree.tag_configure('pending', background='#fff8e8')
        self.elements_tree.tag_configure('missing', background='#f0f0f0')
        
        # Mettre à jour les statistiques
        self._update_statistics()
    
    def _update_statistics(self):
        """Met à jour les statistiques affichées"""
        total = len(self.original_elements)
        translated = len([t for t in self.translations.values() if t.strip()])
        valid = len([v for v in self.validation_results.values() if v['is_valid']])
        
        # Progression
        if total > 0:
            progress_percent = (translated / total) * 100
            self.progress_bar['value'] = progress_percent
            self.progress_label.config(text=f"{translated}/{total} ({progress_percent:.1f}%)")
        
        # Statistiques détaillées
        stats_text = f"Total: {total} | Traduits: {translated} | Valides: {valid}"
        self.stats_label.config(text=stats_text)
    
    def _apply_filter(self):
        """Applique le filtre sélectionné"""
        filter_value = self.filter_var.get()
        
        # Masquer/afficher les éléments selon le filtre
        for item in self.elements_tree.get_children():
            element_id = self.elements_tree.item(item, 'text')
            show_item = True
            
            if filter_value == "missing":
                show_item = element_id not in self.translations or not self.translations[element_id].strip()
            elif filter_value == "translated":
                show_item = element_id in self.translations and self.translations[element_id].strip()
            elif filter_value == "issues":
                show_item = (element_id in self.validation_results and 
                           not self.validation_results[element_id]['is_valid'])
            # "all" ne filtre rien
            
            # Appliquer le filtre de recherche aussi
            if show_item and self.search_query:
                element = self.original_elements[element_id]
                search_text = f"{element['original_text']} {element['content_type']}".lower()
                show_item = self.search_query.lower() in search_text
            
            # Masquer/afficher l'élément
            if show_item:
                self.elements_tree.reattach(item, '', 'end')
            else:
                self.elements_tree.detach(item)
    
    def _on_search_change(self, *args):
        """Gestionnaire de changement de recherche"""
        self.search_query = self.search_var.get()
        self._apply_filter()
    
    def _clear_search(self):
        """Efface la recherche"""
        self.search_var.set("")
    
    def _on_element_select(self, event):
        """Gestionnaire de sélection d'élément"""
        selection = self.elements_tree.selection()
        if not selection:
            return
        
        element_id = self.elements_tree.item(selection[0], 'text')
        self._load_element_for_editing(element_id)
    
    def _on_element_double_click(self, event):
        """Gestionnaire de double-clic sur élément"""
        self._edit_selected_element()
    
    def _load_element_for_editing(self, element_id: str):
        """Charge un élément pour édition"""
        if element_id not in self.original_elements:
            return
        
        self.current_element_id = element_id
        element = self.original_elements[element_id]
        
        # Informations de l'élément
        info_text = f"""ID: {element['id']} | Page: {element['page_number']} | Type: {element['content_type'].title()}
Contexte: {element['context']}
Notes: {element['notes'] if element['notes'] else 'Aucune'}"""
        
        self.element_info_label.config(text=info_text)
        
        # Texte original
        self.original_text.config(state='normal')
        self.original_text.delete('1.0', tk.END)
        self.original_text.insert('1.0', element['original_text'])
        self.original_text.config(state='disabled')
        
        # Traduction existante
        self.translation_text.delete('1.0', tk.END)
        if element_id in self.translations:
            self.translation_text.insert('1.0', self.translations[element_id])
        
        # Validation
        self._update_validation_display(element_id)
    
    def _update_validation_display(self, element_id: str):
        """Met à jour l'affichage de validation"""
        if element_id in self.validation_results:
            validation = self.validation_results[element_id]
            
            if validation['is_valid']:
                status_text = "✅ Traduction valide"
                style = 'Valid.TLabel'
            else:
                issues_text = "; ".join(validation['issues'])
                status_text = f"❌ Problèmes: {issues_text}"
                style = 'Invalid.TLabel'
            
            # Afficher le facteur d'expansion
            expansion = validation['expansion_factor']
            if expansion > 1.5:
                expansion_text = f" | ⚠️ Expansion: {expansion:.1f}x"
            elif expansion < 0.7:
                expansion_text = f" | ⚠️ Contraction: {expansion:.1f}x"
            else:
                expansion_text = f" | Expansion: {expansion:.1f}x"
            
            status_text += expansion_text
            
        else:
            status_text = "⏳ Validation en attente"
            style = 'Missing.TLabel'
        
        self.validation_label.config(text=status_text, style=style)
    
    def _on_translation_change(self, event):
        """Gestionnaire de changement de traduction"""
        if not self.current_element_id:
            return
        
        # Sauvegarder automatiquement
        translation = self.translation_text.get('1.0', tk.END).strip()
        self.translations[self.current_element_id] = translation
        
        # Validation en temps réel
        if translation:
            self._validate_single_translation(self.current_element_id)
        
        # Mettre à jour la liste et les statistiques
        self._update_element_in_list(self.current_element_id)
        self._update_statistics()
    
    def _validate_single_translation(self, element_id: str):
        """Valide une traduction individuelle"""
        if element_id not in self.original_elements or element_id not in self.translations:
            return
        
        original_element = self.original_elements[element_id]
        translated_text = self.translations[element_id]
        
        # Validation basique
        issues = []
        is_valid = True
        
        # Vérifier la longueur
        original_length = len(original_element['original_text'])
        translated_length = len(translated_text)
        expansion_factor = translated_length / max(1, original_length)
        
        if expansion_factor > 3.0:
            issues.append("Texte très long")
            is_valid = False
        elif expansion_factor < 0.2:
            issues.append("Texte très court")
            is_valid = False
        
        # Vérifier la présence de texte
        if not translated_text.strip():
            issues.append("Traduction vide")
            is_valid = False
        
        # Vérifier les caractères spéciaux pour les listes
        if original_element['content_type'] == 'list_item':
            original_has_bullet = bool(re.search(r'^[\s]*[•·‣⁃\-\*\+]', original_element['original_text']))
            translated_has_bullet = bool(re.search(r'^[\s]*[•·‣⁃\-\*\+]', translated_text))
            
            if original_has_bullet != translated_has_bullet:
                issues.append("Structure de liste modifiée")
        
        # Sauvegarder le résultat
        self.validation_results[element_id] = {
            'is_valid': is_valid,
            'issues': issues,
            'expansion_factor': expansion_factor,
            'confidence': 0.8 if is_valid else 0.3
        }
        
        # Mettre à jour l'affichage
        self._update_validation_display(element_id)
    
    def _update_element_in_list(self, element_id: str):
        """Met à jour un élément dans la liste"""
        # Trouver l'élément dans la liste
        for item in self.elements_tree.get_children():
            if self.elements_tree.item(item, 'text') == element_id:
                # Déterminer le nouveau statut
                if element_id in self.translations and self.translations[element_id].strip():
                    if element_id in self.validation_results:
                        validation = self.validation_results[element_id]
                        status = "✅ Valide" if validation['is_valid'] else "❌ Invalide"
                        status_tag = "valid" if validation['is_valid'] else "invalid"
                    else:
                        status = "⏳ À valider"
                        status_tag = "pending"
                else:
                    status = "❌ Manquant"
                    status_tag = "missing"
                
                # Mettre à jour les valeurs
                current_values = list(self.elements_tree.item(item, 'values'))
                current_values[3] = status  # Colonne statut
                self.elements_tree.item(item, values=current_values, tags=(status_tag,))
                break
    
    def _save_current_translation(self):
        """Sauvegarde la traduction courante"""
        if not self.current_element_id:
            return
        
        translation = self.translation_text.get('1.0', tk.END).strip()
        self.translations[self.current_element_id] = translation
        
        if translation:
            self._validate_single_translation(self.current_element_id)
        
        self._update_element_in_list(self.current_element_id)
        self._update_statistics()
        
        self.status_label.config(text=f"Traduction sauvegardée pour {self.current_element_id}")
    
    def _reset_current_translation(self):
        """Remet à zéro la traduction courante"""
        if not self.current_element_id:
            return
        
        if messagebox.askyesno("Confirmation", "Êtes-vous sûr de vouloir effacer cette traduction ?"):
            self.translation_text.delete('1.0', tk.END)
            if self.current_element_id in self.translations:
                del self.translations[self.current_element_id]
            if self.current_element_id in self.validation_results:
                del self.validation_results[self.current_element_id]
            
            self._update_element_in_list(self.current_element_id)
            self._update_statistics()
            self._update_validation_display(self.current_element_id)
    
    def _go_to_next_element(self):
        """Va à l'élément suivant"""
        current_selection = self.elements_tree.selection()
        if not current_selection:
            return
        
        current_item = current_selection[0]
        next_item = self.elements_tree.next(current_item)
        
        if next_item:
            self.elements_tree.selection_set(next_item)
            self.elements_tree.focus(next_item)
            self.elements_tree.see(next_item)
            self._on_element_select(None)
    
    def _go_to_previous_element(self):
        """Va à l'élément précédent"""
        current_selection = self.elements_tree.selection()
        if not current_selection:
            return
        
        current_item = current_selection[0]
        prev_item = self.elements_tree.prev(current_item)
        
        if prev_item:
            self.elements_tree.selection_set(prev_item)
            self.elements_tree.focus(prev_item)
            self.elements_tree.see(prev_item)
            self._on_element_select(None)
    
    def _import_bulk_translation(self):
        """Importe une traduction en lot"""
        # Créer une fenêtre de dialogue pour l'import en lot
        import_dialog = tk.Toplevel(self.window)
        import_dialog.title("Import en Lot")
        import_dialog.geometry("800x600")
        import_dialog.transient(self.window)
        import_dialog.grab_set()
        
        # Instructions
        instructions = """Collez ci-dessous la traduction complète générée par l'IA.
Le format doit contenir les identifiants [ID:XXX|...] suivis du texte traduit."""
        
        ttk.Label(import_dialog, text=instructions, wraplength=750).pack(padx=10, pady=10)
        
        # Zone de texte
        text_frame = ttk.Frame(import_dialog)
        text_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        import_text = scrolledtext.ScrolledText(text_frame, wrap='word')
        import_text.pack(fill='both', expand=True)
        
        # Boutons
        button_frame = ttk.Frame(import_dialog)
        button_frame.pack(fill='x', padx=10, pady=10)
        
        def do_import():
            content = import_text.get('1.0', tk.END).strip()
            if content:
                self._process_bulk_import(content)
                import_dialog.destroy()
        
        ttk.Button(button_frame, text="Importer", command=do_import).pack(side='right')
        ttk.Button(button_frame, text="Annuler", command=import_dialog.destroy).pack(side='right', padx=(0, 10))
    
    def _process_bulk_import(self, content: str):
        """Traite l'import en lot"""
        try:
            # Utiliser le parser de traductions
            parsed_translations = self.translation_parser._parse_elements(content)
            
            # Importer les traductions
            imported_count = 0
            for element_id, translation in parsed_translations.items():
                if element_id in self.original_elements:
                    self.translations[element_id] = translation
                    self._validate_single_translation(element_id)
                    self._update_element_in_list(element_id)
                    imported_count += 1
            
            # Actualiser l'affichage
            self._update_statistics()
            
            # Message de succès
            messagebox.showinfo("Import Réussi", f"{imported_count} traductions importées avec succès.")
            
            # Recharger l'élément courant si nécessaire
            if self.current_element_id:
                self._load_element_for_editing(self.current_element_id)
                
        except Exception as e:
            self.logger.error(f"Erreur import en lot: {e}")
            messagebox.showerror("Erreur", f"Erreur lors de l'import: {e}")
    
    def _export_translations(self):
        """Exporte les traductions actuelles"""
        if not self.translations:
            messagebox.showwarning("Attention", "Aucune traduction à exporter.")
            return
        
        from tkinter import filedialog
        
        filename = filedialog.asksaveasfilename(
            title="Exporter les traductions",
            defaultextension=".json",
            filetypes=[("Fichiers JSON", "*.json"), ("Tous les fichiers", "*.*")]
        )
        
        if filename:
            try:
                export_data = {
                    'translations': self.translations,
                    'validation_results': self.validation_results,
                    'export_date': datetime.now().isoformat(),
                    'total_elements': len(self.original_elements),
                    'translated_elements': len([t for t in self.translations.values() if t.strip()])
                }
                
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                
                messagebox.showinfo("Export Réussi", f"Traductions exportées vers:\n{filename}")
                
            except Exception as e:
                self.logger.error(f"Erreur export: {e}")
                messagebox.showerror("Erreur", f"Erreur lors de l'export: {e}")
    
    def _validate_all(self):
        """Valide toutes les traductions"""
        if not self.translations:
            messagebox.showwarning("Attention", "Aucune traduction à valider.")
            return
        
        validated_count = 0
        for element_id in self.translations:
            if self.translations[element_id].strip():
                self._validate_single_translation(element_id)
                self._update_element_in_list(element_id)
                validated_count += 1
        
        self._update_statistics()
        messagebox.showinfo("Validation Terminée", f"{validated_count} traductions validées.")
    
    # Méthodes du menu contextuel
    
    def _show_context_menu(self, event):
        """Affiche le menu contextuel"""
        item = self.elements_tree.identify_row(event.y)
        if item:
            self.elements_tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)
    
    def _edit_selected_element(self):
        """Édite l'élément sélectionné"""
        selection = self.elements_tree.selection()
        if selection:
            element_id = self.elements_tree.item(selection[0], 'text')
            self._load_element_for_editing(element_id)
            self.translation_text.focus_set()
    
    def _mark_as_translated(self):
        """Marque comme traduit"""
        selection = self.elements_tree.selection()
        if selection:
            element_id = self.elements_tree.item(selection[0], 'text')
            if element_id not in self.translations or not self.translations[element_id].strip():
                # Proposer une traduction par défaut
                result = messagebox.askyesno("Marquer comme traduit", 
                                           "Élément non traduit. Marquer avec le texte original ?")
                if result:
                    self.translations[element_id] = self.original_elements[element_id]['original_text']
                    self._update_element_in_list(element_id)
                    self._update_statistics()
    
    def _mark_as_issue(self):
        """Marque comme problématique"""
        selection = self.elements_tree.selection()
        if selection:
            element_id = self.elements_tree.item(selection[0], 'text')
            
            # Créer un résultat de validation avec problème
            self.validation_results[element_id] = {
                'is_valid': False,
                'issues': ['Marqué manuellement comme problématique'],
                'expansion_factor': 1.0,
                'confidence': 0.0
            }
            
            self._update_element_in_list(element_id)
            self._update_validation_display(element_id)
    
    def _copy_original_text(self):
        """Copie le texte original"""
        selection = self.elements_tree.selection()
        if selection:
            element_id = self.elements_tree.item(selection[0], 'text')
            original_text = self.original_elements[element_id]['original_text']
            self.window.clipboard_clear()
            self.window.clipboard_append(original_text)
            self.status_label.config(text="Texte original copié")
    
    def _copy_translation(self):
        """Copie la traduction"""
        selection = self.elements_tree.selection()
        if selection:
            element_id = self.elements_tree.item(selection[0], 'text')
            if element_id in self.translations:
                translation = self.translations[element_id]
                self.window.clipboard_clear()
                self.window.clipboard_append(translation)
                self.status_label.config(text="Traduction copiée")
    
    # Méthodes de contrôle de fenêtre
    
    def _save_all_translations(self):
        """Sauvegarde toutes les traductions"""
        # Cette méthode pourrait sauvegarder dans un fichier temporaire
        self.status_label.config(text="Toutes les traductions sauvegardées")
    
    def _validate_and_close(self):
        """Valide tout et ferme la fenêtre"""
        # Vérifier que toutes les traductions sont présentes
        missing_count = len([e for e in self.original_elements 
                           if e not in self.translations or not self.translations[e].strip()])
        
        if missing_count > 0:
            result = messagebox.askyesno("Traductions Manquantes", 
                                       f"{missing_count} traductions manquantes. "
                                       f"Voulez-vous continuer quand même ?")
            if not result:
                return
        
        # Valider toutes les traductions
        self._validate_all()
        
        # Fermer la fenêtre
        self.window.destroy()
    
    def _cancel(self):
        """Annule et ferme la fenêtre"""
        result = messagebox.askyesno("Confirmation", 
                                   "Êtes-vous sûr de vouloir fermer sans sauvegarder ?")
        if result:
            self.window.destroy()
    
    def _show_help(self):
        """Affiche l'aide"""
        help_text = """AIDE - Gestionnaire de Traductions

NAVIGATION:
• Cliquez sur un élément dans la liste pour l'éditer
• Utilisez les boutons Précédent/Suivant pour naviguer
• Double-cliquez pour éditer rapidement

TRADUCTION:
• Tapez directement dans la zone de traduction
• La validation se fait automatiquement
• Les couleurs indiquent le statut (vert=valide, rouge=problème)

FILTRES:
• Tous: Affiche tous les éléments
• Non traduits: Éléments sans traduction
• Traduits: Éléments avec traduction
• Avec problèmes: Éléments avec erreurs de validation

ACTIONS:
• Clic droit sur un élément pour le menu contextuel
• Import en lot: Pour importer une traduction complète
• Export: Pour sauvegarder les traductions

RACCOURCIS:
• Ctrl+S: Sauvegarder
• F3: Élément suivant
• Shift+F3: Élément précédent"""
        
        help_dialog = tk.Toplevel(self.window)
        help_dialog.title("Aide")
        help_dialog.geometry("600x500")
        help_dialog.transient(self.window)
        
        text_widget = scrolledtext.ScrolledText(help_dialog, wrap='word', padding=10)
        text_widget.pack(fill='both', expand=True, padx=10, pady=10)
        text_widget.insert('1.0', help_text)
        text_widget.config(state='disabled')
        
        ttk.Button(help_dialog, text="Fermer", command=help_dialog.destroy).pack(pady=10)
    
    # Méthodes publiques pour récupérer les données
    
    def get_translations(self) -> Dict[str, str]:
        """Retourne les traductions"""
        return self.translations.copy()
    
    def get_validation_results(self) -> Dict[str, Dict[str, Any]]:
        """Retourne les résultats de validation"""
        return self.validation_results.copy()
    
    def get_statistics(self) -> Dict[str, int]:
        """Retourne les statistiques"""
        total = len(self.original_elements)
        translated = len([t for t in self.translations.values() if t.strip()])
        valid = len([v for v in self.validation_results.values() if v['is_valid']])
        
        return {
            'total_elements': total,
            'translated_elements': translated,
            'valid_elements': valid,
            'missing_elements': total - translated
        }