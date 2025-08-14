
import re
import json
import os
import time
from typing import Optional, Tuple, Dict
import pytesseract
import pyautogui
from PIL import Image, ImageGrab
from datetime import datetime
from gamestats import GameStats
from utils import resource_path
from config import DEFAULT_OCR_REGIONS, OCR_CONFIG


pytesseract.pytesseract.tesseract_cmd = resource_path("bin/tesseract.exe")

class OCR:
    
    
    def __init__(self, hwnd=None, config_file=None):
        self.hwnd = hwnd
        self.config_file = config_file or resource_path("ocr/ocr.json")
        self.regions = DEFAULT_OCR_REGIONS.copy()
        self.current_stats = GameStats()
        self._load_config()
        

    

    def _load_config(self):
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                if 'regions' in config:
                    self.regions.update(config['regions'])
                    print(f"✅ Configurações OCR carregadas: {self.config_file}")
            except Exception as e:
                print(f"⚠️ Erro ao carregar configurações OCR: {e}")
        
    def set_window_handle(self, hwnd):
        
        self.hwnd = hwnd
        
        
    def capture_region(self, coords: Tuple[int, int, int, int]) -> Optional[Image.Image]:
        
        try:
            x1, y1, x2, y2 = coords
            return pyautogui.screenshot(region=(x1, y1, x2 - x1, y2 - y1))
        except Exception as e:
            print(f"Erro ao capturar região: {e}")
            return None
            
    def extract_text_from_region(self, region_name: str) -> str:
        
        if region_name not in self.regions:
            return ""
            
        try:
            coords = self.regions[region_name]
            image = self.capture_region(coords)
            if image is None:
                return ""
                
            return pytesseract.image_to_string(image, config=OCR_CONFIG).strip()
        except Exception as e:
            print(f"Erro ao extrair texto da região {region_name}: {e}")
            return ""
            
    def extract_vida_mana(self, region_name: str) -> Tuple[int, int]:
        
        try:
            text = self.extract_text_from_region(region_name)
            if not text:
                return 0, 0
                

            match = re.search(r'(\d+)\s*/\s*(\d+)', text)
            if match:
                return int(match.group(1)), int(match.group(2))
                

            numbers = re.findall(r'\d+', text)
            if len(numbers) >= 2:
                return int(numbers[0]), int(numbers[1])
        except:
            pass
        return 0, 0
        
    def extract_single_number(self, region_name: str) -> int:
        
        try:
            text = self.extract_text_from_region(region_name)
            numbers = re.findall(r'\d+', text)
            return int(numbers[0]) if numbers else 0
        except:
            return 0
        
    def extract_character_info(self) -> Dict[str, int]:
        
        try:
            text = self.extract_text_from_region('character_info')
            if not text:
                return {}
                
            patterns = {
                'level': r'Level\s*(\d+)',
                'xp': r'XP\s*(\d+)', 
                'hit_points': r'Hit Points\s*(\d+)',
                'capacity': r'Capacity\s*(\d+)',
                'speed': r'Speed\s*(\d+)',
                'food': r'Food\s*(\d+)',
                'stamina': r'Stamina\s*(\d+)',
                'offline_training': r'Offline Training\s*(\d+)',
                'magic_level': r'Magic Level\s*(\d+)'
            }
            
            info = {}
            for key, pattern in patterns.items():
                match = re.search(pattern, text, re.IGNORECASE)
                info[key] = int(match.group(1)) if match else 0
                
            return info
        except:
            return {}
            
    def extract_combat_skills(self) -> Dict[str, int]:
        
        try:
            text = self.extract_text_from_region('combat_skills')
            if not text:
                return {}
                
            patterns = {
                'fist_fighting': r'Fist Fighting\s*(\d+)',
                'club_fighting': r'Club Fighting\s*(\d+)',
                'sword_fighting': r'Sword Fighting\s*(\d+)',
                'axe_fighting': r'Axe Fighting\s*(\d+)',
                'distance_fighting': r'Distance Fighting\s*(\d+)',
                'shielding': r'Shielding\s*(\d+)',
                'fishing': r'Fishing\s*(\d+)'
            }
            
            skills = {}
            for key, pattern in patterns.items():
                match = re.search(pattern, text, re.IGNORECASE)
                skills[key] = int(match.group(1)) if match else 0
                
            return skills
        except:
            return {}
            
    def get_all_stats(self, force_focus=True):
        
        stats = GameStats()
        
        try:
            if not force_focus:
                print("OCR executando sem mudança de foco")
            

            stats.vida_atual, stats.vida_maxima = self.extract_vida_mana('vida_texto')
            stats.mana_atual, stats.mana_maxima = self.extract_vida_mana('mana_texto')
            

            stats.fps = self.extract_single_number('fps_texto')
            stats.ping = self.extract_single_number('ping_texto')
            

            stats.name = self.extract_text_from_region('name')
            

            char_info = self.extract_character_info()
            for key, value in char_info.items():
                setattr(stats, key, value)
                

            combat_skills = self.extract_combat_skills()
            for key, value in combat_skills.items():
                setattr(stats, key, value)
                
        except Exception as e:
            print(f"Erro ao coletar estatísticas OCR: {e}")
            
        self.current_stats = stats
        return stats
        
    def save_regions_to_file(self, filename=None):
        
        if filename is None:
            filename = self.config_file
            
        try:
            config = {
                'regions': self.regions,
                'timestamp': str(datetime.now()),
                'version': '1.0'
            }
            
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Configurações OCR salvas: {filename}")
            return True
        except Exception as e:
            print(f"❌ Erro ao salvar regiões: {e}")
            return False
            
    def load_regions_from_file(self, filename=None):
        
        if filename is None:
            filename = self.config_file
            
        try:
            if not os.path.exists(filename):
                return False
                
            with open(filename, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            if 'regions' in config:
                self.regions.update(config['regions'])
                print(f"✅ Regiões carregadas: {filename}")
                return True
            return False
                
        except Exception as e:
            print(f"❌ Erro ao carregar regiões: {e}")
            return False
    def open_region_configurator(self, parent, account_name=""):
        
        from region_config_window import RegionConfigWindow
        return RegionConfigWindow(parent, self, account_name)
    

    def read_screen(self) -> str:
        try:
            screenshot = ImageGrab.grab(bbox=(822, 380, 1116, 694))
            a = pytesseract.image_to_string(screenshot, config='--psm 6').strip()
            print(a)
            return a
        except Exception as e:
            print(f"Erro ao extrair texto da tela: {e}")
            return ""

