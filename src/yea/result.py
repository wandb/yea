from typing import Any, Dict, List

class ResultData:
    failures: List[str]
    _state: Dict[str, Any]

    def __init__(self):
        self.failures = []
        self._state = {}
