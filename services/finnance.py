"""
General Ledger & Financial Accounting Service
"""

from datetime import datetime
from sqlalchemy.orm import Session
from services.models import Account, AccountType, JournalEntry, JournalItem, Transaction
from services.csv_utils import safe_read_csv, sanitize_numeric_column, map_column
from services.analytics import AnalyticsEngine
from services.exceptions import TEAMAIException


class FinanceService:

    @staticmethod
    def seed_default_accounts(db: Session):
        default_accounts = [
            ("1010", "Cash & Bank Holdings", AccountType.ASSET),
            ("1200", "Vehicle Inventory Asset", AccountType.ASSET),
            ("1300", "Accounts Receivable", AccountType.ASSET),
            ("2010", "Accounts Payable", AccountType.LIABILITY),
            ("4010", "Vehicle Sales Revenue", AccountType.REVENUE),
            ("4020", "Service Center Revenue", AccountType.REVENUE),
            ("5010", "Cost of Goods Sold (COGS)", AccountType.EXPENSE),
            ("5020", "Operational & Payroll Expense", AccountType.EXPENSE),
        ]
        for code, name, acc_type in default_accounts:
            if not db.query(Account).filter(Account.code == code).first():
                db.add(Account(code=code, name=name, account_type=acc_type, balance=0.0))
        db.commit()

    @staticmethod
    def post_journal_entry(
        db: Session,
        description: str,
        reference: str,
        debit_code: str,
        credit_code: str,
        amount: float
    ) -> JournalEntry:
        if amount <= 0:
            raise TEAMAIException("Journal entry amount must be greater than zero.")

        debit_acc = db.query(Account).filter(Account.code == debit_code).first()
        credit_acc = db.query(Account).filter(Account.code == credit_code).first()

        if not debit_acc or not credit_acc:
            raise TEAMAIException(f"Invalid account codes: {debit_code}, {credit_code}")

        entry = JournalEntry(
            entry_number=f"JE-{int(datetime.utcnow().timestamp())}",
            reference=reference,
            description=description
        )
        db.add(entry)
        db.flush()

        debit_item = JournalItem(entry_id=entry.id, account_id=debit_acc.id, debit=amount, credit=0.0)
        debit_acc.balance += amount

        credit_item = JournalItem(entry_id=entry.id, account_id=credit_acc.id, debit=0.0, credit=amount)
        credit_acc.balance -= amount

        db.add_all([debit_item, credit_item])
        db.commit()
        db.refresh(entry)
        return entry

    @staticmethod
    def import_transactions_csv(db: Session, file_bytes: bytes) -> dict:
        """Ingests transaction CSV and runs IQR anomaly detection to mark suspicious items."""
        try:
            df = safe_read_csv(file_bytes)

            title_col = map_column(df, ["title", "description", "name", "memo"])
            type_col = map_column(df, ["type", "transaction_type", "category_type"])
            cat_col = map_column(df, ["category", "department", "account"])
            amt_col = map_column(df, ["amount", "value", "total", "price"])

            df["clean_amount"] = sanitize_numeric_column(df[amt_col])

            # Run IQR Anomaly Detection Algorithm
            anomaly_res = AnalyticsEngine.detect_anomalies_iqr(df, "clean_amount")
            anomalous_indices = set(
                [row.get("_idx", idx) for idx, row in enumerate(anomaly_res.get("anomalies", []))]
            )

            count = 0
            for idx, row in df.iterrows():
                amt = float(row["clean_amount"])
                t_type = str(row[type_col]).upper() if type_col in row else "EXPENSE"

                tx = Transaction(
                    title=str(row[title_col]),
                    type=t_type if t_type in ["INCOME", "EXPENSE"] else "EXPENSE",
                    category=str(row[cat_col]),
                    amount=amt,
                    is_suspicious=(idx in anomalous_indices)
                )
                db.add(tx)
                count += 1

            db.commit()
            return {
                "success": True,
                "records_imported": count,
                "anomalies_flagged": len(anomalous_indices)
            }
        except Exception as e:
            db.rollback()
            raise TEAMAIException(f"Transaction CSV Error: {str(e)}")