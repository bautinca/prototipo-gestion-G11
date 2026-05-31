from decimal import Decimal, ROUND_HALF_UP

EPSILON = Decimal('0.01')


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
