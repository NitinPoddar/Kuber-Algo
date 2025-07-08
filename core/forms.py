from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User,AlgoList

class CustomUserCreationForm(UserCreationForm):
    name = forms.CharField(max_length=1000, required=True, label='Full Name')
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'name', 'email', 'password1', 'password2']

class AlgorithmForm(forms.ModelForm):
    class Meta:
        model = AlgoList
        fields = ['algo_name', 'minimum_fund_reqd', 'algo_description']
