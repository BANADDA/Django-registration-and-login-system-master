from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.contrib.auth.views import LoginView, PasswordResetView, PasswordChangeView
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.views import View
from django.contrib.auth.decorators import login_required

from .forms import RegisterForm, LoginForm, UpdateUserForm, UpdateProfileForm

from django.shortcuts import render
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

# Import plotly and pandas
import plotly.express as px
import pandas as pd


def home(request):
    return render(request, 'users/home.html')


class RegisterView(View):
    form_class = RegisterForm
    initial = {'key': 'value'}
    template_name = 'users/register.html'

    def dispatch(self, request, *args, **kwargs):
        # will redirect to the home page if a user tries to access the register page while logged in
        if request.user.is_authenticated:
            return redirect(to='/')

        # else process dispatch as it otherwise normally would
        return super(RegisterView, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = self.form_class(initial=self.initial)
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)

        if form.is_valid():
            form.save()

            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}')

            return redirect(to='login')

        return render(request, self.template_name, {'form': form})


# Class based view that extends from the built in login view to add a remember me functionality
class CustomLoginView(LoginView):
    form_class = LoginForm

    def form_valid(self, form):
        remember_me = form.cleaned_data.get('remember_me')

        if not remember_me:
            # set session expiry to 0 seconds. So it will automatically close the session after the browser is closed.
            self.request.session.set_expiry(0)

            # Set session as modified to force data updates/cookie to be saved.
            self.request.session.modified = True

        # else browser session will be as long as the session cookie time "SESSION_COOKIE_AGE" defined in settings.py
        return super(CustomLoginView, self).form_valid(form)


class ResetPasswordView(SuccessMessageMixin, PasswordResetView):
    template_name = 'users/password_reset.html'
    email_template_name = 'users/password_reset_email.html'
    subject_template_name = 'users/password_reset_subject'
    success_message = "We've emailed you instructions for setting your password, " \
                      "if an account exists with the email you entered. You should receive them shortly." \
                      " If you don't receive an email, " \
                      "please make sure you've entered the address you registered with, and check your spam folder."
    success_url = reverse_lazy('users-home')


class ChangePasswordView(SuccessMessageMixin, PasswordChangeView):
    template_name = 'users/change_password.html'
    success_message = "Successfully Changed Your Password"
    success_url = reverse_lazy('users-home')


@login_required
def profile(request):
    if request.method == 'POST':
        user_form = UpdateUserForm(request.POST, instance=request.user)
        profile_form = UpdateProfileForm(request.POST, request.FILES, instance=request.user.profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your profile is updated successfully')
            return redirect(to='users-profile')
    else:
        user_form = UpdateUserForm(instance=request.user)
        profile_form = UpdateProfileForm(instance=request.user.profile)

    return render(request, 'users/profile.html', {'user_form': user_form, 'profile_form': profile_form})


import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase SDK
cred1 = credentials.Certificate('firebase_config/users.json')
cred2 = credentials.Certificate('firebase_config/data.json')

# Initialize one Firebase project with a name
firebase_admin.initialize_app(cred1, name='myapp1')
firebase_admin.initialize_app(cred2, name='myapp2') 

def user_list(request):
    # Get a reference to the Firestore database
    db = firestore.client(app=firebase_admin.get_app('myapp1'))

    # Retrieve all users from the Firestore collection
    users_ref = db.collection('images')

    # Try using a different method to get the documents
    users = [doc.to_dict() for doc in users_ref.get()]

    # Convert timestamp to human-readable format
    for user in users:
        timestamp = user.get('timestamp')
        if timestamp:
            # Convert timestamp to datetime or use another method to format it
            user['timestamp'] = datetime.fromtimestamp(timestamp.timestamp()).strftime('%B %d, %Y at %I:%M:%S %p')

        # Retrieve the image URL from Firestore
        image_url = user.get('image_url')
        if image_url:
            user['image_url'] = image_url  # Assign the image URL to the user dictionary
        
        print(image_url)

    # Pass the users data to the template
    context = {'users': users}
    return render(request, 'users/user.html', context)
    
import plotly.graph_objects as go

def plot_histogram(images):
    df = pd.DataFrame(images)
    df['month'] = df['timestamp'].apply(lambda x: x.split()[0])
    df = df.groupby('month').size().reset_index(name='count')

    # Retrieve the months and counts as lists
    months = df['month'].tolist()
    counts = df['count'].tolist()

    return months, counts

import plotly.express as px
import plotly.io as pio

def data_list(request):
    db = firestore.client(app=firebase_admin.get_app('myapp2'))
    images_ref = db.collection('images')
    images = [doc.to_dict() for doc in images_ref.get()]

    for image in images:
        timestamp = image.get('timestamp')
        if timestamp:
            image['timestamp'] = datetime.fromtimestamp(timestamp.timestamp()).strftime('%B %d, %Y at %I:%M:%S %p')

    months, counts = plot_histogram(images)

    # Create a histogram with Plotly Express
    fig = px.histogram(x=months, y=counts, labels={"x": "Months", "y": "Number of images"}, title="Histogram of images per month", color_discrete_sequence=["green", "violet", "yellow", "orange", "blue", "indigo", "violet"])

    fig.update_layout(
        title_font=dict(size=30, family="Courier", color="green"),
        xaxis_title_font=dict(size=20, family="Arial", color="red"),
        yaxis_title_font=dict(size=20, family="Arial", color="red"),
        title_x=0.5
        )
    # Convert it to HTML string
    plot_html = pio.to_html(fig, include_plotlyjs=False)

    context = {'images': images, 'plot_html': plot_html}
    return render(request, 'users/data.html', context)
