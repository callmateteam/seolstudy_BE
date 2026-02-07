import base64
import json
import logging

import fitz  # PyMuPDF
from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

MAX_PDF_PAGES = 20
TEXT_THRESHOLD_PER_PAGE = 50  # chars; below this → scanned page

_openai_client: AsyncOpenAI | None = None


def _get_openai() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client


def _is_mock_mode() -> bool:
    return settings.APP_ENV == "test" or not settings.OPENAI_API_KEY


# ---------- GPT 프롬프트 ----------

PDF_PARSE_JSON_SCHEMA = """{
  "content": "(지문/본문 전체 텍스트, 여러 지문이면 구분하여 나열, 없으면 빈 문자열)",
  "problems": [
    {
      "number": (정수, 문제 번호),
      "title": "(문제 제목/질문 전문)",
      "content": "(보조 지문이나 <보기>, 없으면 null)",
      "options": [{"label": "1", "text": "선지 내용"}, ...] 또는 null,
      "correctAnswer": "(정답, 모르면 null)"
    }
  ]
}"""

SYSTEM_PROMPT = """당신은 한국 수능 학습지/교재 PDF 분석 AI입니다.
PDF에서 추출된 내용을 분석하여 지문(본문)과 문제를 구조화된 JSON으로 분리합니다.

[분석 규칙]
1. 지문(passage): 문제 풀이에 필요한 본문 텍스트를 모두 추출합니다.
   - 여러 지문이 있으면 줄바꿈(\\n\\n)으로 구분합니다.
   - 지문 앞에 "[지문 1]", "[지문 2]" 등 라벨을 붙여주세요.
2. 문제(problems): 개별 문제를 배열로 반환합니다.
   - number: 문제 번호 (PDF에 표기된 번호, 없으면 순서대로 1부터)
   - title: 문제 제목/질문 전문
   - content: 문제에 딸린 보조 지문이나 <보기> (없으면 null)
   - options: 객관식 선지 배열 [{"label": "1", "text": "선지 내용"}, ...] (주관식이면 null)
   - correctAnswer: 정답이 PDF에 표기되어 있으면 기입, 없으면 null
3. 수학 수식은 가독성을 위해 일반 텍스트로 표현합니다 (예: "x^2 + 2x + 1").
4. 이미지 속 표/그래프는 "[표]" 또는 "[그래프]"로 표시하고 설명합니다.

[중요]
- 반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트를 포함하지 마세요.
- 한국어로 작성하세요.
- 문제가 없고 지문만 있는 경우에도 problems를 빈 배열로 반환하세요.
- 지문이 없고 문제만 있는 경우에도 content를 빈 문자열로 반환하세요."""


# ---------- PDF 추출 ----------

def _extract_pdf_pages(pdf_bytes: bytes) -> tuple[list[str], list[str]]:
    """페이지별 텍스트 + base64 이미지 추출. 텍스트 부족 시 이미지로 대체."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page_count = min(len(doc), MAX_PDF_PAGES)

    if len(doc) > MAX_PDF_PAGES:
        logger.warning(f"PDF has {len(doc)} pages, truncating to {MAX_PDF_PAGES}")

    text_pages: list[str] = []
    base64_images: list[str] = []

    for i in range(page_count):
        page = doc[i]
        text = page.get_text("text")
        text_pages.append(text)

        if len(text.strip()) >= TEXT_THRESHOLD_PER_PAGE:
            base64_images.append("")
        else:
            pix = page.get_pixmap(dpi=200)
            png_bytes = pix.tobytes("png")
            base64_images.append(base64.b64encode(png_bytes).decode("ascii"))

    doc.close()
    return text_pages, base64_images


def _classify_pdf(text_pages: list[str], image_pages: list[str]) -> str:
    """digital / scanned / mixed"""
    if not text_pages:
        return "digital"
    image_count = sum(1 for img in image_pages if img)
    if image_count == 0:
        return "digital"
    if image_count == len(image_pages):
        return "scanned"
    return "mixed"


# ---------- GPT 호출 ----------

def _parse_json_response(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()
    return json.loads(raw)


async def _call_gpt_text(full_text: str) -> dict:
    """디지털 PDF: 텍스트 기반 GPT-4o 호출"""
    client = _get_openai()

    if len(full_text) > 100_000:
        full_text = full_text[:100_000] + "\n\n... (이하 생략)"

    user_prompt = f"""다음은 한국 학습지/교재 PDF에서 추출한 텍스트입니다.
지문과 문제를 분리하여 아래 JSON 형식으로 응답하세요.

[추출된 텍스트]
{full_text}

[응답 JSON 형식]
{PDF_PARSE_JSON_SCHEMA}"""

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=4000,
        temperature=0.1,
    )

    return _parse_json_response(response.choices[0].message.content or "{}")


async def _call_gpt_vision(base64_images: list[str], partial_text: str) -> dict:
    """스캔/혼합 PDF: 이미지 기반 GPT-4o Vision 호출"""
    client = _get_openai()

    partial_note = ""
    if partial_text.strip():
        partial_note = f"\n참고로 일부 페이지에서 다음 텍스트가 추출되었습니다:\n{partial_text[:5000]}"

    user_text = f"""첨부된 이미지는 한국 학습지/교재 PDF의 페이지입니다.
각 페이지에서 지문과 문제를 추출하여 아래 JSON 형식으로 응답하세요.
{partial_note}

[응답 JSON 형식]
{PDF_PARSE_JSON_SCHEMA}"""

    content: list[dict] = [{"type": "text", "text": user_text}]
    for b64_img in base64_images[:MAX_PDF_PAGES]:
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{b64_img}",
                "detail": "high",
            },
        })

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ],
        max_tokens=4000,
        temperature=0.1,
    )

    return _parse_json_response(response.choices[0].message.content or "{}")


# ---------- Mock ----------

def _mock_parse_result() -> dict:
    return {
        "content": "[지문 1]\n다음 글을 읽고 물음에 답하시오.\n\n(테스트용 모의 지문입니다)",
        "problems": [
            {
                "number": 1,
                "title": "윗글의 내용과 일치하는 것은?",
                "content": None,
                "options": [
                    {"label": "1", "text": "모의 선지 1"},
                    {"label": "2", "text": "모의 선지 2"},
                    {"label": "3", "text": "모의 선지 3"},
                    {"label": "4", "text": "모의 선지 4"},
                    {"label": "5", "text": "모의 선지 5"},
                ],
                "correctAnswer": None,
            },
            {
                "number": 2,
                "title": "윗글에 대한 설명으로 적절하지 않은 것은?",
                "content": None,
                "options": [
                    {"label": "1", "text": "모의 선지 A"},
                    {"label": "2", "text": "모의 선지 B"},
                    {"label": "3", "text": "모의 선지 C"},
                    {"label": "4", "text": "모의 선지 D"},
                    {"label": "5", "text": "모의 선지 E"},
                ],
                "correctAnswer": None,
            },
        ],
    }


# ---------- 메인 진입점 ----------

async def parse_pdf_content(pdf_bytes: bytes) -> dict:
    """PDF 바이트에서 지문/문제를 추출. 실패 시 빈 결과 반환."""
    if _is_mock_mode():
        return _mock_parse_result()

    try:
        text_pages, image_pages = _extract_pdf_pages(pdf_bytes)

        if not text_pages:
            return {"content": "", "problems": []}

        pdf_type = _classify_pdf(text_pages, image_pages)

        if pdf_type == "digital":
            full_text = "\n\n---페이지 구분---\n\n".join(text_pages)
            result = await _call_gpt_text(full_text)
        else:
            b64_images = [img for img in image_pages if img]
            partial_text = "\n".join(t for t in text_pages if t.strip())
            result = await _call_gpt_vision(b64_images, partial_text)

        content = result.get("content", "")
        problems = result.get("problems", [])

        sanitized = []
        for i, p in enumerate(problems):
            sanitized.append({
                "number": p.get("number", i + 1),
                "title": p.get("title", f"문제 {i + 1}"),
                "content": p.get("content"),
                "options": p.get("options"),
                "correctAnswer": p.get("correctAnswer"),
            })

        return {"content": content, "problems": sanitized}

    except Exception as e:
        logger.error(f"PDF parsing failed: {e}", exc_info=True)
        return {"content": "", "problems": []}
