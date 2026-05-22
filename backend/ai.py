"""
LLM을 빌드하는 파일입니다.

api에서 직접 호출하기 보다, parameter를 받고, 답변을 return 하는 방식이 좋아보입니다.

예시)
def invoke(people_num : int, budget : int, prefer : string, location : string):
    prompt = f\"""
    당신은 메뉴를 추천해주는 역할입니다. 다음 정보에 따라 식사 메뉴룰 추천해주세요.
    인원 : {people_num}
    장르 선호 : {prefer}
    인당 예산 : {budget}
    위치 : {location}
    
    답변은 단답으로 제한해주세요.
    예시1) 김치찌개
    예시2) 갈비찜
    \"""
    return model.invoke(prompt)
"""
