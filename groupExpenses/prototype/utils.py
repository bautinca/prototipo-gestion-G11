from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime


EPSILON = Decimal('0.01')


def calculate_debts(group):
    members = group.members
    if not members:
        return [], {}

    # Inicializar joined_dates si no existen
    if not group.member_joined_dates:
        group.member_joined_dates = {m: group.created.isoformat() for m in members}
        group.save()

    n = len(members)
    # Matriz de deudas: debts_matrix[debtor][creditor] = amount que debtor debe a creditor
    debts_matrix = {m: {om: Decimal('0') for om in members if om != m} for m in members}

    for expense in group.expense_set.all():
        if expense.transaction_type == 'expense':
            expense_date = expense.created
            # Contar miembros que habían joined antes del gasto
            num_members_at_time = sum(1 for m in members if datetime.fromisoformat(group.member_joined_dates.get(m, '2000-01-01T00:00:00+00:00')) <= expense_date)
            if num_members_at_time > 0:
                amount_per_member = (expense.amount / num_members_at_time).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                for member in members:
                    joined_str = group.member_joined_dates.get(member, '2000-01-01T00:00:00+00:00')
                    joined = datetime.fromisoformat(joined_str)
                    if joined <= expense_date and member != expense.paid_by:
                        debts_matrix[member][expense.paid_by] += amount_per_member
        elif expense.transaction_type == 'settlement':
            # Settlement: paid_by pagó amount a paid_to, reduce deuda de paid_by a paid_to
            debts_matrix[expense.paid_by][expense.paid_to] -= expense.amount

    # Calcular deudas netas
    debts = []
    for debtor in members:
        for creditor in members:
            if debtor != creditor:
                net = debts_matrix[debtor][creditor] - debts_matrix[creditor][debtor]
                if net > EPSILON:
                    debts.append({'from': debtor, 'to': creditor, 'amount': net.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)})

    # Calcular balances
    paid = {m: Decimal('0') for m in members}
    share = {m: Decimal('0') for m in members}
    for expense in group.expense_set.all():
        if expense.transaction_type == 'expense':
            paid[expense.paid_by] += expense.amount
            expense_date = expense.created
            num_members_at_time = sum(1 for m in members if datetime.fromisoformat(group.member_joined_dates.get(m, '2000-01-01T00:00:00+00:00')) <= expense_date)
            if num_members_at_time > 0:
                amount_per_member = (expense.amount / num_members_at_time).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                for m in members:
                    joined_str = group.member_joined_dates.get(m, '2000-01-01T00:00:00+00:00')
                    joined = datetime.fromisoformat(joined_str)
                    if joined <= expense_date:
                        share[m] += amount_per_member
        elif expense.transaction_type == 'settlement':
            paid[expense.paid_by] += expense.amount
            paid[expense.paid_to] -= expense.amount

    balances = {m: paid[m] - share[m] for m in members}

    return debts, balances
