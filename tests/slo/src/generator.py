"""Random row generation for the key-value workload."""

import random
import string
from datetime import datetime
from datetime import timezone


def random_string(min_len=20, max_len=40):
    length = random.randint(min_len, max_len)
    return "".join(random.choices(string.ascii_lowercase, k=length))


def make_row(key):
    """Build a KeyValue row dict for the given primary key."""
    return {
        "id": key,
        "payload_str": random_string(),
        "payload_double": random.random(),
        "payload_timestamp": datetime.now(timezone.utc),
    }
