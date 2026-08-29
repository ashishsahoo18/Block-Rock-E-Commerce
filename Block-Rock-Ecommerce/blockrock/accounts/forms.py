from django import forms
from django.contrib.auth.forms import PasswordChangeForm, UserCreationForm
from django.contrib.auth.models import User


class RegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('first_name', 'last_name', 'username', 'email', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account already uses this email address.')
        return email


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('An account already uses this email address.')
        return email


class BlockRockPasswordChangeForm(PasswordChangeForm):
    """Named form keeps password fields and validator errors in Django's safe flow."""


class NewsletterSubscriptionForm(forms.Form):
    email = forms.EmailField(error_messages={
        'invalid': 'Please enter a valid email address.',
        'required': 'Please enter a valid email address.',
    })

    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()
