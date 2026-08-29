from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.contrib.auth.views import PasswordResetCompleteView, PasswordResetConfirmView, PasswordResetDoneView, PasswordResetView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from cart.models import Cart, Wishlist

from .forms import NewsletterSubscriptionForm, ProfileForm, RegistrationForm
from .models import Subscriber


def _safe_next_url(request):
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url and url_has_allowed_host_and_scheme(next_url, {request.get_host()}):
        return next_url
    return None


def register(request):
    if request.user.is_authenticated:
        return redirect('account')
    form = RegistrationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Your account has been created. Please sign in to continue.')
        return redirect(f"{reverse_lazy('login')}?next={_safe_next_url(request)}" if _safe_next_url(request) else 'login')
    return render(request, 'accounts/register.html', {'form': form, 'next': request.GET.get('next', '')})


def login_user(request):
    if request.user.is_authenticated:
        return redirect(_safe_next_url(request) or 'account')
    next_url = _safe_next_url(request)
    if request.method == 'POST':
        identifier = request.POST.get('identifier', '').strip()
        password = request.POST.get('password', '')
        username = identifier
        if '@' in identifier:
            matched_user = User.objects.filter(email__iexact=identifier).only('username').first()
            username = matched_user.username if matched_user else ''
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if not request.POST.get('remember_me'):
                request.session.set_expiry(0)
            messages.success(request, f'Welcome back, {user.first_name or user.username}.')
            return redirect(next_url or 'home')
        messages.error(request, 'Your username/email or password was not recognised.')
    return render(request, 'accounts/login.html', {'next': next_url or ''})


@require_POST
def logout_user(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')


@require_POST
def subscribe_newsletter(request):
    form = NewsletterSubscriptionForm(request.POST)
    if form.is_valid():
        email = form.cleaned_data['email']
        subscriber, created = Subscriber.objects.get_or_create(email=email)
        if created:
            messages.success(request, "You're subscribed! Welcome to Block Rock.")
        elif subscriber.is_active:
            messages.info(request, "You're already subscribed to Block Rock.")
        else:
            subscriber.is_active = True
            subscriber.subscribed_at = timezone.now()
            subscriber.save(update_fields=['is_active', 'subscribed_at'])
            messages.success(request, "You're subscribed! Welcome to Block Rock.")
    else:
        error = form.errors.get('email')
        messages.error(request, error[0] if error else 'Please enter a valid email address.')
    return redirect('home')


def _account_stats(user):
    cart_items = 0
    wishlist_items = 0
    try:
        cart_items = sum(item.quantity for item in Cart.objects.get(user=user).items.all())
    except Cart.DoesNotExist:
        pass
    try:
        wishlist_items = Wishlist.objects.get(user=user).items.count()
    except Wishlist.DoesNotExist:
        pass
    return {'orders_count': 0, 'cart_items': cart_items, 'wishlist_items': wishlist_items}


@login_required
def account(request):
    return render(request, 'accounts/account.html', _account_stats(request.user))


@login_required
def profile(request):
    return render(request, 'accounts/profile.html', _account_stats(request.user))


@login_required
def profile_edit(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('profile')
    return render(request, 'accounts/profile_edit.html', {'form': form})


@login_required
def profile_password(request):
    form = PasswordChangeForm(request.user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, 'Your password has been changed successfully.')
        return redirect('profile')
    return render(request, 'accounts/password_change.html', {'form': form})


class AccountPasswordResetView(PasswordResetView):
    template_name = 'accounts/password_reset.html'
    email_template_name = 'accounts/password_reset_email.txt'
    subject_template_name = 'accounts/password_reset_subject.txt'
    success_url = reverse_lazy('password_reset_done')


class AccountPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'accounts/password_reset_done.html'


class AccountPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'accounts/password_reset_confirm.html'
    success_url = reverse_lazy('password_reset_complete')


class AccountPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'accounts/password_reset_complete.html'
