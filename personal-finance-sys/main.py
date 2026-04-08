import argparse
import os
from src.db.connection import init_db
from src.ingestion.parsers.volksbank import VolksbankCSVParser
from src.ingestion.parsers.sepa_camt052 import Camt052Parser
from src.ingestion.pipeline import IngestionOrchestrator
from src.engine.rules import RuleEngine
from src.db.models import Account
from src.db.connection import SessionLocal

def ingest_file(filepath: str, account_name: str, file_type: str):
    print(f"Ingesting {filepath} for account '{account_name}' [{file_type.upper()}]...")
    
    db = SessionLocal()
    account = db.query(Account).filter_by(bank_name=account_name).first()
    if not account:
        account = Account(bank_name=account_name)
        db.add(account)
        db.commit()
    account_id = account.id
    db.close()

    if file_type.lower() == 'xml':
        parser = Camt052Parser()
    else:
        parser = VolksbankCSVParser()
        
    orchestrator = IngestionOrchestrator(parser, account_id)
    stats = orchestrator.run(filepath)
    
    print("Ingestion Stats:")
    for k, v in stats.items():
        print(f"  {k}: {v}")

def run_categorization():
    print("Running Categorization Engine...")
    engine = RuleEngine()
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    rules_path = os.path.join(base_dir, 'rules.json')
    added = engine.load_seed_rules(rules_path)
    if added:
        print(f"Loaded {added} new seed rule(s) from rules.json")
        
    updated = engine.categorize_unclassified()
    print(f"Categorization complete. Updated {updated} transaction(s).")

def scan_subscriptions():
    print("Hunting for forgotten subscriptions...")
    engine = RuleEngine()
    freqs = engine.detect_recurring_unknowns()
    if not freqs:
        print("No recurring patterns found.")
    for f in freqs:
        print(f"[{f['payee']}] x{f['count']} (Mean interval: {f['interval_mean']:.0f} days) -> {f['suggestion']}")

def main():
    parser = argparse.ArgumentParser(description="Personal Finance System CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    subparsers.add_parser("init", help="Initialize the database schema")
    
    ingest_cmd = subparsers.add_parser("ingest", help="Ingest a bank file")
    ingest_cmd.add_argument("file", type=str, help="Path to the file")
    ingest_cmd.add_argument("--account", type=str, required=True, help="Account Name")
    ingest_cmd.add_argument("--type", type=str, choices=['csv', 'xml'], default='csv', help="Format")
    
    subparsers.add_parser("categorize", help="Run rules engine")
    subparsers.add_parser("scan", help="Scan for subscriptions")
    
    args = parser.parse_args()
    
    if args.command == "init":
        init_db()
        print("Done.")
    elif args.command == "ingest":
        if not os.path.exists(args.file):
            print("File not found.")
            return
        ingest_file(args.file, args.account, args.type)
    elif args.command == "categorize":
        run_categorization()
    elif args.command == "scan":
        scan_subscriptions()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
