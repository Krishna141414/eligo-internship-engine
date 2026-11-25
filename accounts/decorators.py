"""Role guards. Anonymous -> login page. Wrong role -> 403. Deactivated while logged in -> logged out."""
from functools import wraps

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

from accounts.forms import INACTIVE_MESSAGE


def _role_required(check):
    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            user.refresh_from_db(fields=["status", "is_active", "user_type"])
            if not user.is_active:
                logout(request)
                messages.error(request, INACTIVE_MESSAGE)
                return redirect_to_login(request.get_full_path())
            if not check(user):
                raise PermissionDenied("You don't have access to this page.")
            return view(request, *args, **kwargs)
        return wrapper
    return decorator


student_required = _role_required(lambda u: u.is_student)
admin_required = _role_required(lambda u: u.is_admin_user)
