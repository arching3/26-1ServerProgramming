from dotenv import dotenv_values
from datetime import datetime, timedelta
import os
from urllib.parse import unquote
import requests

from utils.coordinate import coord2grid


KEYS = {
    **dotenv_values(),
    **dotenv_values(os.path.join(os.path.dirname(__file__), ".env")),
}


class KakaoMapAPIReader:
    """Read Kakao Map keyword search API and convert coordinates to KMA grid."""

    def __init__(self, api_key: str | None = None):
        if api_key is None:
            api_key = KEYS["KAKAO_REST_API_KEY"]
        if not api_key:
            raise ValueError("KAKAO_REST_API_KEY was not found.")

        self.__api_key = api_key
        self.url = "https://dapi.kakao.com/v2/local/search/keyword.json"

    def search_place(self, place: str) -> dict:
        """Return the first Kakao keyword search document for a place string."""
        headers = {
            "Authorization": f"KakaoAK {self.__api_key.strip()}"
        }
        params = {
            "query": place
        }

        res = requests.get(self.url, headers=headers, params=params, timeout=5)
        res.raise_for_status()

        documents = res.json()["documents"]
        if not documents:
            raise ValueError(f"장소 검색 결과 없음: {place}")

        return documents[0]

    def get_coord_place_nxny(self, place: str) -> tuple[int, int]:
        """Convert a place string to KMA nx, ny grid coordinates."""
        data = self.search_place(place)
        x = float(data["x"])
        y = float(data["y"])
        return coord2grid((x, y))


class ShortWeatherAPIReader():

    """
        Special key : SKY:{1:맑음, 3:구름많음, 4:흐림},
                      PTY:{0:없음, 1:비, 2:비/눈, 3:눈, 4:소나기}
    """
    __category_keys = ["TMP","UUU","VVV","VEC","WSD","SKY","PTY","POP","WAV","PCP","REH","SNO","TMN","TMX"]
    __sky = {1:"맑음", 3:"구름 많음", 4:"흐림"}
    __pty = {0:"없음", 1:'비', 2:"비/눈", 3:'눈', 4:"소나기"}
    def __init__(self, api_key=None):
        if api_key is None:
            api_key = KEYS["KMA_SHORT_API_KEY_ENCODE"]
            backup_api_key = KEYS["KMA_SHORT_API_KEY_DECODE"]
        else:
            backup_api_key = None
        if not api_key:
            raise ValueError("KMA API key was not found.")
        self.__api_key = api_key
        self.__backup_api_key = backup_api_key
        self.url = "https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
        self.kakao_reader = KakaoMapAPIReader()
    def _get_latest_basetime(self, now: datetime | None = None) -> tuple[str, str]:
        now = now or datetime.now()
        base_times = ["0200", "0500", "0800", "1100", "1400", "1700", "2000", "2300"]
        current_minutes = now.hour * 60 + now.minute

        # 단기예보는 발표시각 직후 바로 조회가 안 될 수 있어 약간 여유를 둔다.
        available_minutes = current_minutes - 45
        for base_time in reversed(base_times):
            hour = int(base_time[:2])
            minute = int(base_time[2:])
            if hour * 60 + minute <= available_minutes:
                return now.strftime("%Y%m%d"), base_time

        yesterday = now - timedelta(days=1)
        return yesterday.strftime("%Y%m%d"), "2300"
    def get(self, date: str, time: str, place: str) -> dict:
        """
            date -- yyyy.mm.dd, time -- yy:mm, place -- "서울 강남"
            return -> {
                date:str[yyyy.mm.dd], time:str[yy:mm], places:str["서울 강남"],
                condition:str["맑음"], temperature:float, rain_probability:float,
                summary:str, source:str, is_mock:bool
            }
        """
        base_date, base_time = self._get_latest_basetime()
        nx, ny = self.kakao_reader.get_coord_place_nxny(place)

        params = {
            "serviceKey": unquote(self.__api_key.strip()),
            "pageNo" : 1,
            "numOfRows":1000,
            "dataType":"JSON",
            "base_date": base_date,
            "base_time": base_time,
            "nx" : nx,
            "ny": ny,
        }

        res = requests.get(self.url, params=params, timeout=5)
        res = res.json()["response"]
        header, body = (res["header"], res["body"])
        item_list = body["items"]["item"]
        parsing = {}
        for item in item_list:
            category = item["category"]
            fcstDate = item["fcstDate"]
            fcstTime = item["fcstTime"]
            fcstValue = item["fcstValue"]
            if category in ["SKY", "PTY"]:
                fcstValue = self.__sky[int(fcstValue)] if category == "SKY" else self.__pty[int(fcstValue)]


            parsing.setdefault(fcstDate, {}).setdefault(fcstTime, {})[category] = fcstValue

        # region Build return data from parsed forecast items
        target_date = date.replace("-", ".")
        target_datetime = datetime.strptime(f"{target_date} {time}", "%Y.%m.%d %H:%M")
        target_key = target_datetime.strftime("%Y%m%d%H%M")
        fcst_keys = [
            f"{fcstDate}{fcstTime}"
            for fcstDate, times in parsing.items()
            for fcstTime in times
        ]
        selected_key = min(
            fcst_keys,
            key=lambda key: (
                key < target_key,
                abs(datetime.strptime(key, "%Y%m%d%H%M") - target_datetime),
            ),
        )
        selected_date = selected_key[:8]
        selected_time = selected_key[8:]
        selected = parsing[selected_date][selected_time]

        condition = selected.get("SKY", "")
        precipitation_type = selected.get("PTY", "없음")
        if precipitation_type != "없음":
            condition = f"{condition}, {precipitation_type}" if condition else precipitation_type

        temperature = float(selected["TMP"]) if "TMP" in selected else None
        rain_probability = float(selected["POP"]) if "POP" in selected else None
        summary = f"{condition} 상태이며 기온은 {temperature}도입니다."
        if rain_probability is not None:
            summary += f" 강수확률은 {rain_probability:g}%입니다."

        rst = {
            "date": target_datetime.strftime("%Y.%m.%d"),
            "time": target_datetime.strftime("%H:%M"),
            "places": place,
            "condition": condition,
            "temperature": temperature,
            "rain_probability": rain_probability,
            "summary": summary,
            "source": "KMA_SHORT_FORECAST",
            "is_mock": False,
        }
        # endregion

        return rst
