from datetime import date

from fastapi import APIRouter, Depends, Query
from prisma import Prisma

from app.core.deps import get_current_user, get_db
from app.schemas.common import ErrorResponse, SuccessResponse
from app.schemas.planner import (
    CommentCreateRequest,
    CommentReplyRequest,
    CommentResponse,
    CompletionRateResponse,
    MonthlyResponse,
    PlannerResponse,
    TodayFeedbackResponse,
    WeeklyResponse,
)
from app.schemas.task import TaskResponse
from app.services import planner_service

router = APIRouter(prefix="/api/planner", tags=["Planner"])


@router.get(
    "",
    response_model=SuccessResponse[PlannerResponse],
    summary="날짜별 플래너 조회",
    description="해당 날짜의 할 일 목록, 코멘트, 완수율, 어제 피드백 여부, 오늘 종합 피드백을 종합하여 조회합니다.",
)
async def get_planner(
    date: date = Query(..., examples=["2026-02-03"]),
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    if not current_user.menteeProfile:
        return SuccessResponse(
            data=PlannerResponse(
                date=date, tasks=[], comments=[], completionRate=0.0,
                totalCount=0, completedCount=0,
                hasYesterdayFeedback=False, yesterdayFeedbackDate=None,
                todayFeedback=None,
            )
        )

    result = await planner_service.get_planner(db, current_user.menteeProfile.id, date)

    today_feedback = None
    if result["todayFeedback"]:
        today_feedback = TodayFeedbackResponse(**result["todayFeedback"])

    return SuccessResponse(
        data=PlannerResponse(
            date=result["date"],
            tasks=[TaskResponse.model_validate(t) for t in result["tasks"]],
            comments=[CommentResponse.model_validate(c) for c in result["comments"]],
            completionRate=result["completionRate"],
            totalCount=result["totalCount"],
            completedCount=result["completedCount"],
            hasYesterdayFeedback=result["hasYesterdayFeedback"],
            yesterdayFeedbackDate=result["yesterdayFeedbackDate"],
            todayFeedback=today_feedback,
        )
    )


@router.get(
    "/completion-rate",
    response_model=SuccessResponse[CompletionRateResponse],
    summary="해당일 완수율",
    description="특정 날짜의 전체 할 일 수, 완료 수, 완수율을 조회합니다.",
)
async def get_completion_rate(
    date: date = Query(..., examples=["2026-02-03"]),
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    if not current_user.menteeProfile:
        return SuccessResponse(
            data=CompletionRateResponse(date=date, total=0, completed=0, rate=0.0)
        )

    result = await planner_service.get_completion_rate(
        db, current_user.menteeProfile.id, date
    )
    return SuccessResponse(data=CompletionRateResponse(**result))


@router.get(
    "/weekly",
    response_model=SuccessResponse[WeeklyResponse],
    summary="주간 캘린더",
    description="해당 주(월~일)의 일별 할 일 수, 완료 수, 완수율을 조회합니다.",
)
async def get_weekly(
    weekOf: date = Query(..., description="해당 주의 아무 날짜", examples=["2026-02-03"]),
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    if not current_user.menteeProfile:
        return SuccessResponse(data=WeeklyResponse(weekOf=weekOf, days=[]))

    result = await planner_service.get_weekly(
        db, current_user.menteeProfile.id, weekOf
    )
    return SuccessResponse(data=WeeklyResponse(**result))


@router.get(
    "/monthly",
    response_model=SuccessResponse[MonthlyResponse],
    summary="월간 캘린더",
    description="해당 월의 일별 할 일 수, 완료 수, 완수율을 조회합니다.",
)
async def get_monthly(
    year: int = Query(..., ge=2020, le=2030, examples=[2026]),
    month: int = Query(..., ge=1, le=12, examples=[2]),
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    if not current_user.menteeProfile:
        return SuccessResponse(
            data=MonthlyResponse(year=year, month=month, days=[])
        )

    result = await planner_service.get_monthly(
        db, current_user.menteeProfile.id, year, month
    )
    return SuccessResponse(data=MonthlyResponse(**result))


@router.post(
    "/comments",
    response_model=SuccessResponse[CommentResponse],
    status_code=201,
    summary="코멘트/질문 등록",
    description="해당 날짜에 코멘트나 질문을 등록합니다. 멘티 본인만 가능합니다.",
    responses={
        400: {"model": ErrorResponse, "description": "온보딩 미완료 (COMMENT_001)"},
    },
)
async def create_comment(
    data: CommentCreateRequest,
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    comment = await planner_service.create_comment(db, current_user, data)
    return SuccessResponse(data=CommentResponse.model_validate(comment))


@router.get(
    "/comments",
    response_model=SuccessResponse[list[CommentResponse]],
    summary="코멘트 조회",
    description="해당 날짜의 코멘트와 멘토 답변을 조회합니다. 멘티 본인 또는 담당 멘토가 조회 가능합니다.",
)
async def get_comments(
    date: date = Query(..., examples=["2026-02-03"]),
    menteeId: str | None = Query(default=None, description="멘티 ID (멘토 전용)"),
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    if current_user.role == "MENTEE":
        if not current_user.menteeProfile:
            return SuccessResponse(data=[])
        target_id = current_user.menteeProfile.id
    elif current_user.role == "MENTOR" and menteeId:
        target_id = menteeId
    else:
        return SuccessResponse(data=[])

    comments = await planner_service.get_comments(db, target_id, date)
    return SuccessResponse(
        data=[CommentResponse.model_validate(c) for c in comments]
    )


@router.put(
    "/comments/{commentId}/reply",
    response_model=SuccessResponse[CommentResponse],
    summary="코멘트 답변",
    description="멘토가 멘티의 코멘트에 답변합니다. 담당 멘티의 코멘트만 답변 가능합니다.",
    responses={
        403: {"model": ErrorResponse, "description": "권한 없음 (PERM_001, PERM_002)"},
        404: {"model": ErrorResponse, "description": "코멘트 없음 (COMMENT_002)"},
    },
)
async def reply_comment(
    commentId: str,
    data: CommentReplyRequest,
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    updated = await planner_service.reply_comment(db, current_user, commentId, data)
    return SuccessResponse(data=CommentResponse.model_validate(updated))


@router.get(
    "/yesterday-feedback",
    response_model=SuccessResponse[dict | None],
    summary="어제자 피드백 요약",
    description="어제 날짜의 멘토 피드백을 조회합니다. 없으면 null 반환.",
)
async def get_yesterday_feedback(
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    if not current_user.menteeProfile:
        return SuccessResponse(data=None)

    feedback = await planner_service.get_yesterday_feedback(
        db, current_user.menteeProfile.id
    )
    if not feedback:
        return SuccessResponse(data=None)

    return SuccessResponse(data={
        "id": feedback.id,
        "date": str(feedback.date.date()) if hasattr(feedback.date, 'date') else str(feedback.date),
        "summary": feedback.summary,
        "generalComment": feedback.generalComment,
        "isHighlighted": feedback.isHighlighted,
    })
