from decimal import Decimal, ROUND_HALF_UP

EPSILON = Decimal('0.01')


def calculate_debts(group):
    members = group.members
    if not members:
        return [], {}

    n = len(members)
    # Matriz de deudas: debts_matrix[debtor][creditor] = amount que debtor debe a creditor
    debts_matrix = {m: {om: Decimal('0') for om in members if om != m} for m in members}

    for expense in group.expense_set.all():
        if expense.transaction_type == 'expense':
            amount_per_member = (expense.amount / Decimal(n)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            for member in members:
                if member != expense.paid_by:
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

    # Calcular balances para la vista (mantener igual para compatibilidad)
    total = group.total
    share = (total / Decimal(n)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    paid = {m: Decimal('0') for m in members}
    for expense in group.expense_set.all():
        if expense.transaction_type == 'expense':
            paid[expense.paid_by] += expense.amount
        elif expense.transaction_type == 'settlement':
            paid[expense.paid_by] += expense.amount
            paid[expense.paid_to] -= expense.amount

    balances = {m: paid[m] - share for m in members}

    return debts, balances
