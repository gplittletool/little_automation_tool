"""
Views de autenticação (login, registro, logout)
"""
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django import forms
from .models import UserProfile


class RegisterForm(UserCreationForm):
    """Formulário de registro customizado"""
    email = forms.EmailField(required=True)
    first_name = forms.CharField(required=False, max_length=100)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'password1', 'password2']
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        
        if commit:
            user.save()
            # Criar UserProfile automaticamente
            UserProfile.objects.get_or_create(user=user)
        
        return user


def register_view(request):
    """View de registro"""
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Login automático após registro
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=password)
            login(request, user)
            
            return redirect('dashboard')
    else:
        form = RegisterForm()
    
    return render(request, 'registration/register.html', {'form': form})

