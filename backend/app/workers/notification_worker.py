from dataclasses import dataclass


@dataclass(frozen=True)
class ZaloNotification:
    zalo_user_id: str
    message: str


def send_zalo_notification(notification: ZaloNotification) -> bool:
    """
    Placeholder worker boundary for Zalo OA notifications.

    Production implementation should call providers/zalo/client.py with the
    configured ZALO_OA_ACCESS_TOKEN and must retry transient failures.
    """
    if not notification.zalo_user_id or not notification.message:
        return False
    return True