"""Full integration test for all 55 API endpoints."""
import io
import sys
import time

from fastapi.testclient import TestClient
from main import app

tokens = {}
ids = {}
ts = int(time.time())

client = TestClient(app)
client.__enter__()


def h(token):
    return {"Authorization": f"Bearer {token}"}


# ===== Phase 1: Auth + Onboarding =====
print("=== Phase 1: Auth + Onboarding ===")

# Signup mentee
r = client.post("/api/auth/signup", json={
    "loginId": f"mentee{ts}", "password": "test1234",
    "name": "멘티1", "phone": "01011111111", "role": "MENTEE"
})
print(f"[Signup mentee] {r.status_code}")
assert r.status_code == 201
tokens["mentee"] = r.json()["data"]["accessToken"]

# Signup mentor
r = client.post("/api/auth/signup", json={
    "loginId": f"mentor{ts}", "password": "test1234",
    "name": "멘토1", "phone": "01022222222", "role": "MENTOR"
})
print(f"[Signup mentor] {r.status_code}")
assert r.status_code == 201
tokens["mentor"] = r.json()["data"]["accessToken"]

# Signup parent
r = client.post("/api/auth/signup", json={
    "loginId": f"parent{ts}", "password": "test1234",
    "name": "학부모1", "phone": "01033333333", "role": "PARENT"
})
print(f"[Signup parent] {r.status_code}")
assert r.status_code == 201
tokens["parent"] = r.json()["data"]["accessToken"]

# Login
r = client.post("/api/auth/login", json={"loginId": f"mentee{ts}", "password": "test1234"})
print(f"[Login] {r.status_code}")
assert r.status_code == 200

# Me
r = client.get("/api/auth/me", headers=h(tokens["mentee"]))
print(f"[Me] {r.status_code} role={r.json()['data']['user']['role']}")
assert r.status_code == 200

# Onboarding mentee
r = client.put("/api/onboarding/mentee", headers=h(tokens["mentee"]), json={
    "school": "테스트고등학교",
    "grade": "HIGH3", "subjects": ["KOREAN", "MATH"],
    "currentGrades": {"KOREAN": 3, "MATH": 4},
    "targetGrades": {"KOREAN": 1, "MATH": 2}
})
print(f"[Onboarding mentee] {r.status_code}")
assert r.status_code == 200

# Get invite code
r = client.get("/api/auth/me", headers=h(tokens["mentee"]))
ids["menteeProfileId"] = r.json()["data"]["profile"]["id"]
ids["inviteCode"] = r.json()["data"]["profile"]["inviteCode"]

# Onboarding mentor
r = client.put("/api/onboarding/mentor", headers=h(tokens["mentor"]), json={
    "university": "서울대", "department": "교육학과",
    "subjects": ["KOREAN", "MATH"], "coachingExperience": True,
    "menteeInviteCode": ids["inviteCode"]
})
print(f"[Onboarding mentor] {r.status_code}")
assert r.status_code == 200

# Get mentor profile id
r = client.get("/api/auth/me", headers=h(tokens["mentor"]))
ids["mentorProfileId"] = r.json()["data"]["profile"]["id"]

# Onboarding parent
r = client.put("/api/onboarding/parent", headers=h(tokens["parent"]), json={
    "inviteCode": ids["inviteCode"]
})
print(f"[Onboarding parent] {r.status_code}")
assert r.status_code == 200

# Logout
r = client.post("/api/auth/logout", headers=h(tokens["mentee"]))
print(f"[Logout] {r.status_code}")
assert r.status_code == 204

# Re-login mentee
r = client.post("/api/auth/login", json={"loginId": f"mentee{ts}", "password": "test1234"})
tokens["mentee"] = r.json()["data"]["accessToken"]

print("--- Phase 1 OK ---\n")

# ===== Phase 2: Mentee Features =====
print("=== Phase 2: Mentee Features ===")

# Create task (mentee)
r = client.post("/api/tasks", headers=h(tokens["mentee"]), json={
    "date": "2026-02-03", "title": "국어 문해력 p.10~15",
    "goal": "독해 연습", "subject": "KOREAN"
})
print(f"[Create task] {r.status_code}")
assert r.status_code == 201
ids["taskId"] = r.json()["data"]["id"]
# Verify default values for new fields
td = r.json()["data"]
assert td["repeat"] == False
assert td["repeatDays"] == []
assert td["targetStudyMinutes"] is None
assert td["memo"] is None
print(f"  -> new fields default OK")

# Create repeat task (mentee) — 2026-02-03 is Tuesday
r = client.post("/api/tasks", headers=h(tokens["mentee"]), json={
    "date": "2026-02-03", "title": "영어 독해 3회차",
    "goal": "독해 연습", "subject": "ENGLISH",
    "repeat": True, "repeatDays": ["MON", "WED", "FRI"],
    "targetStudyMinutes": 90, "memo": "풀이 과정에 집중하기"
})
print(f"[Create repeat task] {r.status_code}")
assert r.status_code == 201
rt = r.json()["data"]
assert rt["repeat"] == True
assert rt["repeatDays"] == ["MON", "WED", "FRI"]
assert rt["targetStudyMinutes"] == 90
assert rt["memo"] == "풀이 과정에 집중하기"
print(f"  -> repeat fields OK")

# Verify repeat tasks created on MON(02-02), WED(02-04), FRI(02-06)
for chk_date in ["2026-02-02", "2026-02-04", "2026-02-06"]:
    r = client.get(f"/api/tasks?menteeId={ids['menteeProfileId']}&date={chk_date}", headers=h(tokens["mentee"]))
    assert r.status_code == 200
    found = [t for t in r.json()["data"] if t["title"] == "영어 독해 3회차"]
    assert len(found) == 1, f"Expected repeat task on {chk_date}"
print(f"  -> repeat dates (MON/WED/FRI) verified")

# Create task (mentor for mentee) — with tags, keyPoints, content, problems
r = client.post(f"/api/tasks?menteeId={ids['menteeProfileId']}", headers=h(tokens["mentor"]), json={
    "date": "2026-02-03", "title": "수학 미적분 p.32~35",
    "goal": "미분 개념", "subject": "MATH",
    "tags": ["수학", "미적분", "미분"],
    "keyPoints": "미분의 정의: lim(h→0) [f(x+h)-f(x)]/h",
    "content": "다음 함수의 도함수를 구하시오.",
    "problems": [
        {"number": 1, "title": "f(x)=x^2의 도함수", "options": [{"label": "1", "text": "2x"}, {"label": "2", "text": "x^2"}], "correctAnswer": "1", "displayOrder": 0},
        {"number": 2, "title": "f(x)=3x+1의 도함수", "correctAnswer": "3", "displayOrder": 1},
        {"number": 3, "title": "f(x)=x^3의 도함수", "correctAnswer": "3x^2", "displayOrder": 2},
    ]
})
print(f"[Create task by mentor] {r.status_code}")
assert r.status_code == 201
mt = r.json()["data"]
ids["mentorTaskId"] = mt["id"]
assert mt["tags"] == ["수학", "미적분", "미분"]
assert mt["keyPoints"] is not None
assert mt["problemCount"] == 3
assert len(mt["problems"]) == 3
assert mt["problems"][0]["number"] == 1
# correctAnswer should not appear in TaskProblemResponse (mentee view)
assert "correctAnswer" not in mt["problems"][0]
print(f"  -> mentor task: tags={mt['tags']} problems={mt['problemCount']}")
ids["problemId1"] = mt["problems"][0]["id"]
ids["problemId2"] = mt["problems"][1]["id"]
ids["problemId3"] = mt["problems"][2]["id"]

# Add problem (mentor)
r = client.post(f"/api/tasks/{ids['mentorTaskId']}/problems", headers=h(tokens["mentor"]), json={
    "number": 4, "title": "f(x)=5의 도함수", "correctAnswer": "0", "displayOrder": 3
})
print(f"[Add problem] {r.status_code}")
assert r.status_code == 201
ids["problemId4"] = r.json()["data"]["id"]
assert r.json()["data"]["correctAnswer"] == "0"  # mentor response includes correctAnswer

# Update problem (mentor)
r = client.put(f"/api/tasks/{ids['mentorTaskId']}/problems/{ids['problemId4']}", headers=h(tokens["mentor"]), json={
    "title": "f(x)=5의 도함수 (수정됨)"
})
print(f"[Update problem] {r.status_code}")
assert r.status_code == 200
assert r.json()["data"]["title"] == "f(x)=5의 도함수 (수정됨)"

# Delete problem (mentor)
r = client.delete(f"/api/tasks/{ids['mentorTaskId']}/problems/{ids['problemId4']}", headers=h(tokens["mentor"]))
print(f"[Delete problem] {r.status_code}")
assert r.status_code == 204

# Bookmark toggle (mentee)
r = client.patch(f"/api/tasks/{ids['mentorTaskId']}/bookmark", headers=h(tokens["mentee"]), json={"isBookmarked": True})
print(f"[Bookmark on] {r.status_code} bookmarked={r.json()['data']['isBookmarked']}")
assert r.status_code == 200
assert r.json()["data"]["isBookmarked"] == True

r = client.patch(f"/api/tasks/{ids['mentorTaskId']}/bookmark", headers=h(tokens["mentee"]), json={"isBookmarked": False})
print(f"[Bookmark off] {r.status_code} bookmarked={r.json()['data']['isBookmarked']}")
assert r.status_code == 200
assert r.json()["data"]["isBookmarked"] == False

# Get tasks
r = client.get(f"/api/tasks?menteeId={ids['menteeProfileId']}&date=2026-02-03", headers=h(tokens["mentee"]))
print(f"[Get tasks] {r.status_code} count={len(r.json()['data'])}")
assert r.status_code == 200

# Get task detail (mentor task with problems)
r = client.get(f"/api/tasks/{ids['mentorTaskId']}", headers=h(tokens["mentee"]))
print(f"[Task detail] {r.status_code} problems={len(r.json()['data']['problems'])}")
assert r.status_code == 200
assert r.json()["data"]["problemCount"] == 3  # 4 added - 1 deleted = 3

# Update task
r = client.put(f"/api/tasks/{ids['taskId']}", headers=h(tokens["mentee"]), json={"goal": "독해 완벽 정리"})
print(f"[Update task] {r.status_code}")
assert r.status_code == 200

# Study time
r = client.patch(f"/api/tasks/{ids['taskId']}/study-time", headers=h(tokens["mentee"]), json={"minutes": 45})
print(f"[Study time] {r.status_code}")
assert r.status_code == 200

# Submit (TEXT) — simple task
r = client.post(f"/api/tasks/{ids['taskId']}/submissions", headers=h(tokens["mentee"]), json={
    "submissionType": "TEXT", "textContent": "풀이 내용입니다..."
})
print(f"[Submit TEXT] {r.status_code}")
assert r.status_code == 201
ids["submissionId"] = r.json()["data"]["id"]

# Submit (mentor task with problemResponses + selfScore + studyTime + comment)
r = client.post(f"/api/tasks/{ids['mentorTaskId']}/submissions", headers=h(tokens["mentee"]), json={
    "submissionType": "TEXT",
    "studyTimeMinutes": 65,
    "selfScoreCorrect": 2,
    "selfScoreTotal": 3,
    "wrongQuestions": [3],
    "comment": "3번 문제가 어려웠어요",
    "problemResponses": [
        {"problemId": ids["problemId1"], "answer": "1", "textNote": "2x가 맞다"},
        {"problemId": ids["problemId2"], "answer": "3"},
        {"problemId": ids["problemId3"], "answer": "2x^2", "textNote": "틀렸다", "highlightData": {"ranges": [{"start": 0, "end": 5}]}},
    ]
})
print(f"[Submit with problems] {r.status_code}")
assert r.status_code == 201
sub = r.json()["data"]
assert sub["comment"] == "3번 문제가 어려웠어요"
assert sub["selfScoreCorrect"] == 2
assert sub["selfScoreTotal"] == 3
assert len(sub["problemResponses"]) == 3
assert sub["problemResponses"][0]["answer"] == "1"
print(f"  -> responses={len(sub['problemResponses'])} selfScore={sub['selfScoreCorrect']}/{sub['selfScoreTotal']}")
ids["mentorSubmissionId"] = sub["id"]

# Verify task status updated to SUBMITTED and studyTimeMinutes saved
r = client.get(f"/api/tasks/{ids['mentorTaskId']}", headers=h(tokens["mentee"]))
assert r.status_code == 200
assert r.json()["data"]["status"] == "SUBMITTED"
assert r.json()["data"]["studyTimeMinutes"] == 65
print(f"  -> task status=SUBMITTED studyTime=65min")

# Get submissions (includes problemResponses)
r = client.get(f"/api/tasks/{ids['taskId']}/submissions", headers=h(tokens["mentee"]))
print(f"[Get submissions] {r.status_code} count={len(r.json()['data'])}")
assert r.status_code == 200

# Self score (simple task)
r = client.put(f"/api/submissions/{ids['submissionId']}/self-score", headers=h(tokens["mentee"]), json={
    "selfScoreCorrect": 8, "selfScoreTotal": 10, "wrongQuestions": [3, 7]
})
print(f"[Self score] {r.status_code}")
assert r.status_code == 200

# Planner (enhanced)
r = client.get("/api/planner?date=2026-02-03", headers=h(tokens["mentee"]))
pd = r.json()["data"]
print(f"[Planner] {r.status_code} tasks={len(pd['tasks'])} total={pd['totalCount']} completed={pd['completedCount']} yesterdayFb={pd['hasYesterdayFeedback']}")
assert r.status_code == 200
assert "totalCount" in pd
assert "completedCount" in pd
assert "hasYesterdayFeedback" in pd

# Completion rate
r = client.get("/api/planner/completion-rate?date=2026-02-03", headers=h(tokens["mentee"]))
print(f"[Completion rate] {r.status_code} rate={r.json()['data']['rate']}")
assert r.status_code == 200

# Weekly
r = client.get("/api/planner/weekly?weekOf=2026-02-03", headers=h(tokens["mentee"]))
print(f"[Weekly] {r.status_code} days={len(r.json()['data']['days'])}")
assert r.status_code == 200

# Monthly
r = client.get("/api/planner/monthly?year=2026&month=2", headers=h(tokens["mentee"]))
md = r.json()["data"]
print(f"[Monthly] {r.status_code} year={md['year']} month={md['month']} days={len(md['days'])}")
assert r.status_code == 200
assert md["year"] == 2026
assert md["month"] == 2
assert len(md["days"]) == 28  # Feb 2026

# Create comment
r = client.post("/api/planner/comments", headers=h(tokens["mentee"]), json={
    "date": "2026-02-03", "content": "오늘 국어가 어려웠어요"
})
print(f"[Create comment] {r.status_code}")
assert r.status_code == 201
ids["commentId"] = r.json()["data"]["id"]

# Mentor reply to comment
r = client.put(f"/api/planner/comments/{ids['commentId']}/reply", headers=h(tokens["mentor"]), json={
    "reply": "국어 지문 분석 방법을 다시 확인해보세요"
})
print(f"[Reply comment] {r.status_code} reply={r.json()['data']['mentorReply'] is not None}")
assert r.status_code == 200
assert r.json()["data"]["mentorReply"] == "국어 지문 분석 방법을 다시 확인해보세요"

# Get comments (with reply)
r = client.get(f"/api/planner/comments?date=2026-02-03&menteeId={ids['menteeProfileId']}", headers=h(tokens["mentee"]))
print(f"[Get comments] {r.status_code} count={len(r.json()['data'])}")
assert r.status_code == 200
assert r.json()["data"][0]["mentorReply"] is not None

# Yesterday feedback
r = client.get("/api/planner/yesterday-feedback", headers=h(tokens["mentee"]))
print(f"[Yesterday feedback] {r.status_code}")
assert r.status_code == 200

print("--- Phase 2 OK ---\n")

# ===== Phase 3: Mentor Features =====
print("=== Phase 3: Mentor Features ===")

# Dashboard
r = client.get("/api/mentor/dashboard", headers=h(tokens["mentor"]))
print(f"[Dashboard] {r.status_code}")
assert r.status_code == 200

# Mentees
r = client.get("/api/mentor/mentees", headers=h(tokens["mentor"]))
print(f"[Mentees] {r.status_code} count={len(r.json()['data'])}")
assert r.status_code == 200

# Mentee detail
r = client.get(f"/api/mentor/mentees/{ids['menteeProfileId']}", headers=h(tokens["mentor"]))
print(f"[Mentee detail] {r.status_code}")
assert r.status_code == 200

# Review queue
r = client.get("/api/mentor/review-queue", headers=h(tokens["mentor"]))
print(f"[Review queue] {r.status_code} count={len(r.json()['data'])}")
assert r.status_code == 200

# AI Analysis: trigger
r = client.post(f"/api/analysis/{ids['submissionId']}/trigger", headers=h(tokens["mentor"]))
print(f"[Analysis trigger] {r.status_code} status={r.json()['data']['status']}")
assert r.status_code == 201
ids["analysisId"] = r.json()["data"]["analysisId"]

# Wait for background analysis
time.sleep(3)

# Analysis status
r = client.get(f"/api/analysis/{ids['submissionId']}/status", headers=h(tokens["mentor"]))
print(f"[Analysis status] {r.status_code} status={r.json()['data']['status']}")
assert r.status_code == 200

# Analysis result
r = client.get(f"/api/analysis/{ids['submissionId']}", headers=h(tokens["mentor"]))
print(f"[Analysis result] {r.status_code} signal={r.json()['data'].get('signalLight')}")
assert r.status_code == 200

# Judgment confirm
r = client.post(f"/api/mentor/judgments/{ids['analysisId']}/confirm", headers=h(tokens["mentor"]))
print(f"[Judgment confirm] {r.status_code}")
assert r.status_code == 201
ids["judgmentId"] = r.json()["data"]["id"]

# Judgment get
r = client.get(f"/api/mentor/judgments/{ids['analysisId']}", headers=h(tokens["mentor"]))
print(f"[Judgment get] {r.status_code}")
assert r.status_code == 200

# Coaching detail
r = client.get(f"/api/coaching/{ids['submissionId']}", headers=h(tokens["mentor"]))
print(f"[Coaching detail] {r.status_code}")
assert r.status_code == 200

# AI draft
r = client.get(f"/api/coaching/{ids['submissionId']}/ai-draft", headers=h(tokens["mentor"]))
print(f"[AI draft] {r.status_code}")
assert r.status_code == 200

# Materials: create
r = client.post("/api/materials", headers=h(tokens["mentor"]), json={
    "title": "국어 문해력 기본 학습지",
    "type": "PDF", "subject": "KOREAN",
    "abilityTags": ["문해력", "독해력"],
    "difficulty": 3, "contentUrl": "https://example.com/material.pdf"
})
print(f"[Material create] {r.status_code}")
assert r.status_code == 201
ids["materialId"] = r.json()["data"]["id"]

# Materials: list
r = client.get("/api/materials?subject=KOREAN", headers=h(tokens["mentor"]))
print(f"[Material list] {r.status_code} count={len(r.json()['data'])}")
assert r.status_code == 200

# Materials: detail
r = client.get(f"/api/materials/{ids['materialId']}", headers=h(tokens["mentor"]))
print(f"[Material detail] {r.status_code}")
assert r.status_code == 200

# Materials: download (redirect)
r = client.get(f"/api/materials/{ids['materialId']}/download", headers=h(tokens["mentor"]), follow_redirects=False)
print(f"[Material download] {r.status_code}")
assert r.status_code == 307

# Recommendations
r = client.get(f"/api/coaching/{ids['submissionId']}/recommendations", headers=h(tokens["mentor"]))
print(f"[Recommendations] {r.status_code} count={len(r.json()['data']['recommendations'])}")
assert r.status_code == 200

# Assign material
r = client.post("/api/coaching/assign-material", headers=h(tokens["mentor"]), json={
    "menteeId": ids["menteeProfileId"],
    "materialId": ids["materialId"],
    "date": "2026-02-04"
})
print(f"[Assign material] {r.status_code}")
assert r.status_code == 201

# Feedback create
r = client.post("/api/mentor/feedback", headers=h(tokens["mentor"]), json={
    "menteeId": ids["menteeProfileId"],
    "date": "2026-02-03",
    "items": [{"taskId": ids["taskId"], "detail": "독해력이 많이 향상되었습니다"}],
    "summary": "국어 학습 양호",
    "isHighlighted": True,
    "generalComment": "이 조자로 계속 열심히 하세요"
})
print(f"[Feedback create] {r.status_code}")
assert r.status_code == 201
ids["feedbackId"] = r.json()["data"]["id"]

# --- Extended Feedback Data ---
print("=== Extended Feedback Data ===")

# Create tasks for 2026-02-04
r = client.post(f"/api/tasks?menteeId={ids['menteeProfileId']}", headers=h(tokens["mentor"]), json={
    "date": "2026-02-04", "title": "국어 비문학 독해 연습",
    "goal": "추론 능력 향상", "subject": "KOREAN",
    "tags": ["국어", "비문학", "추론"],
})
assert r.status_code == 201
ids["task_ko_0204"] = r.json()["data"]["id"]

r = client.post(f"/api/tasks?menteeId={ids['menteeProfileId']}", headers=h(tokens["mentor"]), json={
    "date": "2026-02-04", "title": "영어 문법 복습",
    "goal": "관계대명사 정리", "subject": "ENGLISH",
    "tags": ["영어", "문법"],
})
assert r.status_code == 201
ids["task_en_0204"] = r.json()["data"]["id"]

# Submit tasks on 2026-02-04
r = client.post(f"/api/tasks/{ids['task_ko_0204']}/submissions", headers=h(tokens["mentee"]), json={
    "submissionType": "TEXT", "textContent": "비문학 지문을 분석하고 핵심 내용을 정리했습니다.",
    "studyTimeMinutes": 50,
    "comment": "지문이 길어서 시간이 좀 걸렸어요"
})
assert r.status_code == 201

r = client.post(f"/api/tasks/{ids['task_en_0204']}/submissions", headers=h(tokens["mentee"]), json={
    "submissionType": "TEXT", "textContent": "관계대명사 who, which, that 용법 정리 완료",
    "studyTimeMinutes": 35,
    "comment": "which와 that의 차이가 헷갈려요"
})
assert r.status_code == 201

# Feedback for 02-03: 수학 task (멘토 출제 과제)
r = client.post("/api/mentor/feedback", headers=h(tokens["mentor"]), json={
    "menteeId": ids["menteeProfileId"],
    "date": "2026-02-03",
    "items": [
        {"taskId": ids["mentorTaskId"], "detail": "미분 개념을 잘 이해하고 있습니다. 3번 문제의 풀이 과정을 더 자세히 써보세요."},
    ],
    "summary": "수학 학습 우수",
    "generalComment": "수학 개념 이해도가 높아지고 있어요. 풀이 과정 서술에 조금 더 신경 쓰면 좋겠습니다."
})
assert r.status_code == 201
ids["feedbackId_math_0203"] = r.json()["data"]["id"]

# Feedback for 02-04: 국어+영어
r = client.post("/api/mentor/feedback", headers=h(tokens["mentor"]), json={
    "menteeId": ids["menteeProfileId"],
    "date": "2026-02-04",
    "items": [
        {"taskId": ids["task_ko_0204"], "detail": "비문학 독해 분석이 정확해졌습니다. 핵심 문장 밑줄 긋는 습관을 들이면 더 좋아질 거예요."},
        {"taskId": ids["task_en_0204"], "detail": "관계대명사 용법 정리를 잘했어요. 실전 문제에서 적용 연습을 해보세요."},
    ],
    "summary": "국어·영어 전반적으로 양호",
    "isHighlighted": True,
    "generalComment": "오늘 두 과목 모두 열심히 했습니다. 내일은 수학도 함께 공부해봐요!"
})
assert r.status_code == 201
ids["feedbackId_0204"] = r.json()["data"]["id"]
assert len(r.json()["data"]["items"]) == 2

# Create tasks for 2026-02-05
r = client.post(f"/api/tasks?menteeId={ids['menteeProfileId']}", headers=h(tokens["mentor"]), json={
    "date": "2026-02-05", "title": "수학 적분 기초",
    "goal": "부정적분 연습", "subject": "MATH",
    "tags": ["수학", "적분"],
    "content": "부정적분의 기본 공식을 활용하여 문제를 풀어보세요.",
    "problems": [
        {"number": 1, "title": "∫2x dx = ?", "correctAnswer": "x^2 + C", "displayOrder": 0},
        {"number": 2, "title": "∫3x^2 dx = ?", "correctAnswer": "x^3 + C", "displayOrder": 1},
    ]
})
assert r.status_code == 201
ids["task_math_0205"] = r.json()["data"]["id"]

r = client.post(f"/api/tasks?menteeId={ids['menteeProfileId']}", headers=h(tokens["mentor"]), json={
    "date": "2026-02-05", "title": "국어 화법과 작문",
    "goal": "토론 구조 분석", "subject": "KOREAN",
    "tags": ["국어", "화법과작문"],
})
assert r.status_code == 201
ids["task_ko_0205"] = r.json()["data"]["id"]

# Submit tasks on 2026-02-05
r = client.post(f"/api/tasks/{ids['task_math_0205']}/submissions", headers=h(tokens["mentee"]), json={
    "submissionType": "TEXT", "textContent": "적분 문제 풀이 완료",
    "studyTimeMinutes": 40,
    "comment": "적분 상수 C를 잊지 않도록 주의해야겠어요"
})
assert r.status_code == 201

r = client.post(f"/api/tasks/{ids['task_ko_0205']}/submissions", headers=h(tokens["mentee"]), json={
    "submissionType": "TEXT", "textContent": "토론 구조 분석 - 주장, 근거, 반론 정리",
    "studyTimeMinutes": 30,
})
assert r.status_code == 201

# Feedback for 02-05: 수학+국어
r = client.post("/api/mentor/feedback", headers=h(tokens["mentor"]), json={
    "menteeId": ids["menteeProfileId"],
    "date": "2026-02-05",
    "items": [
        {"taskId": ids["task_math_0205"], "detail": "적분 기초가 탄탄해지고 있어요. 적분 상수 C 잊지 않은 점이 좋습니다."},
        {"taskId": ids["task_ko_0205"], "detail": "토론 구조 분석이 체계적입니다. 반론을 더 구체적으로 써보세요."},
    ],
    "summary": "수학·국어 학습 우수",
    "isHighlighted": False,
    "generalComment": "수학 적분과 국어 화법 모두 꼼꼼하게 학습했습니다. 이 조자로 꾸준히 하면 실력이 많이 오를 거예요."
})
assert r.status_code == 201
ids["feedbackId_0205"] = r.json()["data"]["id"]
assert len(r.json()["data"]["items"]) == 2

print(f"[Extended feedback] 3 additional feedbacks created")
print(f"  -> 02-03: 수학 피드백 (미분 개념 피드백)")
print(f"  -> 02-04: 국어+영어 피드백 (2 items, highlighted)")
print(f"  -> 02-05: 수학+국어 피드백 (2 items, 적분+화법)")

print("--- Phase 3 OK ---\n")

# ===== Feedback Query (Mentee side) =====
print("=== Feedback Query ===")

# By date: 02-03 (2 feedbacks: 국어 + 수학)
r = client.get(f"/api/feedback?menteeId={ids['menteeProfileId']}&date=2026-02-03", headers=h(tokens["mentee"]))
fb_0203 = r.json()["data"]
print(f"[Feedback by date 02-03] {r.status_code} count={len(fb_0203)}")
assert r.status_code == 200
assert len(fb_0203) >= 2

# By date: 02-04 (1 feedback with 2 items)
r = client.get(f"/api/feedback?menteeId={ids['menteeProfileId']}&date=2026-02-04", headers=h(tokens["mentee"]))
fb_0204 = r.json()["data"]
print(f"[Feedback by date 02-04] {r.status_code} count={len(fb_0204)}")
assert r.status_code == 200
assert len(fb_0204) >= 1

# By date: 02-05 (1 feedback with 2 items)
r = client.get(f"/api/feedback?menteeId={ids['menteeProfileId']}&date=2026-02-05", headers=h(tokens["mentee"]))
fb_0205 = r.json()["data"]
print(f"[Feedback by date 02-05] {r.status_code} count={len(fb_0205)}")
assert r.status_code == 200
assert len(fb_0205) >= 1

# By subject: KOREAN (should have feedbacks from 02-03, 02-04, 02-05)
r = client.get(f"/api/feedback/by-subject?menteeId={ids['menteeProfileId']}&subject=KOREAN", headers=h(tokens["mentee"]))
fbs_ko = r.json()["data"]
print(f"[Feedback by subject KOREAN] {r.status_code} count={len(fbs_ko)}")
assert r.status_code == 200
assert len(fbs_ko) >= 1
fb = fbs_ko[0]
assert "items" in fb
assert len(fb["items"]) >= 1
item = fb["items"][0]
assert item["detail"] is not None
print(f"  -> items[0] taskTitle={item['taskTitle']} detail={item['detail'][:30]}...")

# By subject: MATH (should have feedbacks from 02-03, 02-05)
r = client.get(f"/api/feedback/by-subject?menteeId={ids['menteeProfileId']}&subject=MATH", headers=h(tokens["mentee"]))
fbs_math = r.json()["data"]
print(f"[Feedback by subject MATH] {r.status_code} count={len(fbs_math)}")
assert r.status_code == 200
assert len(fbs_math) >= 1
math_items = [it for fb in fbs_math for it in fb.get("items", [])]
print(f"  -> total MATH items: {len(math_items)}")

# By subject: ENGLISH (should have feedback from 02-04)
r = client.get(f"/api/feedback/by-subject?menteeId={ids['menteeProfileId']}&subject=ENGLISH", headers=h(tokens["mentee"]))
fbs_en = r.json()["data"]
print(f"[Feedback by subject ENGLISH] {r.status_code} count={len(fbs_en)}")
assert r.status_code == 200
assert len(fbs_en) >= 1
en_items = [it for fb in fbs_en for it in fb.get("items", [])]
assert any(it["detail"] == "관계대명사 용법 정리를 잘했어요. 실전 문제에서 적용 연습을 해보세요." for it in en_items)
print(f"  -> total ENGLISH items: {len(en_items)}")

# Detail: 02-04 feedback (2 items, highlighted)
r = client.get(f"/api/feedback/{ids['feedbackId_0204']}", headers=h(tokens["mentee"]))
print(f"[Feedback detail 02-04] {r.status_code}")
assert r.status_code == 200
fb_detail = r.json()["data"]
assert fb_detail["isHighlighted"] == True
assert fb_detail["generalComment"] == "오늘 두 과목 모두 열심히 했습니다. 내일은 수학도 함께 공부해봐요!"
assert len(fb_detail["items"]) == 2
print(f"  -> highlighted={fb_detail['isHighlighted']} items={len(fb_detail['items'])} comment={fb_detail['generalComment'][:20]}...")

# Detail: 02-05 feedback (2 items, not highlighted)
r = client.get(f"/api/feedback/{ids['feedbackId_0205']}", headers=h(tokens["mentee"]))
print(f"[Feedback detail 02-05] {r.status_code}")
assert r.status_code == 200
fb_detail2 = r.json()["data"]
assert fb_detail2["isHighlighted"] == False
assert len(fb_detail2["items"]) == 2
print(f"  -> highlighted={fb_detail2['isHighlighted']} items={len(fb_detail2['items'])} summary={fb_detail2['summary']}")

print("--- Feedback Query OK ---\n")

# ===== Wrong Answers =====
print("=== Wrong Answers ===")

# Get wrong answer sheets (empty initially)
r = client.get("/api/wrong-answers", headers=h(tokens["mentee"]))
print(f"[Wrong answers list] {r.status_code} count={len(r.json()['data'])}")
assert r.status_code == 200

print("--- Wrong Answers OK ---\n")

# ===== Phase 4: Parent =====
print("=== Phase 4: Parent ===")

r = client.get("/api/parent/dashboard", headers=h(tokens["parent"]))
print(f"[Parent dashboard] {r.status_code}")
assert r.status_code == 200

r = client.get("/api/parent/mentee-status", headers=h(tokens["parent"]))
print(f"[Mentee status] {r.status_code}")
assert r.status_code == 200

r = client.get("/api/parent/mentor-info", headers=h(tokens["parent"]))
print(f"[Mentor info] {r.status_code}")
assert r.status_code == 200

print("--- Phase 4 OK ---\n")

# ===== Uploads =====
print("=== Uploads ===")

img_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50000
r = client.post("/api/uploads/image", headers=h(tokens["mentee"]),
    files={"file": ("test.png", io.BytesIO(img_data), "image/png")})
print(f"[Upload image] {r.status_code}")
assert r.status_code == 201

pdf_data = b"%PDF-1.4 " + b"\x00" * 1000
r = client.post("/api/uploads/pdf", headers=h(tokens["mentor"]),
    files={"file": ("test.pdf", io.BytesIO(pdf_data), "application/pdf")})
print(f"[Upload PDF] {r.status_code}")
assert r.status_code == 201

r = client.post("/api/uploads/validate-image", headers=h(tokens["mentee"]),
    files={"file": ("test.png", io.BytesIO(img_data), "image/png")})
print(f"[Validate image] {r.status_code} valid={r.json()['data']['valid']}")
assert r.status_code == 200

# Study photo upload (with OCR validation)
# Create a real-ish PNG image via Pillow for OCR check
from PIL import Image as PILImage
study_img = PILImage.new("RGB", (800, 600), color=(255, 255, 255))
# Draw some contrast (simulate writing on white paper)
for x in range(100, 700):
    for y in range(100, 110):
        study_img.putpixel((x, y), (0, 0, 0))
buf = io.BytesIO()
study_img.save(buf, format="PNG")
study_img_data = buf.getvalue()

r = client.post("/api/uploads/study-photo", headers=h(tokens["mentee"]),
    files={"file": ("study.png", io.BytesIO(study_img_data), "image/png")})
print(f"[Study photo] {r.status_code} ocrReady={r.json()['data']['ocrReady']} msg={r.json()['data']['ocrMessage']}")
assert r.status_code == 201
sp = r.json()["data"]
assert "url" in sp
assert "presignedUrl" in sp
assert "ocrReady" in sp
assert "ocrMessage" in sp

# Presigned URL
r = client.post("/api/uploads/presigned-url", headers=h(tokens["mentee"]),
    json={"url": sp["url"]})
print(f"[Presigned URL] {r.status_code} expiresIn={r.json()['data']['expiresIn']}")
assert r.status_code == 200
assert r.json()["data"]["expiresIn"] == 3600
assert "presignedUrl" in r.json()["data"]

print("--- Uploads OK ---\n")

# ===== Settings =====
print("=== Settings ===")

r = client.get("/api/settings/profile", headers=h(tokens["mentee"]))
print(f"[Get profile] {r.status_code} name={r.json()['data']['name']}")
assert r.status_code == 200

r = client.put("/api/settings/profile", headers=h(tokens["mentee"]), json={
    "nickname": "공부왕"
})
print(f"[Update profile] {r.status_code} nickname={r.json()['data']['nickname']}")
assert r.status_code == 200

r = client.put("/api/settings/mentee", headers=h(tokens["mentee"]), json={
    "targetGrades": {"KOREAN": 1, "MATH": 1}
})
print(f"[Mentee settings] {r.status_code}")
assert r.status_code == 200

r = client.put("/api/settings/mentor", headers=h(tokens["mentor"]), json={
    "subjects": ["KOREAN", "ENGLISH", "MATH"]
})
print(f"[Mentor settings] {r.status_code}")
assert r.status_code == 200

print("--- Settings OK ---\n")

# ===== My Page =====
print("=== My Page ===")

# Get my page (mentee)
r = client.get("/api/my", headers=h(tokens["mentee"]))
print(f"[My page mentee] {r.status_code} role={r.json()['data']['role']}")
assert r.status_code == 200
my = r.json()["data"]
assert my["role"] == "MENTEE"
assert my["avatar"] == 1  # 기본 아바타
assert my["school"] == "테스트고등학교"
assert my["grade"] == "HIGH3"
assert "subjectStats" in my
assert "activitySummary" in my
assert my["mentor"] is not None
print(f"  -> avatar: {my['avatar']}")
print(f"  -> mentor: {my['mentor']['name']} ({my['mentor']['university']} {my['mentor']['department']})")
print(f"  -> subjects: {my['subjects']}")
print(f"  -> subjectStats: {len(my['subjectStats'])} subjects")
for ss in my["subjectStats"]:
    print(f"     {ss['subject']}: {ss['completedTasks']}/{ss['totalTasks']} ({ss['completionRate']}%)")
act = my['activitySummary']
print(f"  -> activity: {act['activeDays']}days, streak={act['consecutiveDays']}, {act['totalCompletedTasks']}tasks, {act['totalFeedbacks']}feedbacks, {act['overallCompletionRate']}%")

# Update my page (name, school, avatar)
r = client.patch("/api/my", headers=h(tokens["mentee"]), json={
    "name": "수정된멘티",
    "school": "수정고등학교",
    "avatar": 3
})
print(f"[Update my page] {r.status_code} name={r.json()['data']['name']} school={r.json()['data']['school']} avatar={r.json()['data']['avatar']}")
assert r.status_code == 200
assert r.json()["data"]["name"] == "수정된멘티"
assert r.json()["data"]["school"] == "수정고등학교"
assert r.json()["data"]["avatar"] == 3

# Get my page (mentor) - with activity summary
r = client.get("/api/my", headers=h(tokens["mentor"]))
print(f"[My page mentor] {r.status_code} role={r.json()['data']['role']}")
assert r.status_code == 200
mentor_my = r.json()["data"]
assert mentor_my["role"] == "MENTOR"
assert mentor_my["avatar"] == 1
assert mentor_my["university"] == "서울대"
assert mentor_my["department"] == "교육학과"
assert "activitySummary" in mentor_my
assert mentor_my["activitySummary"]["totalFeedbacks"] >= 0
print(f"  -> avatar: {mentor_my['avatar']}")
print(f"  -> university: {mentor_my['university']} {mentor_my['department']}")
print(f"  -> subjects: {mentor_my['subjects']}")
mentor_act = mentor_my['activitySummary']
print(f"  -> activity: {mentor_act['activeDays']}days, streak={mentor_act['consecutiveDays']}, {mentor_act['totalFeedbacks']}feedbacks")

# Update mentor avatar
r = client.patch("/api/my", headers=h(tokens["mentor"]), json={"avatar": 5})
assert r.status_code == 200
assert r.json()["data"]["avatar"] == 5
print(f"[Update mentor avatar] {r.status_code} avatar={r.json()['data']['avatar']}")

# Get my page (parent)
r = client.get("/api/my", headers=h(tokens["parent"]))
print(f"[My page parent] {r.status_code} role={r.json()['data']['role']}")
assert r.status_code == 200
assert r.json()["data"]["role"] == "PARENT"
assert r.json()["data"]["avatar"] == 1

print("--- My Page OK ---\n")

# ===== Coaching Center (코칭센터) =====
print("=== Coaching Center ===")

# Get coaching session
r = client.get(f"/api/coaching/session?menteeId={ids['menteeProfileId']}&date=2026-02-03", headers=h(tokens["mentor"]))
print(f"[Coaching session] {r.status_code}")
assert r.status_code == 200
session = r.json()["data"]
assert session["mentee"]["id"] == ids["menteeProfileId"]
assert session["date"] == "2026-02-03"
assert len(session["tasks"]) >= 1
print(f"  -> mentee: {session['mentee']['name']}")
print(f"  -> tasks: {len(session['tasks'])}")
for t in session["tasks"][:2]:
    print(f"     - {t['title']} ({t['status']})")
    if t["submission"]:
        print(f"       submission: comment={t['submission'].get('comment')}")
    if t["analysis"]:
        print(f"       analysis: score={t['analysis']['densityScore']} signal={t['analysis']['signalLight']}")
        if t["analysis"].get("detailedAnalysis"):
            print(f"       detailedAnalysis: {t['analysis']['detailedAnalysis'][:50]}...")
    if t["recommendedMaterials"]:
        print(f"       recommended: {len(t['recommendedMaterials'])} materials")

# Save task feedback
r = client.post("/api/coaching/task-feedback", headers=h(tokens["mentor"]), json={
    "taskId": ids["taskId"],
    "detail": "독해력이 향상되고 있습니다. 지문 분석 시 핵심 문장에 밑줄을 긋는 습관을 들이세요."
})
print(f"[Task feedback] {r.status_code}")
assert r.status_code == 201
assert r.json()["data"]["taskId"] == ids["taskId"]
print(f"  -> feedbackItemId: {r.json()['data']['feedbackItemId']}")

# Save daily summary
r = client.post("/api/coaching/daily-summary", headers=h(tokens["mentor"]), json={
    "menteeId": ids["menteeProfileId"],
    "date": "2026-02-03",
    "generalComment": "오늘 학습 잘 진행되었습니다. 국어 독해 실력이 향상되고 있어요!"
})
print(f"[Daily summary] {r.status_code}")
assert r.status_code == 201
assert r.json()["data"]["generalComment"] == "오늘 학습 잘 진행되었습니다. 국어 독해 실력이 향상되고 있어요!"
print(f"  -> feedbackId: {r.json()['data']['feedbackId']}")

# Verify session now includes saved feedback
r = client.get(f"/api/coaching/session?menteeId={ids['menteeProfileId']}&date=2026-02-03", headers=h(tokens["mentor"]))
assert r.status_code == 200
session2 = r.json()["data"]
assert session2["dailySummary"] == "오늘 학습 잘 진행되었습니다. 국어 독해 실력이 향상되고 있어요!"
# Find task with detailFeedback
task_with_fb = next((t for t in session2["tasks"] if t["id"] == ids["taskId"]), None)
assert task_with_fb is not None
assert task_with_fb["detailFeedback"] is not None
print(f"[Session with feedback] verified dailySummary and detailFeedback")

print("--- Coaching Center OK ---\n")

# ===== Lessons (학습관리) =====
print("=== Lessons ===")

# Get ability tags
r = client.get("/api/mentor/lessons/ability-tags?subject=KOREAN", headers=h(tokens["mentor"]))
print(f"[Ability tags KOREAN] {r.status_code} tags={r.json()['data']['tags']}")
assert r.status_code == 200
assert len(r.json()["data"]["tags"]) == 5

# Get all ability tags
r = client.get("/api/mentor/lessons/ability-tags/all", headers=h(tokens["mentor"]))
print(f"[All ability tags] {r.status_code} subjects={list(r.json()['data'].keys())}")
assert r.status_code == 200
assert "KOREAN" in r.json()["data"]
assert "ENGLISH" in r.json()["data"]
assert "MATH" in r.json()["data"]

# Create lesson (with problems, content, targetStudyMinutes)
from datetime import date
today = date.today().isoformat()
r = client.post("/api/mentor/lessons", headers=h(tokens["mentor"]), json={
    "menteeId": ids["menteeProfileId"],
    "date": today,
    "subject": "KOREAN",
    "abilityTags": ["문해력", "비문학"],
    "title": "비문학 독해 연습",
    "goal": "지문 분석 능력 향상",
    "content": "자연권 사상은 근대 정치 철학의 핵심 개념으로...",
    "targetStudyMinutes": 60,
    "problems": [
        {
            "number": 1,
            "title": "윗글의 중심 내용으로 가장 적절한 것은?",
            "options": [
                {"label": "1", "text": "자연권의 역사적 발전 과정"},
                {"label": "2", "text": "국가 권력의 정당화 논리"},
            ],
            "correctAnswer": "2",
        },
        {
            "number": 2,
            "title": "윗글에서 추론할 수 있는 내용으로 적절하지 않은 것은?",
            "content": "<보기> 홉스는 자연 상태를...",
        },
    ],
})
print(f"[Create lesson] {r.status_code} title={r.json()['data']['title']}")
assert r.status_code == 201
lesson_id = r.json()["data"]["id"]
lesson_data = r.json()["data"]
assert lesson_data["abilityTags"] == ["문해력", "비문학"]
assert lesson_data["content"] == "자연권 사상은 근대 정치 철학의 핵심 개념으로..."
assert lesson_data["targetStudyMinutes"] == 60
assert lesson_data["problemCount"] == 2
assert len(lesson_data["problems"]) == 2
assert lesson_data["problems"][0]["title"] == "윗글의 중심 내용으로 가장 적절한 것은?"
print(f"  -> content: {lesson_data['content'][:30]}...")
print(f"  -> targetStudyMinutes: {lesson_data['targetStudyMinutes']}")
print(f"  -> problems: {lesson_data['problemCount']}개")

# Get lessons
r = client.get(f"/api/mentor/lessons?menteeId={ids['menteeProfileId']}&date={today}", headers=h(tokens["mentor"]))
print(f"[Get lessons] {r.status_code} total={r.json()['data']['total']}")
assert r.status_code == 200
assert r.json()["data"]["total"] >= 1
assert r.json()["data"]["lessons"][0]["problemCount"] == 2

# Get lesson detail
r = client.get(f"/api/mentor/lessons/{lesson_id}", headers=h(tokens["mentor"]))
print(f"[Lesson detail] {r.status_code} title={r.json()['data']['title']}")
assert r.status_code == 200
detail = r.json()["data"]
assert detail["content"] is not None
assert detail["targetStudyMinutes"] == 60
assert len(detail["problems"]) == 2
print(f"  -> problems[0]: {detail['problems'][0]['title'][:20]}...")
print(f"  -> problems[1]: {detail['problems'][1]['title'][:20]}...")

# Update lesson
r = client.patch(f"/api/mentor/lessons/{lesson_id}", headers=h(tokens["mentor"]), json={
    "title": "비문학 독해 연습 (수정)",
    "abilityTags": ["문해력", "비문학", "문학"],
    "targetStudyMinutes": 90,
})
print(f"[Update lesson] {r.status_code} title={r.json()['data']['title']}")
assert r.status_code == 200
assert r.json()["data"]["title"] == "비문학 독해 연습 (수정)"
assert len(r.json()["data"]["abilityTags"]) == 3
assert r.json()["data"]["targetStudyMinutes"] == 90

# Delete lesson
r = client.delete(f"/api/mentor/lessons/{lesson_id}", headers=h(tokens["mentor"]))
print(f"[Delete lesson] {r.status_code}")
assert r.status_code == 204

print("--- Lessons OK ---\n")

client.__exit__(None, None, None)

print("\n=============================================")
print("=== ALL API ENDPOINTS TESTED OK ===")
print("=============================================")

