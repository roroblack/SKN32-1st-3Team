from datetime import datetime
from typing import Literal

import pandas as pd
from dataclasses import asdict, fields
from sqlalchemy import text


from crawling.models import *
from data.db import get_engine

# DB 작업을 처리하는 클래스이다.
class Repository:
    # 아이템의 모델에 따라 DB에 추가하는 SQL 사전이다.
    # SQL Injection 위험을 낮추기 위해 바인딩 방식을 사용한다.
    MODEL_INSERT_SQL = {
        CarRegistrationItem:'''
            INSERT INTO car_registrations (
                region_id,
                stat_year,
                count
            )
            VALUES (
                :region_id,
                :stat_year,
                :count
            )
        ''',
        FaqItem:'''
            INSERT INTO faq (
                question,
                answer
            )
            VALUES (
                :question,
                :answer
            )
        ''',
        StationItem:'''
            INSERT INTO hydrogen_charging_station (
                region_id,
                station_name,
                address,
                lat,
                lon
            )
            VALUES (
                :region_id,
                :station_name,
                :address,
                :lat,
                :lon
            )
        '''
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
        return get_engine()
    
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
        
        # 데이터 모델 클래스의 컬럼명을 불러온다.
        column_names = [column.name for column in fields(model_class)]

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
        # if issubclass(model_class, CarRegistrationItem):
        if model_class is CarRegistrationItem:
            return self._build_car_registration_sql(group_type)
        
        # FAQ인 경우
        # elif issubclass(model_class, FaqItem):
        elif model_class is FaqItem:
            return '''
            SELECT
                faq_id,
                question,
                answer
            FROM faq
            '''
        
        # 충전소인 경우
        # elif issubclass(model_class, StationItem):
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
        
        # 크롤링 상태인 경우
        elif model_class is CrawlStat:
            return '''
            SELECT
                target_type,
                last_crawled_at
            FROM crawl_stat
            '''
        
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
            return f'''
            SELECT
                stat_year,
                SUM(count) AS total_count,
            FROM car_registrations
            GROUP BY stat_year
            ORDER BY stat_year
            '''
        
        # 지역코드 컬럼을 기준으로 그룹핑한다.
        elif group_type == 'region':
            return f'''
            SELECT
                r.region_id,
                r.region_name,
                c.stat_year,
                SUM(c.count) AS total_count,
            FROM car_registrations c
            JOIN regions r USING (region_id)
            GROUP BY r.region_id, r.region_name
            ORDER BY r.region_id
            '''
        
        # 컬럼이 지정되지 않으면 그룹핑 하지 않는다.
        return f'''
        SELECT
            r.region_id,
            r.region_name,
            c.stat_year,
            c.count
        FROM car_registrations c
        JOIN regions r USING (region_id)
        ORDER BY c.stat_year, r.region_id
        '''
