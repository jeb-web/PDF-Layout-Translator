#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Fenêtre de prévisualisation
Interface de prévisualisation du PDF avec comparaison avant/après traduction

Auteur: L'OréalGPT
Version: 1.0.0
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import threading
import tempfile
import fitz  # PyMuPDF
from PIL import Image, ImageTk
import io

class PreviewWindow:
    """Fenêtre de prévisualisation PDF avec comparaison"""
    
    def __init__(self, parent, original_pdf_path: Path, layout_data: Dict[str, Any] = None,
                 validated_translations: Dict[str, Any] = None, pdf_reconstructor=None):
        """
        Initialise la fenêtre de prévisualisation
        
        Args:
            parent: Fenêtre parent
            original_pdf_path: Chemin vers le PDF original
            layout_data: Données de mise en page (optionnel)
            validated_translations: Traductions validées (optionnel)
            pdf_reconstructor: Reconstructeur PDF (optionnel)
        """
        self.parent = parent
        self.original_pdf_path = Path(original_pdf_path)
        self.layout_data = layout_data
        self.validated_translations = validated_translations
        self.pdf_reconstructor = pdf_reconstructor
        self.logger = logging.getLogger(__name__)
        
        # Documents PyMuPDF
        self.original_doc: Optional[fitz.Document] = None
        self.preview_doc: Optional[fitz.Document] = None
        self.preview_pdf_path: Optional[Path] = None
        
        # Variables d'interface
        self.current_page = 0
        self.zoom_level = 1.0
        self.comparison_mode = True  # True = côte à côte, False = onglets
        self.show_overlays = True  # Afficher les overlays de mise en page
        
        # Cache des images de page
        self.page_cache = {}  # {(page_num, zoom, doc_type): PhotoImage}
        self.max_cache_size = 20
        
        # Variables de contrôle
        self.loading = False
        
        # Créer la fenêtre
        self._create_window()
        
        # Charger les documents
        self._load_documents()
        
        self.logger.info("Fenêtre de prévisualisation initialisée")
    
    def _create_window(self):
        """Crée la fenêtre de prévisualisation"""
        self.window = tk.Toplevel(self.parent)
        self.window.title("Aperçu PDF - Comparaison")
        self.window.geometry("1600x1000")
        self.window.minsize(1200, 800)
        
        # Configuration de la fenêtre
        self.window.transient(self.parent)
        self.window.grab_set()
        
        # Créer l'interface
        self._create_widgets()
        
        # Centrer sur le parent
        self.window.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - (1600 // 2)
        y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - (1000 // 2)
        self.window.geometry(f"1600x1000+{x}+{y}")
        
        # Gérer la fermeture
        self.window.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _create_widgets(self):
        """Crée les widgets de l'interface"""
        
        # Frame principal
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Barre d'outils
        self._create_toolbar(main_frame)
        
        # Zone de contenu principal
        self._create_content_area(main_frame)
        
        # Barre de statut
        self._create_status_bar(main_frame)
        
        # Boutons de contrôle
        self._create_control_buttons(main_frame)
    
    def _create_toolbar(self, parent):
        """Crée la barre d'outils"""
        toolbar_frame = ttk.Frame(parent)
        toolbar_frame.pack(fill='x', pady=(0, 10))
        
        # Navigation de pages
        nav_frame = ttk.LabelFrame(toolbar_frame, text="Navigation", padding=5)
        nav_frame.pack(side='left', fill='y')
        
        ttk.Button(nav_frame, text="◀◀", command=self._first_page, width=4).pack(side='left', padx=1)
        ttk.Button(nav_frame, text="◀", command=self._previous_page, width=4).pack(side='left', padx=1)
        
        # Sélecteur de page
        self.page_var = tk.StringVar()
        self.page_var.trace('w', self._on_page_change)
        page_entry = ttk.Entry(nav_frame, textvariable=self.page_var, width=4, justify='center')
        page_entry.pack(side='left', padx=5)
        
        self.page_total_label = ttk.Label(nav_frame, text="/ 0")
        self.page_total_label.pack(side='left')
        
        ttk.Button(nav_frame, text="▶", command=self._next_page, width=4).pack(side='left', padx=1)
        ttk.Button(nav_frame, text="▶▶", command=self._last_page, width=4).pack(side='left', padx=1)
        
        # Zoom
        zoom_frame = ttk.LabelFrame(toolbar_frame, text="Zoom", padding=5)
        zoom_frame.pack(side='left', fill='y', padx=(10, 0))
        
        ttk.Button(zoom_frame, text="−", command=self._zoom_out, width=3).pack(side='left', padx=1)
        
        self.zoom_var = tk.StringVar(value="100%")
        zoom_combo = ttk.Combobox(zoom_frame, textvariable=self.zoom_var, width=8,
                                 values=["50%", "75%", "100%", "125%", "150%", "200%"])
        zoom_combo.pack(side='left', padx=5)
        zoom_combo.bind('<<ComboboxSelected>>', self._on_zoom_change)
        
        ttk.Button(zoom_frame, text="+", command=self._zoom_in, width=3).pack(side='left', padx=1)
        ttk.Button(zoom_frame, text="Ajuster", command=self._fit_to_window, width=8).pack(side='left', padx=5)
        
        # Mode d'affichage
        display_frame = ttk.LabelFrame(toolbar_frame, text="Affichage", padding=5)
        display_frame.pack(side='left', fill='y', padx=(10, 0))
        
        self.comparison_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(display_frame, text="Comparaison", variable=self.comparison_var,
                       command=self._toggle_comparison_mode).pack(side='left', padx=5)
        
        self.overlays_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(display_frame, text="Overlays", variable=self.overlays_var,
                       command=self._toggle_overlays).pack(side='left', padx=5)
        
        # Actions
        actions_frame = ttk.LabelFrame(toolbar_frame, text="Actions", padding=5)
        actions_frame.pack(side='right', fill='y')
        
        ttk.Button(actions_frame, text="Générer Aperçu", command=self._generate_preview).pack(side='left', padx=2)
        ttk.Button(actions_frame, text="Exporter Image", command=self._export_page_image).pack(side='left', padx=2)
        ttk.Button(actions_frame, text="Plein Écran", command=self._toggle_fullscreen).pack(side='left', padx=2)
    
    def _create_content_area(self, parent):
        """Crée la zone de contenu principal"""
        
        # Notebook pour les modes d'affichage
        self.content_notebook = ttk.Notebook(parent)
        self.content_notebook.pack(fill='both', expand=True, pady=(0, 10))
        
        # Mode comparaison côte à côte
        self._create_comparison_view()
        
        # Mode onglets séparés
        self._create_tabbed_view()
        
        # Sélectionner le mode par défaut
        self.content_notebook.select(0)  # Comparaison
    
    def _create_comparison_view(self):
        """Crée la vue de comparaison côte à côte"""
        comparison_frame = ttk.Frame(self.content_notebook)
        self.content_notebook.add(comparison_frame, text="Comparaison")
        
        # PanedWindow pour diviser l'espace
        paned = ttk.PanedWindow(comparison_frame, orient='horizontal')
        paned.pack(fill='both', expand=True)
        
        # Frame pour le PDF original
        original_frame = ttk.LabelFrame(paned, text="Original", padding=5)
        self._create_pdf_viewer(original_frame, "original")
        paned.add(original_frame, weight=1)
        
        # Frame pour le PDF traduit
        translated_frame = ttk.LabelFrame(paned, text="Traduit", padding=5)
        self._create_pdf_viewer(translated_frame, "translated")
        paned.add(translated_frame, weight=1)
        
        # Stocker les références
        self.comparison_paned = paned
        self.original_frame = original_frame
        self.translated_frame = translated_frame
    
    def _create_tabbed_view(self):
        """Crée la vue avec onglets séparés"""
        tabbed_frame = ttk.Frame(self.content_notebook)
        self.content_notebook.add(tabbed_frame, text="Onglets Séparés")
        
        # Notebook interne pour les PDFs
        pdf_notebook = ttk.Notebook(tabbed_frame)
        pdf_notebook.pack(fill='both', expand=True)
        
        # Onglet original
        original_tab = ttk.Frame(pdf_notebook)
        pdf_notebook.add(original_tab, text="Original")
        self._create_pdf_viewer(original_tab, "original_tab")
        
        # Onglet traduit
        translated_tab = ttk.Frame(pdf_notebook)
        pdf_notebook.add(translated_tab, text="Traduit")
        self._create_pdf_viewer(translated_tab, "translated_tab")
        
        self.pdf_notebook = pdf_notebook
    
    def _create_pdf_viewer(self, parent, viewer_id: str):
        """Crée un visualiseur PDF dans le frame donné"""
        
        # Frame avec scrollbars
        canvas_frame = ttk.Frame(parent)
        canvas_frame.pack(fill='both', expand=True)
        
        # Canvas pour afficher le PDF
        canvas = tk.Canvas(canvas_frame, bg='white')
        
        # Scrollbars
        v_scroll = ttk.Scrollbar(canvas_frame, orient='vertical', command=canvas.yview)
        h_scroll = ttk.Scrollbar(canvas_frame, orient='horizontal', command=canvas.xview)
        canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        # Placement des widgets
        canvas.grid(row=0, column=0, sticky='nsew')
        v_scroll.grid(row=0, column=1, sticky='ns')
        h_scroll.grid(row=1, column=0, sticky='ew')
        
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)
        
        # Bind des événements
        canvas.bind('<Button-1>', lambda e: canvas.focus_set())
        canvas.bind('<MouseWheel>', self._on_mousewheel)
        canvas.bind('<Control-MouseWheel>', self._on_ctrl_mousewheel)
        
        # Stocker les références
        setattr(self, f'{viewer_id}_canvas', canvas)
        setattr(self, f'{viewer_id}_frame', canvas_frame)
        
        # Frame interne pour le contenu
        content_frame = ttk.Frame(canvas)
        canvas.create_window(0, 0, anchor='nw', window=content_frame)
        setattr(self, f'{viewer_id}_content', content_frame)
        
        # Label pour l'image de la page
        page_label = ttk.Label(content_frame)
        page_label.pack()
        setattr(self, f'{viewer_id}_label', page_label)
    
    def _create_status_bar(self, parent):
        """Crée la barre de statut"""
        status_frame = ttk.Frame(parent, relief='sunken', borderwidth=1)
        status_frame.pack(fill='x', pady=(10, 0))
        
        self.status_label = ttk.Label(status_frame, text="Prêt")
        self.status_label.pack(side='left', padx=5, pady=2)
        
        # Informations sur le document
        self.doc_info_label = ttk.Label(status_frame, text="")
        self.doc_info_label.pack(side='right', padx=5, pady=2)
        
        # Indicateur de chargement
        self.loading_progress = ttk.Progressbar(status_frame, length=100, mode='indeterminate')
        self.loading_progress.pack(side='right', padx=5, pady=2)
    
    def _create_control_buttons(self, parent):
        """Crée les boutons de contrôle"""
        control_frame = ttk.Frame(parent)
        control_frame.pack(fill='x', pady=(10, 0))
        
        ttk.Button(control_frame, text="Aide", command=self._show_help).pack(side='left')
        
        ttk.Button(control_frame, text="Actualiser", command=self._refresh_preview).pack(side='right', padx=(10, 0))
        ttk.Button(control_frame, text="Fermer", command=self._on_closing).pack(side='right')
    
    def _load_documents(self):
        """Charge les documents PDF"""
        def load_thread():
            try:
                self._set_loading(True, "Chargement du PDF original...")
                
                # Charger le document original
                self.original_doc = fitz.open(self.original_pdf_path)
                
                # Mettre à jour l'interface
                self.window.after(0, self._update_page_info)
                self.window.after(0, lambda: self._set_page(0))
                
                # Générer l'aperçu si possible
                if self.layout_data and self.validated_translations:
                    self.window.after(0, self._generate_preview)
                
            except Exception as e:
                self.logger.error(f"Erreur chargement documents: {e}")
                self.window.after(0, lambda e=e: messagebox.showerror("Erreur", f"Erreur lors du chargement: {e}"))
            finally:
                self.window.after(0, lambda: self._set_loading(False))
        
        threading.Thread(target=load_thread, daemon=True).start()
    
    def _generate_preview(self):
        """Génère l'aperçu du PDF traduit"""
        if not self.pdf_reconstructor or not self.layout_data or not self.validated_translations:
            messagebox.showwarning("Attention", "Données de traduction incomplètes.")
            return
        
        def generate_thread():
            try:
                self._set_loading(True, "Génération de l'aperçu traduit...")
                
                # Créer un fichier temporaire pour l'aperçu
                temp_dir = Path(tempfile.gettempdir()) / "pdf_translator_preview"
                temp_dir.mkdir(exist_ok=True)
                
                preview_path = temp_dir / f"preview_{self.original_pdf_path.stem}.pdf"
                
                # Reconstruire le PDF
                result = self.pdf_reconstructor.reconstruct_pdf(
                    self.original_pdf_path,
                    self.layout_data,
                    self.validated_translations,
                    preview_path,
                    preserve_original=False
                )
                
                if result.success:
                    # Charger le document d'aperçu
                    self.preview_doc = fitz.open(preview_path)
                    self.preview_pdf_path = preview_path
                    
                    # Mettre à jour l'affichage
                    self.window.after(0, self._refresh_display)
                    self.window.after(0, lambda: self.status_label.config(text="Aperçu généré avec succès"))
                else:
                    error_msg = f"Erreur lors de la génération: {'; '.join(result.errors[:3])}"
                    self.window.after(0, lambda: messagebox.showerror("Erreur", error_msg))
                
            except Exception as e:
                self.logger.error(f"Erreur génération aperçu: {e}")
                self.window.after(0, lambda e=e: messagebox.showerror("Erreur", f"Erreur lors de la génération: {e}"))
            finally:
                self.window.after(0, lambda: self._set_loading(False))
        
        threading.Thread(target=generate_thread, daemon=True).start()
    
    def _update_page_info(self):
        """Met à jour les informations de page"""
        if self.original_doc:
            total_pages = len(self.original_doc)
            self.page_total_label.config(text=f"/ {total_pages}")
            self.page_var.set(str(self.current_page + 1))
            
            # Informations du document
            doc_info = f"Pages: {total_pages} | Zoom: {self.zoom_level*100:.0f}%"
            self.doc_info_label.config(text=doc_info)
    
    def _set_page(self, page_num: int):
        """Définit la page courante"""
        if not self.original_doc:
            return
        
        # Vérifier les limites
        max_page = len(self.original_doc) - 1
        page_num = max(0, min(page_num, max_page))
        
        if page_num != self.current_page:
            self.current_page = page_num
            self.page_var.set(str(page_num + 1))
            
            # Rafraîchir l'affichage
            self._refresh_display()
    
    def _refresh_display(self):
        """Rafraîchit l'affichage des pages"""
        if not self.original_doc:
            return
        
        # Afficher la page originale
        self._display_page(self.current_page, "original")
        
        # Afficher la page traduite si disponible
        if self.preview_doc:
            if self.current_page < len(self.preview_doc):
                self._display_page(self.current_page, "translated")
            else:
                # Page non disponible dans l'aperçu
                self._show_placeholder("translated", "Page non disponible dans l'aperçu")
        else:
            self._show_placeholder("translated", "Aperçu non généré")
        
        # Afficher dans les onglets aussi
        if hasattr(self, 'original_tab_label'):
            self._display_page(self.current_page, "original_tab")
        if hasattr(self, 'translated_tab_label'):
            if self.preview_doc and self.current_page < len(self.preview_doc):
                self._display_page(self.current_page, "translated_tab")
            else:
                self._show_placeholder("translated_tab", "Aperçu non disponible")
    
    def _display_page(self, page_num: int, viewer_id: str):
        """Affiche une page dans un visualiseur donné"""
        
        # Déterminer le document source
        if viewer_id.startswith("original"):
            doc = self.original_doc
            doc_type = "original"
        else:
            doc = self.preview_doc
            doc_type = "translated"
        
        if not doc or page_num >= len(doc):
            return
        
        # Vérifier le cache
        cache_key = (page_num, self.zoom_level, doc_type)
        if cache_key in self.page_cache:
            photo_image = self.page_cache[cache_key]
        else:
            # Générer l'image de la page
            photo_image = self._render_page(doc, page_num)
            
            # Ajouter au cache
            self._add_to_cache(cache_key, photo_image)
        
        # Afficher l'image
        label = getattr(self, f'{viewer_id}_label')
        label.config(image=photo_image)
        label.image = photo_image  # Garder une référence
        
        # Mettre à jour la zone de scroll
        self._update_scroll_region(viewer_id)
    
    def _render_page(self, doc: fitz.Document, page_num: int) -> ImageTk.PhotoImage:
        """Rend une page en image"""
        page = doc[page_num]
        
        # Calcul de la matrice de transformation (zoom)
        mat = fitz.Matrix(self.zoom_level, self.zoom_level)
        
        # Rendu de la page
        pix = page.get_pixmap(matrix=mat)
        
        # Conversion en image PIL
        img_data = pix.tobytes("ppm")
        pil_image = Image.open(io.BytesIO(img_data))
        
        # Ajouter les overlays si activés
        if self.show_overlays and self.layout_data:
            pil_image = self._add_overlays(pil_image, page_num)
        
        # Conversion en PhotoImage
        photo_image = ImageTk.PhotoImage(pil_image)
        
        return photo_image
    
    def _add_overlays(self, image: Image.Image, page_num: int) -> Image.Image:
        """Ajoute des overlays de mise en page sur l'image"""
        # Cette fonction pourrait dessiner des rectangles pour montrer
        # les zones de texte, les problèmes de mise en page, etc.
        
        # Pour l'instant, retourner l'image sans modification
        # Dans une implémentation complète, on utiliserait PIL.ImageDraw
        # pour dessiner des rectangles colorés autour des éléments de texte
        
        return image
    
    def _show_placeholder(self, viewer_id: str, message: str):
        """Affiche un placeholder dans un visualiseur"""
        # Créer une image placeholder
        placeholder_image = Image.new('RGB', (400, 300), color='lightgray')
        
        # Ajouter du texte si possible (nécessiterait PIL.ImageDraw)
        photo_image = ImageTk.PhotoImage(placeholder_image)
        
        label = getattr(self, f'{viewer_id}_label')
        label.config(image=photo_image)
        label.image = photo_image
        
        self._update_scroll_region(viewer_id)
    
    def _update_scroll_region(self, viewer_id: str):
        """Met à jour la région de scroll"""
        canvas = getattr(self, f'{viewer_id}_canvas')
        content_frame = getattr(self, f'{viewer_id}_content')
        
        # Mettre à jour la région de scroll
        content_frame.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))
    
    def _add_to_cache(self, cache_key: tuple, image: ImageTk.PhotoImage):
        """Ajoute une image au cache"""
        # Nettoyer le cache si trop plein
        if len(self.page_cache) >= self.max_cache_size:
            # Supprimer les plus anciennes entrées
            keys_to_remove = list(self.page_cache.keys())[:5]
            for key in keys_to_remove:
                del self.page_cache[key]
        
        self.page_cache[cache_key] = image
    
    def _clear_cache(self):
        """Vide le cache des images"""
        self.page_cache.clear()
    
    # Gestionnaires d'événements
    
    def _on_page_change(self, *args):
        """Gestionnaire de changement de page"""
        try:
            page_str = self.page_var.get().strip()
            if page_str:
                page_num = int(page_str) - 1  # Conversion en index 0-based
                self._set_page(page_num)
        except ValueError:
            # Restaurer la valeur valide
            self.page_var.set(str(self.current_page + 1))
    
    def _on_zoom_change(self, event):
        """Gestionnaire de changement de zoom"""
        try:
            zoom_str = self.zoom_var.get().replace('%', '')
            zoom_level = float(zoom_str) / 100.0
            self._set_zoom(zoom_level)
        except ValueError:
            # Restaurer la valeur valide
            self.zoom_var.set(f"{self.zoom_level*100:.0f}%")
    
    def _on_mousewheel(self, event):
        """Gestionnaire de molette de souris"""
        # Scroll vertical
        canvas = event.widget
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def _on_ctrl_mousewheel(self, event):
        """Gestionnaire de molette + Ctrl (zoom)"""
        if event.delta > 0:
            self._zoom_in()
        else:
            self._zoom_out()
    
    # Méthodes de navigation
    
    def _first_page(self):
        """Va à la première page"""
        self._set_page(0)
    
    def _previous_page(self):
        """Va à la page précédente"""
        self._set_page(self.current_page - 1)
    
    def _next_page(self):
        """Va à la page suivante"""
        self._set_page(self.current_page + 1)
    
    def _last_page(self):
        """Va à la dernière page"""
        if self.original_doc:
            self._set_page(len(self.original_doc) - 1)
    
    # Méthodes de zoom
    
    def _zoom_in(self):
        """Zoom avant"""
        new_zoom = min(self.zoom_level * 1.25, 5.0)
        self._set_zoom(new_zoom)
    
    def _zoom_out(self):
        """Zoom arrière"""
        new_zoom = max(self.zoom_level / 1.25, 0.25)
        self._set_zoom(new_zoom)
    
    def _set_zoom(self, zoom_level: float):
        """Définit le niveau de zoom"""
        self.zoom_level = zoom_level
        self.zoom_var.set(f"{zoom_level*100:.0f}%")
        
        # Vider le cache et rafraîchir
        self._clear_cache()
        self._refresh_display()
        self._update_page_info()
    
    def _fit_to_window(self):
        """Ajuste le zoom pour adapter à la fenêtre"""
        if not self.original_doc:
            return
        
        # Obtenir la taille de la première page
        page = self.original_doc[0]
        page_width = page.rect.width
        page_height = page.rect.height
        
        # Obtenir la taille disponible dans la fenêtre
        # (approximative, il faudrait calculer plus précisément)
        available_width = 600  # Estimation
        available_height = 700  # Estimation
        
        # Calculer le zoom pour adapter
        zoom_width = available_width / page_width
        zoom_height = available_height / page_height
        zoom_fit = min(zoom_width, zoom_height, 2.0)  # Limiter à 200%
        
        self._set_zoom(zoom_fit)
    
    # Méthodes de mode d'affichage
    
    def _toggle_comparison_mode(self):
        """Basculer entre mode comparaison et onglets"""
        self.comparison_mode = self.comparison_var.get()
        
        if self.comparison_mode:
            self.content_notebook.select(0)  # Vue comparaison
        else:
            self.content_notebook.select(1)  # Vue onglets
    
    def _toggle_overlays(self):
        """Basculer l'affichage des overlays"""
        self.show_overlays = self.overlays_var.get()
        
        # Vider le cache et rafraîchir
        self._clear_cache()
        self._refresh_display()
    
    def _toggle_fullscreen(self):
        """Basculer le mode plein écran"""
        current_state = self.window.attributes('-fullscreen')
        self.window.attributes('-fullscreen', not current_state)
    
    # Méthodes d'export
    
    def _export_page_image(self):
        """Exporte la page courante en image"""
        if not self.original_doc:
            messagebox.showwarning("Attention", "Aucun document chargé.")
            return
        
        filename = filedialog.asksaveasfilename(
            title="Exporter la page en image",
            defaultextension=".png",
            filetypes=[
                ("PNG", "*.png"),
                ("JPEG", "*.jpg"),
                ("PDF", "*.pdf"),
                ("Tous les fichiers", "*.*")
            ]
        )
        
        if filename:
            try:
                file_path = Path(filename)
                
                if file_path.suffix.lower() == '.pdf':
                    # Export en PDF
                    self._export_page_as_pdf(file_path)
                else:
                    # Export en image
                    self._export_page_as_image(file_path)
                
                messagebox.showinfo("Export Réussi", f"Page exportée vers:\n{filename}")
                
            except Exception as e:
                self.logger.error(f"Erreur export: {e}")
                messagebox.showerror("Erreur", f"Erreur lors de l'export: {e}")
    
    def _export_page_as_image(self, file_path: Path):
        """Exporte la page comme image"""
        page = self.original_doc[self.current_page]
        
        # Rendu haute résolution
        mat = fitz.Matrix(2.0, 2.0)  # 200% pour qualité
        pix = page.get_pixmap(matrix=mat)
        
        # Sauvegarder
        pix.save(str(file_path))
    
    def _export_page_as_pdf(self, file_path: Path):
        """Exporte la page comme PDF"""
        # Créer un nouveau document avec juste cette page
        new_doc = fitz.open()
        new_doc.insert_pdf(self.original_doc, from_page=self.current_page, to_page=self.current_page)
        new_doc.save(str(file_path))
        new_doc.close()
    
    # Méthodes utilitaires
    
    def _set_loading(self, loading: bool, message: str = ""):
        """Active/désactive l'indicateur de chargement"""
        self.loading = loading
        
        if loading:
            self.loading_progress.start()
            if message:
                self.status_label.config(text=message)
        else:
            self.loading_progress.stop()
            self.status_label.config(text="Prêt")
    
    def _refresh_preview(self):
        """Actualise l'aperçu"""
        # Vider le cache
        self._clear_cache()
        
        # Recharger si nécessaire
        if self.preview_doc:
            # Regénérer l'aperçu
            self._generate_preview()
        else:
            # Juste rafraîchir l'affichage
            self._refresh_display()
    
    def _show_help(self):
        """Affiche l'aide"""
        help_text = """AIDE - Aperçu PDF

NAVIGATION:
• Utilisez les boutons ◀◀ ◀ ▶ ▶▶ pour naviguer
• Tapez un numéro de page et appuyez sur Entrée
• Molette de souris: scroll vertical
• Ctrl + Molette: zoom

ZOOM:
• Boutons + et - pour zoomer
• Menu déroulant pour zoom précis
• "Ajuster" pour adapter à la fenêtre
• Ctrl + molette de souris

MODES D'AFFICHAGE:
• Comparaison: Original et traduit côte à côte
• Onglets séparés: Documents dans des onglets
• Overlays: Affiche les zones de mise en page

ACTIONS:
• Générer Aperçu: Crée le PDF traduit temporaire
• Exporter Image: Sauvegarde la page courante
• Plein Écran: Mode plein écran (F11 pour quitter)

RACCOURCIS:
• Page Suiv/Préc: ←/→
• Premier/Dernier: Ctrl+Home/End
• Zoom +/-: Ctrl +/-
• Plein écran: F11"""
        
        help_dialog = tk.Toplevel(self.window)
        help_dialog.title("Aide")
        help_dialog.geometry("500x600")
        help_dialog.transient(self.window)
        
        import tkinter.scrolledtext as scrolledtext
        text_widget = scrolledtext.ScrolledText(help_dialog, wrap='word', padding=10)
        text_widget.pack(fill='both', expand=True, padx=10, pady=10)
        text_widget.insert('1.0', help_text)
        text_widget.config(state='disabled')
        
        ttk.Button(help_dialog, text="Fermer", command=help_dialog.destroy).pack(pady=10)
    
    def _on_closing(self):
        """Gestionnaire de fermeture de fenêtre"""
        try:
            # Fermer les documents
            if self.original_doc:
                self.original_doc.close()
            if self.preview_doc:
                self.preview_doc.close()
            
            # Nettoyer le fichier temporaire
            if self.preview_pdf_path and self.preview_pdf_path.exists():
                try:
                    self.preview_pdf_path.unlink()
                except:
                    pass  # Fichier peut-être encore utilisé
            
            # Fermer la fenêtre
            self.window.destroy()
            
        except Exception as e:
            self.logger.error(f"Erreur fermeture: {e}")
            self.window.destroy()
    
    # Méthodes publiques
    
    def show(self):
        """Affiche la fenêtre"""
        self.window.deiconify()
        self.window.lift()
        self.window.focus_force()
    
    def hide(self):
        """Masque la fenêtre"""
        self.window.withdraw()
    
    def get_current_page(self) -> int:
        """Retourne la page courante"""
        return self.current_page
    
    def set_page(self, page_num: int):
        """Définit la page courante (interface publique)"""
        self._set_page(page_num)
    
    def get_zoom_level(self) -> float:
        """Retourne le niveau de zoom actuel"""
        return self.zoom_level
    
    def set_zoom_level(self, zoom: float):
        """Définit le niveau de zoom (interface publique)"""

        self._set_zoom(zoom)
