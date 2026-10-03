from django import forms
from django.db.models import Q
from .models import Application, Comment, Product, Ticket
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
import os

class TicketForm(forms.ModelForm):
    BUG_ONLY_FIELDS = ('application', 'product')

    class Meta:
        model = Ticket
        fields = ['title', 'description', 'ticket_type', 'application', 'product',
                  'priority', 'status', 'assignee', 'due_date']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'What needs to be done?',
                'autofocus': True,
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 4,
                'placeholder': 'Add more details...',
            }),
            'ticket_type': forms.Select(attrs={'class': 'form-input'}),
            'application': forms.Select(attrs={'class': 'form-input'}),
            'product': forms.Select(attrs={'class': 'form-input'}),
            'priority': forms.Select(attrs={'class': 'form-input'}),
            'status': forms.Select(attrs={'class': 'form-input'}),
            'assignee': forms.Select(attrs={'class': 'form-input'}),
            'due_date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Offer only active records, but keep the current value selectable when
        # editing a ticket whose application or product has since been retired.
        self.fields['application'].queryset = Application.objects.filter(
            Q(is_active=True) | Q(pk=self.instance.application_id)
        )
        self.fields['product'].queryset = Product.objects.filter(
            Q(is_active=True) | Q(pk=self.instance.product_id)
        )
        self.fields['application'].empty_label = 'Select an application'
        self.fields['product'].empty_label = 'Select a product'
        for name in self.BUG_ONLY_FIELDS:
            self.fields[name].help_text = 'Required for bugs.'

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('ticket_type') == 'bug':
            for name in self.BUG_ONLY_FIELDS:
                if not cleaned.get(name):
                    self.add_error(name, 'This field is required for bugs.')
        else:
            # These fields only apply to bugs, so clear any leftover value
            for name in self.BUG_ONLY_FIELDS:
                cleaned[name] = None
        return cleaned

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['body']
        widgets = {
            'body': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 3,
                'placeholder': 'Add a comment...',
            }),
        }
        labels = {
            'body': '',  # No label needed, the placeholder is enough
        }

class CancelTicketForm(forms.Form):
    reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-input',
            'rows': 4,
            'placeholder': 'Why is this ticket being cancelled? (e.g., duplicate of PROJ-5, scope changed, no longer needed)',
            'autofocus': True,
        }),
        required=True,
        min_length=10,
        error_messages={
            'required': 'A reason is required for audit purposes.',
            'min_length': 'Please provide a more detailed reason (at least 10 characters).',
        }
    )        

class SignUpForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'you@company.com',
        }),
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Style the inherited fields (username, password1, password2)
        for field_name in ['username', 'password1', 'password2']:
            self.fields[field_name].widget.attrs['class'] = 'form-input'

    def clean_email(self):
        email = self.cleaned_data.get('email', '').lower()
        # Restrict signups to the company domain (set via env var)
        allowed_domain = os.environ.get('ALLOWED_SIGNUP_DOMAIN', '').strip().lower()
        if allowed_domain:
            if not email.endswith('@' + allowed_domain):
                raise forms.ValidationError(
                    f'Signups are restricted to @{allowed_domain} email addresses.'
                )
        # Prevent duplicate emails
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user    