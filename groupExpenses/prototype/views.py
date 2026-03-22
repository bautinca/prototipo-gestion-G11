from django.shortcuts import render, redirect
from django.http import HttpResponse # Respuestas HTTP simples
from .models import Group # Importamos tabla grupos
from .forms import GroupForm # Importamos formulario creacion grupo

# Logica home page
def home(request):
  groups = Group.objects.all()
  context = {'groups': groups}
  return render(request=request, template_name='./prototype/home.html', context=context)

# Logica pagina grupo
def group(request, pk):
  group = Group.objects.get(id=pk)

  if request.method == "POST":
    # Logica agregado miembro
    if 'new_member' in request.POST:
      new_member = request.POST.get('new_member')
      if new_member:
        members = group.members
        members.append(new_member)
        group.members = members
        group.save()
      return redirect('group', pk=pk)
    
    # Logica agregado gasto miembro
    elif 'expense' in request.POST:
      expense = request.POST.get('expense')
      if expense:
        expense_float = float(expense)
        group.total += expense_float
        group.save()
      return redirect('group', pk=pk)
    
    # Logica eliminado grupo
    else:
      group.delete()
      return redirect('home')
    
  cost_per_member = group.total / len(group.members)

  context = {'group': group, 'cost_per_member': cost_per_member}
  return render(request=request, template_name='./prototype/group.html', context=context)

# Logica crear grupo
def createGroup(request):
  form = GroupForm()

  if request.method == "POST":
    form = GroupForm(request.POST)
    if form.is_valid():
      form.save()
      return redirect('home')

  context = {'form': form}
  return render(request=request, template_name='./prototype/group_form.html', context=context)

# Logica editar grupo
def updateGroup(request, pk):
  group = Group.objects.get(id=pk)
  form = GroupForm(instance=group)

  if request.method == "POST":
    form = GroupForm(request.POST, instance=group)
    if form.is_valid():
      form.save()
      return redirect('group', pk=pk)

  context = {"form": form}
  return render(request=request, template_name='./prototype/group_form.html', context=context)