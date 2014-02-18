from crispy_forms.bootstrap import Field, FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Layout, Submit
from django import forms
from django.forms import widgets
from django.forms.extras.widgets import SelectDateWidget


class LoginForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(LoginForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_show_labels = False
        self.helper.layout = Layout(
            Field('email', placeholder='Email', css_class='input-xlarge'),
            Field('password', css_class='input-xlarge', placeholder='Password'),
            FormActions(
                Submit('submit', value='Log In', css_class='btn-info btn-large btn-embossed mlm', css_id='loginButton'),
                HTML('<i id="spinnerLogin" class="icon-spinner icon-spin icon-large" '
                     'style="font-size: 18px; padding: 3px; display:none;"></i>')
            )
        )
    email = forms.CharField(max_length=200)
    password = forms.CharField(widget=widgets.PasswordInput)


class RegistrationForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(RegistrationForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_show_labels = False
        self.helper.layout = Layout(
            Field('first_name', placeholder='First name', css_class='input-xlarge'),
            Field('last_name', placeholder='Last name', css_class='input-xlarge'),
            Field('email', placeholder='Email', css_class='input-xlarge'),
            Field('password', css_class='input-xlarge', placeholder='Password'),
            FormActions(
                Submit('submit', value='Sign Up', css_class='btn-info btn-large btn-embossed mlm', css_id='registrationButton'),
                HTML('<i id="spinnerSignup" class="icon-spinner icon-spin icon-large" '
                     'style="font-size: 18px; padding: 3px; display:none;"></i>')
            )
        )
    first_name = forms.CharField(max_length=200, label="First name")
    last_name = forms.CharField(max_length=200, label="Last name")
    email = forms.EmailField(max_length=200)
    password = forms.CharField(widget=widgets.PasswordInput)


class ProfileForm(forms.Form):
    full_name = forms.CharField(max_length=200, label="Full Name")
    email = forms.EmailField(max_length=200)
    gender = forms.Select(choices=['Male', 'Female'])
    birth_date = forms.DateField(widget=SelectDateWidget())
    country = forms.CharField(max_length=200)