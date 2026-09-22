from dmr import Controller
from dmr.plugins.msgspec import MsgspecSerializer
from dmr.security.jwt.auth import JWTSyncAuth


class BaseController(Controller[MsgspecSerializer]):
    """Base for every controller in this project.

    Endpoints require a valid JWT by default; set ``auth = ()`` on a controller
    to make it public.
    """

    SUCCESS_MESSAGE = "OK"
    ERROR_MESSAGE = "NOT OK"

    auth = (JWTSyncAuth(),)

    @classmethod
    def ok(cls, data, message: str | None = None):
        return {
            "success": True,
            "message": message or cls.SUCCESS_MESSAGE,
            "data": data,
        }

    @classmethod
    def fail(cls, error, message: str | None = None):
        return {
            "success": False,
            "message": message or cls.ERROR_MESSAGE,
            "error": error,
        }


#: Alias kept so app code can import the same name under either API framework.
BaseAPIView = BaseController
