"""Project middleware.

Write middleware as a plain callable -- it is the documented Django pattern and
it composes correctly with the rest of the stack::

    class TimingMiddleware:
        def __init__(self, get_response):
            self.get_response = get_response      # runs once at startup

        def __call__(self, request):
            # before the view
            response = self.get_response(request)
            # after the view
            return response

Django also calls these optional hooks if the class defines them:
``process_view``, ``process_exception`` and ``process_template_response``.
Define them directly on the class above -- Django wires them up itself, and
they receive the real view function rather than the next link in the chain.

If you want the legacy ``process_request`` / ``process_response`` hooks, inherit
from ``django.utils.deprecation.MiddlewareMixin`` instead of hand-rolling the
dispatch loop.

Register middleware by dotted path in ``MIDDLEWARE`` in
``config/settings/base.py``; order matters and is outermost-first.
"""
