from django.test import TestCase, Client
from decimal import Decimal
from .models import Group, Expense
from .utils import calculate_debts


class GroupModelTests(TestCase):
    def setUp(self):
        self.group = Group.objects.create(name='Test', currency='ARS')
        self.group.members = ['A', 'B']
        self.group.save()

    def test_total_is_zero_with_no_expenses(self):
        self.assertEqual(self.group.total, Decimal('0'))

    def test_total_sums_expenses(self):
        Expense.objects.create(
            group=self.group, paid_by='A',
            amount=Decimal('1000'), original_amount=Decimal('1000'),
            original_currency='ARS'
        )
        Expense.objects.create(
            group=self.group, paid_by='B',
            amount=Decimal('500'), original_amount=Decimal('500'),
            original_currency='ARS'
        )
        self.assertEqual(self.group.total, Decimal('1500'))

    def test_expense_str(self):
        e = Expense.objects.create(
            group=self.group, paid_by='A',
            amount=Decimal('100'), original_amount=Decimal('100'),
            original_currency='ARS'
        )
        self.assertIn('A', str(e))
        self.assertIn('100', str(e))

    def test_group_str(self):
        self.assertEqual(str(self.group), 'Test')

    def test_expenses_deleted_with_group(self):
        Expense.objects.create(
            group=self.group, paid_by='A',
            amount=Decimal('100'), original_amount=Decimal('100'),
            original_currency='ARS'
        )
        group_id = self.group.id
        self.group.delete()
        self.assertEqual(Expense.objects.filter(group_id=group_id).count(), 0)


class DebtCalculationTests(TestCase):
    def setUp(self):
        self.group = Group.objects.create(name='Deudas', currency='ARS')
        self.group.members = ['A', 'B', 'C']
        self.group.save()

    def test_no_expenses_returns_empty(self):
        debts, balances = calculate_debts(self.group)
        self.assertEqual(debts, [])
        self.assertEqual(balances, {'A': Decimal('0'), 'B': Decimal('0'), 'C': Decimal('0')})

    def test_single_payer_owes_rest(self):
        Expense.objects.create(
            group=self.group, paid_by='A',
            amount=Decimal('3000'), original_amount=Decimal('3000'),
            original_currency='ARS'
        )
        debts, balances = calculate_debts(self.group)
        self.assertEqual(balances['A'], Decimal('2000'))
        self.assertEqual(balances['B'], Decimal('-1000'))
        self.assertEqual(balances['C'], Decimal('-1000'))
        self.assertIn({'from': 'B', 'to': 'A', 'amount': Decimal('1000.00')}, debts)
        self.assertIn({'from': 'C', 'to': 'A', 'amount': Decimal('1000.00')}, debts)

    def test_everyone_paid_equally_no_debts(self):
        for member in ['A', 'B', 'C']:
            Expense.objects.create(
                group=self.group, paid_by=member,
                amount=Decimal('1000'), original_amount=Decimal('1000'),
                original_currency='ARS'
            )
        debts, balances = calculate_debts(self.group)
        self.assertEqual(debts, [])
        for m in ['A', 'B', 'C']:
            self.assertAlmostEqual(float(balances[m]), 0, places=1)

    def test_no_members_returns_empty(self):
        self.group.members = []
        self.group.save()
        debts, balances = calculate_debts(self.group)
        self.assertEqual(debts, [])
        self.assertEqual(balances, {})


class GroupViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.group = Group.objects.create(name='Viaje', currency='ARS')
        self.group.members = ['A', 'B']
        self.group.save()

    def test_add_expense_creates_expense_object(self):
        self.client.post(f'/group/{self.group.id}/', {
            'expense': '500',
            'paid_by': 'A',
            'expense_currency': 'ARS',
        })
        self.assertEqual(self.group.expense_set.count(), 1)
        expense = self.group.expense_set.first()
        self.assertEqual(expense.paid_by, 'A')
        self.assertEqual(expense.amount, Decimal('500'))

    def test_expense_currency_conversion(self):
        self.client.post(f'/group/{self.group.id}/', {
            'expense': '10',
            'paid_by': 'A',
            'expense_currency': 'USD',
            'exchange_rate': '1000',
        })
        expense = self.group.expense_set.first()
        self.assertEqual(expense.original_amount, Decimal('10'))
        self.assertEqual(expense.original_currency, 'USD')
        self.assertEqual(expense.amount, Decimal('10000'))

    def test_expense_same_currency_no_conversion(self):
        self.client.post(f'/group/{self.group.id}/', {
            'expense': '200',
            'paid_by': 'B',
            'expense_currency': 'ARS',
        })
        expense = self.group.expense_set.first()
        self.assertEqual(expense.amount, Decimal('200'))
        self.assertEqual(expense.original_currency, 'ARS')

    def test_add_expense_without_members_blocked(self):
        empty_group = Group.objects.create(name='Vacío', currency='ARS')
        self.client.post(f'/group/{empty_group.id}/', {
            'expense': '100',
            'paid_by': '',
            'expense_currency': 'ARS',
        })
        self.assertEqual(empty_group.expense_set.count(), 0)

    def test_delete_member_without_expenses(self):
        self.client.post(f'/group/{self.group.id}/delete-member/', {
            'member_name': 'B'
        })
        self.group.refresh_from_db()
        self.assertNotIn('B', self.group.members)

    def test_delete_member_with_expenses_blocked(self):
        Expense.objects.create(
            group=self.group, paid_by='B',
            amount=Decimal('100'), original_amount=Decimal('100'),
            original_currency='ARS'
        )
        self.client.post(f'/group/{self.group.id}/delete-member/', {
            'member_name': 'B'
        })
        self.group.refresh_from_db()
        self.assertIn('B', self.group.members)

    def test_update_name(self):
        self.client.post(f'/group/{self.group.id}/update-name/', {
            'name': 'Asado'
        })
        self.group.refresh_from_db()
        self.assertEqual(self.group.name, 'Asado')

    def test_update_name_empty_ignored(self):
        self.client.post(f'/group/{self.group.id}/update-name/', {
            'name': ''
        })
        self.group.refresh_from_db()
        self.assertEqual(self.group.name, 'Viaje')

    def test_delete_group(self):
        group_id = self.group.id
        self.client.post(f'/group/{group_id}/', {'delete_group': '1'})
        self.assertEqual(Group.objects.filter(id=group_id).count(), 0)

    def test_group_currency_change_reconverts_expenses(self):
        group_usd = Group.objects.create(name='USD Group', currency='USD')
        group_usd.members = ['A']
        group_usd.save()
        Expense.objects.create(
            group=group_usd, paid_by='A',
            amount=Decimal('100'), original_amount=Decimal('100'),
            original_currency='USD'
        )
        self.client.post(f'/update-group/{group_usd.id}/', {
            'name': 'USD Group',
            'currency': 'ARS',
            'exchange_rate': '1000',
        })
        expense = group_usd.expense_set.first()
        self.assertEqual(expense.amount, Decimal('100000'))

    def test_create_group_empty_name_fails(self):
        response = self.client.post('/create-group/', {
            'name': '',
            'currency': 'ARS',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ingresá un nombre')
