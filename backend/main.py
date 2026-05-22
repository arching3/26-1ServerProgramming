"""
fastapi 시작점입니다.
main app을 정의하고 다음을 실행할 수 있게 작성하시면 됩니다.
uvicorn backend.main:{fastapi 시작점}

api는 다른 곳에서 기능을 정의 후, import 하여 사용합니다.
예시)
# example.py
def example_api_function -> dict:
    return {"status":"ok"}

# main
from example import example_api_function
app = FastAPI()
@app.get("/api/example")
def get_example(param : any) -> dict:
    return example_api_function(param)

"""
