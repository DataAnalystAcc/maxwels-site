from typing import Dict, Any
import logging

from src.ingestion.base_parser import BaseParser
from src.ingestion.validators import RawTransaction
from src.ingestion.loaders import DatabaseLoader
from pydantic import ValidationError

class IngestionOrchestrator:
    def __init__(self, parser: BaseParser, account_id: str):
        self.parser = parser
        self.loader = DatabaseLoader(account_id)
        
    def run(self, filepath: str) -> Dict[str, Any]:
        logging.info(f"Starting ingestion for {filepath}")
        
        # 1. Parse (Extract)
        try:
            raw_dicts = self.parser.parse(filepath)
        except Exception as e:
            logging.error(f"Failed to parse file: {e}")
            return {"fatal_error": str(e)}
        
        # 2. Validate & Normalize (Transform)
        valid_txs = []
        validation_errors = 0
        for r in raw_dicts:
            try:
                valid_txs.append(RawTransaction(**r))
            except ValidationError as e:
                logging.warning(f"Validation error for record: {e}")
                validation_errors += 1
                
        # 3. Load 
        stats = self.loader.load(valid_txs)
        stats['validation_errors'] = validation_errors
        return stats
