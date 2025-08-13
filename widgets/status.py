import tkinter as tk

class StatusIndicator(tk.Canvas):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, width=20, height=20, bg="white", highlightthickness=0, **kwargs)
        self.create_oval(2, 2, 18, 18, fill='#e74c3c', outline='#c0392b', width=2)
        self.status = 'fechada'
    
    def set_status(self, status):
        self.status = status
        if status == 'aberta':
            self.itemconfig(1, fill='#27ae60', outline='#229954')
        elif status == 'iniciando':
            self.itemconfig(1, fill='#f39c12', outline='#d68910')
        elif status == 'crashed':
            self.itemconfig(1, fill='#8e44ad', outline='#7d3c98')
        elif status == 'restarting':
            self.itemconfig(1, fill='#3498db', outline='#2980b9')
        else:
            self.itemconfig(1, fill='#e74c3c', outline='#c0392b')

