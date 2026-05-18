import os
import re
from datetime import datetime
from typing import Literal

import pandas as pd
from dataclasses import asdict
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


from crawling.models import *

# DB 작업을 처리하는 클래스이다.
class Repository:
    # 아이템의 모델에 따라 DB에 추가하는 SQL 사전이다.
    # SQL Injection 위험을 낮추기 위해 바인딩 방식을 사용한다.
    #
    # CarRegistrationItem / StationItem:
    #   모델 필드가 region(문자열)인데 DB 테이블은 region_id(FK 정수)를 요구한다.
    #   서브쿼리로 region 문자열을 region_id 로 변환하여 저장한다.
    # CarRegistrationItem:
    #   같은 (region_id, stat_year) 조합이 이미 있으면 count 를 덮어쓴다 (UPSERT).
    # FaqItem:
    #   source_site, category 는 DB faq 테이블에 컬럼이 없으므로 SQL 에 포함하지 않는다.
    #   SQL 에 선언된 파라미터만 바인딩되므로 모델의 나머지 필드는 자동으로 무시된다.
    MODEL_INSERT_SQL = {
        CarRegistrationItem: '''
            INSERT INTO car_registrations (
                region_id,
                stat_year,
                count
            )
            VALUES (
                (SELECT region_id FROM regions WHERE region_name = :region),
                :stat_year,
                :count
            )
            ON DUPLICATE KEY UPDATE count = VALUES(count)
        ''',
        FaqItem: '''
            INSERT INTO faq (
                question,
                answer
            )
            VALUES (
                :question,
                :answer
            )
        ''',
        StationItem: '''
            INSERT INTO hydrogen_charging_station (
                region_id,
                station_name,
                address,
                lat,
                lon
            )
            VALUES (
                (SELECT region_id FROM regions WHERE region_name = :region),
                :station_name,
                :address,
                :lat,
                :lon
            )
        '''
    }

    # 저장 전에 실행할 선처리 SQL 사전이다.
    # FaqItem 은 최신 크롤링 결과로 교체하기 위해 저장 전 기존 데이터를 전부 삭제한다.
    MODEL_PRE_SQL = {
        FaqItem: 'DELETE FROM faq'
    }

    # 아이템의 모델에 따라 마지막 크롤링 시간을 갱신할 레코드를 지정한다.
    MODEL_TARGET_TYPE = {
        CarRegistrationItem : 'car_registration',
        FaqItem : 'faq',
        StationItem : 'station'
    }

    def __init__(self):
        self.engine = self._get_engine()

    # DB 연결을 관리하는 엔진 객체를 만들고, 이를 반환하는 메소드이다.
    def _get_engine(self):
        # 프로젝트 폴더의 .env 파일을 불러온다.
        load_dotenv()

        # .env 파일에서 DB 환경 변수를 불러온다.
        # 불러올 수 없는 경우 기본값을 사용한다.
        host = os.getenv('DB_HOST', 'localhost')
        port = os.getenv('DB_PORT', 3306)
        user = os.getenv('DB_USER', 'student')
        password = os.getenv('DB_PASSWORD', 'student80')
        db_name = os.getenv('DB_NAME', 'crawler_db')

        # DB에 접속하기 위한 DB URL을 만든다.
        # 한글을 안전하게 저장하기 위해 utf8mb4 문자셋을 사용한다.
        db_url = f'mysql+pymysql://{user}:{password}@{host}:{port}/{db_name}?charset=utf8mb4'

        # DB 연결을 관리하는 엔진 객체를 만들고, 이를 반환한다.
        # pool_pre_ping 옵션
        #   DB에 연결하기 전에 연결이 살아 있는지 확인한다.
        #   연결이 유효하면 그대로 사용하고, 아니면 새 연결을 만든다.
        #   매 연결마다 약간의 오버헤드가 있지만, 연결 문제로 인한 오류를 줄여준다.
        # pool_recycle 옵션
        #   초 단위로 지정한 시간이 지나면 기존 연결을 버리고, 새 연결을 만든다.
        return create_engine(db_url, pool_pre_ping=True, pool_recycle=3600)

    # 아이템 리스트를 DB에 저장하는 메소드이다.
    # 저장한 아이템 개수를 반환한다.
    def save_items(self, items: list) -> int:
        # 아이템 리스트인지 확인한다.
        if not isinstance(items, list):
            raise TypeError('Items should be a list.')
        
        # 아이템 리스트가 비어 있는지 확인한다.
        if not items:
            return 0
        
        model_class = type(items[0])

        # 아이템 리스트에 허용되지 않는 모델의 아이템이 있는지 확인한다.
        if model_class not in self.MODEL_INSERT_SQL:
            raise TypeError(f'Unsupported model type: {model_class.__name__}')
        
        # 아이템 리스트에 같은 모델의 아이템만 있는지 확인한다.
        if not all(isinstance(item, model_class) for item in items):
            raise TypeError('All items in the list must have the same model type.')
        
        # 아이템의 모델에 따라 DB에 추가하는 SQL을 가져온다.
        sql = self.MODEL_INSERT_SQL[model_class]

        # SQL 에 선언된 :param 이름을 추출하여 필요한 컬럼명 목록을 만든다.
        # 기존에는 fields(model_class)로 전체 모델 필드를 사용했으나,
        # DB에 없는 모델 필드(FaqItem.source_site 등)를 제외하기 위해 SQL 기준으로 추출한다.
        column_names = re.findall(r':(\w+)', sql)

        # 아이템 리스트를 파라미터 리스트로 변환한다.
        params_list = [self._item_to_params(item, column_names) for item in items]

        # 아이템의 모델에 따라 마지막 크롤링 시간을 갱신할 레코드를 지정한다.
        # 마지막 크롤링 시간을 갱신할 SQL을 만든다.
        target_type = self.MODEL_TARGET_TYPE[model_class]
        update_crawl_stat_sql = '''
            UPDATE crawl_stat
            SET last_crawled_at = :last_crawled_at
            WHERE target_type = :target_type
        '''

        # begin() : 한 블록 안에서 트랜잭션을 처리한다.
        #   정상 종료되면 자동으로 commit 처리된다.
        #   예외가 생기면 자동으로 rollback 처리된다.
        with self.engine.begin() as conn:
            # 선처리 SQL이 있으면 먼저 실행한다 (예: FAQ 기존 데이터 전체 삭제).
            if model_class in self.MODEL_PRE_SQL:
                conn.execute(text(self.MODEL_PRE_SQL[model_class]))

            # SQL에 파라미터 리스트를 바인딩하여 처리한다.
            # text() : 문자열 SQL을 SQLAlchemy가 처리할 수 있는 객체로 바꾼다.
            # execute() : SQL을 실제 DB에 실행한다.
            result = conn.execute(text(sql), params_list)

            conn.execute(
                text(update_crawl_stat_sql),
                {
                    'last_crawled_at': datetime.now(),
                    'target_type': target_type
                }
            )

        # 저장한 아이템 개수를 반환한다.
        return result.rowcount if result.rowcount is not None else len(items)
    
    # 아이템을 파라미터로 변환하는 메소드이다.
    def _item_to_params(self, item, column_names: list[str]) -> dict:
        raw = asdict(item)
        return {k: v for k, v in raw.items() if k in column_names}

    # ── 조회 (app.py 의 db.py 함수 대체용) ─────────────────────────────────────

    # car_registrations + regions 조인 결과를
    # (region_name, stat_year, count) 컬럼의 DataFrame 으로 반환한다.
    # db.fetch_registrations() 와 동일한 반환 형식이다.
    def fetch_registrations(self) -> pd.DataFrame:
        df = self.fetch_all(CarRegistrationItem)
        return df[['region_name', 'stat_year', 'count']]

    # hydrogen_charging_station + regions 조인 결과를
    # (station_name, address, lat, lon, region_name) 컬럼의 DataFrame 으로 반환한다.
    # db.fetch_stations() 와 동일한 반환 형식이다.
    def fetch_stations(self) -> pd.DataFrame:
        df = self.fetch_all(StationItem)
        return df[['station_name', 'address', 'lat', 'lon', 'region_name']]

    # faq 테이블 전체를 (question, answer) 튜플 리스트로 반환한다.
    # db.fetch_faqs() 와 동일한 반환 형식이다.
    def fetch_faqs(self) -> list[tuple[str, str]]:
        with self.engine.connect() as conn:
            rows = conn.execute(
                text('SELECT question, answer FROM faq ORDER BY faq_id')
            ).fetchall()
        return [(r[0], r[1] or '') for r in rows]

    # car_registration 의 마지막 크롤링 시각을 반환한다.
    # 기록이 없으면 None 을 반환한다.
    # db.fetch_car_last_crawled() 와 동일한 반환 형식이다.
    def fetch_car_last_crawled(self) -> datetime | None:
        with self.engine.connect() as conn:
            row = conn.execute(
                text("SELECT last_crawled_at FROM crawl_stat WHERE target_type = 'car_registration'")
            ).fetchone()
        if row and row[0]:
            return row[0] if isinstance(row[0], datetime) else datetime.fromisoformat(str(row[0]))
        return None

    # faq 의 마지막 크롤링 시각을 반환한다.
    # 기록이 없으면 None 을 반환한다.
    # db.fetch_faq_last_crawled() 와 동일한 반환 형식이다.
    def fetch_faq_last_crawled(self) -> datetime | None:
        with self.engine.connect() as conn:
            row = conn.execute(
                text("SELECT last_crawled_at FROM crawl_stat WHERE target_type = 'faq'")
            ).fetchone()
        if row and row[0]:
            return row[0] if isinstance(row[0], datetime) else datetime.fromisoformat(str(row[0]))
        return None

    # ── 일반 조회 ────────────────────────────────────────────────────────────────

    # DB의 지정한 테이블에서 저장된 전체 데이터를 조회하여 반환하는 메소드이다.
    def fetch_all(
            self,
            model_class,
            group_type: Literal['', 'year', 'region']=''
        ) -> pd.DataFrame:
        # 전체 데이터를 조회하는 SQL을 만든다.
        sql = self._build_fetch_all_sql(model_class, group_type)

        # SQL 실행 결과를 pandas DataFrame으로 반환한다.
        return pd.read_sql(text(sql), self.engine)

    # 데이터를 조회할 테이블과 그룹 방식에 따라 SQL을 만드는 메소드이다.
    # 그룹 방식을 정하는 group_type은 자동차 등록 정보를 조회할 때만 사용한다.
    def _build_fetch_all_sql(
            self,
            model_class,
            group_type: Literal['', 'year', 'region']=''
        ) -> str:
        # 자동차 등록 현황인 경우
        if model_class is CarRegistrationItem:
            return self._build_car_registration_sql(group_type)

        # FAQ인 경우
        elif model_class is FaqItem:
            return '''
            SELECT
                faq_id,
                question,
                answer
            FROM faq
            '''

        # 충전소인 경우
        elif model_class is StationItem:
            # 지도에 나타낼 수 없는 위도와 경도가 저장되지 않은 데이터는 제외한다.
            return '''
            SELECT
                r.region_id,
                r.region_name,
                h.station_name,
                h.address,
                h.lat,
                h.lon
            FROM hydrogen_charging_station h
            JOIN regions r USING (region_id)
            WHERE h.lat IS NOT NULL
                AND h.lon IS NOT NULL
            '''

        # CrawlStat 은 models.py 에 정의되지 않아 사용할 수 없다.
        # elif model_class is CrawlStat:
        #     return '''
        #     SELECT
        #         target_type,
        #         last_crawled_at
        #     FROM crawl_stat
        #     '''

        # 예외 처리
        else:
            raise TypeError(f'Unsupported model type: {model_class.__name__}')

    # 지정한 그룹 방식에 따라 자동차 등록 정보를 모두 조회하는 SQL을 만드는 메소드이다.
    def _build_car_registration_sql(
            self,
            group_type: Literal['', 'year', 'region']=''
        ) -> str:
        # 연도 컬럼을 기준으로 그룹핑한다.
        if group_type == 'year':
            return '''
            SELECT
                stat_year,
                SUM(count) AS total_count
            FROM car_registrations
            GROUP BY stat_year
            ORDER BY stat_year
            '''

        # 지역코드 컬럼을 기준으로 그룹핑한다.
        # group_type='region' 은 지역별 전체 기간 합계를 반환한다.
        # stat_year 기준 그룹핑이 없으므로 SELECT 에서도 stat_year 를 제외한다.
        elif group_type == 'region':
            return '''
            SELECT
                r.region_id,
                r.region_name,
                SUM(c.count) AS total_count
            FROM car_registrations c
            JOIN regions r USING (region_id)
            GROUP BY r.region_id, r.region_name
            ORDER BY r.region_id
            '''

        # 컬럼이 지정되지 않으면 그룹핑 하지 않는다.
        return '''
        SELECT
            r.region_id,
            r.region_name,
            c.stat_year,
            c.count
        FROM car_registrations c
        JOIN regions r USING (region_id)
        ORDER BY c.stat_year, r.region_id
        '''
