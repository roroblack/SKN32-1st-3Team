from dataclasses import dataclass
from datetime import datetime
from typing import Optional


# 미완성
@dataclass
class CarRegistrationItem:
    region_id: int      # 시도명 코드 -> regions.region_id
    stat_year: int      # 연도
    count: int          # 등록 대수
    crawled_at: datetime


# 수정 예정
@dataclass
class FaqItem:
    question: str
    answer: str
    crawled_at: datetime
    faq_id: Optional[int] = None


# 미완성
@dataclass
class StationItem:
    region_id: int          # 시도명 (서울, 경기 ...) -> regions.region_id
    station_name: str       # 충전소명
    address: str | None     # 상세 주소 (없으면 None)
    lat: float | None       # 위도 (없으면 None)
    lon: float | None       # 경도 (없으면 None)
    crawled_at: datetime
