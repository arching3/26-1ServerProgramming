# API Data Specification

## Menu Recommendation API

### Endpoint

```http
POST http://127.0.0.1:8000/api/recommend-menu
Content-Type: application/json
```

## Request Body

메뉴 추천 요청 시 아래 JSON 형식으로 데이터를 전송합니다.

| Field | Type | Description | Example |
| --- | --- | --- | --- |
| `date` | `string` | 모임 날짜 | `"2025-05-26"` |
| `time` | `string` | 모임 시간 | `"18:00"` |
| `place` | `string` | 모임 장소 | `"서울 강남구"` |
| `people_count` | `string` | 인원수 | `"2"` |
| `preference` | `string` | 선호 음식 종류 | `"한식"` |
| `avoid_foods` | `string` | 피해야 하는 음식 또는 식재료 | `"해산물, 회, 돼지고기"` |
| `budget` | `string` | 총 예산 | `"30000"` |

백엔드는 `preference`를 호환 입력으로 처리합니다. 신규 프론트엔드 연동에서는
`preferences` 필드명 사용을 권장합니다.

### Request Example

```json
{
  "date": "2025-05-26",
  "time": "18:00",
  "place": "서울 강남구",
  "people_count": "2",
  "preference": "한식",
  "avoid_foods": "해산물, 회, 돼지고기",
  "budget": "30000"
}
```

## Response Body

응답은 날씨 정보, 추천 메뉴 목록, 추천 식당 목록을 포함합니다.

| Field | Type | Description |
| --- | --- | --- |
| `weather` | `object` | 요청 날짜, 시간, 장소에 대한 날씨 정보 |
| `menus` | `array` | 추천 메뉴 목록 |
| `restaurants` | `array` | 추천 식당 목록 |

### Response Example

```json
{
  "weather": {
    "date": "2025-05-26",
    "time": "18:00",
    "place": "서울 강남구",
    "condition": "맑음",
    "temperature": 23,
    "rain_probability": 20,
    "summary": "맑고 따뜻한 날씨입니다.",
    "source": "KMA_MID_FORECAST",
    "is_mock": true
  },
  "menus": [
    {
      "rank": 1,
      "name": "소불고기 정식",
      "category": "한식",
      "price_estimate": "22000원",
      "reason": "한식을 선호하고 2명이 함께 먹기 좋은 든든한 메뉴입니다.",
      "weather_reason": "맑은 날씨라 부담 없이 먹기 좋은 따뜻한 한식 메뉴로 추천했습니다.",
      "recommend_score": 95
    },
    {
      "rank": 2,
      "name": "김치찌개",
      "category": "한식",
      "price_estimate": "18000원",
      "reason": "예산 안에서 2명이 함께 먹기 좋고 피해야 할 음식과 충돌하지 않습니다.",
      "weather_reason": "따뜻한 국물 메뉴라 식사 만족도가 높을 수 있습니다.",
      "recommend_score": 91
    }
  ],
  "restaurants": [
    {
      "name": "식당 이름",
      "category": "음식점 카테고리",
      "address": "지번 주소",
      "road_address": "도로명 주소",
      "phone": "전화번호",
      "place_url": "장소 URL",
      "x": "경도",
      "y": "위도",
      "matched_menu": "소불고기 정식",
      "selection_reason": "입력 장소와 추천 메뉴를 고려해 선택한 음식점입니다."
    },
    {
      "name": "식당 이름",
      "category": "음식점 카테고리",
      "address": "지번 주소",
      "road_address": "도로명 주소",
      "phone": "전화번호",
      "place_url": "장소 URL",
      "x": "경도",
      "y": "위도",
      "matched_menu": "연어 덮밥",
      "selection_reason": "입력 장소와 추천 메뉴를 고려해 선택한 음식점입니다."
    }
  ]
}
```

## Field Details

### `weather`

| Field | Type | Description |
| --- | --- | --- |
| `date` | `string` | 날씨 기준 날짜 |
| `time` | `string` | 날씨 기준 시간 |
| `place` | `string` | 날씨 기준 장소 |
| `condition` | `string` | 날씨 상태 |
| `temperature` | `number` | 기온 |
| `rain_probability` | `number` | 강수 확률 |
| `summary` | `string` | 날씨 요약 |
| `source` | `string` | 날씨 데이터 출처 |
| `is_mock` | `boolean` | Mock 데이터 여부 |

### `menus`

| Field | Type | Description |
| --- | --- | --- |
| `rank` | `number` | 추천 순위 |
| `name` | `string` | 메뉴 이름 |
| `category` | `string` | 음식 카테고리 |
| `price_estimate` | `string` | 예상 가격 |
| `reason` | `string` | 추천 이유 |
| `weather_reason` | `string` | 날씨 기반 추천 이유 |
| `recommend_score` | `number` | 추천 점수 |

### `restaurants`

| Field | Type | Description |
| --- | --- | --- |
| `name` | `string` | 식당 이름 |
| `category` | `string` | 식당 카테고리 |
| `address` | `string` | 지번 주소 |
| `road_address` | `string` | 도로명 주소 |
| `phone` | `string` | 전화번호 |
| `place_url` | `string` | 장소 URL |
| `x` | `string` | 경도 |
| `y` | `string` | 위도 |
| `matched_menu` | `string` | 식당과 매칭된 추천 메뉴 |
| `selection_reason` | `string` | 음식점 선정 이유 |

## Frontend Display Fields

프론트엔드 상세 화면 및 지도 이동 기능에서는 아래 응답 필드를 사용합니다.

| Field | Description |
| --- | --- |
| `menus[].reason` | 메뉴 추천 이유 |
| `menus[].weather_reason` | 날씨 반영 이유 |
| `restaurants[].selection_reason` | 음식점 선정 이유 |
| `restaurants[].place_url` | Kakao 지도 바로가기 URL |

초기화 버튼은 프론트엔드 입력 상태를 초기화하는 기능이므로 별도 백엔드 API가 필요하지 않습니다.
