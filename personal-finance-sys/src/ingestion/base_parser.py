from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseParser(ABC):
    @abstractmethod
    def parse(self, filepath: str) -> List[Dict[str, Any]]:
        """Reads a file and yields a list of raw dictionaries to be validated."""
        pass
