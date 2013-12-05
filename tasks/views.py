from django.http import HttpResponseRedirect, Http404
from django.core.urlresolvers import reverse
from django.shortcuts import render, get_object_or_404
from tasks.models import TaskList, Task, User
from tasks.forms import TaskForm, ListForm, UserForm, ShareForm
from tasks.forms import SHARE_READ, SHARE_WRITE
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User as AuthUser
from django.contrib.auth import authenticate, login


def user_can_write(user, tasklist):
    if tasklist in user.owned.all():
        return True
    elif tasklist in user.shared.all():
        return True
    elif tasklist in user.readonly.all():
        return False
    else:
        raise Http404


def register(request):
    p_err = False
    u_err = False
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            confirm = form.cleaned_data['confirm']
            p_err = password != confirm
            if not p_err:
                try:
                    AuthUser.objects.create_user(username,
                                                 email,
                                                 password)
                    authuser = authenticate(username=username,
                                            password=password)
                    user = User(authuser=authuser)
                    user.save()
                    login(request, authuser)
                    return HttpResponseRedirect(reverse('tasks:index'))
                except:
                    u_err = True
    else:
        form = UserForm()
    context = {'logged_in': request.user and request.user.is_authenticated(),
               'form': form, 'perr': p_err, 'uerr': u_err}
    return render(request, 'tasks/register.html', context)


@login_required
def index(request):
    user = request.user.user
    context = {'logged_in': request.user and request.user.is_authenticated(),
               'owned': user.owned.all().order_by('title'),
               'shared': user.shared.all().order_by('title'),
               'readonly': user.readonly.all().order_by('title')}
    return render(request, 'tasks/index.html', context)


@login_required
def details(request, list_id):
    tasklist = get_object_or_404(TaskList, pk=list_id)
    can_edit = user_can_write(request.user.user, tasklist)
    tasks_list = tasklist.task_set.all().order_by('due_date')
    context = {'logged_in': request.user and request.user.is_authenticated(),
               'can_edit': can_edit,
               'tasklist': tasklist,
               'tasks_list': tasks_list,
               'list_id': list_id}
    return render(request, 'tasks/details.html', context)


@login_required
def add_list(request):
    if request.method == 'POST':
        form = ListForm(request.POST)
        if form.is_valid():
            title = form.cleaned_data['title']
            description = form.cleaned_data['description']
            category = form.cleaned_data['category']
            readonly = form.cleaned_data['readonly']
            tasklist = TaskList(title=title,
                                description=description,
                                category=category,
                                readonly_can_check=readonly)
            tasklist.save()
            user = request.user.user
            user.owned.add(tasklist)
            return HttpResponseRedirect(reverse('tasks:index'))
    else:
        form = ListForm()
    context = {'logged_in': request.user and request.user.is_authenticated(),
               'new': True,
               'form': form}
    return render(request, 'tasks/list.html', context)


@login_required
def edit_list(request, list_id):
    tasklist = get_object_or_404(TaskList, pk=list_id)
    if not user_can_write(request.user.user, tasklist):
        return HttpResponseRedirect(reverse('tasks:details',
                                    kwargs={'list_id': list_id}))
    if request.method == 'POST':
        form = ListForm(request.POST)
        if form.is_valid():
            tasklist.title = form.cleaned_data['title']
            tasklist.description = form.cleaned_data['description']
            tasklist.category = form.cleaned_data['category']
            tasklist.readonly_can_check = form.cleaned_data['readonly']
            tasklist.save()
            return HttpResponseRedirect(reverse('tasks:details',
                                        kwargs={'list_id': tasklist.id}))
    else:
        form = ListForm(initial={'title': tasklist.title,
                                 'description': tasklist.description,
                                 'category': tasklist.category,
                                 'readonly': tasklist.readonly_can_check})
    context = {'logged_in': request.user and request.user.is_authenticated(),
               'new': False,
               'form': form}
    return render(request, 'tasks/list.html', context)


@login_required
def share_list(request, list_id):
    tasklist = get_object_or_404(TaskList, pk=list_id)
    if tasklist not in request.user.user.owned.all():
        return HttpResponseRedirect(reverse('tasks:details',
                                            kwargs={'list_id': list_id}))
    if request.method == 'POST':
        form = ShareForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            authuser = AuthUser.objects.get(username__iexact=username)
            if authuser and authuser is not request.user:
                share_mode = form.cleaned_data['share_mode']
                if share_mode == SHARE_WRITE:
                    authuser.user.shared.add(tasklist)
                elif share_mode == SHARE_READ:
                    authuser.user.readonly.add(tasklist)
            return HttpResponseRedirect(reverse('tasks:details',
                                                kwargs={'list_id': list_id}))
    else:
        form = ShareForm()
    context = {'logged_in': request.user and request.user.is_authenticated(),
               'tasklist': tasklist,
               'form': form}
    return render(request, 'tasks/share.html', context)


@login_required
def add_task(request, list_id):
    tasklist = get_object_or_404(TaskList, pk=list_id)
    if not user_can_write(request.user.user, tasklist):
        return HttpResponseRedirect(reverse('tasks:details',
                                    kwargs={'list_id': list_id}))
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = Task(tasklist=tasklist,
                        title=form.cleaned_data['title'],
                        description=form.cleaned_data['description'],
                        category=form.cleaned_data['category'],
                        due_date=form.cleaned_data['due_date'])
            task.save()
            return HttpResponseRedirect(reverse('tasks:details',
                                        kwargs={'list_id': list_id}))
    else:
        form = TaskForm()
    context = {'logged_in': request.user and request.user.is_authenticated(),
               'tasklist': tasklist,
               'new': True,
               'form': form}
    return render(request, 'tasks/task.html', context)


@login_required
def edit_task(request, task_id):
    task = get_object_or_404(Task, pk=task_id)
    list_id = task.tasklist.id
    if not user_can_write(request.user.user, task.tasklist):
        return HttpResponseRedirect(reverse('tasks:details',
                                    kwargs={'list_id': list_id}))
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task.title = form.cleaned_data['title']
            task.description = form.cleaned_data['description']
            task.category = form.cleaned_data['category']
            task.due_date = form.cleaned_data['due_date']
            task.save()
            return HttpResponseRedirect(reverse('tasks:details',
                                        kwargs={'list_id': list_id}))
    else:
        form = TaskForm(initial={'title': task.title,
                                 'description': task.description,
                                 'category': task.category,
                                 'due_date': task.due_date})
    context = {'logged_in': request.user and request.user.is_authenticated(),
               'tasklist': task.tasklist,
               'new': False,
               'form': form}
    return render(request, 'tasks/task.html', context)


@login_required
def check_task(request, task_id):
    task = get_object_or_404(Task, pk=task_id)
    id = task.tasklist.id
    if not user_can_write(request.user.user, task.tasklist):
        if not task.tasklist.readonly_can_check:
            return HttpResponseRedirect(reverse('tasks:details',
                                        kwargs={'list_id': id}))
    task.is_completed = not task.is_completed
    task.save()
    return HttpResponseRedirect(reverse('tasks:details',
                                kwargs={'list_id': id}))


@login_required
def delete_list(request, list_id):
    tasklist = get_object_or_404(TaskList, pk=list_id)
    user = request.user.user
    if not user_can_write(user, tasklist):
        return HttpResponseRedirect(reverse('tasks:index'))
    if tasklist in user.owned.all():
        tasklist.delete()
    elif tasklist in user.shared.all():
        user.shared.remove(tasklist)
    elif tasklist in user.readonly.all():
        user.readonly.remove(tasklist)
    return HttpResponseRedirect(reverse('tasks:index'))


@login_required
def delete_task(request, task_id):
    task = get_object_or_404(Task, pk=task_id)
    id = task.tasklist.id
    if not user_can_write(request.user.user, task.tasklist):
        return HttpResponseRedirect(reverse('tasks:details',
                                    kwargs={'list_id': id}))
    task.delete()
    return HttpResponseRedirect(reverse('tasks:details',
                                kwargs={'list_id': id}))