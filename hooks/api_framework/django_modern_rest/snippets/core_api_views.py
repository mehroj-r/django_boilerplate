from http import HTTPStatus

from dmr import Controller
from dmr.plugins.msgspec import MsgspecSerializer
from dmr.security.jwt.auth import JWTSyncAuth

from core.api.errors import ApiError
from core.api.errors import format_error as format_error_envelope


class ErrorEnvelopeMixin:
    """Gives a controller the project-wide {success, message, error} body.

    A plain mixin rather than a Controller subclass: dmr's own JWT controllers
    are Controllers in their own right and need this too.
    """

    #: dmr both documents and runtime-validates every semantic error response
    #: against this, so it has to match what format_error returns exactly.
    error_model = ApiError

    def format_error(self, error, *, loc=None, error_type=None, status_code=None):
        return format_error_envelope(error, loc=loc, error_type=error_type, status_code=status_code)


class BaseController(ErrorEnvelopeMixin, Controller[MsgspecSerializer]):
    """Base for every controller in this project.

    Endpoints require a valid JWT by default; set ``auth = None`` on a
    controller to make it public. ``auth = ()`` does not: dmr merges a
    controller's auth with DMR_SETTINGS["auth"] rather than replacing it.
    """

    SUCCESS_MESSAGE = "OK"

    auth = (JWTSyncAuth(),)

    @classmethod
    def ok(cls, data, message: str | None = None):
        return {
            "success": True,
            "message": message or cls.SUCCESS_MESSAGE,
            "data": data,
        }

    @classmethod
    def fail(cls, error, message: str | None = None, *, status_code=HTTPStatus.BAD_REQUEST):
        """Build an error envelope by hand, to pass to ``APIError``.

        Usage: ``raise APIError(self.fail("Already claimed"), status_code=HTTPStatus.CONFLICT)``.
        """
        envelope = format_error_envelope(error, status_code=status_code)
        if message:
            envelope["message"] = message
        return envelope


#: Alias kept so app code can import the same name under either API framework.
BaseAPIView = BaseController
