from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional


# 수정 예정
@dataclass
class CarRegistrationItem:
    region: str     # 시도명 이름
    stat_year: int  # 연도
    count: int      # 등록 대수


# 수정 예정
@dataclass
class FaqItem:
    question: str
    answer: str
    faq_id: Optional[int] = None


# 수정 예정
@dataclass
class StationItem:
    region_id: int          # 시도명 (서울, 경기 ...) -> regions.region_id
    station_name: str       # 충전소명
    address: str | None     # 상세 주소 (없으면 None)
    lat: float | None       # 위도 (없으면 None)
    lon: float | None       # 경도 (없으면 None)


# 수정 예정
@dataclass
class CrawlStat:
    target_type: Literal['car_registration', 'station', 'faq']
    last_crawled_at: Optional[datetime] = None
    crawl_id: Optional[int] = None
