import re


TRACKING_PATTERN = re.compile(r"^CB_(?P<user_id>\d+)_(?P<affiliate_link_id>\d+)$")


def build_tracking_id(user_id: int, affiliate_link_id: int) -> str:
    return f"CB_{user_id}_{affiliate_link_id}"


def parse_tracking_id(tracking_id: str) -> tuple[int, int] | None:
    match = TRACKING_PATTERN.match(tracking_id)
    if not match:
        return None
    return int(match.group("user_id")), int(match.group("affiliate_link_id"))