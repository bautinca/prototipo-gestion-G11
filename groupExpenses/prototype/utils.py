from decimal import Decimal, ROUND_HALF_UP

EPSILON = Decimal('0.01')


def calculate_debts(group):
    members = group.members
    if not members:
        return [], {}

    total = group.total
    n = Decimal(len(members))
    share = (total / n).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    paid = {m: Decimal('0') for m in members}
    for expense in group.expense_set.all():
        if expense.paid_by in paid:
            paid[expense.paid_by] += expense.amount

    balances = {m: paid[m] - share for m in members}

    creditors = [[m, b] for m, b in balances.items() if b > EPSILON]
    debtors = [[m, -b] for m, b in balances.items() if b < -EPSILON]
    creditors.sort(key=lambda x: -x[1])
    debtors.sort(key=lambda x: -x[1])

    debts = []
    i, j = 0, 0
    while i < len(creditors) and j < len(debtors):
        creditor, credit = creditors[i]
        debtor, debt = debtors[j]
        amount = min(credit, debt).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        debts.append({'from': debtor, 'to': creditor, 'amount': amount})
        creditors[i][1] = credit - amount
        debtors[j][1] = debt - amount
        if creditors[i][1] < EPSILON:
            i += 1
        if debtors[j][1] < EPSILON:
            j += 1

    return debts, balances
