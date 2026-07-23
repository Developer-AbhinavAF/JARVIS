class MoodEngine:
    def __init__(self):
        # Maps mood string to playback speed (multiplier)
        self.mood_map = {
            "calm": 1.0,
            "serious": 0.9,
            "happy": 1.1,
            "motivational": 1.05,
            "warning": 0.85,
            "beast": 1.15,
            "excited": 1.15,
            "assistant": 1.0,
            "night": 0.8,
            "focus": 0.9
        }
        self.current_mood = "calm"
        
    def set_mood(self, mood: str):
        mood = mood.lower()
        if mood in self.mood_map:
            self.current_mood = mood
            return True
        return False
        
    def get_speed(self, mood: str = None) -> float:
        m = mood or self.current_mood
        return self.mood_map.get(m.lower(), 1.0)
        
    def get_current_mood(self) -> str:
        return self.current_mood

mood_engine = MoodEngine()
