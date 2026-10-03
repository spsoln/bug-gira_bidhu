from django.contrib import admin
from django.db.models import Count, Q

from .models import Application, Comment, Product, Project, Sprint, Ticket


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
    list_display = ('id', 'title', 'project', 'ticket_type', 'application', 'product',
                    'status', 'priority', 'assignee', 'sprint', 'due_date')
    list_filter = ('ticket_type', 'status', 'priority', 'project',
                   'application', 'product', 'sprint')
    search_fields = ('title', 'description')
    autocomplete_fields = ('project', 'sprint', 'assignee', 'reporter',
                           'application', 'product')
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


class BugCountMixin:
    """Adds a 'Bugs' column showing how many bug tickets reference each record."""

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            bug_total=Count('tickets', filter=Q(tickets__ticket_type='bug'))
        )

    @admin.display(description='Bugs', ordering='bug_total')
    def bug_count(self, obj):
        return obj.bug_total


@admin.register(Application)
class ApplicationAdmin(BugCountMixin, admin.ModelAdmin):
    list_display = ('name', 'is_active', 'bug_count')
    list_editable = ('is_active',)
    list_filter = ('is_active',)
    search_fields = ('name',)


@admin.register(Product)
class ProductAdmin(BugCountMixin, admin.ModelAdmin):
    list_display = ('name', 'is_active', 'bug_count')
    list_editable = ('is_active',)
    list_filter = ('is_active',)
    search_fields = ('name',)