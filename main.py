import tkinter as tk
from config import *
import config
from ocr.ocr import OCR
from widgets.app import App
from updater import check_updates_on_startup

if __name__ == "__main__":

    print("AureraOT Launcher - Verificando atualizações...")
    check_updates_on_startup()
    
    print(f"Sistema OCR: {'Habilitado' if config.OCR_ENABLED else 'Desabilitado'}")
    print(f"Iniciando aplicação com API na porta {API_PORT}")
    print("Aguarde alguns segundos para a API ficar disponível...")
    
    root = tk.Tk()
    ocr = OCR() if config.OCR_ENABLED else None
    app = App(root, ocr)
    
    if config.OCR_ENABLED and ocr:
        config_window = ocr.open_region_configurator(root, "Conta Teste")
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\nEncerrando aplicação...")
        app.parar_tudo()