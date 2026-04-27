from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
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
                group.save()
            return redirect('group', pk=pk)

        elif 'expense' in request.POST:
            paid_by = request.POST.get('paid_by', '').strip()
            amount_str = request.POST.get('expense', '').strip()
            expense_currency = request.POST.get('expense_currency', group.currency)
            exchange_rate_str = request.POST.get('exchange_rate', '').strip()

            if paid_by and amount_str and group.members:
                try:
                    original_amount = Decimal(amount_str)
                except InvalidOperation:
                    return redirect('group', pk=pk)

                if original_amount <= 0:
                    messages.error(request, 'El monto debe ser mayor a 0.')
                    return redirect('group', pk=pk)

                if expense_currency != group.currency:
                    if not exchange_rate_str:
                        messages.error(request, 'Ingresá el tipo de cambio para convertir la moneda.')
                        return redirect('group', pk=pk)
                    try:
                        exchange_rate = Decimal(exchange_rate_str)
                    except InvalidOperation:
                        return redirect('group', pk=pk)
                    if exchange_rate <= 0:
                        messages.error(request, 'El tipo de cambio debe ser mayor a 0.')
                        return redirect('group', pk=pk)
                    direction = request.POST.get('exchange_direction', 'multiply')
                    if direction == 'divide':
                        amount = original_amount / exchange_rate
                    else:
                        amount = original_amount * exchange_rate
                else:
                    amount = original_amount
                Expense.objects.create(
                    group=group,
                    paid_by=paid_by,
                    amount=amount,
                    original_amount=original_amount,
                    original_currency=expense_currency,
                )
            return redirect('group', pk=pk)

        elif 'delete_group' in request.POST:
            group.delete()
            return redirect('home')

        return redirect('group', pk=pk)

    debts, balances = calculate_debts(group)

    members_data = []
    for member in group.members:
        balance = balances.get(member, Decimal('0'))
        if balance > Decimal('0.01'):
            status = {'type': 'cobrar', 'amount': balance}
        elif balance < Decimal('-0.01'):
            member_debts = [d for d in debts if d['from'] == member]
            status = {'type': 'debe', 'debts': member_debts}
        else:
            status = {'type': 'al_dia'}
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
