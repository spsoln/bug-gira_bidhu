from django.contrib import admin
from .models import Project, Ticket, Comment, Sprint


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('key', 'name', 'created_at', 'updated_at')
    search_fields = ('key', 'name')


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 1
    fields = ('author', 'body', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'project', 'sprint', 'status', 'priority', 'ticket_type', 'assignee','due_date', 'created_at')
    list_filter = ('status', 'priority', 'ticket_type', 'project', 'sprint')
    search_fields = ('title', 'description')
    autocomplete_fields = ('project', 'sprint', 'assignee', 'reporter')
    inlines = [CommentInline]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket', 'author', 'created_at')
    search_fields = ('body',)
    autocomplete_fields = ('ticket', 'author')


@admin.register(Sprint)
class SprintAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'status', 'start_date', 'end_date', 'created_at')
    list_filter = ('status', 'project')
    search_fields = ('name', 'goal')
    autocomplete_fields = ('project',)