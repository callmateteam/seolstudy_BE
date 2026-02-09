from fastapi import HTTPException, status
from prisma import Json, Prisma

from app.schemas.submission import SelfScoreRequest, SubmissionCreateRequest
from app.services.wrong_answer_service import create_wrong_answer_sheets_for_submission


def _normalize_answer(s: str | None) -> str:
    """정답 비교용 정규화: 공백 제거 + 소문자"""
    if s is None:
        return ""
    return s.strip().lower()


async def create_submission(
    db: Prisma, user, task_id: str, data: SubmissionCreateRequest
):
    if not user.menteeProfile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "SUBMIT_001", "message": "온보딩을 먼저 완료해주세요"},
        )

    task = await db.task.find_unique(
        where={"id": task_id},
        include={"problems": True},
    )
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TASK_002", "message": "할 일을 찾을 수 없습니다"},
        )

    if task.menteeId != user.menteeProfile.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PERM_002", "message": "본인의 데이터만 접근 가능합니다"},
        )

    has_problems = data.problemResponses and len(data.problemResponses) > 0

    # TEXT/DRAWING 검증: problemResponses가 없을 때만 기존 검증 적용
    if not has_problems:
        if data.submissionType == "TEXT" and not data.textContent:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "SUBMIT_002", "message": "TEXT 모드에서는 textContent가 필요합니다"},
            )
        if data.submissionType == "DRAWING" and (not data.images or len(data.images) == 0):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "SUBMIT_002", "message": "DRAWING 모드에서는 이미지가 필요합니다"},
            )

    # selfScore 검증
    if data.selfScoreCorrect is not None and data.selfScoreTotal is not None:
        if data.selfScoreCorrect > data.selfScoreTotal:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "SUBMIT_004", "message": "맞은 문제 수가 전체 문제 수보다 클 수 없습니다"},
            )

    submission = await db.tasksubmission.create(
        data={
            "task": {"connect": {"id": task_id}},
            "mentee": {"connect": {"id": user.menteeProfile.id}},
            "submissionType": data.submissionType,
            "textContent": data.textContent,
            "images": data.images or [],
            "selfScoreCorrect": data.selfScoreCorrect,
            "selfScoreTotal": data.selfScoreTotal,
            "wrongQuestions": data.wrongQuestions or [],
            "comment": data.comment,
        }
    )

    # problemResponses 생성
    if has_problems:
        task_problem_ids = {p.id for p in (task.problems or [])}
        for pr in data.problemResponses:
            if pr.problemId not in task_problem_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"code": "SUBMIT_005", "message": f"문제 {pr.problemId}가 이 과제에 속하지 않습니다"},
                )
            pr_data: dict = {
                "submission": {"connect": {"id": submission.id}},
                "problem": {"connect": {"id": pr.problemId}},
                "answer": pr.answer,
                "textNote": pr.textNote,
                "drawingUrl": pr.drawingUrl,
            }
            if pr.highlightData is not None:
                pr_data["highlightData"] = Json(pr.highlightData)
            await db.problemresponse.create(data=pr_data)

    # 자동 채점: correctAnswer가 있는 문제의 정답 비교
    if has_problems and task.problems:
        problem_map = {p.id: p for p in task.problems}
        auto_correct = 0
        auto_total = 0
        wrong_problems = []

        for pr in data.problemResponses:
            problem = problem_map.get(pr.problemId)
            if not problem or not problem.correctAnswer:
                continue

            is_correct = (
                _normalize_answer(pr.answer)
                == _normalize_answer(problem.correctAnswer)
            )
            auto_total += 1
            if is_correct:
                auto_correct += 1
            else:
                wrong_problems.append({
                    "problemId": problem.id,
                    "problemNumber": problem.number,
                    "problemTitle": problem.title,
                    "originalAnswer": pr.answer,
                    "correctAnswer": problem.correctAnswer,
                })

            await db.problemresponse.update_many(
                where={
                    "submissionId": submission.id,
                    "problemId": pr.problemId,
                },
                data={"isCorrect": is_correct},
            )

        if auto_total > 0:
            wrong_numbers = [wp["problemNumber"] for wp in wrong_problems]
            await db.tasksubmission.update(
                where={"id": submission.id},
                data={
                    "selfScoreCorrect": auto_correct,
                    "selfScoreTotal": auto_total,
                    "wrongQuestions": wrong_numbers,
                },
            )

            if wrong_problems:
                await create_wrong_answer_sheets_for_submission(
                    db, submission.id, user.menteeProfile.id, wrong_problems
                )

    # Task 업데이트: status + studyTimeMinutes
    task_update: dict = {"status": "SUBMITTED"}
    if data.studyTimeMinutes is not None:
        task_update["studyTimeMinutes"] = data.studyTimeMinutes
    await db.task.update(where={"id": task_id}, data=task_update)

    # 응답에 problemResponses 포함
    result = await db.tasksubmission.find_unique(
        where={"id": submission.id},
        include={"problemResponses": True},
    )
    return result


async def get_submissions(db: Prisma, task_id: str):
    task = await db.task.find_unique(where={"id": task_id})
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TASK_002", "message": "할 일을 찾을 수 없습니다"},
        )

    return await db.tasksubmission.find_many(
        where={"taskId": task_id},
        order={"submittedAt": "desc"},
        include={"problemResponses": True},
    )


async def update_self_score(
    db: Prisma, user, submission_id: str, data: SelfScoreRequest
):
    submission = await db.tasksubmission.find_unique(where={"id": submission_id})
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SUBMIT_003", "message": "제출 내역을 찾을 수 없습니다"},
        )

    if not user.menteeProfile or submission.menteeId != user.menteeProfile.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PERM_002", "message": "본인의 데이터만 접근 가능합니다"},
        )

    if data.selfScoreCorrect > data.selfScoreTotal:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "SUBMIT_004", "message": "맞은 문제 수가 전체 문제 수보다 클 수 없습니다"},
        )

    updated = await db.tasksubmission.update(
        where={"id": submission_id},
        data={
            "selfScoreCorrect": data.selfScoreCorrect,
            "selfScoreTotal": data.selfScoreTotal,
            "wrongQuestions": data.wrongQuestions,
        },
        include={"problemResponses": True},
    )
    return updated
