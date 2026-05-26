import gradio as gr
import requests

# 틀만 잡아놓은 UI디자인입니다!

# 백엔드 API 주소
API_URL = "http://127.0.0.1:8000/api/recommend-menu"

# CSS 디자인
css = """
body { background: #fafbff; }

#title {
    font-size: 32px;
    font-weight: 800;
    color: #111827;
}

.card {
    border: 1px solid #e5e7eb;
    border-radius: 18px;
    padding: 20px;
    background: white;
    box-shadow: 0 4px 14px rgba(0,0,0,0.04);
}

.menu-card {
    border: 1px solid #ddd6fe;
    border-radius: 16px;
    padding: 20px;
    background: linear-gradient(135deg, #ffffff, #f7f5ff);
    min-height: 150px;
}

.badge {
    display: inline-block;
    background: #ede9fe;
    color: #4f46e5;
    padding: 5px 10px;
    border-radius: 8px;
    margin-right: 6px;
    font-size: 13px;
}

.rank {
    display: inline-block;
    background: #5b4bff;
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
    border-bottom: 1px solid #e5e7eb;
    padding: 16px 0;
}

.main-btn button {
    background: linear-gradient(90deg, #5b4bff, #8b5cf6) !important;
    color: white !important;
    font-weight: 700 !important;
    border-radius: 12px !important;
}
"""

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

    # 2. API 요청
    try:
        res = requests.post(API_URL, json=payload, timeout=10)
        res.raise_for_status()
        data = res.json()

    except Exception as e:
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
        </div>
        """

    # 6. 주변 맛집 HTML 만들기
    restaurant_html = ""

    for r in restaurants[:3]:
        restaurant_html += f"""
        <div class='restaurant'>
            <b>{r.get('name', '맛집')}</b>
            <span class='badge'>{r.get('category', '')}</span>
            <br>
            📍 {r.get('address', '')}
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
with gr.Blocks(css=css, title="오늘 뭐 먹지?") as demo:
    gr.HTML("<div id='title'>오늘 뭐 먹지? 🍽️</div>")

    with gr.Row():
        with gr.Column(scale=1):
            people = gr.Number(label="👥 인원 수", value=2, precision=0)
            budget = gr.Number(label="💰 예산", value=30000, precision=0)
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

if __name__ == "__main__":
    demo.launch()