# Backend 변경사항 및 팀원 주의사항

## 변경사항

- `backend/`에 FastAPI 백엔드 구조가 추가되었습니다.
- 환경변수 예시와 백엔드 의존성 파일은 `backend/백앤드_외부_환경_파일/`에 있습니다.
- 실제 API 키가 없어도 mock 데이터로 실행 가능합니다.

```text
backend/
├── __init__.py
├── main.py
├── api.py
├── ai.py
├── weather.py
├── place.py
└── 백앤드_외부_환경_파일/
    ├── requirements.txt
    └── .env.example

.gitignore
```

## Git 주의사항

- `.env`에는 실제 API 키가 들어갈 수 있으므로 Git에 올리면 안 됩니다.
- `.gitignore`에 `.env`가 추가되어 있습니다.
- 커밋 전 반드시 `git status`로 `.env`가 staged 되지 않았는지 확인하세요.
- 팀원 공유는 `backend/백앤드_외부_환경_파일/.env.example`만 사용합니다.
- 실제 키를 사용할 때는 로컬에서 `.env`를 만들고 커밋하지 않습니다.

필요한 환경변수:

```text
KMA_API_KEY=
KAKAO_REST_API_KEY=
LLM_API_KEY=
LLM_MODEL=
GOOGLE_API_KEY=
```

## 현재 동작 방식

- 현재 LLM은 실제 API가 아니라 mock 함수로 동작합니다.
- `LLM_API_KEY`, `LLM_MODEL`은 나중에 실제 LLM 연동을 위해 미리 잡아둔 값입니다.
- 기상청 API 키가 없으면 mock weather가 반환됩니다.
- Kakao API 키가 없으면 mock restaurants가 반환됩니다.
- mock 응답이라도 전체 API 흐름은 정상 테스트 가능합니다.
- `LOCATION_CODE_MAP`은 날씨 API 응답값이 아니라, 입력 장소를 기상청 중기예보 `regId`로 바꾸기 위한 지역 코드 매핑입니다.

## 실행 방법

```bash
conda activate min
pip install -r backend/백앤드_외부_환경_파일/requirements.txt
uvicorn backend.main:app --reload
```

정보 확인:

```bash
curl http://127.0.0.1:8000/info
```

추천 API 테스트:

```bash
curl -X POST http://127.0.0.1:8000/api/recommend-menu \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2026-05-24",
    "time": "18:00",
    "place": "강남역",
    "people_count": 4,
    "preferences": "한식",
    "avoid_foods": "회, 해산물",
    "budget": "30000"
  }'
```

## API 계약

요청 필드:

```text
date: str
time: str
place: str
people_count: int
preferences: str
avoid_foods: str
budget: str
```

- PDF 명세 호환을 위해 `preference` 단수 입력도 받을 수 있습니다.
- 신규 구현에서는 `preferences` 사용을 권장합니다.

응답 핵심 구조:

```json
{
  "weather": {},
  "menus": [],
  "restaurants": []
}
```

현재 구현에는 디버깅용으로 `"input"` 필드도 함께 반환됩니다. 명세와 완전히 맞추려면 추후 제거 대상입니다.

프론트엔드 상세 표시 및 지도 이동에 사용할 응답 필드:

```text
menus[].reason
menus[].weather_reason
restaurants[].selection_reason
restaurants[].place_url
```

- 초기화 버튼은 프론트엔드 입력 상태만 바꾸므로 백엔드 API 추가가 필요 없습니다.
- 음식점 이름, 주소, 전화번호, 지도 URL은 Kakao 응답 또는 mock fallback 결과만 사용합니다.

## 파일별 역할

- `backend/main.py`: FastAPI 앱 생성, CORS 설정, 라우팅 연결
- `backend/api.py`: 요청 모델, `/info`, 전체 추천 흐름 담당
- `backend/weather.py`: 기상청 중기예보 API 구조와 mock weather fallback
- `backend/place.py`: Kakao Local API 검색과 mock restaurant fallback
- `backend/ai.py`: mock 메뉴 추천, 음식점 선정 이유 생성, 향후 LLM 교체 지점
- `backend/백앤드_외부_환경_파일/requirements.txt`: 백엔드 실행에 필요한 Python 패키지 목록
- `backend/백앤드_외부_환경_파일/.env.example`: 팀원 공유용 환경변수 예시
- `.env`: 개인 로컬 API 키 저장용, Git 업로드 금지

## 커밋 전 확인

```bash
git status
python -m py_compile backend/main.py backend/api.py backend/ai.py backend/weather.py backend/place.py
```
