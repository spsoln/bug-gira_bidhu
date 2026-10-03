"""
Bug-Gira — Automated tests.

Copyright (c) [2026] [Bidhu Shekhar Tiwari]
Licensed under the MIT License. See LICENSE for details.
"""

from django.test import TestCase
from django.contrib.auth.models import User
from .models import Project, Ticket, Sprint, Comment
from django.test import override_settings
from django.db.models import ProtectedError
from .forms import TicketForm
from .models import Application, Product

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




class SignUpTest(TestCase):
    def test_signup_page_loads(self):
        """The signup page is publicly accessible."""
        response = self.client.get(reverse("projects:signup"))
        self.assertEqual(response.status_code, 200)

    def test_successful_signup_creates_user_and_logs_in(self):
        """A valid signup creates the user and logs them in."""
        response = self.client.post(
            reverse("projects:signup"),
            {
                "username": "newperson",
                "email": "newperson@example.com",
                "password1": "SecurePass123!",
                "password2": "SecurePass123!",
            },
        )
        # Redirects to dashboard on success
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("projects:dashboard"), response.url)
        # User was created
        self.assertTrue(User.objects.filter(username="newperson").exists())

    def test_signup_password_mismatch_fails(self):
        """Mismatched passwords do not create a user."""
        self.client.post(
            reverse("projects:signup"),
            {
                "username": "badperson",
                "email": "badperson@example.com",
                "password1": "SecurePass123!",
                "password2": "DifferentPass123!",
            },
        )
        self.assertFalse(User.objects.filter(username="badperson").exists())

    def test_duplicate_email_rejected(self):
        """Signing up with an existing email is rejected."""
        User.objects.create_user(
            username="first", email="taken@example.com", password="SecurePass123!"
        )
        self.client.post(
            reverse("projects:signup"),
            {
                "username": "second",
                "email": "taken@example.com",
                "password1": "SecurePass123!",
                "password2": "SecurePass123!",
            },
        )
        # Second user should NOT be created
        self.assertFalse(User.objects.filter(username="second").exists())

    @override_settings()
    def test_domain_restriction_blocks_wrong_domain(self):
        """When a domain is configured, other domains are rejected."""
        import os
        os.environ["ALLOWED_SIGNUP_DOMAIN"] = "mycompany.com"
        try:
            self.client.post(
                reverse("projects:signup"),
                {
                    "username": "outsider",
                    "email": "outsider@gmail.com",
                    "password1": "SecurePass123!",
                    "password2": "SecurePass123!",
                },
            )
            self.assertFalse(User.objects.filter(username="outsider").exists())
        finally:
            # Clean up so other tests aren't affected
            del os.environ["ALLOWED_SIGNUP_DOMAIN"]   

from django.core import mail


class EmailNotificationTest(TestCase):
    def setUp(self):
        self.reporter = User.objects.create_user(
            username="reporter", password="testpass123", email="reporter@example.com"
        )
        self.assignee = User.objects.create_user(
            username="assignee", password="testpass123", email="assignee@example.com"
        )
        self.other = User.objects.create_user(
            username="other", password="testpass123", email="other@example.com"
        )
        self.project = Project.objects.create(key="BAT", name="Test Project")
        self.client.login(username="reporter", password="testpass123")

    def test_email_sent_on_create_with_assignee(self):
        """Creating a ticket with an assignee sends them an email."""
        self.client.post(
            reverse("projects:ticket_create", args=[self.project.id]),
            {
                "title": "Assigned ticket",
                "ticket_type": "task",
                "priority": "medium",
                "status": "todo",
                "assignee": self.assignee.id,
            },
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("assignee@example.com", mail.outbox[0].to)
        self.assertIn("Assigned ticket", mail.outbox[0].subject)

    def test_no_email_when_no_assignee(self):
        """Creating a ticket with no assignee sends no email."""
        self.client.post(
            reverse("projects:ticket_create", args=[self.project.id]),
            {
                "title": "Unassigned ticket",
                "ticket_type": "task",
                "priority": "medium",
                "status": "todo",
            },
        )
        self.assertEqual(len(mail.outbox), 0)

    def test_email_sent_on_reassignment(self):
        """Changing a ticket's assignee to a new person emails them."""
        ticket = Ticket.objects.create(
            project=self.project, title="A ticket", assignee=self.assignee
        )
        mail.outbox = []  # clear any setup mail
        self.client.post(
            reverse("projects:ticket_edit", args=[ticket.id]),
            {
                "title": "A ticket",
                "ticket_type": "task",
                "priority": "medium",
                "status": "todo",
                "assignee": self.other.id,  # reassign to someone new
            },
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("other@example.com", mail.outbox[0].to)

    def test_no_email_when_assignee_unchanged(self):
        """Editing a ticket without changing assignee sends no email."""
        ticket = Ticket.objects.create(
            project=self.project, title="A ticket", assignee=self.assignee
        )
        mail.outbox = []
        self.client.post(
            reverse("projects:ticket_edit", args=[ticket.id]),
            {
                "title": "A ticket EDITED",  # changed title, same assignee
                "ticket_type": "task",
                "priority": "high",          # changed priority too
                "status": "todo",
                "assignee": self.assignee.id,  # same assignee
            },
        )
        self.assertEqual(len(mail.outbox), 0)    

class TicketDeletePermissionTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_staff=True
        )
        self.regular = User.objects.create_user(
            username="regular", password="testpass123"
        )
        self.project = Project.objects.create(key="BAT", name="Test Project")
        self.ticket = Ticket.objects.create(project=self.project, title="A ticket")

    def test_non_staff_cannot_delete(self):
        """A regular user cannot permanently delete a ticket."""
        self.client.login(username="regular", password="testpass123")
        self.client.post(reverse("projects:ticket_delete", args=[self.ticket.id]))
        self.assertTrue(Ticket.objects.filter(id=self.ticket.id).exists())

    def test_staff_can_delete(self):
        """A staff user can permanently delete a ticket."""
        self.client.login(username="admin", password="testpass123")
        self.client.post(reverse("projects:ticket_delete", args=[self.ticket.id]))
        self.assertFalse(Ticket.objects.filter(id=self.ticket.id).exists())

    def test_anonymous_cannot_delete(self):
        """An unauthenticated request cannot delete a ticket."""
        self.client.post(reverse("projects:ticket_delete", args=[self.ticket.id]))
        self.assertTrue(Ticket.objects.filter(id=self.ticket.id).exists())


class BoardViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="testpass123")
        self.project = Project.objects.create(key="BAT", name="Test Project")
        self.client.login(username="alice", password="testpass123")

    def test_board_loads_with_no_active_sprint(self):
        """The board renders fine when the project has no active sprint."""
        response = self.client.get(
            reverse("projects:project_board", args=[self.project.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["swimlanes"]), 0)

    def test_board_loads_with_active_sprint(self):
        """The board shows tickets from the active sprint, grouped by assignee."""
        sprint = Sprint.objects.create(
            project=self.project, name="Sprint 1", status="active"
        )
        Ticket.objects.create(
            project=self.project, title="In sprint", sprint=sprint, assignee=self.user
        )
        response = self.client.get(
            reverse("projects:project_board", args=[self.project.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["swimlanes"]), 1)

    def test_cancelled_tickets_excluded_from_board(self):
        """Cancelled tickets do not appear on the board."""
        sprint = Sprint.objects.create(
            project=self.project, name="Sprint 1", status="active"
        )
        Ticket.objects.create(
            project=self.project, title="Cancelled one", sprint=sprint,
            assignee=self.user, status="cancelled",
        )
        response = self.client.get(
            reverse("projects:project_board", args=[self.project.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["swimlanes"]), 0)     

class BugFieldsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="testpass123")
        self.project = Project.objects.create(key="BAT", name="Test Project")
        self.app = Application.objects.create(name="Mobile App")
        self.product = Product.objects.create(name="Motor")
        self.client.login(username="alice", password="testpass123")

    def _create(self, **extra):
        data = {"title": "A ticket", "ticket_type": "task",
                "priority": "medium", "status": "todo"}
        data.update(extra)
        return self.client.post(
            reverse("projects:ticket_create", args=[self.project.id]), data
        )

    def test_bug_requires_application_and_product(self):
        """A bug without application and product is rejected."""
        self._create(title="Bad bug", ticket_type="bug")
        self.assertFalse(Ticket.objects.filter(title="Bad bug").exists())

    def test_bug_with_both_fields_is_saved(self):
        """A bug with both fields is saved with them."""
        self._create(title="Good bug", ticket_type="bug",
                     application=self.app.id, product=self.product.id)
        ticket = Ticket.objects.get(title="Good bug")
        self.assertEqual(ticket.application, self.app)
        self.assertEqual(ticket.product, self.product)

    def test_task_does_not_need_them(self):
        """A task can be created without application or product."""
        self._create(title="Plain task")
        self.assertIsNone(Ticket.objects.get(title="Plain task").application)

    def test_task_discards_bug_fields(self):
        """Application and product submitted on a non-bug are not saved."""
        self._create(title="Sneaky task",
                     application=self.app.id, product=self.product.id)
        ticket = Ticket.objects.get(title="Sneaky task")
        self.assertIsNone(ticket.application)
        self.assertIsNone(ticket.product)

    def test_changing_bug_to_task_clears_fields(self):
        """Converting a bug to a task removes its application and product."""
        ticket = Ticket.objects.create(
            project=self.project, title="Was a bug", ticket_type="bug",
            application=self.app, product=self.product,
        )
        self.client.post(reverse("projects:ticket_edit", args=[ticket.id]), {
            "title": "Was a bug", "ticket_type": "task",
            "priority": "medium", "status": "todo",
            "application": self.app.id, "product": self.product.id,
        })
        ticket.refresh_from_db()
        self.assertIsNone(ticket.application)
        self.assertIsNone(ticket.product)

    def test_inactive_product_hidden_from_new_tickets(self):
        """A retired product is not offered when creating a ticket."""
        self.product.is_active = False
        self.product.save()
        self.assertNotIn(self.product, TicketForm().fields["product"].queryset)

    def test_inactive_product_kept_on_existing_ticket(self):
        """A retired product stays selectable on a ticket that already uses it."""
        ticket = Ticket.objects.create(
            project=self.project, title="Old bug", ticket_type="bug",
            application=self.app, product=self.product,
        )
        self.product.is_active = False
        self.product.save()
        form = TicketForm(instance=ticket)
        self.assertIn(self.product, form.fields["product"].queryset)

    def test_product_in_use_cannot_be_deleted(self):
        """A product referenced by a bug is protected from deletion."""
        Ticket.objects.create(
            project=self.project, title="Bug", ticket_type="bug",
            application=self.app, product=self.product,
        )
        with self.assertRaises(ProtectedError):
            self.product.delete()  

class TicketFilterTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="testpass123")
        self.project = Project.objects.create(key="BAT", name="Test Project")
        self.app = Application.objects.create(name="Mobile App")
        self.motor = Product.objects.create(name="Motor")
        self.health = Product.objects.create(name="Health")
        Ticket.objects.create(project=self.project, title="Motor bug", ticket_type="bug",
                              application=self.app, product=self.motor)
        Ticket.objects.create(project=self.project, title="Health bug", ticket_type="bug",
                              application=self.app, product=self.health)
        Ticket.objects.create(project=self.project, title="A task")
        self.client.login(username="alice", password="testpass123")
        self.url = reverse("projects:project_detail", args=[self.project.id])

    def titles(self, response):
        return {t.title for t in response.context["tickets"]}

    def test_filter_by_product(self):
        """Filtering by product returns only that product's tickets."""
        response = self.client.get(self.url, {"product": self.motor.id})
        self.assertEqual(self.titles(response), {"Motor bug"})

    def test_filter_by_type(self):
        """Filtering by type returns only that type."""
        response = self.client.get(self.url, {"type": "bug"})
        self.assertEqual(self.titles(response), {"Motor bug", "Health bug"})

    def test_filters_combine(self):
        """Multiple filters narrow the results together."""
        response = self.client.get(self.url, {"type": "bug", "product": self.health.id})
        self.assertEqual(self.titles(response), {"Health bug"})

    def test_invalid_id_is_ignored(self):
        """A junk product ID in the URL is ignored rather than crashing the page."""
        response = self.client.get(self.url, {"product": "abc"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.titles(response)), 3)

    def test_retired_product_still_filterable(self):
        """Retired products remain available in the filter for historical reporting."""
        self.motor.is_active = False
        self.motor.save()
        response = self.client.get(self.url)
        self.assertIn(self.motor, response.context["products"])                                                