#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Dialogue de Gestion des Polices
Interface pour gérer les polices manquantes et leurs remplacements.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging

class AutocompleteCombobox(ttk.Combobox):
    # ... (le code de cette classe reste inchangé) ...
    def set_completion_list(self, completion_list):
        self._completion_list = sorted(completion_list)
        self._hits = []
        self._hit_index = 0
        self.position = 0
        self.bind('<KeyRelease>', self.handle_keyrelease)
        self['values'] = self._completion_list

    def autocomplete(self, delta=0):
        if delta:
            self.delete(self.position, tk.END)
        else:
            self.position = len(self.get())
        
        _hits = [item for item in self._completion_list if item.lower().startswith(self.get().lower())]
        
        if _hits != self._hits:
            self._hit_index = 0
            self._hits = _hits
        
        if self._hits:
            self._hit_index = (self._hit_index + delta) % len(self._hits)
            current_text = self.get()
            self.delete(0, tk.END)
            self.insert(0, self._hits[self._hit_index])
            self.icursor(len(current_text))
            
    def handle_keyrelease(self, event):
        if event.keysym in ("BackSpace", "Left", "Right", "Up", "Down", "Return", "KP_Enter"):
            return
        self.autocomplete()

class FontDialog:
    def __init__(self, parent, font_manager, missing_fonts_report):
        self.parent = parent
        self.font_manager = font_manager
        self.report = missing_fonts_report
        self.logger = logging.getLogger(__name__)
        self.user_choices = {}
        
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
        # ... (cette fonction reste inchangée) ...
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill="both", expand=True)
        instructions = "Certaines polices sont manquantes. Choisissez un remplacement pour chacune."
        ttk.Label(main_frame, text=instructions, wraplength=780).pack(fill="x", pady=(0, 10))
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill="both", expand=True)
        
        self.tree = ttk.Treeview(tree_frame, columns=("missing", "replacement"), show="headings")
        self.tree.heading("missing", text="Police Manquante"); self.tree.heading("replacement", text="Police de Remplacement")
        self.tree.pack(side="left", fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y"); self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.bind("<Double-1>", self._on_edit_cell)

        button_frame = ttk.Frame(main_frame); button_frame.pack(fill="x", pady=(10, 0))
        ttk.Button(button_frame, text="Annuler", command=self._on_cancel).pack(side="right")
        ttk.Button(button_frame, text="Valider et Sauvegarder", command=self._on_validate).pack(side="right", padx=(0, 10))

    def _populate_fonts(self):
        for font_name in self.report['missing_fonts']:
            # --- MODIFICATION ---
            # Priorité 1: Mapping déjà sauvegardé
            # Priorité 2: Suggestion de l'analyseur
            # Priorité 3: Arial par défaut
            saved_mapping = self.font_manager.get_font_mapping(font_name)
            if saved_mapping:
                suggestion = saved_mapping
            else:
                suggestion = self.report['suggestions'].get(font_name, [{}])[0].get('font_name', "Arial")
            # --- FIN MODIFICATION ---
            self.user_choices[font_name] = tk.StringVar(value=suggestion)
            self.tree.insert("", "end", values=(font_name, suggestion))

    def _on_edit_cell(self, event):
        # ... (cette fonction reste inchangée) ...
        item_id = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        if not item_id or column != "#2": return

        missing_font = self.tree.item(item_id, "values")[0]
        x, y, width, height = self.tree.bbox(item_id, column)
        
        combo = AutocompleteCombobox(self.tree)
        combo.set_completion_list(self.font_manager.get_all_available_fonts())
        combo.set(self.user_choices[missing_font].get())
        combo.place(x=x, y=y, width=width, height=height)
        combo.focus_set()
        
        def on_combo_close(event=None):
            new_value = combo.get()
            self.tree.set(item_id, "replacement", new_value)
            self.user_choices[missing_font].set(new_value)
            combo.destroy()

        combo.bind("<<ComboboxSelected>>", on_combo_close)
        combo.bind("<FocusOut>", on_combo_close)
        combo.bind("<Return>", on_combo_close)
        combo.bind("<KP_Enter>", on_combo_close)


    def _on_validate(self):
        # ... (cette fonction reste inchangée) ...
        try:
            for item_id in self.tree.get_children():
                font_name, replacement = self.tree.item(item_id, "values")
                self.font_manager.create_font_mapping(font_name, replacement)
            
            messagebox.showinfo("Succès", "Correspondances de polices sauvegardées.", parent=self.window)
            self.window.destroy()
        except Exception as e:
            messagebox.showerror("Erreur", f"Une erreur est survenue: {e}", parent=self.window)

    def _on_cancel(self):
        # ... (cette fonction reste inchangée) ...
        if messagebox.askyesno("Confirmation", "Annuler ? Les polices manquantes seront remplacées par défaut.", parent=self.window):
            self.window.destroy()

    def show(self):
        self.parent.wait_window(self.window)
