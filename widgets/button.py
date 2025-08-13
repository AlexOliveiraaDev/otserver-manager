import tkinter as tk

class ModernButton(tk.Button):
    def __init__(self, parent, text, command=None, bg_color="#4CAF50", hover_color="#45a049", **kwargs):
        super().__init__(parent, text=text, command=command, **kwargs)
        self.bg_color = bg_color
        self.hover_color = hover_color
        
        self.config(
            bg=bg_color,
            fg="white",
            font=("Arial", 9, "bold"),
            border=0,
            relief="flat",
            cursor="hand2",
            padx=15,
            pady=5
        )
        
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
    
    def on_enter(self, event):
        self.config(bg=self.hover_color)
    
    def on_leave(self, event):
        self.config(bg=self.bg_color)

