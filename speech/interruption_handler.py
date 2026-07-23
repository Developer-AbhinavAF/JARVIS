import threading

class InterruptionHandler:
    def __init__(self):
        self.is_interrupted = False
        self._lock = threading.Lock()
        
    def check(self) -> bool:
        """Check if an interruption has occurred."""
        with self._lock:
            return self.is_interrupted
            
    def interrupt(self) -> None:
        """Trigger an interruption."""
        with self._lock:
            self.is_interrupted = True
            
    def clear(self) -> None:
        """Clear the interruption flag (usually before starting new speech)."""
        with self._lock:
            self.is_interrupted = False

interruption_handler = InterruptionHandler()
