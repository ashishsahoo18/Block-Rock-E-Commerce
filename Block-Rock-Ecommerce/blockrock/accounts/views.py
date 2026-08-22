from django.shortcuts import render, redirect

from django.contrib.auth.models import User

from django.contrib.auth import authenticate, login, logout
from django.utils.http import url_has_allowed_host_and_scheme


def signup(request):

    if request.method == "POST":

        username = request.POST['username']

        email = request.POST['email']

        password = request.POST['password']


        user = User.objects.create_user(

            username=username,

            email=email,

            password=password

        )


        user.save()


        return redirect('login')


    return render(request,'signup.html')




def login_user(request):

    if request.method == "POST":


        username = request.POST['username']

        password = request.POST['password']


        user = authenticate(

            username=username,

            password=password

        )


        if user:

            login(request,user)

            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url and url_has_allowed_host_and_scheme(next_url, {request.get_host()}):
                return redirect(next_url)
            return redirect('/')


    return render(request, 'login.html', {'next': request.GET.get('next', '')})




def logout_user(request):

    logout(request)

    return redirect('login')
