from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.db import models
from .models import Project, Ticket, Sprint
from django.utils import timezone
from .forms import TicketForm, CommentForm, CancelTicketForm
from datetime import date


@login_required
def project_list(request):
    projects = Project.objects.all().order_by('key')
    return render(request, 'projects/project_list.html', {'projects': projects})

@login_required
def project_detail(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    tickets = project.tickets.all()
    
    # Apply search filter if a query was provided
    search_query = request.GET.get('q', '').strip()
    if search_query:
        tickets = tickets.filter(title__icontains=search_query)
    
    tickets = tickets.order_by('-created_at')
    
    return render(request, 'projects/project_detail.html', {
        'project': project,
        'tickets': tickets,
        'search_query': search_query,
    })

@login_required
def ticket_detail(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    comments = ticket.comments.all()
    comment_form = CommentForm()
    # Sprints this ticket could be moved into (not completed ones)
    available_sprints = ticket.project.sprints.exclude(status='completed').order_by('-created_at')
    return render(request, 'projects/ticket_detail.html', {
        'ticket': ticket,
        'comments': comments,
        'comment_form': comment_form,
        'available_sprints': available_sprints,
    })

@login_required
def project_board(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    # Board only shows active workflow statuses, not 'cancelled'
    statuses = [s for s in Ticket.STATUS_CHOICES if s[0] != 'cancelled']
    
    # Find the active sprint for this project
    active_sprint = project.sprints.filter(status='active').first()
    
    # Only show tickets in the active sprint (if one exists)
    if active_sprint:
        all_tickets = active_sprint.tickets.exclude(status='cancelled').annotate(
          comment_count=models.Count('comments')
        ).order_by('-created_at')
    
    # Group tickets by assignee, then by status
    swimlanes_dict = {}
    for ticket in all_tickets:
        assignee_key = ticket.assignee.id if ticket.assignee else 'unassigned'
        assignee_name = ticket.assignee.username if ticket.assignee else 'Unassigned'
        
        if assignee_key not in swimlanes_dict:
            swimlanes_dict[assignee_key] = {
                'assignee_key': assignee_key,
                'assignee_name': assignee_name,
                'columns': {status[0]: [] for status in statuses},
                'total': 0,
            }
        
        swimlanes_dict[assignee_key]['columns'][ticket.status].append(ticket)
        swimlanes_dict[assignee_key]['total'] += 1
    
    swimlanes = sorted(
        swimlanes_dict.values(),
        key=lambda x: (x['assignee_key'] == 'unassigned', x['assignee_name'].lower())
    )
    
    for swimlane in swimlanes:
        swimlane['columns'] = [
            {
                'value': status_value,
                'label': status_label,
                'tickets': swimlane['columns'][status_value],
            }
            for status_value, status_label in statuses
        ]
    
    from datetime import date
    return render(request, 'projects/project_board.html', {
        'project': project,
        'statuses': statuses,
        'swimlanes': swimlanes,
        'active_sprint': active_sprint,
        'today': date.today(),
    })


import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST


@login_required
@require_POST
def update_ticket_status(request, ticket_id):
    try:
        ticket = get_object_or_404(Ticket, id=ticket_id)
        data = json.loads(request.body)
        new_status = data.get('status')
        
        # Validate the status value
        valid_statuses = [choice[0] for choice in Ticket.STATUS_CHOICES]
        if new_status not in valid_statuses:
            return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)
        
        ticket.status = new_status
        ticket.save()
        
        return JsonResponse({'success': True, 'ticket_id': ticket.id, 'status': new_status})
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
    

from django.shortcuts import redirect
from .forms import TicketForm


@login_required
def ticket_create(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        form = TicketForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.project = project
            ticket.reporter = request.user
            ticket.save()
            return redirect('projects:project_board', project_id=project.id)
    else:
        form = TicketForm()
    
    return render(request, 'projects/ticket_create.html', {
        'project': project,
        'form': form,
    })

@login_required
def ticket_edit(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    
    if request.method == 'POST':
        form = TicketForm(request.POST, instance=ticket)
        if form.is_valid():
            form.save()
            return redirect('projects:ticket_detail', ticket_id=ticket.id)
    else:
        form = TicketForm(instance=ticket)
    
    return render(request, 'projects/ticket_edit.html', {
        'ticket': ticket,
        'form': form,
    })

@login_required
def project_backlog(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    
    # Backlog = tickets not in any sprint, excluding cancelled
    backlog_tickets = project.tickets.filter(sprint__isnull=True).exclude(status='cancelled')
    
    # Apply search filter if a query was provided
    search_query = request.GET.get('q', '').strip()
    if search_query:
        backlog_tickets = backlog_tickets.filter(title__icontains=search_query)
    
    backlog_tickets = backlog_tickets.order_by('-priority', '-created_at')
    
    sprints = project.sprints.exclude(status='completed').order_by('-created_at')
    
    return render(request, 'projects/project_backlog.html', {
        'project': project,
        'backlog_tickets': backlog_tickets,
        'sprints': sprints,
        'search_query': search_query,
    })


@login_required
@require_POST
def move_ticket_to_sprint(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    sprint_id = request.POST.get('sprint_id')
    
    if sprint_id:
        sprint = get_object_or_404(Sprint, id=sprint_id, project=ticket.project)
        ticket.sprint = sprint
    else:
        ticket.sprint = None  # Move back to backlog
    
    ticket.save()
    
    # Redirect back to wherever the request came from
    next_url = request.POST.get('next')
    if next_url == 'detail':
        return redirect('projects:ticket_detail', ticket_id=ticket.id)
    return redirect('projects:project_backlog', project_id=ticket.project.id)

@login_required
def project_sprints(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    all_sprints = project.sprints.all().order_by('-created_at')
    
    # Add ticket counts to each sprint
    for sprint in all_sprints:
        sprint.ticket_count = sprint.tickets.count()
        sprint.completed_count = sprint.tickets.filter(status='done').count()
    
    # Split into active/planned (shown prominently) and completed (collapsed)
    current_sprints = [s for s in all_sprints if s.status != 'completed']
    completed_sprints = [s for s in all_sprints if s.status == 'completed']
    
    return render(request, 'projects/project_sprints.html', {
        'project': project,
        'current_sprints': current_sprints,
        'completed_sprints': completed_sprints,
    })

@login_required
@require_POST
def update_sprint_status(request, sprint_id):
    sprint = get_object_or_404(Sprint, id=sprint_id)
    
    # Only admin (staff) users can start/complete sprints
    if not request.user.is_staff:
        return redirect('projects:project_sprints', project_id=sprint.project.id)
    
    new_status = request.POST.get('status')
    
    valid_statuses = [choice[0] for choice in Sprint.STATUS_CHOICES]
    if new_status not in valid_statuses:
        return redirect('projects:project_sprints', project_id=sprint.project.id)
    
    if new_status == 'active':
        Sprint.objects.filter(
            project=sprint.project, 
            status='active'
        ).exclude(id=sprint.id).update(status='planned')
    
    sprint.status = new_status
    sprint.save()
    
    return redirect('projects:project_sprints', project_id=sprint.project.id)



@login_required
@require_POST
def comment_create(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    form = CommentForm(request.POST)
    
    if form.is_valid():
        comment = form.save(commit=False)
        comment.ticket = ticket
        comment.author = request.user
        comment.save()
    
    return redirect('projects:ticket_detail', ticket_id=ticket.id)


@login_required
def ticket_cancel(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    
    # Already cancelled? Just go back to ticket detail
    if ticket.status == 'cancelled':
        return redirect('projects:ticket_detail', ticket_id=ticket.id)
    
    if request.method == 'POST':
        form = CancelTicketForm(request.POST)
        if form.is_valid():
            ticket.status = 'cancelled'
            ticket.cancellation_reason = form.cleaned_data['reason']
            ticket.cancelled_by = request.user
            ticket.cancelled_at = timezone.now()
            ticket.save()
            return redirect('projects:ticket_detail', ticket_id=ticket.id)
    else:
        form = CancelTicketForm()
    
    return render(request, 'projects/ticket_cancel.html', {
        'ticket': ticket,
        'form': form,
    })

@login_required
@require_POST
def ticket_delete(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    project_id = ticket.project.id
    ticket.delete()
    return redirect('projects:project_detail', project_id=project_id)

@login_required
def dashboard(request):
    user = request.user
    
    # My open tickets (assigned to me, not done or cancelled)
    my_tickets = Ticket.objects.filter(
        assignee=user
    ).exclude(status__in=['done', 'cancelled']).select_related('project', 'sprint').order_by('due_date')
    
    my_open_count = my_tickets.count()
    my_overdue_count = my_tickets.filter(due_date__lt=date.today()).count()
    
    # Active sprints across all projects
    active_sprints = list(Sprint.objects.filter(status='active').select_related('project'))
    for sprint in active_sprints:
        sprint.ticket_count = sprint.tickets.exclude(status='cancelled').count()
        sprint.completed_count = sprint.tickets.filter(status='done').count()
    
    total_projects = Project.objects.count()
    
    return render(request, 'projects/dashboard.html', {
        'my_tickets': my_tickets,
        'my_open_count': my_open_count,
        'my_overdue_count': my_overdue_count,
        'active_sprints': active_sprints,
        'active_sprint_count': len(active_sprints),
        'total_projects': total_projects,
        'today': date.today(),
    })