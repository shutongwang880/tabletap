# tabletapapp/forms.py
from django import forms
from .models import Menu, MenuItem, CustomUser
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class MenuForm(forms.ModelForm):
    class Meta:
        model = Menu
        fields = ['name', 'description', 'active']

class MenuItemForm(forms.ModelForm):
    class Meta:
        model = MenuItem
        fields = ['name', 'description', 'price', 'image']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

User = get_user_model()

class CustomUserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Confirm Password', widget=forms.PasswordInput)

    class Meta:
        model = CustomUser
        fields = ('username', 'email')

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user

class CustomUserUpdateForm(forms.ModelForm):
    password1 = forms.CharField(label='New Password', widget=forms.PasswordInput, required=False)
    password2 = forms.CharField(label='Confirm Password', widget=forms.PasswordInput, required=False)

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'is_superuser', 'is_archived') 

    def clean(self):
        cleaned_data = super().clean()
        pwd1 = cleaned_data.get("password1")
        pwd2 = cleaned_data.get("password2")

        if pwd1 or pwd2:
            if pwd1 != pwd2:
                raise forms.ValidationError("Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password1")
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user



class CustomLoginForm(AuthenticationForm):
    """
    Form for user login with email
    """
    username = forms.EmailField(
        label=_("Email"),
        max_length=254,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'id': 'email', 'placeholder': 'Email address'})
    )
    password = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'id': 'password', 'placeholder': 'Password'})
    )