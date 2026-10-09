from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


Usuario = get_user_model()


class EmailOrUsernameModelBackend(ModelBackend):
    """
    Backend de autenticación que permite iniciar sesión con:
      · Username (coord01pe) — O BIEN —
      · Correo electrónico (jatobonv@sena.edu.co)

    Mantiene compatibilidad total con el ModelBackend nativo de Django.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        login_normalizado = str(username).strip().lower()
        try:
            user = Usuario.objects.get(
                Q(username__iexact=login_normalizado) | Q(email__iexact=login_normalizado)
            )
        except Usuario.DoesNotExist:
            Usuario().set_password(password)
            return None
        except Usuario.MultipleObjectsReturned:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def get_user(self, user_id):
        try:
            return Usuario.objects.get(pk=user_id)
        except Usuario.DoesNotExist:
            return None
