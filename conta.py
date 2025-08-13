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
        
        hwnd, proc = encontrar_janela_por_processo(self._used_pids)
        if hwnd and proc:
            self.process = proc
            self.pid = proc.pid
            self._used_pids.add(proc.pid)
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
                    if 'aurera' in proc.info['name'].lower() and proc.pid not in self._used_pids:
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
        
        if self.verificar_instancia_existente():
            print(f"Instância de {self.login} já está rodando - reconectando...")
            self.status = 'aberta'
            return True

        self.status = 'iniciando'
        executavel = EXECUTAVEL2 if self.indice >= 8 else EXECUTAVEL

        self.inicio_tempo = datetime.now()
        self.tempo_estimado = self.inicio_tempo + timedelta(
            seconds=DELAY_INICIAL + 5 + self.indice * 0.1 + DELAY_FINAL
        )

        try:
            subprocess.Popen(executavel)
            time.sleep(3)
            
            hwnd = self._encontrar_janela_processo()
            if not hwnd:
                print(f"Não foi possível localizar a janela da conta {self.login}")
                self.status = 'crashed'
                self.crash_time = datetime.now()
                return False

            self.hwnd = hwnd
            self.window_title = win32gui.GetWindowText(self.hwnd)
            
            if self.ocr:
                self.ocr.set_window_handle(self.hwnd)
            
            print(f"Janela encontrada para {self.login}: hwnd={self.hwnd}")
            
            if forcar_foco_janela(self.hwnd):
                print(f"Foco definido com sucesso para {self.login}")
            else:
                print(f"Falha ao definir foco para {self.login}")
            
            esperar(DELAY_INICIAL)
            DELAY_INICIAL *= 1.02


            for _ in range(3):
                pyautogui.keyDown('ctrl')
                pyautogui.press('a')
                pyautogui.keyUp('ctrl')
                time.sleep(0.05)
                pyautogui.press('delete')
                time.sleep(0.05)
                pyautogui.press('tab')
                time.sleep(0.2)

            pyautogui.write(self.login)
            pyautogui.press('tab')
            pyautogui.write(self.senha)
            pyautogui.press('enter')

            esperar(5)
            for _ in range(self.id):
                pyautogui.press('down')
            pyautogui.press('enter')
            esperar(3)

            self.status = 'aberta'
            self.crash_time = None
            self.last_window_check = datetime.now()
            return True

        except Exception as e:
            self.status = 'crashed'
            self.crash_time = datetime.now()
            print(f"Erro ao iniciar conta {self.login}: {e}")
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