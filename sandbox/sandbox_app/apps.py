from django.apps import AppConfig


class SandboxAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sandbox_app"
    verbose_name = "Sandbox"
