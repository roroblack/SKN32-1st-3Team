from apscheduler.schedulers.background import BackgroundScheduler

from data.repository import Repository

# 테스트용
from model.models import CarRegistrationItem, FaqItem, StationItem
from datetime import datetime

# 크롤러와 DB를 연결하는 서비스 클래스이다.
class CrawlService:
    def __init__(self):
        # 크롤러 클래스 작성 후 변경
        # self.crawler = Crawler()

        self.repository = Repository()

    # 크롤러를 실행하고 가져온 아이템들을 DB에 저장하는 메소드이다.
    def crawl_and_save(self):
        # 크롤러를 실행하여 아이템 리스트를 가져온다.
        # 크롤러 클래스 작성 후 변경
        # items = self.crawler.crawl()

        # 테스트용 아이템 리스트
        items = [CarRegistrationItem(1, 2024, 65000, datetime.now()),
                 CarRegistrationItem(1, 2025, 80000, datetime.now()),
                 CarRegistrationItem(1, 2026, 90000, datetime.now())]

        # items = [FaqItem('Question1', 'Answer1', datetime.now()),
        #          FaqItem('Question2', 'Answer2', datetime.now()),
        #          FaqItem('Question3', 'Answer3', datetime.now())]

        # items = [StationItem(0, 'Seoul Station', 'Seoul', 72.1386, 65.9432, datetime.now()),
        #          StationItem(1, 'Incheon Station', 'Incheon', 70.6276, 62.9582, datetime.now()),
        #          StationItem(2, 'Busan Station', 'Busan', 68.1527, 70.1382, datetime.now())]

        # 아이템 리스트를 DB에 저장한다.
        self.repository.save_items(items)


# UI 연결 작업 후 테스트 필요
# 스케줄러를 관리하는 클래스이다.
class SchedulerService:
    def __init__(self):
        # 백그라운드 스케줄러 객체를 만든다.
        self.scheduler = BackgroundScheduler()

        # 스케줄러가 실행할 크롤링 서비스 객체를 만든다.
        self.service = CrawlService()
    
    # 스케줄러를 시작하는 메소드이다.
    def start(self):
        # 스케줄러가 이미 실행 중인지 확인한다.
        # 실행 중이 아니면 시작한다.
        if not self.scheduler.running:
            self.scheduler.start()

    # 분 단위 interval 방식의 자동 실행 작업을 등록하는 메소드이다.
    def add_interval_job(self, minutes: int):
        # 기존에 등록된 작업이 있으면 먼저 삭제하여 중복을 방지한다.
        self.remove_job()

        # APScheduler에 작업을 등록한다.
        self.scheduler.add_job(
            # 실행할 함수
            func=self.service.crawl_and_save,

            # interval 방식: 일정 간격으로 반복 실행한다.
            trigger="interval",

            # 몇 분마다 실행할지 지정한다.
            minutes=minutes,

            # 작업을 삭제하거나 조회할 때 사용한다.
            id="auto_crawling_job",

            # 같은 ID의 작업이 있으면 교체한다.
            replace_existing=True
        )

    # cron 방식의 자동 실행 작업을 등록한다.
    def add_cron_job(self, hour: int, minute: int):
        # 기존 작업이 있으면 먼저 삭제한다.
        self.remove_job()

        # APScheduler에 cron 작업을 등록한다.
        self.scheduler.add_job(
            # 실행할 함수
            func=self.service.crawl_and_save,

            # cron 방식: 매일 특정 시각에 실행한다.
            trigger="cron",

            # 실행할 시각
            hour=hour,

            # 실행할 분
            minute=minute,

            # 작업을 삭제하거나 조회할 때 사용한다.
            id="auto_crawling_job",

            # 같은 ID의 작업이 있으면 교체한다.
            replace_existing=True
        )

    # 등록된 스케줄 작업을 삭제하는 메소드이다.
    def remove_job(self):
        # 지정한 ID의 작업을 찾는다.
        job = self.scheduler.get_job("auto_crawling_job")

        # 해당 작업이 존재하면 삭제한다.
        if job:
            self.scheduler.remove_job("auto_crawling_job")

    # 현재 등록된 모든 스케줄 작업을 반환하는 메소드이다.
    def get_jobs(self):
        return self.scheduler.get_jobs()
