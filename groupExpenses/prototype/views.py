from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from decimal import Decimal, InvalidOperation
from .models import Group, Expense, CURRENCY_CHOICES
from .forms import GroupForm
from .utils import calculate_debts


def home(request):
    groups = Group.objects.all()
    return render(request, './prototype/home.html', {'groups': groups})


def group(request, pk):
    group = get_object_or_404(Group, id=pk)

    if request.method == 'POST':
        if 'new_member' in request.POST:
            new_member = request.POST.get('new_member', '').strip()
            if new_member:
                members = group.members
                members.append(new_member)
                group.members = members
                group.member_joined_dates[new_member] = timezone.now().isoformat()
                group.save()
            return redirect('group', pk=pk)

        elif 'settlement' in request.POST:
            paid_by = request.POST.get('paid_by', '').strip()
            paid_to = request.POST.get('paid_to', '').strip()
            amount_str = request.POST.get('settlement_amount', '').strip()

            if paid_by and paid_to and paid_by != paid_to and amount_str and group.members:
                if paid_by not in group.members or paid_to not in group.members:
                    messages.error(request, 'El miembro pagador y el receptor deben ser parte del grupo.')
                    return redirect('group', pk=pk)
                try:
                    original_amount = Decimal(amount_str)
                except InvalidOperation:
                    return redirect('group', pk=pk)

                if original_amount <= 0:
                    messages.error(request, 'El monto debe ser mayor a 0.')
                    return redirect('group', pk=pk)

                amount = original_amount
                debts_before, _ = calculate_debts(group)
                max_settlement = next((d['amount'] for d in debts_before if d['from'] == paid_by and d['to'] == paid_to), Decimal('0'))
                if max_settlement <= 0:
                    messages.error(request, f'No hay deuda de {paid_by} hacia {paid_to}.')
                    return redirect('group', pk=pk)
                if amount > max_settlement:
                    messages.error(request, f'El monto no puede superar la deuda actual ({max_settlement} {group.currency}).')
                    return redirect('group', pk=pk)

                Expense.objects.create(
                    group=group,
                    paid_by=paid_by,
                    paid_to=paid_to,
                    transaction_type='settlement',
                    amount=amount,
                    original_amount=original_amount,
                    original_currency=group.currency,
                )
            return redirect('group', pk=pk)

        elif 'expense' in request.POST:
            paid_by = request.POST.get('paid_by', '').strip()
            amount_str = request.POST.get('expense', '').strip()

            if paid_by and amount_str and group.members:
                try:
                    original_amount = Decimal(amount_str)
                except InvalidOperation:
                    return redirect('group', pk=pk)

                if original_amount <= 0:
                    messages.error(request, 'El monto debe ser mayor a 0.')
                    return redirect('group', pk=pk)

                Expense.objects.create(
                    group=group,
                    paid_by=paid_by,
                    amount=original_amount,
                    original_amount=original_amount,
                    original_currency=group.currency,
                )
            return redirect('group', pk=pk)

        elif 'delete_group' in request.POST:
            group.delete()
            return redirect('home')

        return redirect('group', pk=pk)

    debts, balances = calculate_debts(group)

    # Calculate debts for each member
    member_debts_owed = {m: [] for m in group.members}  # debts this member owes
    member_debts_owed_to = {m: [] for m in group.members}  # debts owed to this member

    for d in debts:
        member_debts_owed[d['from']].append({'to': d['to'], 'amount': d['amount']})
        member_debts_owed_to[d['to']].append({'from': d['from'], 'amount': d['amount']})

    members_data = []
    for member in group.members:
        status = {
            'debts_owed': member_debts_owed.get(member, []),
            'debts_owed_to': member_debts_owed_to.get(member, [])
        }
        members_data.append({'name': member, 'status': status})

    cost_per_member = (group.total / len(group.members)) if group.members else Decimal('0')
    expenses = group.expense_set.all().order_by('-id')

    context = {
        'group': group,
        'cost_per_member': cost_per_member,
        'members_data': members_data,
        'expenses': expenses,
        'currency_choices': CURRENCY_CHOICES,
    }
    return render(request, './prototype/group.html', context)


def deleteMember(request, pk):
    group = get_object_or_404(Group, id=pk)
    if request.method == 'POST':
        member_name = request.POST.get('member_name', '').strip()
        if member_name and member_name in group.members:
            has_expenses = group.expense_set.filter(paid_by=member_name).exists()
            if not has_expenses:
                members = group.members
                members.remove(member_name)
                group.members = members
                group.save()
            else:
                messages.error(request, f'No se puede eliminar a {member_name} porque tiene gastos registrados.')
    return redirect('group', pk=pk)


def updateName(request, pk):
    group = get_object_or_404(Group, id=pk)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if name:
            group.name = name
            group.save()
    return redirect('group', pk=pk)


def createGroup(request):
    form = GroupForm()
    if request.method == 'POST':
        form = GroupForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('home')
    return render(request, './prototype/group_form.html', {'form': form})


def updateGroup(request, pk):
    group = get_object_or_404(Group, id=pk)
    old_currency = group.currency
    form = GroupForm(request.POST or None, instance=group)

    if request.method == 'POST':
        if form.is_valid():
            new_currency = form.cleaned_data['currency']
            if new_currency != old_currency:
                exchange_rate_str = request.POST.get('exchange_rate', '').strip()
                if exchange_rate_str:
                    rate = Decimal(exchange_rate_str)
                    direction = request.POST.get('exchange_direction', 'multiply')
                    for expense in group.expense_set.all():
                        if direction == 'divide':
                            expense.amount = expense.amount / rate
                        else:
                            expense.amount = expense.amount * rate
                        expense.save()
            form.save()
            return redirect('group', pk=pk)

    return render(request, './prototype/group_form.html', {'form': form, 'group': group})
