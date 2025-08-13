# config.py - Todas as configurações centralizadas e otimizadas
import os
import logging
import pyautogui

# === CONFIGURAÇÕES DE EXECUTÁVEIS ===
EXECUTAVEL = os.path.join(os.environ["APPDATA"], "AureraOT", "aurera_dx.exe")
EXECUTAVEL2 = os.path.join(os.environ["APPDATA"], "AureraOT", "aurera_dx2.exe")

# === CONFIGURAÇÕES DE TIMING ===
DELAY_INICIAL = 22.0
DELAY_FINAL = 2
AUTO_RESTART_ENABLED = True
AUTO_RESTART_DELAY = 30
WINDOW_CHECK_INTERVAL = 3  # Centralizado
OCR_UPDATE_INTERVAL = 20.0

# === CONFIGURAÇÕES DA API ===
API_PORT = 5000

# === CONFIGURAÇÕES DO OCR ===
OCR_ENABLED = True
OCR_CONFIG = '--psm 6'
ocr_paused = False

# === REGIÕES OCR PADRÃO ===
DEFAULT_OCR_REGIONS = {
    'vida_texto': (380, 25, 480, 40),
    'mana_texto': (1050, 25, 1150, 40),
    'fps_texto': (150, 55, 200, 75),
    'character_info': (1200, 90, 1350, 280),
    'combat_skills': (1200, 320, 1350, 450),
    'name': (700, 10, 900, 40),
    'ping_texto': (188, 90, 244, 103)
}

# === CONFIGURAÇÕES DE PROCESSO ===
MAX_RESTART_ATTEMPTS = 3
MIN_WINDOW_SIZE = 50
WINDOW_VALIDATION_SIZE = 10
PROCESS_TIMEOUT = 10
FOCUS_DELAY = 0.2

# === CONFIGURAÇÕES PYAUTOGUI ===
pyautogui.FAILSAFE = False

# === CONFIGURAÇÕES DE LOGGING ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === CORES PARA STATUS ===
STATUS_COLORS = {
    'aberta': '#27ae60',
    'fechada': '#e74c3c', 
    'iniciando': '#f39c12',
    'restarting': '#3498db',
    'crashed': '#8e44ad'
}

# === CORES PARA REGIÕES OCR ===
REGION_COLORS = {
    'vida_texto': '#FF0000',
    'mana_texto': '#0000FF', 
    'fps_texto': '#00FF00',
    'character_info': '#FF00FF',
    'combat_skills': '#00FFFF',
    'name': '#FFA500',
    'ping_texto': '#FFFF00'
}