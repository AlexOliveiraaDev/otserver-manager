import threading
import time
import tkinter as tk
from tkinter import ttk
from conta import Conta
from widgets.button import ModernButton
from widgets.status import StatusIndicator
import time
import threading
from queue import Queue
from datetime import datetime
from api import FlaskAPI
from config import *
import config
from pynput import keyboard
import version



class App:
    def __init__(self, root, ocr):
        self.root = root
        self.root.title("Dashboard de Contas - " + version.__version__ )
        self.root.geometry("1100x800")
        self.root.configure(bg="#2c3e50")
        

        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('Title.TLabel', font=('Arial', 16, 'bold'), background='#2c3e50', foreground='white')
        self.style.configure('Subtitle.TLabel', font=('Arial', 10), background='#2c3e50', foreground='#bdc3c7')
        self.style.configure('Account.TLabel', font=('Arial', 10, 'bold'), background='#34495e', foreground='white')
        
        self.contas = self.ler_contas(r'accounts.txt')
        self.queue = Queue()
        self.running = True
        config.ocr_paused = False
        

        self.instancias_abertas = 0
        self.instancias_crashed = 0
        self.status_atual = "Pronto"
        self.operacao_em_andamento = False
        self.inicio_operacao = None
        self.contas_restantes = 0
        

        self.api = FlaskAPI(self)
        
        self.criar_ui()
        self.iniciar_thread_status()
        self.iniciar_auto_restart_thread()
        

        self.iniciar_api_thread()
        self.contas_iniciando = False
        for conta in self.contas:
            conta.set_ocr(ocr)
            conta._app_instance = self
        
        self.iniciar_hotkeys_globais()



    def ler_contas(self, path):
        contas = []
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for indice, linha in enumerate(f):
                    linha = linha.strip()
                    if linha:
                        partes = linha.split()
                        if len(partes) >= 2:
                            login, senha = partes[0], partes[1]
                            id = int(partes[2]) if len(partes) == 3 else indice
                            contas.append(Conta(login, senha, id, indice))
        except FileNotFoundError:
            print(f"Arquivo não encontrado: {path}")
        return contas
    
    def iniciar_hotkeys_globais(self):
        
        def on_hotkey():

            self.root.after(0, self.toggle_ocr_pause)
        
        def hotkey_listener():
            try:

                with keyboard.GlobalHotKeys({'<ctrl>+<shift>+p': on_hotkey}):
                    while self.running:
                        time.sleep(0.1)
            except Exception as e:
                print(f"Erro no hotkey global: {e}")
        

        hotkey_thread = threading.Thread(target=hotkey_listener, daemon=True)
        hotkey_thread.start()
        print("Hotkey global ativado: Ctrl+Shift+P para pausar/retomar OCR")
    
    def tem_contas_iniciando(self):
        
        iniciando = any(
            ui_elements['conta'].status in ['iniciando', 'restarting'] 
            for ui_elements in self.botoes_conta
        )
        
        return iniciando or self.operacao_em_andamento

    def iniciar_api_thread(self):
        
        def run_api():
            try:
                self.api.run(host='0.0.0.0', port=API_PORT, debug=False)
            except Exception as e:
                logger.error(f"Erro ao iniciar API: {e}")
                print(f"Erro ao iniciar API na porta {API_PORT}: {e}")
        
        api_thread = threading.Thread(target=run_api, daemon=True)
        api_thread.start()
        logger.info(f"API iniciada na porta {API_PORT}")
        print(f"API disponível em: http://localhost:{API_PORT}/api/status")
        
    def toggle_ocr_pause(self):
        
        config.ocr_paused = not config.ocr_paused
        
        if config.ocr_paused:
            config.OCR_ENABLED = False
            self.botao_pausar_ocr.config(text="▶️ Retomar OCR")
            self.atualizar_status("OCR pausado")
        else:
            config.OCR_ENABLED =  True
            self.botao_pausar_ocr.config(text="⏸️ Pausar OCR") 
            self.atualizar_status("OCR retomado")

    def criar_ui(self):

        header_frame = tk.Frame(self.root, bg="#34495e", height=100)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(header_frame, text="Dashboard de Contas - " + version.__version__, 
                              font=('Arial', 18, 'bold'), bg="#34495e", fg="white")
        title_label.pack(pady=10)
        

        api_info_label = tk.Label(header_frame, text=f"API: http://localhost:{API_PORT}/api/status", 
                                 font=('Arial', 10), bg="#34495e", fg="#3498db")
        api_info_label.pack()
        

        ocr_status = "Habilitado" if config.OCR_ENABLED else "Desabilitado"
        ocr_info_label = tk.Label(header_frame, text=f"OCR: {ocr_status} (Intervalo: {OCR_UPDATE_INTERVAL}s)", 
                                 font=('Arial', 10), bg="#34495e", fg="#e74c3c" if not config.OCR_ENABLED else "#27ae60")
        ocr_info_label.pack()
        

        status_frame = tk.Frame(self.root, bg="#2c3e50")
        status_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        

        status_line1 = tk.Frame(status_frame, bg="#2c3e50")
        status_line1.pack(fill=tk.X)
        
        self.status_label = tk.Label(status_line1, text=f"Status: {self.status_atual}", 
                                    font=('Arial', 12, 'bold'), bg="#2c3e50", fg="#3498db")
        self.status_label.pack(side=tk.LEFT)
        
        self.contador_label = tk.Label(status_line1, text=f"Abertas: {self.instancias_abertas} | Crashed: {self.instancias_crashed}", 
                                      font=('Arial', 12, 'bold'), bg="#2c3e50", fg="#e67e22")
        self.contador_label.pack(side=tk.RIGHT)
        

        status_line2 = tk.Frame(status_frame, bg="#2c3e50")
        status_line2.pack(fill=tk.X)
        
        self.tempo_label = tk.Label(status_line2, text="Tempo restante: --", 
                                   font=('Arial', 10), bg="#2c3e50", fg="#95a5a6")
        self.tempo_label.pack(side=tk.LEFT)
        

        auto_restart_status = "Ativado" if AUTO_RESTART_ENABLED else "Desativado"
        self.recursos_label = tk.Label(status_line2, text=f"Auto-Restart: {auto_restart_status} | API: Ativada | OCR: {ocr_status}", 
                                      font=('Arial', 10), bg="#2c3e50", fg="#95a5a6")
        self.recursos_label.pack(side=tk.RIGHT)
        

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(status_frame, variable=self.progress_var, 
                                           mode='determinate', length=300)
        self.progress_bar.pack(pady=5)
        

        buttons_frame = tk.Frame(self.root, bg="#2c3e50")
        buttons_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        self.botao_iniciar_tudo = ModernButton(buttons_frame, "Iniciar Todas", 
                                              command=self.iniciar_todas_thread,
                                              bg_color="#27ae60", hover_color="#229954")
        self.botao_iniciar_tudo.pack(side=tk.LEFT, padx=5)
        
        self.botao_fechar_tudo = ModernButton(buttons_frame, "Fechar Todas", 
                                             command=self.fechar_todas,
                                             bg_color="#e74c3c", hover_color="#c0392b")
        self.botao_fechar_tudo.pack(side=tk.LEFT, padx=5)
        
        self.botao_restart_crashed = ModernButton(buttons_frame, "Reiniciar Crashed", 
                                                 command=self.reiniciar_crashed,
                                                 bg_color="#8e44ad", hover_color="#7d3c98")
        self.botao_restart_crashed.pack(side=tk.LEFT, padx=5)
        

        self.botao_toggle_auto = ModernButton(buttons_frame, "Toggle Auto-Restart", 
                                             command=self.toggle_auto_restart,
                                             bg_color="#34495e", hover_color="#2c3e50")
        self.botao_toggle_auto.pack(side=tk.LEFT, padx=5)

        self.botao_parar = ModernButton(buttons_frame, "Parar Aplicação", 
                                       command=self.parar_tudo,
                                       bg_color="#95a5a6", hover_color="#7f8c8d")
        self.botao_parar.pack(side=tk.RIGHT, padx=5)
        
        self.botao_pausar_ocr = ModernButton(buttons_frame, "⏸️ Pausar OCR", 
                                   command=self.toggle_ocr_pause,
                                   bg_color="#fd7e14", hover_color="#e6670a")
        self.botao_pausar_ocr.pack(side=tk.LEFT, padx=5)
        

        legenda_frame = tk.Frame(self.root, bg="#2c3e50")
        legenda_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        tk.Label(legenda_frame, text="Legenda:", font=('Arial', 9, 'bold'), bg="#2c3e50", fg="white").pack(side=tk.LEFT)
        
        cores_status = [
            ('aberta', 'Aberta'),
            ('fechada', 'Fechada'),
            ('iniciando', 'Iniciando'),
            ('restarting', 'Reiniciando'),
            ('crashed', 'Crashed')
        ]
        
        for status, texto in cores_status:
            indicator = StatusIndicator(legenda_frame)
            indicator.pack(side=tk.LEFT, padx=5)
            indicator.set_status(status)
            tk.Label(legenda_frame, text=texto, font=('Arial', 8), bg="#2c3e50", fg="white").pack(side=tk.LEFT, padx=(0, 10))
        

        canvas = tk.Canvas(self.root, bg="#2c3e50", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#2c3e50")
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True, padx=20)
        scrollbar.pack(side="right", fill="y")
        
        self.scrollable_frame = scrollable_frame
        self.botoes_conta = []
        self.criar_contas_ui()

    def testar_ocr(self):
        
        if not config.OCR_ENABLED:
            self.atualizar_status("OCR não está habilitado")
            return
            
        contas_abertas = [conta for conta in self.contas if conta.status == 'aberta']
        if not contas_abertas:
            self.atualizar_status("Nenhuma conta aberta para testar OCR")
            return
        
        def testar_async():
            for conta in contas_abertas:
                if conta.ocr:
                    self.root.after(0, lambda c=conta.login: self.atualizar_status(f"Testando OCR em {c}..."))
                    conta.last_ocr_update = None  
                    conta.update_game_stats()
                    
                    stats = conta.game_stats
                    print(conta.game_stats)
                    if stats.vida_atual > 0 or stats.level > 0:
                        self.root.after(0, lambda c=conta.login: self.atualizar_status(f"OCR OK em {c}: Level {stats.level}, Vida {stats.vida_atual}/{stats.vida_maxima}"))
                    else:
                        self.root.after(0, lambda c=conta.login: self.atualizar_status(f"OCR não detectou dados em {c}"))
                    
                    time.sleep(1)
            
            self.root.after(0, lambda: self.atualizar_status("Teste OCR concluído"))
        
        threading.Thread(target=testar_async, daemon=True).start()

    def criar_contas_ui(self):
        for i, conta in enumerate(self.contas):

            conta_frame = tk.Frame(self.scrollable_frame, bg="#34495e", relief="raised", bd=1)
            conta_frame.pack(fill=tk.X, padx=5, pady=3)
            

            info_frame = tk.Frame(conta_frame, bg="#34495e")
            info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10, pady=8)
            

            nome_label = tk.Label(info_frame, text=f"Conta: {conta.login}", 
                                 font=('Arial', 11, 'bold'), bg="#34495e", fg="white")
            nome_label.pack(anchor="w")
            

            executavel_tipo = "aurera_dx2.exe" if conta.indice >= 10 else "aurera_dx.exe"
            id_label = tk.Label(info_frame, text=f"Posição: {conta.indice} | ID: {conta.id} | Executável: {executavel_tipo}", 
                               font=('Arial', 9), bg="#34495e", fg="#bdc3c7")
            id_label.pack(anchor="w")
            

            tempo_conta_label = tk.Label(info_frame, text="", 
                                        font=('Arial', 8), bg="#34495e", fg="#95a5a6")
            tempo_conta_label.pack(anchor="w")
            

            ocr_label = None
            if config.OCR_ENABLED:
                ocr_label = tk.Label(info_frame, text="OCR: Aguardando dados...", 
                                    font=('Arial', 8), bg="#34495e", fg="#3498db")
                ocr_label.pack(anchor="w")
            

            stats_frame = tk.Frame(conta_frame, bg="#34495e")
            if config.OCR_ENABLED:
                stats_frame.pack(side=tk.RIGHT, padx=10, pady=5)
                

                vida_label = tk.Label(stats_frame, text="💚 Vida: --/--", 
                                     font=('Arial', 8), bg="#34495e", fg="#27ae60")
                vida_label.pack(anchor="w")
                
                mana_label = tk.Label(stats_frame, text="💙 Mana: --/--", 
                                     font=('Arial', 8), bg="#34495e", fg="#3498db")
                mana_label.pack(anchor="w")
                
                level_label = tk.Label(stats_frame, text="📊 Level: --", 
                                      font=('Arial', 8), bg="#34495e", fg="#f39c12")
                level_label.pack(anchor="w")
                
                fps_label = tk.Label(stats_frame, text="🖥️ FPS: --", 
                                    font=('Arial', 8), bg="#34495e", fg="#95a5a6")
                fps_label.pack(anchor="w")
            else:
                stats_frame = None
                vida_label = mana_label = level_label = fps_label = None
            

            buttons_frame = tk.Frame(conta_frame, bg="#34495e")
            buttons_frame.pack(side=tk.RIGHT, padx=10, pady=5)
            

            btn_iniciar = ModernButton(buttons_frame, "Iniciar", 
                                      command=lambda c=conta: self.toggle_conta_thread(c),
                                      bg_color="#3498db", hover_color="#2980b9")
            btn_iniciar.pack(side=tk.LEFT, padx=3)
            

            btn_mostrar = ModernButton(buttons_frame, "Mostrar", 
                                      command=lambda c=conta: c.mostrar(),
                                      bg_color="#f39c12", hover_color="#d68910")
            btn_mostrar.pack(side=tk.LEFT, padx=3)
            btn_mostrar.config(state=tk.DISABLED)
            

            btn_ocr = None
            if config.OCR_ENABLED:
                btn_ocr = ModernButton(buttons_frame, "OCR", 
                                      command=lambda c=conta: self.atualizar_ocr_conta(c),
                                      bg_color="#6f42c1", hover_color="#5a2d91")
                btn_ocr.pack(side=tk.LEFT, padx=3)
                btn_ocr.config(state=tk.DISABLED)
            

            status_indicator = StatusIndicator(buttons_frame)
            status_indicator.pack(side=tk.LEFT, padx=5)
            

            ui_elements = {
                'conta': conta,
                'btn_iniciar': btn_iniciar,
                'btn_mostrar': btn_mostrar,
                'btn_ocr': btn_ocr,
                'status_indicator': status_indicator,
                'tempo_label': tempo_conta_label,
                'ocr_label': ocr_label,
                'vida_label': vida_label,
                'mana_label': mana_label,
                'level_label': level_label,
                'fps_label': fps_label
            }
            
            self.botoes_conta.append(ui_elements)

    def atualizar_ocr_conta(self, conta):
        
        if not config.OCR_ENABLED or not conta.ocr or conta.status != 'aberta':
            return
            
        def atualizar_async():
            self.root.after(0, lambda: self.atualizar_status(f"Atualizando OCR para {conta.login}..."))
            conta.last_ocr_update = None  
            conta.update_game_stats()
            self.root.after(0, lambda: self.atualizar_status(f"OCR atualizado para {conta.login}"))
        
        threading.Thread(target=atualizar_async, daemon=True).start()

    def verificar_instancias_existentes(self):
        
        def verificar_async():
            self.root.after(0, lambda: self.atualizar_status("Verificando instâncias existentes..."))
            
            instancias_encontradas = 0
            for ui_elements in self.botoes_conta:
                conta = ui_elements['conta']
                if conta.status == 'fechada':
                    if conta.verificar_instancia_existente():
                        conta.status = 'aberta'
                        self.root.after(0, lambda b=ui_elements['btn_iniciar']: b.config(text='Parar'))
                        self.root.after(0, lambda ind=ui_elements['status_indicator']: ind.set_status('aberta'))
                        self.root.after(0, lambda m=ui_elements['btn_mostrar']: m.config(state=tk.NORMAL))
                        if ui_elements['btn_ocr']:
                            self.root.after(0, lambda o=ui_elements['btn_ocr']: o.config(state=tk.NORMAL))
                        instancias_encontradas += 1
                        print(f"Reconectado com instância existente de {conta.login}")
            
            self.root.after(0, lambda: self.atualizar_contador())
            if instancias_encontradas > 0:
                self.root.after(0, lambda: self.atualizar_status(f"Reconectado com {instancias_encontradas} instâncias existentes"))
            else:
                self.root.after(0, lambda: self.atualizar_status("Nenhuma instância existente encontrada"))
        
        threading.Thread(target=verificar_async, daemon=True).start()

    def toggle_auto_restart(self):
        
        global AUTO_RESTART_ENABLED
        AUTO_RESTART_ENABLED = not AUTO_RESTART_ENABLED
        
        status = "Ativado" if AUTO_RESTART_ENABLED else "Desativado"
        ocr_status = "Habilitado" if config.OCR_ENABLED else "Desabilitado"
        self.recursos_label.config(text=f"Auto-Restart: {status} | API: Ativada | OCR: {ocr_status}")
        
        self.atualizar_status(f"Auto-Restart {'ativado' if AUTO_RESTART_ENABLED else 'desativado'}")

    def iniciar_auto_restart_thread(self):
        
        def auto_restart_loop():
            while self.running:
                try:
                    if AUTO_RESTART_ENABLED:
                        if not self.operacao_em_andamento and not self.tem_contas_iniciando():
                            for ui_elements in self.botoes_conta:
                                conta = ui_elements['conta']
                                if conta.pode_reiniciar_automaticamente():
                                    print(f"Iniciando auto-restart para {conta.login}")
                                    
                                    self.operacao_em_andamento = True
                                    self.contas_iniciando = True
                                    
                                    try:

                                        self.root.after(0, lambda ind=ui_elements['status_indicator']: ind.set_status('restarting'))
                                        self.root.after(0, lambda b=ui_elements['btn_iniciar']: b.config(state=tk.DISABLED))
                                        

                                        if conta.reiniciar_automaticamente():

                                            self.root.after(0, lambda b=ui_elements['btn_iniciar']: b.config(text='Parar', state=tk.NORMAL))
                                            self.root.after(0, lambda ind=ui_elements['status_indicator']: ind.set_status('aberta'))
                                            self.root.after(0, lambda m=ui_elements['btn_mostrar']: m.config(state=tk.NORMAL))
                                            if ui_elements['btn_ocr']:
                                                self.root.after(0, lambda o=ui_elements['btn_ocr']: o.config(state=tk.NORMAL))
                                            print(f"Auto-restart bem-sucedido para {conta.login}")
                                        else:

                                            self.root.after(0, lambda b=ui_elements['btn_iniciar']: b.config(state=tk.NORMAL))
                                            self.root.after(0, lambda ind=ui_elements['status_indicator']: ind.set_status('crashed'))
                                            
                                            if conta.restart_attempts >= config.MAX_RESTART_ATTEMPTS:
                                                print(f"Máximo de tentativas de restart atingido para {conta.login}")
                             
                                    finally:

                                        self.operacao_em_andamento = False
                                        self.contas_iniciando = False
                                    time.sleep(2)
                                    break
                    time.sleep(5)
                    
                except Exception as e:
                    print(f"Erro no auto-restart: {e}")
                    self.operacao_em_andamento = False
                    self.contas_iniciando = False
                    time.sleep(5)
        
        thread = threading.Thread(target=auto_restart_loop, daemon=True)
        thread.start()

    def atualizar_status(self, novo_status):
        self.status_atual = novo_status
        self.status_label.config(text=f"Status: {novo_status}")
        
    def verificar_status_contas(self):
        
        ocr_suspenso = self.tem_contas_iniciando() or config.ocr_paused
        
        if ocr_suspenso:
            print("🚫 OCR suspenso durante operações de inicialização/restart")
        
        for ui_elements in self.botoes_conta:
            conta = ui_elements['conta']
            if conta.status == 'aberta':
                if not conta.verificar_status():

                    ui_elements['btn_iniciar'].config(text='Iniciar', state=tk.NORMAL)
                    ui_elements['status_indicator'].set_status('crashed')
                    ui_elements['btn_mostrar'].config(state=tk.DISABLED)
                    if ui_elements['btn_ocr']:
                        ui_elements['btn_ocr'].config(state=tk.DISABLED)
            

            self.atualizar_info_conta(ui_elements)
            

            if config.OCR_ENABLED and conta.status == 'aberta' and not ocr_suspenso:
                self.atualizar_stats_ocr_ui(ui_elements)
                
    def get_operation_status(self):
        
        return {
            'operacao_em_andamento': self.operacao_em_andamento,
            'contas_iniciando': self.contas_iniciando,
            'tem_contas_iniciando': self.tem_contas_iniciando(),
            'contas_status': {
                ui['conta'].login: ui['conta'].status 
                for ui in self.botoes_conta
            }
        }
        
    def atualizar_info_conta(self, ui_elements):
        
        conta = ui_elements['conta']
        tempo_restante = conta.get_tempo_restante()
        info_text = ""
        
        if tempo_restante > 0:
            mins, secs = divmod(tempo_restante, 60)
            info_text = f"Tempo restante: {mins:02d}:{secs:02d}"
        
        if conta.restart_attempts > 0:
            if info_text:
                info_text += f" | Restarts: {conta.restart_attempts}/{config.MAX_RESTART_ATTEMPTS}"
            else:
                info_text = f"Restarts: {conta.restart_attempts}/{config.MAX_RESTART_ATTEMPTS}"
        
        if conta.status == 'crashed' and conta.crash_time:
            tempo_desde_crash = (datetime.now() - conta.crash_time).total_seconds()
            if AUTO_RESTART_ENABLED and conta.restart_attempts < config.MAX_RESTART_ATTEMPTS:
                tempo_para_restart = max(0, AUTO_RESTART_DELAY - tempo_desde_crash)
                if tempo_para_restart > 0:
                    mins, secs = divmod(int(tempo_para_restart), 60)
                    if info_text:
                        info_text += f" | Auto-restart em: {mins:02d}:{secs:02d}"
                    else:
                        info_text = f"Auto-restart em: {mins:02d}:{secs:02d}"
        
        if conta.window_title:
            if info_text:
                info_text += f" | Janela: {conta.window_title[:30]}..."
            else:
                info_text = f"Janela: {conta.window_title[:30]}..."
        
        ui_elements['tempo_label'].config(text=info_text)

    def atualizar_stats_ocr_ui(self, ui_elements):
        
        conta = ui_elements['conta']
        stats = conta.game_stats
        
        if not stats or not ui_elements['vida_label']:
            return
        
        try:

            if ui_elements['ocr_label']:
                if conta.last_ocr_update:
                    tempo_desde_update = (datetime.now() - conta.last_ocr_update).total_seconds()
                    ui_elements['ocr_label'].config(text=f"OCR: Atualizado há {int(tempo_desde_update)}s")
                else:
                    ui_elements['ocr_label'].config(text="OCR: Aguardando dados...")
            

            ui_elements['vida_label'].config(text=f"💚 Vida: {stats.vida_atual}/{stats.vida_maxima}")
            ui_elements['mana_label'].config(text=f"💙 Mana: {stats.mana_atual}/{stats.mana_maxima}")
            ui_elements['level_label'].config(text=f"📊 Level: {stats.level}")
            ui_elements['fps_label'].config(text=f"🖥️ FPS: {stats.fps}")
            
        except Exception as e:
            print(f"Erro ao atualizar UI OCR para {conta.login}: {e}")
    
    def atualizar_contador(self):
        for conta in self.contas:
            if conta.status == "iniciando":
                break
        
        self.verificar_status_contas()
        self.instancias_abertas = sum(1 for ui_elements in self.botoes_conta if ui_elements['conta'].status == 'aberta')
        self.instancias_crashed = sum(1 for ui_elements in self.botoes_conta if ui_elements['conta'].status == 'crashed')
        self.contador_label.config(text=f"Abertas: {self.instancias_abertas} | Crashed: {self.instancias_crashed}")

    def calcular_tempo_restante_total(self):
        
        if not self.operacao_em_andamento or not self.inicio_operacao:
            return "Tempo restante: --"
        
        agora = datetime.now()
        tempo_decorrido = (agora - self.inicio_operacao).total_seconds()
        
        if self.contas_restantes > 0:
            tempo_medio_por_conta = tempo_decorrido / max(1, (len(self.contas) - self.contas_restantes))
            tempo_restante = tempo_medio_por_conta * self.contas_restantes
            
            if tempo_restante > 0:
                mins, secs = divmod(int(tempo_restante), 60)
                return f"Tempo restante: {mins:02d}:{secs:02d}"
        
        return "Tempo restante: Finalizando..."

    def reiniciar_crashed(self):
        
        contas_crashed = [ui_elements['conta'] for ui_elements in self.botoes_conta if ui_elements['conta'].status == 'crashed']
        
        if not contas_crashed:
            self.atualizar_status("Nenhuma conta crashed para reiniciar")
            return
        
        for conta in contas_crashed:
            conta.status = 'fechada'
            conta.restart_attempts = 0
        
        self.atualizar_status(f"Reiniciando {len(contas_crashed)} contas que crasharam...")
        self.iniciar_todas_thread()

    def toggle_conta_thread(self, conta):
        if not self.operacao_em_andamento:
            thread = threading.Thread(target=self.toggle_conta, args=(conta,), daemon=True)
            thread.start()

    def toggle_conta(self, conta):
        self.operacao_em_andamento = True
        self.contas_iniciando = True
        

        ui_elements = None
        for elements in self.botoes_conta:
            if elements['conta'] == conta:
                ui_elements = elements
                break
        
        if not ui_elements:
            self.operacao_em_andamento = False
            return
        
        if conta.status in ['fechada', 'crashed']:

            self.root.after(0, lambda: self.atualizar_status(f"Iniciando conta {conta.login}..."))
            self.root.after(0, lambda: ui_elements['status_indicator'].set_status('iniciando'))
            self.root.after(0, lambda: ui_elements['btn_iniciar'].config(state=tk.DISABLED))
            
            try:
                if conta.iniciar():

                    self.root.after(0, lambda: ui_elements['btn_iniciar'].config(text='Parar', state=tk.NORMAL))
                    self.root.after(0, lambda: ui_elements['status_indicator'].set_status('aberta'))
                    self.root.after(0, lambda: ui_elements['btn_mostrar'].config(state=tk.NORMAL))
                    if ui_elements['btn_ocr']:
                        self.root.after(0, lambda: ui_elements['btn_ocr'].config(state=tk.NORMAL))
                    self.root.after(0, lambda: self.atualizar_status(f"Conta {conta.login} iniciada com sucesso"))
                    pass
                else:
                    raise Exception("Falha na inicialização")
            except Exception as e:

                self.root.after(0, lambda: self.atualizar_status(f"Erro ao iniciar {conta.login}: {str(e)}"))
                self.root.after(0, lambda: ui_elements['btn_iniciar'].config(state=tk.NORMAL))
                self.root.after(0, lambda: ui_elements['status_indicator'].set_status('crashed'))
                conta.crash_time = datetime.now()
                pass
                
        else:

            self.root.after(0, lambda: self.atualizar_status(f"Fechando conta {conta.login}..."))
            conta.fechar()
            self.root.after(0, lambda: ui_elements['btn_iniciar'].config(text='Iniciar'))
            self.root.after(0, lambda: ui_elements['status_indicator'].set_status('fechada'))
            self.root.after(0, lambda: ui_elements['btn_mostrar'].config(state=tk.DISABLED))
            if ui_elements['btn_ocr']:
                self.root.after(0, lambda: ui_elements['btn_ocr'].config(state=tk.DISABLED))
            self.root.after(0, lambda: self.atualizar_status(f"Conta {conta.login} fechada"))
            pass
        
        self.root.after(0, lambda: self.atualizar_contador())
        self.operacao_em_andamento = False
        self.contas_iniciando = False  

    def iniciar_todas_thread(self):
        if not self.operacao_em_andamento:
            thread = threading.Thread(target=self.iniciar_todas, daemon=True)
            thread.start()

    def iniciar_todas(self):
        self.operacao_em_andamento = True
        self.inicio_operacao = datetime.now()
        self.contas_iniciando = True
        self.root.after(0, lambda: self.progress_var.set(0))
        
        contas_para_iniciar = [ui_elements['conta'] for ui_elements in self.botoes_conta if ui_elements['conta'].status in ['fechada', 'crashed']]
        total_contas = len(contas_para_iniciar)
        self.contas_restantes = total_contas
        
        if total_contas == 0:
            self.root.after(0, lambda: self.atualizar_status("Todas as contas já estão abertas"))
            self.operacao_em_andamento = False
            return
        
        self.root.after(0, lambda: self.atualizar_status("Iniciando todas as contas..."))
        try:
            for i, ui_elements in enumerate(self.botoes_conta):
                conta = ui_elements['conta']
                if conta.status in ['fechada', 'crashed']:
                    self.contas_restantes -= 1
                    self.root.after(0, lambda c=conta.login, idx=i+1, total=total_contas: 
                                self.atualizar_status(f"Iniciando conta {c} ({idx}/{total})..."))
                    self.root.after(0, lambda ind=ui_elements['status_indicator']: ind.set_status('iniciando'))
                    self.root.after(0, lambda b=ui_elements['btn_iniciar']: b.config(state=tk.DISABLED))
                    
                    try:
                        if conta.iniciar():
                            self.root.after(0, lambda b=ui_elements['btn_iniciar']: b.config(text='Parar', state=tk.NORMAL))
                            self.root.after(0, lambda ind=ui_elements['status_indicator']: ind.set_status('aberta'))
                            self.root.after(0, lambda m=ui_elements['btn_mostrar']: m.config(state=tk.NORMAL))
                            if ui_elements['btn_ocr']:
                                self.root.after(0, lambda o=ui_elements['btn_ocr']: o.config(state=tk.NORMAL))
                        else:
                            raise Exception("Falha na inicialização")
                        
                        progress = ((i + 1) / total_contas) * 100
                        self.root.after(0, lambda p=progress: self.progress_var.set(p))
                        
                    except Exception as e:
                        self.root.after(0, lambda c=conta.login, err=str(e): 
                                    self.atualizar_status(f"Erro ao iniciar {c}: {err}"))
                        self.root.after(0, lambda b=ui_elements['btn_iniciar']: b.config(state=tk.NORMAL))
                        self.root.after(0, lambda ind=ui_elements['status_indicator']: ind.set_status('crashed'))
                        conta.crash_time = datetime.now()
        
        finally:

            self.root.after(0, lambda: self.atualizar_contador())
            self.root.after(0, lambda: self.atualizar_status("Todas as contas foram processadas"))
            self.root.after(0, lambda: self.progress_var.set(100))
            self.contas_restantes = 0
            self.operacao_em_andamento = False
            self.contas_iniciando = False

       

    def fechar_todas(self):
        self.root.after(0, lambda: self.atualizar_status("Fechando todas as contas..."))
        
        for ui_elements in self.botoes_conta:
            conta = ui_elements['conta']
            if conta.status in ['aberta', 'crashed', 'restarting']:
                conta.fechar()
                self.root.after(0, lambda b=ui_elements['btn_iniciar']: b.config(text='Iniciar'))
                self.root.after(0, lambda ind=ui_elements['status_indicator']: ind.set_status('fechada'))
                self.root.after(0, lambda m=ui_elements['btn_mostrar']: m.config(state=tk.DISABLED))
                if ui_elements['btn_ocr']:
                    self.root.after(0, lambda o=ui_elements['btn_ocr']: o.config(state=tk.DISABLED))
        
        self.root.after(0, lambda: self.atualizar_contador())
        self.root.after(0, lambda: self.atualizar_status("Todas as contas foram fechadas"))

    def iniciar_thread_status(self):
        def atualizar_ui():
            while self.running:
                try:

                    self.root.after(100, self.atualizar_contador)
                    

                    if self.operacao_em_andamento:
                        tempo_texto = self.calcular_tempo_restante_total()
                        self.root.after(100, lambda: self.tempo_label.config(text=tempo_texto))
                    else:
                        self.root.after(100, lambda: self.tempo_label.config(text="Tempo restante: --"))
                    
                    time.sleep(1)
                except:
                    break
        
        thread = threading.Thread(target=atualizar_ui, daemon=True)
        thread.start()

    def parar_tudo(self):
        self.running = False
        self.fechar_todas()
        self.root.quit()
