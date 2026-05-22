"""
간단한 Gradio UI입니다.

실행 예시:
python frontend/app.py
"""

import json
from urllib import error, request

import gradio as gr


API_URL = "http://127.0.0.1:8000/api/recommend-menu"


def request_recommend_menu(
    date: str,
    time: str,
    place: str,
    people_count: int,
    preferences: str,
    avoid_foods: str,
    budget: str,
) -> str:
    payload = {
        "date": date,
        "time": time,
        "place": place,
        "people_count": int(people_count),
        "preferences": preferences,
        "avoid_foods": avoid_foods,
        "budget": budget,
    }

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    api_request = request.Request(
        API_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(api_request, timeout=10) as response:
            response_body = response.read().decode("utf-8")
    except error.HTTPError as exc:
        response_body = exc.read().decode("utf-8")
        return f"HTTP {exc.code}\n\n{response_body}"
    except error.URLError as exc:
        return f"API 요청 실패: {exc.reason}"
    except TimeoutError:
        return "API 요청 실패: 요청 시간이 초과되었습니다."

    try:
        return json.dumps(json.loads(response_body), ensure_ascii=False, indent=2)
    except json.JSONDecodeError:
        return response_body


with gr.Blocks(title="메뉴 추천 테스트") as demo:
    gr.Markdown("# 메뉴 추천 API 테스트")
    gr.Markdown("Mock 데이터를 입력하거나 기본값 그대로 전송할 수 있습니다.")

    with gr.Row():
        date = gr.Textbox(label="날짜", value="2026-05-17")
        time = gr.Textbox(label="시간", value="18:00")

    with gr.Row():
        place = gr.Textbox(label="장소", value="강남역")
        people_count = gr.Number(label="인원 수", value=4, precision=0)

    preferences = gr.Textbox(label="선호 음식", value="매운 음식, 고기")
    avoid_foods = gr.Textbox(label="피해야 할 음식", value="회, 해산물")
    budget = gr.Textbox(label="예산", value="1인당 15000원")

    submit_button = gr.Button("추천 요청", variant="primary")
    output = gr.Code(label="API 응답", language="json")

    submit_button.click(
        fn=request_recommend_menu,
        inputs=[date, time, place, people_count, preferences, avoid_foods, budget],
        outputs=output,
    )


if __name__ == "__main__":
    demo.launch()
