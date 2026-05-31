import csv
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

EPSILON = Decimal('0.01')
CONVERSION_RATES_CSV = Path(__file__).resolve().parent / 'conversion_rates.csv'


def load_conversion_rates():
    rates = {}
    if not CONVERSION_RATES_CSV.exists():
        return rates

    with CONVERSION_RATES_CSV.open(newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            from_currency = row.get('from')
            to_currency = row.get('to')
            rate = row.get('rate')
            if from_currency and to_currency and rate:
                try:
                    rates.setdefault(from_currency, {})[to_currency] = Decimal(rate)
                except Exception:
                    continue
    return rates


def get_conversion_rate(from_currency, to_currency):
    if from_currency == to_currency:
        return Decimal('1')
    rates = load_conversion_rates()
    return rates.get(from_currency, {}).get(to_currency)


def calculate_debts(group):
    members = [member.username for member in group.members.all()]
    if not members:
        return [], {}

    n = len(members)
    # Matriz de deudas: debts_matrix[debtor][creditor] = amount que debtor debe a creditor
    debts_matrix = {m: {om: Decimal('0') for om in members if om != m} for m in members}

    for expense in group.expense_set.all():
        if expense.transaction_type == 'expense':
            expense_members = [m for m in expense.participants if m in members] if expense.participants else members
            if not expense_members:
                expense_members = members
            amount_per_member = (expense.amount / Decimal(len(expense_members))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            for member in expense_members:
                if member != expense.paid_by:
                    debts_matrix[member][expense.paid_by] += amount_per_member
        elif expense.transaction_type == 'settlement' and expense.paid_to:
            # Settlement: paid_by pagó amount a paid_to, reduce deuda de paid_by a paid_to
            if expense.paid_by in debts_matrix and expense.paid_to in debts_matrix[expense.paid_by]:
                debts_matrix[expense.paid_by][expense.paid_to] -= expense.amount

    # Calcular deudas netas
    debts = []
    for debtor in members:
        for creditor in members:
            if debtor != creditor:
                net = debts_matrix[debtor][creditor] - debts_matrix[creditor][debtor]
                if net > EPSILON:
                    debts.append({'from': debtor, 'to': creditor, 'amount': net.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)})

    # Calcular balances correctamente usando los participantes de cada gasto
    paid = {m: Decimal('0') for m in members}
    for expense in group.expense_set.all():
        if expense.transaction_type == 'expense':
            expense_members = [m for m in expense.participants if m in members] if getattr(expense, 'participants', None) else members
            if not expense_members:
                expense_members = members
            share = (expense.amount / Decimal(len(expense_members))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            paid[expense.paid_by] += expense.amount
            for member in expense_members:
                paid[member] -= share
        elif expense.transaction_type == 'settlement':
            paid[expense.paid_by] += expense.amount
            paid[expense.paid_to] -= expense.amount

    balances = paid

    return debts, balances
