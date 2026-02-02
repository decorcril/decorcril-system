from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, "Login realizado com sucesso!")
            return redirect("dashboard")
        else:
            messages.error(request, "Usuário ou senha incorretos.")

    return render(request, "catalogo/auth/login.html")


def logout_view(request):
    logout(request)
    messages.success(request, "Você saiu do sistema.")
    return redirect("login")
