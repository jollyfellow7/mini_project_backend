# -*- coding: utf-8 -*-
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class CleaningMemoryEntity:
    id: UUID
    user_id: str
    room_id: str
    room_name: str
    cleanliness: int
    created_at: datetime
