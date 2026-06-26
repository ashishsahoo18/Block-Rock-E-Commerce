from django.shortcuts import render, redirect

from django.contrib.auth.models import User

from django.contrib.auth import authenticate, login, logout


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

            return redirect('/')


    return render(request,'login.html')




def logout_user(request):

    logout(request)

    return redirect('login')