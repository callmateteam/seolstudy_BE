import datetime as dt

from pydantic import BaseModel

from app.schemas.mentor import FeedbackItemResponse


class FeedbackDetailResponse(BaseModel):
    id: str
    menteeId: str
    mentorId: str
    date: dt.date
    summary: str | None = None
    isHighlighted: bool
    generalComment: str | None = None
    items: list[FeedbackItemResponse] = []
    mentorName: str | None = None

    model_config = {"from_attributes": True}


class FeedbackListItem(BaseModel):
    id: str
    date: dt.date
    summary: str | None = None
    isHighlighted: bool
    generalComment: str | None = None
    mentorName: str | None = None
    itemCount: int = 0
