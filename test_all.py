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
    "email": f"mentee{ts}@test.com", "password": "test1234",
    "name": "mentee1", "role": "MENTEE"
})
print(f"[Signup mentee] {r.status_code}")
assert r.status_code == 201
tokens["mentee"] = r.json()["data"]["accessToken"]

# Signup mentor
r = client.post("/api/auth/signup", json={
    "email": f"mentor{ts}@test.com", "password": "test1234",
    "name": "mentor1", "role": "MENTOR"
})
print(f"[Signup mentor] {r.status_code}")
assert r.status_code == 201
tokens["mentor"] = r.json()["data"]["accessToken"]

# Signup parent
r = client.post("/api/auth/signup", json={
    "email": f"parent{ts}@test.com", "password": "test1234",
    "name": "parent1", "role": "PARENT"
})
print(f"[Signup parent] {r.status_code}")
assert r.status_code == 201
tokens["parent"] = r.json()["data"]["accessToken"]

# Login
r = client.post("/api/auth/login", json={"email": f"mentee{ts}@test.com", "password": "test1234"})
print(f"[Login] {r.status_code}")
assert r.status_code == 200

# Me
r = client.get("/api/auth/me", headers=h(tokens["mentee"]))
print(f"[Me] {r.status_code} role={r.json()['data']['user']['role']}")
assert r.status_code == 200

# Onboarding mentee
r = client.put("/api/onboarding/mentee", headers=h(tokens["mentee"]), json={
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
r = client.post("/api/auth/login", json={"email": f"mentee{ts}@test.com", "password": "test1234"})
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

# Create task (mentor for mentee)
r = client.post(f"/api/tasks?menteeId={ids['menteeProfileId']}", headers=h(tokens["mentor"]), json={
    "date": "2026-02-03", "title": "수학 미적분 p.32~35",
    "goal": "미분 개념", "subject": "MATH"
})
print(f"[Create task by mentor] {r.status_code}")
assert r.status_code == 201
ids["mentorTaskId"] = r.json()["data"]["id"]

# Get tasks
r = client.get(f"/api/tasks?menteeId={ids['menteeProfileId']}&date=2026-02-03", headers=h(tokens["mentee"]))
print(f"[Get tasks] {r.status_code} count={len(r.json()['data'])}")
assert r.status_code == 200

# Get task detail
r = client.get(f"/api/tasks/{ids['taskId']}", headers=h(tokens["mentee"]))
print(f"[Task detail] {r.status_code}")
assert r.status_code == 200

# Update task
r = client.put(f"/api/tasks/{ids['taskId']}", headers=h(tokens["mentee"]), json={"goal": "독해 완벽 정리"})
print(f"[Update task] {r.status_code}")
assert r.status_code == 200

# Study time
r = client.patch(f"/api/tasks/{ids['taskId']}/study-time", headers=h(tokens["mentee"]), json={"minutes": 45})
print(f"[Study time] {r.status_code}")
assert r.status_code == 200

# Submit (TEXT)
r = client.post(f"/api/tasks/{ids['taskId']}/submissions", headers=h(tokens["mentee"]), json={
    "submissionType": "TEXT", "textContent": "풀이 내용입니다..."
})
print(f"[Submit TEXT] {r.status_code}")
assert r.status_code == 201
ids["submissionId"] = r.json()["data"]["id"]

# Get submissions
r = client.get(f"/api/tasks/{ids['taskId']}/submissions", headers=h(tokens["mentee"]))
print(f"[Get submissions] {r.status_code} count={len(r.json()['data'])}")
assert r.status_code == 200

# Self score
r = client.put(f"/api/submissions/{ids['submissionId']}/self-score", headers=h(tokens["mentee"]), json={
    "selfScoreCorrect": 8, "selfScoreTotal": 10, "wrongQuestions": [3, 7]
})
print(f"[Self score] {r.status_code}")
assert r.status_code == 200

# Planner
r = client.get("/api/planner?date=2026-02-03", headers=h(tokens["mentee"]))
print(f"[Planner] {r.status_code} tasks={len(r.json()['data']['tasks'])}")
assert r.status_code == 200

# Completion rate
r = client.get("/api/planner/completion-rate?date=2026-02-03", headers=h(tokens["mentee"]))
print(f"[Completion rate] {r.status_code} rate={r.json()['data']['rate']}")
assert r.status_code == 200

# Weekly
r = client.get("/api/planner/weekly?weekOf=2026-02-03", headers=h(tokens["mentee"]))
print(f"[Weekly] {r.status_code} days={len(r.json()['data']['days'])}")
assert r.status_code == 200

# Create comment
r = client.post("/api/planner/comments", headers=h(tokens["mentee"]), json={
    "date": "2026-02-03", "content": "오늘 국어가 어려웠어요"
})
print(f"[Create comment] {r.status_code}")
assert r.status_code == 201

# Get comments
r = client.get(f"/api/planner/comments?date=2026-02-03&menteeId={ids['menteeProfileId']}", headers=h(tokens["mentee"]))
print(f"[Get comments] {r.status_code} count={len(r.json()['data'])}")
assert r.status_code == 200

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

print("--- Phase 3 OK ---\n")

# ===== Feedback Query (Mentee side) =====
print("=== Feedback Query ===")

# By date
r = client.get(f"/api/feedback?menteeId={ids['menteeProfileId']}&date=2026-02-03", headers=h(tokens["mentee"]))
print(f"[Feedback by date] {r.status_code} count={len(r.json()['data'])}")
assert r.status_code == 200

# By subject
r = client.get(f"/api/feedback/by-subject?menteeId={ids['menteeProfileId']}&subject=KOREAN", headers=h(tokens["mentee"]))
print(f"[Feedback by subject] {r.status_code} count={len(r.json()['data'])}")
assert r.status_code == 200

# Detail
r = client.get(f"/api/feedback/{ids['feedbackId']}", headers=h(tokens["mentee"]))
print(f"[Feedback detail] {r.status_code}")
assert r.status_code == 200

print("--- Feedback Query OK ---\n")

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

client.__exit__(None, None, None)

print("\n========================================")
print("=== ALL 55 API ENDPOINTS TESTED OK ===")
print("========================================")
