"""
Enterprise General Ledger, Financial Accounting & Quantitative Finance Service
Implements GAAP/IFRS Double-Entry Standards, Compound Journal Entries,
Financial Statements, Financial Ratio Analytics, and Capital Budgeting Math.
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, case
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from services.models import Account, AccountType, JournalEntry, JournalItem, Transaction
from services.csv_utils import safe_read_csv, sanitize_numeric_column, map_column
from services.analytics import AnalyticsEngine
from services.exceptions import TEAMAIException, ValidationException

logger = logging.getLogger(__name__)


# ============================================================================
# 1. PYDANTIC CONTRACTS & SCHEMAS
# ============================================================================

class JournalItemInput(BaseModel):
    account_code: str
    debit: float = Field(default=0.0, ge=0.0)
    credit: float = Field(default=0.0, ge=0.0)

    @field_validator("debit", "credit")
    def round_amounts(cls, v: float) -> float:
        return round(v, 2)


class CompoundJournalEntryInput(BaseModel):
    description: str = Field(..., min_length=3, max_length=255)
    reference: str = Field(..., min_length=1, max_length=100)
    items: List[JournalItemInput] = Field(..., min_items=2)

    @field_validator("items")
    def validate_double_entry_balance(cls, items: List[JournalItemInput]) -> List[JournalItemInput]:
        total_debit = sum(item.debit for item in items)
        total_credit = sum(item.credit for item in items)
        if round(total_debit, 2) != round(total_credit, 2):
            raise ValueError(
                f"Unbalanced Journal Entry! Total Debits (${total_debit:,.2f}) "
                f"must equal Total Credits (${total_credit:,.2f})."
            )
        if total_debit == 0.0:
            raise ValueError("Journal Entry total monetary value must be greater than zero.")
        return items


class AccountBalanceSchema(BaseModel):
    code: str
    name: str
    account_type: str
    debit_balance: float
    credit_balance: float


class TrialBalanceReport(BaseModel):
    as_of_date: str
    total_debits: float
    total_credits: float
    is_balanced: bool
    accounts: List[AccountBalanceSchema]


class IncomeStatementReport(BaseModel):
    period_start: Optional[str]
    period_end: Optional[str]
    gross_revenue: float
    cost_of_goods_sold: float
    gross_profit: float
    operating_expenses: float
    operating_income_ebit: float
    net_profit_margin_pct: float


class BalanceSheetReport(BaseModel):
    as_of_date: str
    total_current_assets: float
    total_non_current_assets: float
    total_assets: float
    total_current_liabilities: float
    total_long_term_liabilities: float
    total_liabilities: float
    total_equity: float
    total_liabilities_and_equity: float
    is_equation_valid: bool  # Assets == Liabilities + Equity


class FinancialRatiosReport(BaseModel):
    current_ratio: float = Field(..., description="Liquidity: Current Assets / Current Liabilities")
    quick_ratio: float = Field(..., description="Acid-Test: (Cash + AR) / Current Liabilities")
    debt_to_equity: float = Field(..., description="Solvency: Total Liabilities / Total Equity")
    return_on_assets_roa: float = Field(..., description="Efficiency: Net Income / Total Assets (%)")
    return_on_equity_roe: float = Field(..., description="Profitability: Net Income / Total Equity (%)")
    asset_turnover: float = Field(..., description="Efficiency: Revenue / Total Assets")
    altman_z_score: float = Field(..., description="Bankruptcy Risk Score (<1.1 High Risk, >2.6 Safe)")
    solvency_status: str


class CapitalBudgetingReport(BaseModel):
    initial_investment: float
    discount_rate_pct: float
    net_present_value_npv: float
    internal_rate_of_return_irr_pct: Optional[float]
    profitability_index: float
    payback_period_years: float
    investment_recommendation: str


# ============================================================================
# 2. GENERAL LEDGER & FINANCIAL SERVICE
# ============================================================================

class FinanceService:
    """
    Enterprise General Ledger & Accounting Engine.
    Handles GAAP Chart of Accounts seeding, Normal Balance rules,
    Compound Journal Entries, Financial Statements, and Quantitative Ratios.
    """

    # ------------------------------------------------------------------------
    # ACCOUNT NORMAL BALANCE ENGINE
    # ------------------------------------------------------------------------
    @staticmethod
    def _apply_normal_balance_delta(account: Account, debit: float, credit: float) -> None:
        """
        Updates account balance based on GAAP Normal Balance Conventions:
        - Assets & Expenses: DEBIT increases (+), CREDIT decreases (-)
        - Liabilities, Equity & Revenue: CREDIT increases (+), DEBIT decreases (-)
        """
        acc_type_str = str(account.account_type).upper()

        if "ASSET" in acc_type_str or "EXPENSE" in acc_type_str:
            account.balance += (debit - credit)
        elif "LIABILITY" in acc_type_str or "EQUITY" in acc_type_str or "REVENUE" in acc_type_str:
            account.balance += (credit - debit)
        else:
            # Fallback for generic types
            account.balance += (debit - credit)

    # ------------------------------------------------------------------------
    # CHART OF ACCOUNTS SEEDING
    # ------------------------------------------------------------------------
    @staticmethod
    def seed_default_accounts(db: Session) -> Dict[str, Any]:
        """
        Seeds a comprehensive automotive dealership Chart of Accounts.
        """
        default_accounts = [
            # ASSETS (1000s)
            ("1010", "Cash & Operating Bank Holdings", AccountType.ASSET),
            ("1100", "Floorplan Finance Reserve Asset", AccountType.ASSET),
            ("1200", "New Vehicle Inventory Asset", AccountType.ASSET),
            ("1220", "Used Vehicle Inventory Asset", AccountType.ASSET),
            ("1250", "Spare Parts & Accessories Inventory", AccountType.ASSET),
            ("1300", "Accounts & Contracts Receivable", AccountType.ASSET),
            ("1500", "Dealership Real Estate & Equipment", AccountType.ASSET),
            
            # LIABILITIES (2000s)
            ("2010", "Accounts Payable (Trade Vendors)", AccountType.LIABILITY),
            ("2020", "Bank Floorplan Inventory Payables", AccountType.LIABILITY),
            ("2050", "Customer Service Deposits", AccountType.LIABILITY),
            ("2200", "Long-Term Commercial Notes Payable", AccountType.LIABILITY),

            # EQUITY (3000s)
            ("3010", "Contributed Common Capital Stock", AccountType.EQUITY),
            ("3020", "Retained Earnings", AccountType.EQUITY),

            # REVENUE (4000s)
            ("4010", "New Vehicle Sales Revenue", AccountType.REVENUE),
            ("4020", "Used Vehicle Sales Revenue", AccountType.REVENUE),
            ("4030", "Service Center Labor & Parts Revenue", AccountType.REVENUE),
            ("4040", "F&I (Finance & Insurance) Commission Revenue", AccountType.REVENUE),

            # COST OF GOODS SOLD / EXPENSES (5000s & 6000s)
            ("5010", "COGS - Vehicle Wholesale Cost", AccountType.EXPENSE),
            ("5020", "COGS - Spare Parts & Materials", AccountType.EXPENSE),
            ("6010", "Payroll, Commissions & Benefits", AccountType.EXPENSE),
            ("6020", "Facility Lease & Dealership Utilities", AccountType.EXPENSE),
            ("6030", "Floorplan Credit Interest Expense", AccountType.EXPENSE),
            ("6040", "Sales Promotion & Marketing Expense", AccountType.EXPENSE),
        ]

        created_count = 0
        for code, name, acc_type in default_accounts:
            existing = db.query(Account).filter(Account.code == code).first()
            if not existing:
                db.add(Account(code=code, name=name, account_type=acc_type, balance=0.0))
                created_count += 1

        try:
            db.commit()
            return {"status": "success", "accounts_created": created_count}
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to seed chart of accounts: {e}")
            raise TEAMAIException(f"Database error seeding accounts: {str(e)}")

    # ------------------------------------------------------------------------
    # DOUBLE-ENTRY JOURNAL POSTING
    # ------------------------------------------------------------------------
    @staticmethod
    def post_compound_journal_entry(
        db: Session,
        payload: CompoundJournalEntryInput
    ) -> JournalEntry:
        """
        Posts multi-leg compound journal entries with verified balance equality sum(dr) == sum(cr).
        Updates general ledger balances atomically following normal balance rules.
        """
        entry_number = f"JE-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{int(datetime.now().microsecond/1000)}"

        entry = JournalEntry(
            entry_number=entry_number,
            reference=payload.reference,
            description=payload.description
        )

        try:
            db.add(entry)
            db.flush()  # Generates entry.id

            journal_items: List[JournalItem] = []

            for item in payload.items:
                account = db.query(Account).filter(Account.code == item.account_code).first()
                if not account:
                    raise ValidationException(f"Target account code '{item.account_code}' does not exist.")

                # Apply Normal Balance Delta to ledger account
                FinanceService._apply_normal_balance_delta(account, item.debit, item.credit)

                j_item = JournalItem(
                    entry_id=entry.id,
                    account_id=account.id,
                    debit=item.debit,
                    credit=item.credit
                )
                journal_items.append(j_item)

            db.add_all(journal_items)
            db.commit()
            db.refresh(entry)
            logger.info(f"Successfully posted Journal Entry #{entry_number}")
            return entry

        except Exception as e:
            db.rollback()
            logger.error(f"Failed posting journal entry: {e}")
            if isinstance(e, (TEAMAIException, ValidationException)):
                raise e
            raise TEAMAIException(f"Failed to commit journal entry: {str(e)}")

    # ------------------------------------------------------------------------
    # FINANCIAL STATEMENT GENERATION
    # ------------------------------------------------------------------------
    @staticmethod
    def generate_trial_balance(db: Session) -> TrialBalanceReport:
        """Generates a Trial Balance report verifying total Debits equal total Credits."""
        accounts = db.query(Account).order_by(Account.code.asc()).all()
        
        total_debits = 0.0
        total_credits = 0.0
        schema_list: List[AccountBalanceSchema] = []

        for acc in accounts:
            acc_type_str = str(acc.account_type).upper()
            
            # Extract debit or credit balance representation
            if "ASSET" in acc_type_str or "EXPENSE" in acc_type_str:
                dr = max(0.0, acc.balance)
                cr = abs(min(0.0, acc.balance))
            else:
                cr = max(0.0, acc.balance)
                dr = abs(min(0.0, acc.balance))

            total_debits += dr
            total_credits += cr

            schema_list.append(AccountBalanceSchema(
                code=acc.code,
                name=acc.name,
                account_type=str(acc.account_type),
                debit_balance=round(dr, 2),
                credit_balance=round(cr, 2)
            ))

        total_dr_rounded = round(total_debits, 2)
        total_cr_rounded = round(total_credits, 2)

        return TrialBalanceReport(
            as_of_date=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            total_debits=total_dr_rounded,
            total_credits=total_cr_rounded,
            is_balanced=(total_dr_rounded == total_cr_rounded),
            accounts=schema_list
        )

    @staticmethod
    def generate_income_statement(
        db: Session,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> IncomeStatementReport:
        """Computes Revenue, COGS, Gross Profit, Expenses, and Net Operating Profit (EBIT)."""
        accounts = db.query(Account).all()

        revenue = 0.0
        cogs = 0.0
        opex = 0.0

        for acc in accounts:
            acc_type_str = str(acc.account_type).upper()
            code = acc.code

            if "REVENUE" in acc_type_str or code.startswith("4"):
                revenue += acc.balance
            elif code.startswith("50"):  # Cost of Goods Sold
                cogs += acc.balance
            elif "EXPENSE" in acc_type_str or code.startswith("6"):
                opex += acc.balance

        gross_profit = revenue - cogs
        ebit = gross_profit - opex
        net_margin = (ebit / revenue * 100.0) if revenue > 0 else 0.0

        return IncomeStatementReport(
            period_start=start_date.isoformat() if start_date else "Inception",
            period_end=end_date.isoformat() if end_date else datetime.now(timezone.utc).isoformat(),
            gross_revenue=round(revenue, 2),
            cost_of_goods_sold=round(cogs, 2),
            gross_profit=round(gross_profit, 2),
            operating_expenses=round(opex, 2),
            operating_income_ebit=round(ebit, 2),
            net_profit_margin_pct=round(net_margin, 2)
        )

    @staticmethod
    def generate_balance_sheet(db: Session) -> BalanceSheetReport:
        """
        Generates the Balance Sheet and validates the Fundamental Accounting Equation:
        Assets = Liabilities + Equity
        """
        accounts = db.query(Account).all()

        curr_assets = 0.0
        non_curr_assets = 0.0
        curr_liabilities = 0.0
        long_term_liabilities = 0.0
        equity = 0.0

        for acc in accounts:
            code = acc.code
            acc_type_str = str(acc.account_type).upper()

            if "ASSET" in acc_type_str or code.startswith("1"):
                if code in ["1500"]:  # Real estate / PP&E
                    non_curr_assets += acc.balance
                else:
                    curr_assets += acc.balance
            elif "LIABILITY" in acc_type_str or code.startswith("2"):
                if code in ["2200"]:  # Long-term notes
                    long_term_liabilities += acc.balance
                else:
                    curr_liabilities += acc.balance
            elif "EQUITY" in acc_type_str or code.startswith("3"):
                equity += acc.balance

        total_assets = curr_assets + non_curr_assets
        total_liabilities = curr_liabilities + long_term_liabilities
        total_liab_equity = total_liabilities + equity

        is_balanced = abs(round(total_assets, 2) - round(total_liab_equity, 2)) < 0.01

        return BalanceSheetReport(
            as_of_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            total_current_assets=round(curr_assets, 2),
            total_non_current_assets=round(non_curr_assets, 2),
            total_assets=round(total_assets, 2),
            total_current_liabilities=round(curr_liabilities, 2),
            total_long_term_liabilities=round(long_term_liabilities, 2),
            total_liabilities=round(total_liabilities, 2),
            total_equity=round(equity, 2),
            total_liabilities_and_equity=round(total_liab_equity, 2),
            is_equation_valid=is_balanced
        )

    # ------------------------------------------------------------------------
    # QUANTITATIVE FINANCE & RATIO ANALYTICS
    # ------------------------------------------------------------------------
    @staticmethod
    def calculate_financial_ratios(db: Session) -> FinancialRatiosReport:
        """
        Calculates key liquidity, solvency, efficiency ratios, and Altman Z-Score:
        Altman Z-Score (Private Service Firm Variant):
        Z = 0.717(X1) + 0.847(X2) + 3.107(X3) + 0.420(X4) + 0.998(X5)
        """
        income_stmt = FinanceService.generate_income_statement(db)
        bal_sheet = FinanceService.generate_balance_sheet(db)

        cash_and_ar = 0.0
        for acc_code in ["1010", "1300"]:
            acc = db.query(Account).filter(Account.code == acc_code).first()
            if acc:
                cash_and_ar += acc.balance

        # Ratios Math
        curr_liab = max(bal_sheet.total_current_liabilities, 1.0)
        tot_liab = max(bal_sheet.total_liabilities, 1.0)
        tot_assets = max(bal_sheet.total_assets, 1.0)
        tot_equity = max(bal_sheet.total_equity, 1.0)

        current_ratio = bal_sheet.total_current_assets / curr_liab
        quick_ratio = cash_and_ar / curr_liab
        debt_to_equity = tot_liab / tot_equity
        roa = (income_stmt.operating_income_ebit / tot_assets) * 100.0
        roe = (income_stmt.operating_income_ebit / tot_equity) * 100.0
        asset_turnover = income_stmt.gross_revenue / tot_assets

        # Altman Z-Score Variables
        working_capital = bal_sheet.total_current_assets - bal_sheet.total_current_liabilities
        x1 = working_capital / tot_assets
        x2 = (bal_sheet.total_equity * 0.5) / tot_assets  # Estimate Retained Earnings portion
        x3 = income_stmt.operating_income_ebit / tot_assets
        x4 = tot_equity / tot_liab
        x5 = income_stmt.gross_revenue / tot_assets

        z_score = 0.717 * x1 + 0.847 * x2 + 3.107 * x3 + 0.420 * x4 + 0.998 * x5

        if z_score > 2.9:
            status_str = "SAFE_ZONE (Low Insolvency Risk)"
        elif z_score >= 1.23:
            status_str = "GREY_ZONE (Moderate Solvency Risk)"
        else:
            status_str = "DISTRESS_ZONE (High Bankruptcy Risk)"

        return FinancialRatiosReport(
            current_ratio=round(current_ratio, 2),
            quick_ratio=round(quick_ratio, 2),
            debt_to_equity=round(debt_to_equity, 2),
            return_on_assets_roa=round(roa, 2),
            return_on_equity_roe=round(roe, 2),
            asset_turnover=round(asset_turnover, 2),
            altman_z_score=round(z_score, 2),
            solvency_status=status_str
        )

    @staticmethod
    def calculate_capital_budgeting(
        initial_investment: float,
        cash_flows: List[float],
        discount_rate: float = 0.10
    ) -> CapitalBudgetingReport:
        """
        Computes Net Present Value (NPV), Internal Rate of Return (IRR) via Newton-Raphson,
        Profitability Index (PI), and Payback Period for Dealership Capital Investments.
        """
        if initial_investment <= 0:
            raise ValidationException("Initial investment must be greater than zero.")

        # 1. Net Present Value (NPV)
        npv = -initial_investment
        present_values = []
        for t, cf in enumerate(cash_flows, start=1):
            pv = cf / ((1.0 + discount_rate) ** t)
            present_values.append(pv)
            npv += pv

        # 2. Profitability Index (PI)
        total_pv = sum(present_values)
        pi = total_pv / initial_investment

        # 3. Payback Period
        cumulative = 0.0
        payback_years = float(len(cash_flows))
        for t, cf in enumerate(cash_flows, start=1):
            cumulative += cf
            if cumulative >= initial_investment:
                prev_cum = cumulative - cf
                fraction = (initial_investment - prev_cum) / cf
                payback_years = (t - 1) + fraction
                break

        # 4. Internal Rate of Return (IRR) via Newton-Raphson Numerical Method
        irr_estimate = FinanceService._solve_irr(initial_investment, cash_flows)

        # Recommendation Logic
        if npv > 0 and (irr_estimate is None or irr_estimate > (discount_rate * 100)):
            rec = "ACCEPT_PROJECT (Positive NPV and strong Return on Invested Capital)"
        elif npv == 0:
            rec = "NEUTRAL (Project meets exact hurdle rate)"
        else:
            rec = "REJECT_PROJECT (Negative NPV - Value destruction likely)"

        return CapitalBudgetingReport(
            initial_investment=round(initial_investment, 2),
            discount_rate_pct=round(discount_rate * 100, 2),
            net_present_value_npv=round(npv, 2),
            internal_rate_of_return_irr_pct=round(irr_estimate, 2) if irr_estimate else None,
            profitability_index=round(pi, 2),
            payback_period_years=round(payback_years, 2),
            investment_recommendation=rec
        )

    @staticmethod
    def _solve_irr(initial_inv: float, cash_flows: List[float], max_iter: int = 100) -> Optional[float]:
        """Solves for IRR where sum(CF_t / (1+r)^t) - C0 = 0 using Newton-Raphson iterations."""
        rate = 0.10  # Initial guess 10%
        for _ in range(max_iter):
            # Evaluate f(rate) and f'(rate)
            f_val = -initial_inv
            f_prime = 0.0

            for t, cf in enumerate(cash_flows, start=1):
                f_val += cf / ((1.0 + rate) ** t)
                f_prime -= (t * cf) / ((1.0 + rate) ** (t + 1))

            if abs(f_prime) < 1e-12:
                break

            new_rate = rate - (f_val / f_prime)
            if abs(new_rate - rate) < 1e-6:
                return new_rate * 100.0  # Return percentage
            rate = new_rate

        return round(rate * 100.0, 2) if -0.99 < rate < 5.0 else None

    # ------------------------------------------------------------------------
    # TRANSACTION CSV IMPORT & ANOMALY DETECTION PIPELINE
    # ------------------------------------------------------------------------
    @staticmethod
    def import_transactions_csv(db: Session, file_bytes: bytes) -> Dict[str, Any]:
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
            logger.error(f"Transaction CSV Ingestion Error: {e}")
            raise TEAMAIException(f"Transaction CSV Error: {str(e)}")
