
from dataclasses import dataclass, asdict

@dataclass
class GameStats:
    
    

    name: str = ""
    level: int = 0
    xp: int = 0
    

    vida_atual: int = 0
    vida_maxima: int = 0
    mana_atual: int = 0
    mana_maxima: int = 0
    

    hit_points: int = 0
    capacity: int = 0
    speed: int = 0
    food: int = 0
    stamina: int = 0
    magic_level: int = 0
    offline_training: int = 0
    

    fps: int = 0
    ping: int = 0
    

    fist_fighting: int = 0
    club_fighting: int = 0
    sword_fighting: int = 0
    axe_fighting: int = 0
    distance_fighting: int = 0
    shielding: int = 0
    fishing: int = 0
    
    def to_dict(self):
        
        data = asdict(self)
        return {
            'name': data['name'],
            'vida': {'atual': data['vida_atual'], 'maxima': data['vida_maxima']},
            'mana': {'atual': data['mana_atual'], 'maxima': data['mana_maxima']},
            'performance': {'fps': data['fps'], 'ping': data['ping']},
            'character': {
                'level': data['level'],
                'xp': data['xp'],
                'hit_points': data['hit_points'],
                'capacity': data['capacity'],
                'speed': data['speed'],
                'food': data['food'],
                'stamina': data['stamina'],
                'offline_training': data['offline_training'],
                'magic_level': data['magic_level']
            },
            'skills': {
                'fist_fighting': data['fist_fighting'],
                'club_fighting': data['club_fighting'],
                'sword_fighting': data['sword_fighting'],
                'axe_fighting': data['axe_fighting'],
                'distance_fighting': data['distance_fighting'],
                'shielding': data['shielding'],
                'fishing': data['fishing']
            }
        }