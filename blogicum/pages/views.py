"""View-функции и классы приложения pages."""
from django.shortcuts import render
from django.views import generic


class AboutView(generic.TemplateView):
    """Статичная страница «О проекте»."""

    template_name = 'pages/about.html'


class RulesView(generic.TemplateView):
    """Статичная страница «Правила»."""

    template_name = 'pages/rules.html'


def page_not_found(request, exception=None):
    """Обработчик ошибки 404."""
    return render(request, 'pages/404.html', status=404)


def csrf_failure(request, reason=''):
    """Обработчик ошибки 403 CSRF."""
    return render(request, 'pages/403csrf.html', status=403)


def server_error(request):
    """Обработчик ошибки 500."""
    return render(request, 'pages/500.html', status=500)
