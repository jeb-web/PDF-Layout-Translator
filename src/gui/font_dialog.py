#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Dialogue de Gestion des Polices
Interface pour gérer les polices manquantes et leurs remplacements.

Auteur: L'OréalGPT
Version: 1.0.0
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging

class FontDialog:
    def __init__(self, parent, font_manager, missing_fonts_report):
        self.parent = parent
        self.font_manager = font_manager
        self.report = missing_fonts_report
        self.logger = logging.getLogger(__name__)
        
        self.user_choices = {} # Dictionnaire pour stocker les choix de l'utilisateur
        
        self.window = tk.Toplevel(parent)
        self.window.title("Gestion des Polices Manquantes")
        self.window.geometry("800x600")
        self.window.minsize(600, 400)
        self.window.transient(parent)
        self.window.grab_set()
        
        self._create_widgets()
        self._populate_fonts()
        
        self.window.protocol("WM_DELETE_WINDOW", self._on_cancel)
    
    def _create_widgets(self):
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill="both", expand=True)

        # Instructions
        instructions = "Certaines polices du document sont manquantes. Veuillez choisir une police de remplacement pour chacune."
        ttk.Label(main_frame, text=instructions, wraplength=780).pack(fill="x", pady=(0, 10))
        
        # Treeview pour afficher les polices
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill="both", expand=True)
        
        self.tree = ttk.Treeview(tree_frame, columns=("missing", "replacement"), show="headings")
        self.tree.heading("missing", text="Police Manquante")
        self.tree.heading("replacement", text="Police de Remplacement (votre choix)")
        self.tree.pack(side="left", fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.bind("<Double-1>", self._on_edit_cell)

        # Boutons de contrôle
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(10, 0))
        
        ttk.Button(button_frame, text="Annuler", command=self._on_cancel).pack(side="right")
        ttk.Button(button_frame, text="Valider et Sauvegarder", command=self._on_validate).pack(side="right", padx=(0, 10))

    def _populate_fonts(self):
        for font_name in self.report['missing_fonts']:
            # La suggestion est la première de la liste, si elle existe
            suggestion = self.report['suggestions'].get(font_name, [{}])[0].get('font_name', "Arial")
            self.user_choices[font_name] = tk.StringVar(value=suggestion)
            self.tree.insert("", "end", values=(font_name, suggestion))

    def _on_edit_cell(self, event):
        item_id = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        
        if not item_id or column != "#2": # Uniquement éditable sur la 2ème colonne
            return

        # Créer le menu déroulant de remplacement
        missing_font = self.tree.item(item_id, "values")[0]
        x, y, width, height = self.tree.bbox(item_id, column)
        
        available_fonts = self.font_manager.get_all_available_fonts()
        
        combo = ttk.Combobox(self.tree, values=available_fonts, textvariable=self.user_choices[missing_font])
        combo.place(x=x, y=y, width=width, height=height)
        combo.focus_set()
        
        def on_combo_close(event):
            self.tree.set(item_id, "replacement", combo.get())
            combo.destroy()

        combo.bind("<<ComboboxSelected>>", on_combo_close)
        combo.bind("<FocusOut>", on_combo_close)

    def _on_validate(self):
        try:
            for font_name, choice_var in self.user_choices.items():
                replacement = choice_var.get()
                if replacement:
                    self.font_manager.create_font_mapping(font_name, replacement)
            
            messagebox.showinfo("Succès", "Les correspondances de polices ont été sauvegardées.", parent=self.window)
            self.window.destroy()
        except Exception as e:
            self.logger.error(f"Erreur lors de la sauvegarde des polices: {e}")
            messagebox.showerror("Erreur", f"Une erreur est survenue: {e}", parent=self.window)

    def _on_cancel(self):
        if messagebox.askyesno("Confirmation", "Êtes-vous sûr de vouloir annuler ?\nLes polices manquantes seront remplacées par des polices par défaut.", parent=self.window):
            self.window.destroy()

    def show(self):
        # Bloque l'exécution jusqu'à ce que la fenêtre soit fermée
        self.parent.wait_window(self.window)
