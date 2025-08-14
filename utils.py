
import time
import sys
import os
import win32gui
import win32process
import win32con
import ctypes
import psutil
from config import *

def esperar(segundos):
    
    for _ in range(int(segundos)):
        time.sleep(1)

def resource_path(relative_path):
    
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.abspath(relative_path)

def forcar_foco_janela(hwnd):
    
    try:
        if not win32gui.IsWindow(hwnd):
            return False
        
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(FOCUS_DELAY)
        
        ctypes.windll.user32.AllowSetForegroundWindow(-1)
        
        current_thread = ctypes.windll.kernel32.GetCurrentThreadId()
        target_thread = ctypes.windll.user32.GetWindowThreadProcessId(hwnd, None)
        
        if target_thread != current_thread:
            ctypes.windll.user32.AttachThreadInput(target_thread, current_thread, True)
        
        try:
            win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, 
                                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
            time.sleep(0.1)
            
            win32gui.SetForegroundWindow(hwnd)
            win32gui.BringWindowToTop(hwnd)
            
            win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0, 
                                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
            
            return win32gui.GetForegroundWindow() == hwnd
                
        finally:
            if target_thread != current_thread:
                ctypes.windll.user32.AttachThreadInput(target_thread, current_thread, False)
                
    except Exception as e:
        print(f"Erro ao forçar foco: {e}")
        return False

def encontrar_janela_por_processo(used_pids=None):
    
    if used_pids is None:
        used_pids = set()
        
    start = time.time()
    while time.time() - start < PROCESS_TIMEOUT:
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if 'otc' in proc.info['name'].lower() and 'dashboard' not in proc.info['name'].lower():
                        if proc.pid in used_pids:
                            continue
                        
                        def callback(hwnd, pid_list):
                            try:
                                _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
                                if found_pid == proc.pid and win32gui.IsWindowVisible(hwnd):
                                    rect = win32gui.GetWindowRect(hwnd)
                                    width = rect[2] - rect[0]
                                    height = rect[3] - rect[1]
                                    if width > MIN_WINDOW_SIZE and height > MIN_WINDOW_SIZE:
                                        pid_list.append(hwnd)
                            except:
                                pass
                        
                        hwnds = []
                        win32gui.EnumWindows(callback, hwnds)
                        
                        if hwnds:
                            melhor_hwnd = max(hwnds, key=lambda h: 
                                (win32gui.GetWindowRect(h)[2] - win32gui.GetWindowRect(h)[0]) * 
                                (win32gui.GetWindowRect(h)[3] - win32gui.GetWindowRect(h)[1]),
                                default=None)
                            
                            if melhor_hwnd:
                                return melhor_hwnd, proc
                                
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            print(f"Erro ao buscar processo: {e}")
        
        time.sleep(0.5)
    return None, None

def verificar_janela_valida(hwnd):
    
    try:
        if not hwnd or not win32gui.IsWindow(hwnd):
            return False
            
        if not win32gui.IsWindowVisible(hwnd):
            return False
            
        rect = win32gui.GetWindowRect(hwnd)
        width = rect[2] - rect[0] 
        height = rect[3] - rect[1]
        return width > WINDOW_VALIDATION_SIZE and height > WINDOW_VALIDATION_SIZE
    except:
        return False