import gradio as gr
import logging
import sys
from pathlib import Path

import requests

# 백엔드 API 주소
API_URL = "http://127.0.0.1:8000/api/recommend-menu"


def configure_logging():
    project_root = Path(__file__).resolve().parents[1]
    logs_dir = project_root / "logs"
    logs_dir.mkdir(exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    )
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    if not any(getattr(handler, "_project_stdout", False) for handler in root_logger.handlers):
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setLevel(logging.INFO)
        stdout_handler.setFormatter(formatter)
        stdout_handler._project_stdout = True
        root_logger.addHandler(stdout_handler)

    if not any(getattr(handler, "_project_error_file", False) for handler in root_logger.handlers):
        error_handler = logging.FileHandler(logs_dir / "error.log", encoding="utf-8")
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        error_handler._project_error_file = True
        root_logger.addHandler(error_handler)

    return logging.getLogger("frontend")


logger = configure_logging()

# CSS 디자인
css = """
:root {
    color-scheme: light;
    --app-bg: #f6f8fb;
    --panel-bg: #ffffff;
    --panel-soft: #f8fafc;
    --text-main: #111827;
    --text-muted: #4b5563;
    --border: #e5e7eb;
    --badge-bg: #e8f2ff;
    --badge-text: #155e75;
    --accent: #2563eb;
    --accent-strong: #0f766e;
    --card-shadow: 0 4px 14px rgba(15, 23, 42, 0.06);
    --menu-bg: linear-gradient(135deg, #ffffff, #eef7ff);
}

.dark {
    color-scheme: dark;
    --app-bg: #111827;
    --panel-bg: #1f2937;
    --panel-soft: #273449;
    --text-main: #f9fafb;
    --text-muted: #cbd5e1;
    --border: #374151;
    --badge-bg: #123344;
    --badge-text: #7dd3fc;
    --accent: #60a5fa;
    --accent-strong: #2dd4bf;
    --card-shadow: 0 6px 18px rgba(0, 0, 0, 0.28);
    --menu-bg: linear-gradient(135deg, #1f2937, #243042);
}

body,
.gradio-container {
    background: var(--app-bg) !important;
    color: var(--text-main) !important;
}

#title {
    font-size: 32px;
    font-weight: 800;
    color: var(--text-main);
}

.toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 18px;
}

.toolbar .theme-toggle {
    min-width: 170px;
}

.card {
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 20px;
    background: var(--panel-bg);
    color: var(--text-main);
    box-shadow: var(--card-shadow);
}

.menu-card {
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 20px;
    background: var(--menu-bg);
    color: var(--text-main);
    min-height: 150px;
}

.badge {
    display: inline-block;
    background: var(--badge-bg);
    color: var(--badge-text);
    padding: 5px 10px;
    border-radius: 8px;
    margin-right: 6px;
    font-size: 13px;
}

.rank {
    display: inline-block;
    background: var(--accent);
    color: white;
    border-radius: 999px;
    width: 34px;
    height: 34px;
    text-align: center;
    line-height: 34px;
    font-weight: bold;
    margin-right: 10px;
}

.restaurant {
    border-bottom: 1px solid var(--border);
    padding: 16px 0;
}

.main-btn button {
    background: linear-gradient(90deg, var(--accent), var(--accent-strong)) !important;
    color: white !important;
    font-weight: 700 !important;
    border-radius: 12px !important;
}

.gradio-container input,
.gradio-container textarea,
.gradio-container select {
    background: var(--panel-bg) !important;
    color: var(--text-main) !important;
    border-color: var(--border) !important;
}

.gradio-container label,
.gradio-container .wrap,
.gradio-container .prose,
.gradio-container p,
.gradio-container h2,
.gradio-container h3 {
    color: var(--text-main) !important;
}

.gradio-container a {
    color: var(--accent) !important;
}
"""


def keep_theme_value(mode):
    return mode

# 데이터를 매핑하고 API와 통신하는 함수
def recommend(people, budget, date, time, cuisines, avoid_foods, region):

    # 1. 사용자가 입력한 값을 백엔드로 보낼 데이터로 정리
    if cuisines:
        preference = ", ".join(cuisines)
    else:
        preference = ""

    payload = {
        "date": str(date),
        "time": str(time),
        "place": str(region),
        "people_count": str(people),
        "preference": preference,
        "avoid_foods": str(avoid_foods),
        "budget": str(budget)
    }
    logger.info(
        "Frontend recommendation request place=%s people=%s cuisines=%s",
        region,
        people,
        preference,
    )

    # 2. API 요청
    try:
        res = requests.post(API_URL, json=payload, timeout=10)
        res.raise_for_status()
        data = res.json()
        logger.info(
            "Frontend recommendation response menus=%s restaurants=%s",
            len(data.get("menus", [])),
            len(data.get("restaurants", [])),
        )

    except Exception as e:
        logger.exception("Frontend API request failed")
        return f"""
        <div class='card'>
            <h2>⚠️ API 연결 오류</h2>
            <p>백엔드 서버를 확인하세요.</p>
            <p>{e}</p>
        </div>
        """

    # 3. 응답 데이터 꺼내기
    weather = data.get("weather", {})
    menus = data.get("menus", [])
    restaurants = data.get("restaurants", [])

    # 4. 날씨 HTML 만들기
    weather_html = f"""
    <div class='card' style='padding:12px 20px;'>
        ☀️ {date} | {region} |
        {weather.get('condition', '정보없음')}
        {weather.get('temperature', '')}°C
    </div>
    """

    # 5. 추천 메뉴 HTML 만들기
    menu_cards = ""

    for i, m in enumerate(menus[:3]):
        menu_cards += f"""
        <div class='menu-card'>
            <h3>
                <span class='rank'>{i+1}</span>
                {m.get('name', '메뉴')}
            </h3>
            <span class='badge'>{m.get('category', '')}</span>
            <h3>{m.get('price_estimate', '')}</h3>
            <p>👍 추천도: {m.get('recommend_score', 0)}%</p>
            <p><b>추천 이유</b><br>
            {m.get('reason', '추천 이유가 없습니다.')}</p>
            <p><b>날씨 반영 이유</b><br>
            {m.get('weather_reason', '날씨 반영 이유가 없습니다.')}</p>
        </div>
        """

    # 6. 주변 맛집 HTML 만들기
    restaurant_html = ""

    for r in restaurants[:3]:
        place_url = r.get("place_url", "#")

        restaurant_html += f"""
        <div class='restaurant'>
            <b>{r.get('name', '맛집')}</b>
            <span class='badge'>{r.get('category', '')}</span>
            <br>
            📍 {r.get('address', '')}<br>
            ☎️ {r.get('phone', '전화번호 정보 없음')}

            <p><b>선정 이유</b><br>
            {r.get('selection_reason', '선정 이유가 없습니다.')}</p>
            <a href="{place_url}" target="_blank">
                🗺️ 지도 바로가기
            </a>
        </div>
        """

    if restaurant_html == "":
        restaurant_html = "정보가 없습니다."

    # 7. 최종 결과 화면
    result = f"""
    <div style='display:flex; justify-content:space-between; align-items:center; gap:20px;'>
        <div><h2>✨ 추천 결과</h2></div>
        {weather_html}
    </div>

    <hr>

    <h3>🍽️ 추천 메뉴</h3>

    <div style='display:grid; grid-template-columns: repeat(3, 1fr); gap:20px;'>
        {menu_cards}
    </div>

    <br>

    <div class='card'>
        <h3>📍 주변 맛집 추천</h3>
        {restaurant_html}
    </div>
    """

    return result


# UI 구성
with gr.Blocks(title="오늘 뭐 먹지?", elem_classes=["light"]) as demo:
    with gr.Row(elem_classes="toolbar"):
        gr.HTML("<div id='title'>오늘 뭐 먹지? 🍽️</div>")
        theme_mode = gr.Radio(
            choices=["라이트", "다크"],
            value="라이트",
            label="테마",
            elem_classes="theme-toggle",
        )

    with gr.Row():
        with gr.Column(scale=1):
            people = gr.Number(label="👥 인원 수", value=2, precision=0)
            budget = gr.Number(label="💰 예산", value=30000, precision=0, step=1000)
            date = gr.Textbox(label="📅 날짜", value="2025-05-26")
            time = gr.Textbox(label="🕐 모임 시간", value="13:00")

            cuisines = gr.CheckboxGroup(
                choices=["한식", "중식", "일식", "양식"],
                value=["한식"],
                label="🍽️ 선호 음식 유형"
            )

            avoid_foods = gr.Textbox(
                label="🚫 못 먹는 음식",
                placeholder="예) 해산물, 고수"
            )

            region = gr.Textbox(label="📍 방문할 지역", value="서울 강남구")
            btn = gr.Button("✨ 메뉴 추천 받기", elem_classes="main-btn")

        with gr.Column(scale=3):
            output = gr.HTML("<div class='card'>추천 결과를 기다리는 중입니다...</div>")

    btn.click(
        fn=recommend,
        inputs=[people, budget, date, time, cuisines, avoid_foods, region],
        outputs=output
    )
    theme_mode.change(
        fn=keep_theme_value,
        inputs=theme_mode,
        outputs=theme_mode,
        js="""
        (mode) => {
            const root = document.querySelector('.gradio-container');
            if (root) {
                root.classList.toggle('dark', mode === '다크');
                root.classList.toggle('light', mode !== '다크');
            }
            return mode;
        }
        """,
    )

if __name__ == "__main__":
    demo.launch(css=css)
