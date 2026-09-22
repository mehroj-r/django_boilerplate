from dmr.errors import global_error_handler as dmr_global_error_handler


def global_error_handler(endpoint, controller, exc):
    """Where this project maps its own exception types onto responses.

    The response *shape* lives in core.api.errors. Map your exceptions here,
    then always delegate to dmr's handler so its built-in 4xx handling still
    applies. Re-raising instead (the obvious-looking shortcut) turns every
    validation error and 401 into a 500.
    """
    # if isinstance(exc, MyDomainError):
    #     return controller.to_error(
    #         controller.format_error(str(exc), status_code=HTTPStatus.CONFLICT),
    #         status_code=HTTPStatus.CONFLICT,
    #     )
    return dmr_global_error_handler(endpoint, controller, exc)
