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
    def set_completion_list(self, completion_list):
        self._completion_list = sorted(completion_list)
        self._hits = []
        self._hit_index = 0
        self.position = 0
        self.bind('<KeyRelease>', self.handle_keyrelease)
        self['values'] = self._completion_list

    def autocomplete(self, delta=0):
        if delta: self.delete(self.position, tk.END)
        else: self.position = len(self.get())
        
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
        if event.keysym in ("BackSpace", "Left", "Right", "Up", "Down", "Return", "KP_Enter"): return
        self.autocomplete()


class FontDialog:
    def __init__(self, parent, font_manager, missing_fonts_report):
        self.parent = parent
        self.font_manager = font_manager
        self.report = missing_fonts_report
        self.logger = logging.getLogger(__name__)
        self.user_choices = {}
        
        self.window = tk.Toplevel(parent)
        self.window.title("Gestion des Polices Manquantes (Action Requise)")
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
        instructions = "ACTION REQUISE : Le PDF utilise des polices non installées. Vous devez choisir une police de remplacement pour CHAQUE ligne avant de continuer."
        ttk.Label(main_frame, text=instructions, wraplength=780, font=("", 9, "bold")).pack(fill="x", pady=(0, 10))
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill="both", expand=True)
        
        self.tree = ttk.Treeview(tree_frame, columns=("missing", "replacement"), show="headings")
        self.tree.heading("missing", text="Police Manquante"); self.tree.heading("replacement", text="Police de Remplacement (Votre Choix)")
        self.tree.pack(side="left", fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y"); self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.bind("<Double-1>", self._on_edit_cell)

        button_frame = ttk.Frame(main_frame); button_frame.pack(fill="x", pady=(10, 0))
        ttk.Button(button_frame, text="Annuler le Processus", command=self._on_cancel).pack(side="right")
        ttk.Button(button_frame, text="Valider et Continuer", command=self._on_validate).pack(side="right", padx=(0, 10))

    def _populate_fonts(self):
        for font_name in self.report['missing_fonts']:
            # On pré-remplit avec un mapping déjà sauvegardé, sinon on laisse vide pour forcer un choix.
            suggestion = self.font_manager.get_font_mapping(font_name) or ""
            
            self.user_choices[font_name] = tk.StringVar(value=suggestion)
            self.tree.insert("", "end", values=(font_name, suggestion))

    def _on_edit_cell(self, event):
        item_id = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        if not item_id or column != "#2": return

        missing_font = self.tree.item(item_id, "values")[0]
        x, y, width, height = self.tree.bbox(item_id, column)
        
        combo = AutocompleteCombobox(self.tree)
        # L'utilisateur ne peut choisir que parmi les polices que le système connaît.
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
        """
        Fonction critique : Valide les choix de l'utilisateur AVANT de sauvegarder et de fermer.
        C'est le gardien qui empêche les données invalides de continuer.
        """
        errors = []
        all_system_fonts = self.font_manager.get_all_available_fonts()
        mappings_to_save = {}

        for item_id in self.tree.get_children():
            font_name, replacement = self.tree.item(item_id, "values")
            
            # Vérification 1: L'utilisateur a-t-il fait un choix ?
            if not replacement or not replacement.strip():
                errors.append(f"- Aucune police n'a été choisie pour '{font_name}'.")
                continue

            # Vérification 2: Le choix de l'utilisateur est-il une police qui existe réellement ?
            if replacement not in all_system_fonts:
                errors.append(f"- La police '{replacement}' choisie pour '{font_name}' n'est pas une police système valide.")
                continue
            
            # Si tout est bon, on prépare la sauvegarde
            mappings_to_save[font_name] = replacement

        # Si des erreurs ont été trouvées, on bloque le processus et on informe l'utilisateur.
        if errors:
            error_message = "Impossible de valider. Veuillez corriger les erreurs suivantes :\n\n" + "\n".join(errors)
            messagebox.showerror("Erreurs de Validation des Polices", error_message, parent=self.window)
            return  # On ne ferme PAS la fenêtre. L'utilisateur doit corriger.

        # Si AUCUNE erreur n'a été trouvée, on peut sauvegarder et fermer.
        try:
            for original_font, replacement_font in mappings_to_save.items():
                self.font_manager.create_font_mapping(original_font, replacement_font)
            
            messagebox.showinfo("Succès", "Correspondances de polices validées et sauvegardées.", parent=self.window)
            self.window.destroy() # Le processus peut continuer en toute sécurité.
        except Exception as e:
            messagebox.showerror("Erreur", f"Une erreur est survenue lors de la sauvegarde : {e}", parent=self.window)

    def _on_cancel(self):
        # Annuler signifie ici abandonner TOUT le processus de traduction. C'est une action bloquante.
        if messagebox.askyesno("Confirmation d'Annulation", 
                               "Ceci annulera l'ensemble du processus d'analyse et de traduction.\n\nÊtes-vous sûr de vouloir abandonner ?", 
                               icon='warning', parent=self.window):
            # Pour réellement annuler, il faudrait une communication avec la fenêtre principale.
            # Pour l'instant, la destruction de la fenêtre arrêtera le flux.
            self.user_choices = {} # Efface les choix
            self.window.destroy()

    def show(self):
        self.parent.wait_window(self.window)
