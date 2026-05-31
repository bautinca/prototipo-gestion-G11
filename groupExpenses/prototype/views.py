from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from decimal import Decimal, InvalidOperation
from .models import Group, Expense, CURRENCY_CHOICES, GroupInvitation
from .forms import GroupForm
from .utils import calculate_debts, get_conversion_rate

MAX_AMOUNT = Decimal('999999999.99')


@login_required
def home(request):
    groups = Group.objects.filter(Q(owner=request.user) | Q(members=request.user)).distinct()
    pending_invitations = GroupInvitation.objects.filter(invited_user=request.user, status='pending').select_related('group', 'invited_by')
    return render(request, './prototype/home.html', {'groups': groups, 'pending_invitations': pending_invitations})


@login_required
def group(request, pk):
    group = get_object_or_404(Group, id=pk)
    is_admin = request.user == group.owner
    if not (is_admin or group.members.filter(id=request.user.id).exists()):
        return redirect('home')

    if request.method == 'POST':
        if 'new_member' in request.POST:
            if not is_admin:
                messages.error(request, 'Solo el administrador puede agregar miembros al grupo.')
                return redirect('group', pk=pk)
            new_member = request.POST.get('new_member', '').strip()
            if new_member:
                try:
                    member_user = User.objects.get(username__iexact=new_member)
                except User.DoesNotExist:
                    messages.error(request, 'El usuario debe estar registrado para ser agregado al grupo.')
                    return redirect('group', pk=pk)

                if group.members.filter(id=member_user.id).exists():
                    messages.error(request, 'Ese usuario ya es miembro del grupo.')
                    return redirect('group', pk=pk)

                invitation, created = GroupInvitation.objects.get_or_create(
                    group=group,
                    invited_user=member_user,
                    defaults={'invited_by': request.user}
                )
                if not created:
                    if invitation.status == 'pending':
                        messages.info(request, 'Ya existe una invitación pendiente para este usuario.')
                    elif invitation.status == 'accepted':
                        messages.error(request, 'Ese usuario ya aceptó su invitación y es miembro del grupo.')
                    else:
                        invitation.status = 'pending'
                        invitation.invited_by = request.user
                        invitation.responded = None
                        invitation.save()
                        messages.info(request, 'Invitación reenviada al usuario.')
                    return redirect('group', pk=pk)

                messages.info(request, 'Invitación enviada correctamente.')
            return redirect('group', pk=pk)

        elif 'settlement' in request.POST:
            paid_by = request.POST.get('paid_by', '').strip()
            paid_to = request.POST.get('paid_to', '').strip()
            amount_str = request.POST.get('settlement_amount', '').strip()

            if paid_by and paid_to and paid_by != paid_to and amount_str and group.members.exists():
                if not group.members.filter(username__iexact=paid_by).exists() or not group.members.filter(username__iexact=paid_to).exists():
                    messages.error(request, 'El miembro pagador y el receptor deben ser parte del grupo.')
                    return redirect('group', pk=pk)
                if not is_admin and paid_by != request.user.username:
                    messages.error(request, 'Solo el administrador puede registrar un pago en nombre de otro miembro.')
                    return redirect('group', pk=pk)
                try:
                    original_amount = Decimal(amount_str)
                except InvalidOperation:
                    return redirect('group', pk=pk)

                if original_amount <= 0:
                    messages.error(request, 'El monto debe ser mayor a 0.')
                    return redirect('group', pk=pk)

                if original_amount > MAX_AMOUNT:
                    messages.error(request, 'El sistema no admite montos demasiado altos.')
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

            if paid_by and amount_str and group.members.exists():
                if not group.members.filter(username__iexact=paid_by).exists():
                    messages.error(request, 'El miembro pagador debe ser parte del grupo.')
                    return redirect('group', pk=pk)
                if not is_admin and paid_by != request.user.username:
                    messages.error(request, 'Solo el administrador puede registrar gastos en nombre de otro miembro.')
                    return redirect('group', pk=pk)
                try:
                    original_amount = Decimal(amount_str)
                except InvalidOperation:
                    return redirect('group', pk=pk)

                if original_amount <= 0:
                    messages.error(request, 'El monto debe ser mayor a 0.')
                    return redirect('group', pk=pk)

                if original_amount > MAX_AMOUNT:
                    messages.error(request, 'El sistema no admite montos demasiado altos.')
                    return redirect('group', pk=pk)

                Expense.objects.create(
                    group=group,
                    paid_by=paid_by,
                    amount=original_amount,
                    original_amount=original_amount,
                    original_currency=group.currency,
                    participants=[member.username for member in group.members.all()],
                )
            return redirect('group', pk=pk)

        elif 'delete_group' in request.POST:
            if request.user == group.owner:
                group.delete()
                return redirect('home')
            return redirect('group', pk=pk)

        return redirect('group', pk=pk)

    debts, balances = calculate_debts(group)

    members_data = []
    for member in group.members.all():
        member_debts = [d for d in debts if d['from'] == member.username]
        if member_debts:
            status = {'type': 'debe', 'debts': member_debts}
        else:
            status = {'type': 'al_dia'}
        members_data.append({'name': member.username, 'status': status})

    cost_per_member = (group.total / group.members.count()) if group.members.exists() else Decimal('0')
    expenses = group.expense_set.all().order_by('-id')

    debt_amounts = {}
    members_usernames = []
    for member in group.members.all():
        member_username = member.username
        members_usernames.append(member_username)
        debt_total = sum(
            (d['amount'] for d in debts if d['from'] == member_username),
            Decimal('0')
        )
        debt_amounts[member_username] = float(debt_total)

    # Calcular aportes: suma de todos los gastos (transaction_type='expense') pagados por cada miembro
    contribution_amounts = {m: 0.0 for m in members_usernames}
    for exp in group.expense_set.filter(transaction_type='expense'):
        payer = exp.paid_by
        if payer in contribution_amounts:
            # usar exp.amount (ya en la moneda del grupo) como aportación
            try:
                contribution_amounts[payer] += float(exp.amount)
            except Exception:
                # en caso de datos inesperados, saltar
                continue

    # Calcular el pozo acumulado (suma de todos los gastos, no incluye settlements)
    total_pooled = 0.0
    for exp in group.expense_set.filter(transaction_type='expense'):
        try:
            total_pooled += float(exp.amount)
        except Exception:
            continue

    context = {
        'group': group,
        'cost_per_member': cost_per_member,
        'members_data': members_data,
        'expenses': expenses,
        'currency_choices': CURRENCY_CHOICES,
        'debt_amounts': debt_amounts,
        'members_usernames': members_usernames,
        'members_count': group.members.count(),
        'contribution_amounts': contribution_amounts,
        'total_pooled': total_pooled,
        'is_admin': is_admin,
    }
    return render(request, './prototype/group.html', context)


@login_required
def respondInvitation(request, pk):
    invitation = get_object_or_404(GroupInvitation, id=pk, invited_user=request.user)
    if request.method == 'POST':
        response = request.POST.get('response')
        if response == 'accept':
            invitation.status = 'accepted'
            invitation.responded = timezone.now()
            invitation.save()
            if not invitation.group.members.filter(id=request.user.id).exists():
                invitation.group.members.add(request.user)
            messages.success(request, f'Has aceptado la invitación al grupo {invitation.group.name}.')
        elif response == 'decline':
            invitation.status = 'declined'
            invitation.responded = timezone.now()
            invitation.save()
            messages.error(request, f'Has rechazado la invitación al grupo {invitation.group.name}.')
    return redirect('home')


@login_required
def deleteMember(request, pk):
    group = get_object_or_404(Group, id=pk, owner=request.user)
    if request.method == 'POST':
        member_name = request.POST.get('member_name', '').strip()
        if member_name:
            try:
                member_user = User.objects.get(username__iexact=member_name)
            except User.DoesNotExist:
                member_user = None

            if member_user and group.members.filter(id=member_user.id).exists():
                debts, balances = calculate_debts(group)
                has_pending = any(d['from'] == member_user.username or d['to'] == member_user.username for d in debts)
                if has_pending:
                    messages.error(request, f'{member_user.username} tiene deudas pendientes. Debe estar al día antes de ser eliminado.')
                else:
                    group.members.remove(member_user)
    return redirect('group', pk=pk)


@login_required
def updateName(request, pk):
    group = get_object_or_404(Group, id=pk, owner=request.user)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if name:
            group.name = name
            group.save()
    return redirect('group', pk=pk)


@login_required
def createGroup(request):
    form = GroupForm()
    if request.method == 'POST':
        form = GroupForm(request.POST)
        if form.is_valid():
            new_group = form.save(commit=False)
            new_group.owner = request.user
            new_group.save()
            new_group.members.add(request.user)
            return redirect('home')
    return render(request, './prototype/group_form.html', {'form': form})


@login_required
def updateGroup(request, pk):
    group = get_object_or_404(Group, id=pk, owner=request.user)
    old_currency = group.currency
    form = GroupForm(request.POST or None, instance=group)

    if request.method == 'POST':
        if form.is_valid():
            new_currency = form.cleaned_data['currency']
            conversion_message = None
            if new_currency != old_currency:
                rate = get_conversion_rate(old_currency, new_currency)
                if rate is None:
                    messages.error(request, 'No hay una tasa de conversión disponible para estas monedas.')
                    return redirect('update-group', pk=pk)
                for expense in group.expense_set.all():
                    new_amount = (expense.amount * rate).quantize(Decimal('0.01'))
                    if new_amount > MAX_AMOUNT:
                        messages.error(request, 'La conversión de moneda resultaría en montos demasiado altos. Operación cancelada.')
                        return redirect('update-group', pk=pk)
                    expense.amount = new_amount
                    expense.original_amount = new_amount
                    expense.original_currency = new_currency
                    expense.save()
                conversion_message = f'Conversión a {new_currency} aplicada con tasa {rate}.'
            form.save()
            if conversion_message:
                messages.success(request, conversion_message)
            else:
                messages.success(request, 'Grupo actualizado correctamente.')
            return redirect('group', pk=pk)

    return render(request, './prototype/group_form.html', {'form': form, 'group': group})


def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip().lower()
        password = request.POST.get('password', '')
        if not username or not password:
            messages.error(request, 'Completá todos los campos.')
            return render(request, 'prototype/register.html')
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Ese nombre de usuario ya existe.')
            return render(request, 'prototype/register.html')
        User.objects.create_user(username=username, password=password)
        return redirect('login')
    return render(request, 'prototype/register.html')


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip().lower()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
        messages.error(request, 'Usuario o contraseña incorrectos.')
    return render(request, 'prototype/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


def tutorial(request):
    """Renderiza la página de tutorial explicativa (pública)."""
    return render(request, 'prototype/tutorial.html')
