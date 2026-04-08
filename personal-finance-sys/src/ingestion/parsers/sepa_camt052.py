from lxml import etree
from datetime import datetime
import os
from typing import List, Dict, Any
from src.ingestion.base_parser import BaseParser

class Camt052Parser(BaseParser):
    def parse(self, filepath: str) -> List[Dict[str, Any]]:
        tree = etree.parse(filepath)
        root = tree.getroot()
        
        # Strip namespaces dynamically for easier XPath evaluation
        for elem in root.getiterator():
            if not hasattr(elem.tag, 'find'): continue
            i = elem.tag.find('}')
            if i >= 0:
                elem.tag = elem.tag[i+1:]
                
        records = []
        filename = os.path.basename(filepath)
        
        for ntry in root.findall('.//Ntry'):
            try:
                amt_node = ntry.find('.//Amt')
                amt = float(amt_node.text) if amt_node is not None else 0.0
                
                # Handling Credit/Debit indicator
                cdt_dbt = ntry.find('.//CdtDbtInd')
                if cdt_dbt is not None and cdt_dbt.text == 'DBIT':
                    amt = -amt
                    
                # Date logic
                dt_node = ntry.find('.//BookgDt/Dt')
                if dt_node is not None:
                    bookg_dt = datetime.strptime(dt_node.text, '%Y-%m-%d').date()
                else:
                    dt_tm_node = ntry.find('.//BookgDt/DtTm')
                    if dt_tm_node is not None:
                        bookg_dt = datetime.strptime(dt_tm_node.text[:10], '%Y-%m-%d').date()
                    else:
                        continue # Required field
                
                # Payee
                payee_node = ntry.find('.//NtryDtls/TxDtls/RltdPties/Cdtr/Nm')
                if payee_node is None:
                    payee_node = ntry.find('.//NtryDtls/TxDtls/RltdPties/Dbtr/Nm')
                payee = payee_node.text if payee_node is not None else "UNKNOWN_PAYEE"
                
                # Purpose
                purpose_node = ntry.find('.//NtryDtls/TxDtls/RmtInf/Ustrd')
                purpose = purpose_node.text if purpose_node is not None else ""
                
                records.append({
                    'booking_date': bookg_dt,
                    'valuta_date': bookg_dt,
                    'amount': amt,
                    'currency': amt_node.get('Ccy', 'EUR') if amt_node is not None else 'EUR',
                    'raw_payee': payee,
                    'raw_purpose': purpose,
                    'source_file': filename
                })
            except Exception as e:
                print(f"Error parsing CAMT.052 Ntry node: {e}")
                
        return records
