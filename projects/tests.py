"""
Bug-Gira — Automated tests.

Copyright (c) [2026] [Bidhu Shekhar Tiwari]
Licensed under the MIT License. See LICENSE for details.
"""

from django.test import TestCase
from django.contrib.auth.models import User
from .models import Project, Ticket, Sprint, Comment


class ProjectModelTest(TestCase):
    def setUp(self):
        self.project = Project.objects.create(
            key="BAT",
            name="Bug-Gira Development",
            description="Main project",
        )

    def test_project_str(self):
        """A project's string representation is 'KEY - Name'."""
        self.assertEqual(str(self.project), "BAT - Bug-Gira Development")

    def test_project_key_is_unique(self):
        """Two projects can't share the same key."""
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Project.objects.create(key="BAT", name="Duplicate")


class TicketModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="testpass123")
        self.project = Project.objects.create(key="BAT", name="Test Project")
        self.ticket = Ticket.objects.create(
            project=self.project,
            title="Fix the login bug",
            assignee=self.user,
            reporter=self.user,
        )

    def test_ticket_str(self):
        """A ticket's string representation includes project key and id."""
        expected = f"BAT-{self.ticket.id}: Fix the login bug"
        self.assertEqual(str(self.ticket), expected)

    def test_ticket_defaults(self):
        """New tickets default to 'todo' status, 'medium' priority, 'task' type."""
        self.assertEqual(self.ticket.status, "todo")
        self.assertEqual(self.ticket.priority, "medium")
        self.assertEqual(self.ticket.ticket_type, "task")

    def test_ticket_starts_with_no_sprint(self):
        """A new ticket is not in any sprint (it's in the backlog)."""
        self.assertIsNone(self.ticket.sprint)


class SprintModelTest(TestCase):
    def setUp(self):
        self.project = Project.objects.create(key="BAT", name="Test Project")
        self.sprint = Sprint.objects.create(
            project=self.project,
            name="Sprint 1",
            goal="Ship the MVP",
        )

    def test_sprint_str(self):
        """A sprint's string representation is 'KEY - Sprint Name'."""
        self.assertEqual(str(self.sprint), "BAT - Sprint 1")

    def test_sprint_defaults_to_planned(self):
        """New sprints start in 'planned' status."""
        self.assertEqual(self.sprint.status, "planned")


class CommentModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="bob", password="testpass123")
        self.project = Project.objects.create(key="BAT", name="Test Project")
        self.ticket = Ticket.objects.create(project=self.project, title="A ticket")
        self.comment = Comment.objects.create(
            ticket=self.ticket,
            author=self.user,
            body="This is a comment",
        )

    def test_comment_belongs_to_ticket(self):
        """A comment is linked to its ticket."""
        self.assertEqual(self.comment.ticket, self.ticket)
        self.assertIn(self.comment, self.ticket.comments.all())

    def test_deleting_ticket_deletes_comments(self):
        """Deleting a ticket cascades to delete its comments."""
        ticket_id = self.ticket.id
        self.ticket.delete()
        self.assertEqual(Comment.objects.filter(ticket_id=ticket_id).count(), 0)

from django.urls import reverse


class AuthenticationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="testpass123")
        self.project = Project.objects.create(key="BAT", name="Test Project")

    def test_dashboard_requires_login(self):
        """Anonymous users are redirected away from the dashboard."""
        response = self.client.get(reverse("projects:dashboard"))
        self.assertEqual(response.status_code, 302)  # redirect to login
        self.assertIn("/accounts/login/", response.url)

    def test_project_list_requires_login(self):
        """Anonymous users are redirected away from the project list."""
        response = self.client.get(reverse("projects:project_list"))
        self.assertEqual(response.status_code, 302)

    def test_board_requires_login(self):
        """Anonymous users can't see the board."""
        response = self.client.get(reverse("projects:project_board", args=[self.project.id]))
        self.assertEqual(response.status_code, 302)

    def test_logged_in_user_sees_dashboard(self):
        """A logged-in user gets a 200 OK on the dashboard."""
        self.client.login(username="alice", password="testpass123")
        response = self.client.get(reverse("projects:dashboard"))
        self.assertEqual(response.status_code, 200)


class ProjectViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="testpass123")
        self.project = Project.objects.create(key="BAT", name="Test Project")
        self.client.login(username="alice", password="testpass123")

    def test_project_list_shows_projects(self):
        """The project list page displays existing projects."""
        response = self.client.get(reverse("projects:project_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Project")

    def test_project_detail_loads(self):
        """The project detail page loads for a valid project."""
        response = self.client.get(reverse("projects:project_detail", args=[self.project.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "BAT")

    def test_project_detail_404_for_missing(self):
        """Requesting a nonexistent project returns 404."""
        response = self.client.get(reverse("projects:project_detail", args=[99999]))
        self.assertEqual(response.status_code, 404)


class TicketCreateTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="testpass123")
        self.project = Project.objects.create(key="BAT", name="Test Project")
        self.client.login(username="alice", password="testpass123")

    def test_create_ticket(self):
        """Submitting the create form makes a new ticket with the user as reporter."""
        response = self.client.post(
            reverse("projects:ticket_create", args=[self.project.id]),
            {
                "title": "New test ticket",
                "description": "Some details",
                "ticket_type": "task",
                "priority": "high",
                "status": "todo",
            },
        )
        # Should redirect to board after creation
        self.assertEqual(response.status_code, 302)
        # Ticket should exist
        ticket = Ticket.objects.get(title="New test ticket")
        self.assertEqual(ticket.reporter, self.user)
        self.assertEqual(ticket.priority, "high")     
from django.utils import timezone


class SprintBusinessRulesTest(TestCase):
    def setUp(self):
        # Staff user, since sprint management is admin-only
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_staff=True
        )
        self.project = Project.objects.create(key="BAT", name="Test Project")
        self.sprint1 = Sprint.objects.create(project=self.project, name="Sprint 1", status="active")
        self.sprint2 = Sprint.objects.create(project=self.project, name="Sprint 2", status="planned")
        self.client.login(username="admin", password="testpass123")

    def test_only_one_active_sprint(self):
        """Activating a sprint sets any other active sprint back to planned."""
        # Activate sprint2 — sprint1 should become planned
        self.client.post(
            reverse("projects:update_sprint_status", args=[self.sprint2.id]),
            {"status": "active"},
        )
        self.sprint1.refresh_from_db()
        self.sprint2.refresh_from_db()
        self.assertEqual(self.sprint2.status, "active")
        self.assertEqual(self.sprint1.status, "planned")

    def test_non_staff_cannot_change_sprint(self):
        """A regular (non-staff) user cannot start or complete sprints."""
        regular = User.objects.create_user(username="bob", password="testpass123")
        self.client.login(username="bob", password="testpass123")
        self.client.post(
            reverse("projects:update_sprint_status", args=[self.sprint2.id]),
            {"status": "active"},
        )
        self.sprint2.refresh_from_db()
        # Status should be unchanged — still planned
        self.assertEqual(self.sprint2.status, "planned")


class TicketCancellationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="testpass123")
        self.project = Project.objects.create(key="BAT", name="Test Project")
        self.ticket = Ticket.objects.create(project=self.project, title="To be cancelled")
        self.client.login(username="alice", password="testpass123")

    def test_cancellation_records_audit_info(self):
        """Cancelling a ticket records reason, who, and when."""
        self.client.post(
            reverse("projects:ticket_cancel", args=[self.ticket.id]),
            {"reason": "Duplicate of BAT-5, no longer needed"},
        )
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, "cancelled")
        self.assertEqual(self.ticket.cancellation_reason, "Duplicate of BAT-5, no longer needed")
        self.assertEqual(self.ticket.cancelled_by, self.user)
        self.assertIsNotNone(self.ticket.cancelled_at)

    def test_cancellation_requires_reason(self):
        """Cancelling without a reason (too short) does not cancel the ticket."""
        self.client.post(
            reverse("projects:ticket_cancel", args=[self.ticket.id]),
            {"reason": "no"},  # too short (min 10 chars)
        )
        self.ticket.refresh_from_db()
        # Ticket should NOT be cancelled — validation failed
        self.assertEqual(self.ticket.status, "todo")


class MoveToBacklogTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="testpass123")
        self.project = Project.objects.create(key="BAT", name="Test Project")
        self.sprint = Sprint.objects.create(project=self.project, name="Sprint 1", status="active")
        self.ticket = Ticket.objects.create(
            project=self.project, title="In sprint", sprint=self.sprint
        )
        self.client.login(username="alice", password="testpass123")

    def test_move_ticket_to_backlog(self):
        """Moving a ticket out of a sprint sets its sprint to None."""
        self.client.post(
            reverse("projects:move_to_sprint", args=[self.ticket.id]),
            {"sprint_id": "", "next": "detail"},
        )
        self.ticket.refresh_from_db()
        self.assertIsNone(self.ticket.sprint)

    def test_move_ticket_into_sprint(self):
        """Moving a backlog ticket into a sprint sets its sprint."""
        self.ticket.sprint = None
        self.ticket.save()
        self.client.post(
            reverse("projects:move_to_sprint", args=[self.ticket.id]),
            {"sprint_id": str(self.sprint.id)},
        )
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.sprint, self.sprint)           