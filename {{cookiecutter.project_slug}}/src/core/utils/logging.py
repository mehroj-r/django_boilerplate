import atexit
import copy
import html
import json
import logging
import queue
import threading
import traceback
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)

_SHUTDOWN = object()


class TelegramErrorHandler(logging.Handler):
    """
    A logging handler that sends error logs to a Telegram chat via a bot.
    It uses a background thread and a queue to avoid blocking the request.

    Messages are sent with parse_mode=HTML and every interpolated value is
    escaped, so an exception message containing `<`, `&` or stray Markdown
    characters cannot break the payload (Telegram answers 400 and the alert is
    lost silently).
    """

    #: Telegram rejects messages longer than 4096 characters.
    MAX_MESSAGE_LENGTH = 4000

    ESCAPED_ATTRS = ("user", "method", "path", "ip", "module", "filename", "funcName", "traceback")

    def __init__(self, bot_token, chat_id, level=logging.ERROR, max_queue=100, include_traceback=False):
        super().__init__(level)
        self.api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        self.chat_id = chat_id
        self.include_traceback = include_traceback
        self.enabled = bool(bot_token and chat_id)
        self.queue = queue.Queue(maxsize=max_queue)

        self.worker = threading.Thread(target=self._worker, daemon=True, name="telegram-log")
        self.worker.start()
        atexit.register(self.close)

    def emit(self, record):
        if not self.enabled:
            return
        try:
            # Copy: the console handler shares this record.
            safe = copy.copy(record)
            safe.msg = html.escape(record.getMessage())
            safe.args = ()
            safe.exc_info = None
            safe.exc_text = None

            for attr in self.ESCAPED_ATTRS:
                value = getattr(safe, attr, None)
                if isinstance(value, str):
                    setattr(safe, attr, html.escape(value))

            if not self.include_traceback:
                safe.traceback = "(disabled; set LOGGING_TELEGRAM_INCLUDE_TRACEBACK=True)"

            self.queue.put_nowait(self.format(safe))
        except queue.Full:
            pass  # alerting must never block or crash the request
        except Exception:
            self.handleError(record)

    def _send(self, message: str) -> None:
        payload = json.dumps(
            {
                "chat_id": self.chat_id,
                "text": message[: self.MAX_MESSAGE_LENGTH],
                "parse_mode": "HTML",
            }
        ).encode("utf-8")
        # S310: api_url is a literal https:// endpoint, no user-controlled scheme.
        request = urllib.request.Request(  # noqa: S310
            self.api_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5):  # noqa: S310
            pass

    def _worker(self):
        while True:
            message = self.queue.get()
            try:
                if message is _SHUTDOWN:
                    return
                self._send(message)
            except (urllib.error.URLError, OSError, ValueError) as exc:
                # Never re-enter this handler: log to stderr only.
                print(f"Failed to send log to Telegram: {exc}")  # noqa: T201
            finally:
                self.queue.task_done()

    def close(self):
        """Drain the queue so alerts are not lost when the process exits."""
        if not self.worker.is_alive():
            super().close()
            return
        try:
            self.queue.put_nowait(_SHUTDOWN)
        except queue.Full:
            pass
        self.worker.join(timeout=5)
        super().close()


class RequestContextFilter(logging.Filter):
    """
    Adds request/user/IP/path/method + traceback info to log records.
    """

    def filter(self, record):
        request = getattr(record, "request", None)

        if request is not None:
            user = getattr(request, "user", None)
            record.user = getattr(user, "username", None) or "Anonymous"
            record.method = getattr(request, "method", "-")
            record.path = getattr(request, "path", "-")
            record.ip = self.get_client_ip(request)
        else:
            record.user = "Unknown"
            record.method = "-"
            record.path = "-"
            record.ip = "-"

        if record.exc_info:
            record.traceback = "".join(traceback.format_exception(*record.exc_info))
        else:
            record.traceback = "No traceback"

        return True

    @staticmethod
    def get_client_ip(request) -> str:
        """Prefer the left-most X-Forwarded-For entry when behind a proxy."""
        meta = getattr(request, "META", {})
        forwarded = meta.get("HTTP_X_FORWARDED_FOR")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return meta.get("REMOTE_ADDR", "-")
