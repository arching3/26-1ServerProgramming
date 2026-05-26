import gradio as gr
import requests

# testt에서 조금 더 꾸며본 UI 디자인입니다.

# 백엔드 API 주소
API_URL = "http://127.0.0.1:8000/api/recommend"

# CSS 디자인
css = """
/* 페이지 전체 배경색을 베이지로 고정 */
.gradio-container { 
    background-color: #EFE7DA !important; 
}

/*  입력창 라벨 스타일 */
.gradio-container span {
    color: #000000 !important;   /* 검정색 */
    font-weight: 700 !important; /* 굵게 */
}

/* 체크박스 클릭 시 색상 */
input[type="checkbox"]:checked {
    accent-color: #5b4bff !important;
}

#title {
    font-size: 40px;
    font-weight: 800;
    color: #111827;
    margin-bottom: 20px;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.2); 
}

/* 3. 깔끔하고 둥근 카드 디자인 */
.card {
    border: none !important;
    border-radius: 24px !important;
    padding: 24px !important;
    background: white;
    box-shadow: 0 8px 20px rgba(0,0,0,0.05) !important;
}

/* 4. 메뉴 카드 디자인 */
.menu-card {
    border: 1px solid #ede9fe;
    border-radius: 20px !important;
    padding: 20px;
    background: #ffffff;
    min-height: 150px;
    transition: transform 0.2s ease;
}

.menu-card:hover {
    transform: translateY(-8px);
    box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1) !important;
    border-color: #5b4bff !important;
}
/* 5. 배지 및 순위 스타일 */
.badge {
    display: inline-block;
    background: #ede9fe;
    color: #4f46e5;
    padding: 4px 12px;
    border-radius: 20px;
    margin-right: 6px;
    font-size: 12px;
    font-weight: bold;
}

.rank {
    display: inline-block;
    background: #5b4bff;
    color: white !important;
    border-radius: 50%;
    width: 30px;
    height: 30px;
    text-align: center;
    line-height: 30px;
    font-weight: bold;
    margin-right: 10px;
}

/* 6. 버튼 스타일 */
.main-btn {
    background: #5b4bff !important;
    color: white !important;
    font-weight: 700 !important;
    border-radius: 16px !important;
    border: none !important;
    transition: all 0.3s ease !important;
    height: 50px !important;
}

/* 맛집 카드 애니메이션 추가 */
.restaurant {
    border-bottom: 1px solid #e5e7eb;
    padding: 16px 0;
    transition: transform 0.2s ease;
}

/* 마우스를 올렸을 때 오른쪽으로 살짝 이동하며 강조 */
.restaurant:hover {
    transform: translateX(10px); 
    background-color: rgba(91, 75, 255, 0.05); /* 마우스 올릴 때 연한 보라색 배경 */
    border-radius: 8px;
    padding-left: 10px;
}

.main-btn:hover {
    background: #0000FF !important;
    transform: translateY(-2px);
    box-shadow: 0 5px 15px rgba(0,0,255,0.3) !important;
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
        {weather.get('condition', '맑음')}
        {weather.get('temperature', '')}
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
            {f"<p>👍 추천도: {m.get('recommend_score', 0)}%</p>" if m.get('recommend_score') else ""}
            <p style='font-size: 0.9em; color: #666;'>{m.get('reason', '')}</p>
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