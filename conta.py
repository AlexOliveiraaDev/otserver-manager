from datetime import datetime, timedelta
import subprocess
import time
import psutil
import pyautogui
import win32gui
import win32process
from gamestats import GameStats
from config import *
import config
from ocr.ocr import OCR
from utils import esperar, forcar_foco_janela, encontrar_janela_por_processo, verificar_janela_valida

class Conta:

    _used_pids = set()
    
    def __init__(self, login, senha, id, indice):
        self.login = login
        self.senha = senha
        self.id = id
        self.indice = indice
        self.status = 'fechada'
        self.window_title = None
        self.process = None
        self.hwnd = None
        self.pid = None
        self.inicio_tempo = None
        self.tempo_estimado = None
        self.crash_time = None
        self.restart_attempts = 0
        self.last_window_check = None
        

        self.game_stats = GameStats()
        self.last_ocr_update = None
        config.ocr_paused = False
    
    def set_ocr(self, ocr: OCR):
        self.ocr = ocr

    def _encontrar_janela_processo(self):
        print(f"Debug: Iniciando _encontrar_janela_processo() para {self.login}")
        print(f"Debug: used_pids atual: {self._used_pids}")
        
        hwnd, proc = encontrar_janela_por_processo(self._used_pids)
        print(f"Debug: encontrar_janela_por_processo retornou:")
        print(f"Debug: hwnd = {hwnd}")
        print(f"Debug: proc = {proc}")
        print(f"Debug: type(hwnd) = {type(hwnd)}")
        print(f"Debug: type(proc) = {type(proc)}")
        
        if hwnd and proc:
            print(f"Debug: Janela e processo encontrados!")
            print(f"Debug: proc.pid = {proc.pid}")
            print(f"Debug: proc.name = {proc.info.get('name', 'N/A') if hasattr(proc, 'info') else 'N/A'}")
            
            self.process = proc
            self.pid = proc.pid
            self._used_pids.add(proc.pid)
            print(f"Debug: Processo definido e PID adicionado aos used_pids")
            print(f"Debug: used_pids atualizado: {self._used_pids}")
        else:
            print(f"Debug: Nenhuma janela/processo encontrado")
            print(f"Debug: Vamos verificar processos ativos...")
            
            # Debug adicional: listar todos os processos que contêm as keywords
            try:
                keywords = config.KEYWORDS
                print(f"Debug: Keywords de busca: {keywords}")
                
                processos_encontrados = []
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        name = proc.info['name'].lower()
                        if any(k in name for k in keywords):
                            processos_encontrados.append({
                                'pid': proc.pid,
                                'name': proc.info['name'],
                                'usado': proc.pid in self._used_pids
                            })
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                        
                print(f"Debug: Processos encontrados com keywords:")
                for p in processos_encontrados:
                    print(f"Debug: - PID {p['pid']}: {p['name']} (usado: {p['usado']})")
                    
                if not processos_encontrados:
                    print(f"Debug: NENHUM processo encontrado com as keywords!")
                    print(f"Debug: Isso pode indicar que o executável não iniciou ou tem nome diferente")
                
            except Exception as e:
                print(f"Debug: Erro ao listar processos: {e}")
        
        return hwnd
    def encontrar_hwnd(self):
        try:
            hwnd = self._encontrar_janela_processo()
            if hwnd:
                self.hwnd = hwnd
                self.window_title = win32gui.GetWindowText(self.hwnd)
                
                if self.ocr:
                    self.ocr.set_window_handle(self.hwnd)
                    
                print(f"Hwnd encontrado para {self.login}: {self.hwnd}")
                return True
            
            print(f"Nenhuma janela encontrada para {self.login}")
            return False
            
        except Exception as e:
            print(f"Erro ao encontrar hwnd de {self.login}: {e}")
            return False

    def verificar_instancia_existente(self):
        
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    keywords = config.KEYWORDS
                    name = proc.info['name'].lower()

                    if any(k in name for k in keywords) and proc.pid not in self._used_pids:
                        def callback(hwnd, pid_list):
                            try:
                                _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
                                if found_pid == proc.pid and win32gui.IsWindowVisible(hwnd):
                                    rect = win32gui.GetWindowRect(hwnd)
                                    if (rect[2] - rect[0]) > MIN_WINDOW_SIZE and (rect[3] - rect[1]) > MIN_WINDOW_SIZE:
                                        pid_list.append(hwnd)
                            except:
                                pass
                        
                        hwnds = []
                        win32gui.EnumWindows(callback, hwnds)
                        
                        if hwnds:
                            self.hwnd = hwnds[0]
                            self.window_title = win32gui.GetWindowText(self.hwnd)
                            self.process = proc
                            self.pid = proc.pid
                            self._used_pids.add(proc.pid)
                            
                            if self.ocr:
                                self.ocr.set_window_handle(self.hwnd)
                            return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            print(f"Erro ao verificar instância existente para {self.login}: {e}")
        return False

    def iniciar(self):
        global DELAY_INICIAL
        
        print(f"Debug: Iniciando método iniciar() para conta {self.login}")
        
        # VERIFICAÇÃO DAS VARIÁVEIS DE EXECUTÁVEL
        print(f"Debug: Verificando variáveis de executável...")
        print(f"Debug: EXECUTAVEL = {EXECUTAVEL}")
        print(f"Debug: EXECUTAVEL2 = {EXECUTAVEL2}")
        print(f"Debug: config.EXECUTAVEL = {config.EXECUTAVEL}")
        print(f"Debug: config.EXECUTAVEL2 = {config.EXECUTAVEL2}")
        
        # Usar as variáveis do config em vez das globais
        executavel = config.EXECUTAVEL2 if self.indice >= 8 else config.EXECUTAVEL
        print(f"Debug: Executável selecionado: {executavel}")
        print(f"Debug: self.indice = {self.indice}")
        print(f"Debug: Condição (self.indice >= 8): {self.indice >= 8}")
        
        if executavel is None:
            print(f"Debug: ERRO - Executável ainda é None!")
            print(f"Debug: Tentando re-inicializar paths...")
            try:
                from paths import init_exec_paths
                init_exec_paths()
                executavel = config.EXECUTAVEL2 if self.indice >= 8 else config.EXECUTAVEL
                print(f"Debug: Após re-inicialização: {executavel}")
            except Exception as e:
                print(f"Debug: Erro ao re-inicializar: {e}")
                self.status = 'crashed'
                self.crash_time = datetime.now()
                return False
        
        if executavel is None or not os.path.exists(executavel):
            print(f"Debug: ERRO - Executável inválido ou não existe: {executavel}")
            if executavel:
                print(f"Debug: Arquivo existe: {os.path.exists(executavel)}")
            self.status = 'crashed'
            self.crash_time = datetime.now()
            return False
        
        print(f"Debug: Executável validado com sucesso: {executavel}")
        
        # Verificar instância existente
        print(f"Debug: Verificando instância existente...")
        if self.verificar_instancia_existente():
            print(f"Debug: Instância de {self.login} já está rodando - reconectando...")
            self.status = 'aberta'
            return True

        print(f"Debug: Nenhuma instância existente encontrada, iniciando nova...")
        self.status = 'iniciando'
        
        print(f"Debug: Tempo estimado calculado...")
        self.inicio_tempo = datetime.now()
        self.tempo_estimado = self.inicio_tempo + timedelta(
            seconds=DELAY_INICIAL + 5 + self.indice * 0.1 + DELAY_FINAL
        )
        print(f"Debug: Tempo estimado: {self.tempo_estimado}")

        try:
            print(f"Debug: Iniciando subprocess com executável: {executavel}")
            subprocess.Popen(executavel)
            print(f"Debug: Subprocess iniciado, aguardando 3 segundos...")
            time.sleep(3)
            
            print(f"Debug: Procurando janela do processo...")
            print(f"Debug: self._used_pids atual: {self._used_pids}")
            
            resultado = self._encontrar_janela_processo()
            print(f"Debug: Resultado de _encontrar_janela_processo(): {resultado}")
            print(f"Debug: Tipo do resultado: {type(resultado)}")
            
            if resultado is None:
                print(f"Debug: _encontrar_janela_processo() retornou None")
                hwnd = None
            else:
                hwnd = resultado
                print(f"Debug: hwnd obtido: {hwnd}")
            
            if not hwnd:
                print(f"Debug: Não foi possível localizar a janela da conta {self.login}")
                self.status = 'crashed'
                self.crash_time = datetime.now()
                return False

            print(f"Debug: Janela encontrada com sucesso")
            self.hwnd = hwnd
            
            try:
                self.window_title = win32gui.GetWindowText(self.hwnd)
                print(f"Debug: Título da janela obtido: {self.window_title}")
            except Exception as e:
                print(f"Debug: Erro ao obter título da janela: {e}")
                self.window_title = "Título não disponível"
            
            print(f"Debug: Verificando OCR...")
            print(f"Debug: self.ocr = {self.ocr}")
            print(f"Debug: type(self.ocr) = {type(self.ocr)}")
            
            if self.ocr:
                print(f"Debug: Configurando window handle no OCR...")
                try:
                    self.ocr.set_window_handle(self.hwnd)
                    print(f"Debug: Window handle configurado no OCR com sucesso")
                except Exception as e:
                    print(f"Debug: Erro ao configurar window handle no OCR: {e}")
            else:
                print(f"Debug: OCR não está disponível")
            
            print(f"Debug: Janela encontrada para {self.login}: hwnd={self.hwnd}")
            
            print(f"Debug: Forçando foco da janela...")
            if forcar_foco_janela(self.hwnd):
                print(f"Debug: Foco definido com sucesso para {self.login}")
            else:
                print(f"Debug: Falha ao definir foco para {self.login}")
            
            print(f"Debug: Aguardando DELAY_INICIAL ({DELAY_INICIAL} segundos)...")
            esperar(DELAY_INICIAL)
            DELAY_INICIAL *= 1.02
            print(f"Debug: DELAY_INICIAL atualizado para: {DELAY_INICIAL}")
            
            print(f"Debug: Verificando OCR_ENABLED...")
            print(f"Debug: config.OCR_ENABLED = {config.OCR_ENABLED}")
            
            if config.OCR_ENABLED:
                print(f"Debug: OCR está habilitado")
                print(f"Debug: Verificando se self.ocr existe...")
                
                if self.ocr is None:
                    print(f"Debug: ERRO - self.ocr é None mas OCR_ENABLED está True!")
                    print(f"Debug: Pulando verificação de OCR...")
                else:
                    print(f"Debug: self.ocr existe, tentando ler tela...")
                    try:
                        screen_text = self.ocr.read_screen()
                        print(f"Debug: screen_text obtido")
                        print(f"Debug: type(screen_text) = {type(screen_text)}")
                        print(f"Debug: screen_text = '{screen_text}'")
                        
                        if screen_text is None:
                            print(f"Debug: screen_text é None, definindo como string vazia")
                            screen_text = ""
                        
                        keywords = ["account name", "password", "token", "login", "optimize", "connection", "remember"]
                        print(f"Debug: Keywords definidas: {keywords}")
                        
                        print(f"Debug: Verificando se alguma keyword está presente...")
                        screen_text_lower = screen_text.lower() if screen_text else ""
                        print(f"Debug: screen_text_lower = '{screen_text_lower}'")
                        
                        keyword_found = any(word in screen_text_lower for word in keywords)
                        print(f"Debug: Keyword encontrada: {keyword_found}")
                        
                        loop_count = 0
                        while not keyword_found:
                            loop_count += 1
                            print(f"Debug: Loop #{loop_count} - Nenhuma keyword encontrada, pressionando enter...")
                            
                            pyautogui.press('enter')
                            time.sleep(1)
                            pyautogui.press('esc')
                            time.sleep(2)
                            
                            print(f"Debug: Lendo tela novamente...")
                            try:
                                screen_text = self.ocr.read_screen()
                                print(f"Debug: Nova leitura - type(screen_text) = {type(screen_text)}")
                                print(f"Debug: Nova leitura - screen_text = '{screen_text}'")
                                
                                if screen_text is None:
                                    print(f"Debug: screen_text é None na nova leitura")
                                    screen_text = ""
                                
                                screen_text_lower = screen_text.lower() if screen_text else ""
                                keyword_found = any(word in screen_text_lower for word in keywords)
                                print(f"Debug: Keyword encontrada na nova tentativa: {keyword_found}")
                                
                            except Exception as e:
                                print(f"Debug: Erro ao ler tela no loop: {e}")
                                screen_text = ""
                                screen_text_lower = ""
                                keyword_found = False
                            
                            time.sleep(1)
                            
                            # Segurança para evitar loop infinito
                            if loop_count > 10:
                                print(f"Debug: Limite de tentativas atingido (10), saindo do loop")
                                break
                        
                        print(f"Debug: Saiu do loop de verificação de keywords")
                        
                    except Exception as e:
                        print(f"Debug: Erro durante verificação OCR: {e}")
                        print(f"Debug: Continuando sem verificação OCR...")
            else:
                print(f"Debug: OCR não está habilitado, pulando verificação")

            print(f"Debug: Iniciando processo de login...")
            print(f"Debug: Digitando login: {self.login}")
            pyautogui.write(self.login)
            pyautogui.press('tab')
            time.sleep(0.5)
            
            print(f"Debug: Digitando senha...")
            pyautogui.write(self.senha)
            pyautogui.press('enter')

            print(f"Debug: Aguardando 5 segundos...")
            esperar(5)
            
            print(f"Debug: Pressionando 'down' {self.id} vezes...")
            for i in range(self.id):
                print(f"Debug: Pressionando 'down' - iteração {i+1}/{self.id}")
                pyautogui.press('down')
                
            print(f"Debug: Pressionando enter final...")
            pyautogui.press('enter')
            esperar(3)

            print(f"Debug: Definindo status como 'aberta'...")
            self.status = 'aberta'
            self.crash_time = None
            self.last_window_check = datetime.now()
            
            print(f"Debug: Inicialização concluída com sucesso para {self.login}")
            return True

        except Exception as e:
            print(f"Debug: ERRO CAPTURADO durante inicialização:")
            print(f"Debug: Tipo do erro: {type(e).__name__}")
            print(f"Debug: Mensagem do erro: {str(e)}")
            print(f"Debug: Linha do erro: {e.__traceback__.tb_lineno if e.__traceback__ else 'N/A'}")
            
            import traceback
            print(f"Debug: Traceback completo:")
            traceback.print_exc()
            
            self.status = 'crashed'
            self.crash_time = datetime.now()
            print(f"Debug: Status definido como 'crashed' para {self.login}")
            return False
    def mostrar(self):
        try:
            if not self.hwnd or not win32gui.IsWindow(self.hwnd):
                if not self.encontrar_hwnd():
                    print(f"Não foi possível encontrar janela para {self.login}")
                    return False
            
            if forcar_foco_janela(self.hwnd):
                print(f"Janela de {self.login} mostrada e focada com sucesso")
                return True
            else:
                print(f"Falha ao focar janela de {self.login}")
                return False
                
        except Exception as e:
            print(f"Erro ao mostrar janela de {self.login}: {e}")
            return False

    def update_game_stats(self):
        
        if not config.OCR_ENABLED or not self.ocr or self.status != 'aberta':
            return
            

        if hasattr(self, '_app_instance') and self._app_instance:
            if self._app_instance.tem_contas_iniciando() or config.ocr_paused:
                print(f"🚫 OCR suspenso para {self.login}")
                return
            
        agora = datetime.now()
        if (self.last_ocr_update and 
            (agora - self.last_ocr_update).total_seconds() < OCR_UPDATE_INTERVAL):
            return
        
        try:

            if hasattr(self, '_app_instance') and self._app_instance:
                if not self._app_instance.operacao_em_andamento:
                    self.mostrar()
                    time.sleep(0.5)
                    print(f"🎯 OCR com foco para {self.login}")
                else:
                    print(f"👁️ OCR sem mudança de foco para {self.login}")
            else:
                self.mostrar()
                time.sleep(0.5)
                
            self.game_stats = self.ocr.get_all_stats()
            self.last_ocr_update = agora
            print(f"✅ OCR atualizado para {self.login}: Level {self.game_stats.level}, Vida {self.game_stats.vida_atual}/{self.game_stats.vida_maxima}")
        except Exception as e:
            print(f"❌ Erro ao atualizar stats OCR para {self.login}: {e}")

    def verificar_janela_ativa(self):
        
        try:
            if not verificar_janela_valida(self.hwnd):
                print(f"Janela {self.login} inválida")
                self.hwnd = None
                if self.ocr:
                    self.ocr.set_window_handle(None)
                return self.encontrar_hwnd()
            return True
        except Exception as e:
            print(f"Erro ao verificar janela de {self.login}: {e}")
            return False

    def fechar(self):
        if self.pid:
            try:
                proc = psutil.Process(self.pid)
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except psutil.TimeoutExpired:
                    proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            
            self._used_pids.discard(self.pid)
        

        self.hwnd = None
        self.window_title = None
        self.pid = None
        self.process = None
        self.status = 'fechada'
        self.inicio_tempo = None
        self.tempo_estimado = None
        self.crash_time = None
        self.last_window_check = None
        self.last_ocr_update = None
        self.game_stats = GameStats()
        
        if self.ocr:
            self.ocr.set_window_handle(None)

    def verificar_status(self):
        if self.status != 'aberta':
            return True
        
        agora = datetime.now()
        if self.last_window_check and (agora - self.last_window_check).total_seconds() < WINDOW_CHECK_INTERVAL:
            return True
        
        self.last_window_check = agora
        

        processo_ativo = False
        if self.pid:
            try:
                proc = psutil.Process(self.pid)
                processo_ativo = proc.is_running()
                if processo_ativo:
                    self.process = proc
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        

        janela_ativa = self.verificar_janela_ativa()
        if not janela_ativa and processo_ativo:
            janela_ativa = self.encontrar_hwnd()
        

        if not processo_ativo and not janela_ativa:
            self.status = 'crashed'
            self.crash_time = datetime.now()
            self.process = None
            self.hwnd = None
            self.window_title = None
            self.pid = None
            self.game_stats = GameStats()
            if self.ocr:
                self.ocr.set_window_handle(None)
            print(f"Conta {self.login} crashou às {self.crash_time}")
            return False
        

        self.update_game_stats()
        return True

    def pode_reiniciar_automaticamente(self):
        if not AUTO_RESTART_ENABLED or self.status != 'crashed' or not self.crash_time:
            return False
        if self.restart_attempts >= MAX_RESTART_ATTEMPTS:
            return False
        tempo_desde_crash = (datetime.now() - self.crash_time).total_seconds()
        return tempo_desde_crash >= AUTO_RESTART_DELAY

    def reiniciar_automaticamente(self):
        if self.pode_reiniciar_automaticamente():
            self.restart_attempts += 1
            self.status = 'restarting'
            print(f"Tentativa {self.restart_attempts} de reiniciar conta {self.login}")
            
            self.fechar()
            time.sleep(2)
            
            if self.iniciar():
                self.restart_attempts = 0
                return True
            else:
                print(f"Falha ao reiniciar conta {self.login}")
                return False
        return False

    def get_tempo_restante(self):
        if self.inicio_tempo and self.tempo_estimado and self.status not in ['aberta', 'fechada']:
            agora = datetime.now()
            if agora < self.tempo_estimado:
                restante = self.tempo_estimado - agora
                return int(restante.total_seconds())
        return 0

    def get_status_info(self):
        info = {
            'login': self.login,
            'status': self.status,
            'indice': self.indice,
            'id': self.id,
            'restart_attempts': self.restart_attempts,
            'max_restart_attempts': MAX_RESTART_ATTEMPTS,
            'window_title': self.window_title,
            'process_active': self.process is not None,
            'hwnd': self.hwnd,
            'pid': self.pid,
            'ocr_enabled': config.OCR_ENABLED and self.ocr is not None,
        }
        
        if config.OCR_ENABLED and self.game_stats:
            info['game_stats'] = self.game_stats.to_dict()
        
        if self.crash_time:
            info['crash_time'] = self.crash_time.isoformat()
            info['time_since_crash'] = (datetime.now() - self.crash_time).total_seconds()
        
        if self.inicio_tempo:
            info['start_time'] = self.inicio_tempo.isoformat()
        
        if self.tempo_estimado:
            info['estimated_completion'] = self.tempo_estimado.isoformat()
            
        info['remaining_time'] = self.get_tempo_restante()
        return info