import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import win32gui
from PIL import Image, ImageTk, ImageGrab
import json
from config import REGION_COLORS

class RegionConfigWindow:
    """Janela para configurar regiões do OCR visualmente - versão otimizada"""
    
    def __init__(self, parent, ocr_instance, account_name=""):
        self.parent = parent
        self.ocr = ocr_instance
        self.account_name = account_name
        
        # Dados das regiões centralizadas
        self.regions = self.ocr.regions.copy() if self.ocr else {}
        self.region_names = list(REGION_COLORS.keys())
        
        # Interface
        self.window = None
        self.canvas = None
        self.screenshot = None
        self.photo = None
        self.current_region = None
        self.selection_rect = None
        self.start_x = None
        self.start_y = None
        self.scale = 1.0
        
        self.create_window()
        
    def create_window(self):
        self.window = tk.Toplevel(self.parent)
        self.window.title(f"Configurar Regiões OCR - {self.account_name}")
        self.window.geometry("1200x800")
        
        # Frame principal
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self._create_controls(main_frame)
        self._create_canvas(main_frame)
        self._create_info_panel(main_frame)
        
        # Carregar regiões atuais
        self.load_current_regions()
        
    def _create_controls(self, parent):
        """Cria controles da interface"""
        control_frame = ttk.Frame(parent)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Botões principais
        ttk.Button(control_frame, text="📷 Capturar Tela", 
                  command=self.capture_screenshot).pack(side=tk.LEFT, padx=(0, 5))
        
        # Seleção de região
        ttk.Label(control_frame, text="Região:").pack(side=tk.LEFT, padx=(10, 5))
        self.region_var = tk.StringVar()
        region_combo = ttk.Combobox(control_frame, textvariable=self.region_var,
                                   values=self.region_names, state="readonly")
        region_combo.pack(side=tk.LEFT, padx=(0, 10))
        region_combo.bind('<<ComboboxSelected>>', self.on_region_selected)
        
        # Campos de coordenadas
        self._create_coordinate_fields(control_frame)
        
        # Botões de ação
        self._create_action_buttons(control_frame)
        
    def _create_coordinate_fields(self, parent):
        """Cria campos de coordenadas"""
        coord_frame = ttk.Frame(parent)
        coord_frame.pack(side=tk.LEFT, padx=(10, 0))
        
        coords = ['X1', 'Y1', 'X2', 'Y2']
        self.coord_vars = {}
        
        for i, coord in enumerate(coords):
            ttk.Label(coord_frame, text=f"{coord}:").grid(row=0, column=i*2, padx=2)
            var = tk.IntVar()
            self.coord_vars[coord.lower()] = var
            ttk.Entry(coord_frame, textvariable=var, width=6).grid(row=0, column=i*2+1, padx=2)
        
        ttk.Button(coord_frame, text="Aplicar", 
                  command=self.apply_coordinates).grid(row=0, column=8, padx=5)
    
    def _create_action_buttons(self, parent):
        """Cria botões de ação"""
        action_frame = ttk.Frame(parent)
        action_frame.pack(side=tk.RIGHT)
        
        buttons = [
            ("💾 Salvar", self.save_config),
            ("📁 Carregar", self.load_config),
            ("🔄 Reset", self.reset_regions),
            ("✅ Aplicar ao OCR", self.apply_to_ocr)
        ]
        
        for text, command in buttons:
            ttk.Button(action_frame, text=text, command=command).pack(side=tk.LEFT, padx=2)
    
    def _create_canvas(self, parent):
        """Cria canvas para visualização"""
        canvas_frame = ttk.Frame(parent)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(canvas_frame, bg='white')
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Bind eventos do mouse
        self.canvas.bind("<Button-1>", self.on_mouse_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_release)
    
    def _create_info_panel(self, parent):
        """Cria painel de informações"""
        info_frame = ttk.LabelFrame(parent, text="Informações", padding=5)
        info_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.info_text = tk.Text(info_frame, height=4, wrap=tk.WORD)
        self.info_text.pack(fill=tk.X)
        
        self.update_info("1. Clique em 'Capturar Tela' para começar\n"
                        "2. Selecione uma região na lista\n"
                        "3. Clique e arraste no canvas para definir a área\n"
                        "4. Use as coordenadas para ajustes finos")
        
    def capture_screenshot(self):
        """Captura screenshot da janela do jogo ou tela inteira"""
        try:
            if self.ocr and self.ocr.hwnd and win32gui.IsWindow(self.ocr.hwnd):
                rect = win32gui.GetWindowRect(self.ocr.hwnd)
                screenshot = ImageGrab.grab(bbox=rect)
                self.update_info(f"Screenshot capturada da janela do jogo: {rect}")
            else:
                screenshot = ImageGrab.grab()
                self.update_info("Screenshot capturada da tela inteira")
            
            # Redimensionar para caber no canvas
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            if canvas_width > 1 and canvas_height > 1:
                img_width, img_height = screenshot.size
                scale_x = canvas_width / img_width
                scale_y = canvas_height / img_height
                self.scale = min(scale_x, scale_y)
                
                new_width = int(img_width * self.scale)
                new_height = int(img_height * self.scale)
                
                screenshot = screenshot.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            self.screenshot = screenshot
            self.photo = ImageTk.PhotoImage(screenshot)
            
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
            self.draw_all_regions()
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao capturar screenshot: {e}")
            
    def on_region_selected(self, event=None):
        """Quando uma região é selecionada no dropdown"""
        region_name = self.region_var.get()
        if region_name in self.regions:
            coords = self.regions[region_name]
            coord_names = ['x1', 'y1', 'x2', 'y2']
            for i, name in enumerate(coord_names):
                self.coord_vars[name].set(coords[i])
            self.current_region = region_name
            self.draw_all_regions()
            
    def on_mouse_press(self, event):
        """Início da seleção de região"""
        if not self.region_var.get():
            messagebox.showwarning("Aviso", "Selecione uma região primeiro!")
            return
            
        self.start_x = event.x
        self.start_y = event.y
        self.current_region = self.region_var.get()
        
        if self.selection_rect:
            self.canvas.delete(self.selection_rect)
            
    def on_mouse_drag(self, event):
        """Durante o arraste do mouse"""
        if self.start_x is not None and self.start_y is not None:
            if self.selection_rect:
                self.canvas.delete(self.selection_rect)
            
            color = REGION_COLORS.get(self.current_region, '#FF0000')
            self.selection_rect = self.canvas.create_rectangle(
                self.start_x, self.start_y, event.x, event.y,
                outline=color, width=2, dash=(5, 5)
            )
            
    def on_mouse_release(self, event):
        """Fim da seleção de região"""
        if self.start_x is not None and self.start_y is not None:
            coords = self._calculate_final_coordinates(event)
            
            if self.current_region:
                self.regions[self.current_region] = coords
                self._update_coordinate_fields(coords)
                self.update_info(f"Região '{self.current_region}' definida: {coords}")
            
            if self.selection_rect:
                self.canvas.delete(self.selection_rect)
                self.selection_rect = None
            
            self.draw_all_regions()
            
        self.start_x = None
        self.start_y = None
    
    def _calculate_final_coordinates(self, event):
        """Calcula coordenadas finais da seleção"""
        x1 = min(self.start_x, event.x)
        y1 = min(self.start_y, event.y)
        x2 = max(self.start_x, event.x)
        y2 = max(self.start_y, event.y)
        
        # Converter coordenadas do canvas para coordenadas reais
        if self.scale:
            x1 = int(x1 / self.scale)
            y1 = int(y1 / self.scale)
            x2 = int(x2 / self.scale)
            y2 = int(y2 / self.scale)
        
        return (x1, y1, x2, y2)
    
    def _update_coordinate_fields(self, coords):
        """Atualiza campos de coordenadas"""
        coord_names = ['x1', 'y1', 'x2', 'y2']
        for i, name in enumerate(coord_names):
            self.coord_vars[name].set(coords[i])
        
    def apply_coordinates(self):
        """Aplica coordenadas digitadas manualmente"""
        region_name = self.region_var.get()
        if not region_name:
            messagebox.showwarning("Aviso", "Selecione uma região primeiro!")
            return
            
        try:
            coords = tuple(self.coord_vars[name].get() for name in ['x1', 'y1', 'x2', 'y2'])
            
            if coords[0] >= coords[2] or coords[1] >= coords[3]:
                messagebox.showerror("Erro", "Coordenadas inválidas!")
                return
            
            self.regions[region_name] = coords
            self.draw_all_regions()
            self.update_info(f"Coordenadas aplicadas à região '{region_name}': {coords}")
            
        except tk.TclError:
            messagebox.showerror("Erro", "Digite coordenadas válidas!")
            
    def draw_all_regions(self):
        """Desenha todas as regiões no canvas"""
        if not self.screenshot:
            return
            
        # Limpar regiões anteriores
        for item in self.canvas.find_all():
            if 'region' in self.canvas.gettags(item):
                self.canvas.delete(item)
        
        # Desenhar cada região
        for region_name, coords in self.regions.items():
            if len(coords) == 4:
                self._draw_region(region_name, coords)
    
    def _draw_region(self, region_name, coords):
        """Desenha uma região específica"""
        x1, y1, x2, y2 = coords
        
        # Converter para coordenadas do canvas
        if self.scale:
            x1_canvas = int(x1 * self.scale)
            y1_canvas = int(y1 * self.scale)
            x2_canvas = int(x2 * self.scale)
            y2_canvas = int(y2 * self.scale)
        else:
            x1_canvas, y1_canvas, x2_canvas, y2_canvas = x1, y1, x2, y2
        
        color = REGION_COLORS.get(region_name, '#FF0000')
        
        # Desenhar retângulo
        self.canvas.create_rectangle(
            x1_canvas, y1_canvas, x2_canvas, y2_canvas,
            outline=color, width=2, tags='region'
        )
        
        # Adicionar label
        self.canvas.create_text(
            x1_canvas + 5, y1_canvas - 15,
            text=region_name, fill=color, anchor=tk.W,
            font=('Arial', 9, 'bold'), tags='region'
        )
                
    def save_config(self):
        """Salva configuração de regiões em arquivo"""
        filename = filedialog.asksaveasfilename(
            title="Salvar Configuração OCR",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                config = {
                    'regions': self.regions,
                    'account_name': self.account_name,
                    'region_colors': REGION_COLORS
                }
                
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                
                messagebox.showinfo("Sucesso", f"Configuração salva em: {filename}")
                self.update_info(f"Configuração salva: {filename}")
                
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao salvar configuração: {e}")
                
    def load_config(self):
        """Carrega configuração de regiões de arquivo"""
        filename = filedialog.askopenfilename(
            title="Carregar Configuração OCR",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                if 'regions' in config:
                    self.regions = config['regions']
                    self.load_current_regions()
                    self.draw_all_regions()
                    messagebox.showinfo("Sucesso", f"Configuração carregada de: {filename}")
                    self.update_info(f"Configuração carregada: {filename}")
                
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao carregar configuração: {e}")
                
    def reset_regions(self):
        """Reset das regiões para valores padrão"""
        if messagebox.askyesno("Confirmar", "Deseja restaurar as regiões padrão?"):
            from config import DEFAULT_OCR_REGIONS
            self.regions = DEFAULT_OCR_REGIONS.copy()
            self.load_current_regions()
            self.draw_all_regions()
            self.update_info("Regiões restauradas para valores padrão")
            
    def apply_to_ocr(self):
        """Aplica as regiões configuradas ao sistema OCR"""
        if self.ocr:
            self.ocr.regions = self.regions.copy()
            messagebox.showinfo("Sucesso", "Regiões aplicadas ao sistema OCR!")
            self.update_info("Configurações aplicadas ao OCR com sucesso")
        else:
            messagebox.showwarning("Aviso", "Nenhuma instância OCR disponível")
            
    def load_current_regions(self):
        """Carrega regiões atuais do OCR para interface"""
        if self.regions and self.region_names:
            self.region_var.set(self.region_names[0])
            self.on_region_selected()
                
    def update_info(self, message):
        """Atualiza área de informações"""
        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(tk.END, message)