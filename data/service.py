import logging

from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)


# 크롤러와 DB를 연결하는 서비스 클래스이다.
class CrawlService:
    def __init__(self, crawler, repository=None):
        # 실행할 크롤러 객체를 받는다.
        self.crawler = crawler
        # 아이템 목록을 반환하는 크롤러(MolitCarCrawler, EvFaqCrawler 등)는
        # repository를 통해 DB에 저장한다.
        # 직접 DB에 저장하는 크롤러(StationCrawler 등)는 None으로 둬도 된다.
        self.repository = repository

    # 크롤러를 실행하고 결과를 DB에 저장하는 메소드이다.
    def crawl_and_save(self):
        try:
            result = self.crawler.crawl()
        except Exception as e:
            logger.error(f"[CrawlService] 크롤링 중 오류 발생: {e}")
            return 0

        # crawl()이 int를 반환하면 크롤러가 DB 저장까지 직접 처리한 것이다.
        # (StationCrawler 등)
        if isinstance(result, int):
            logger.info(f"[CrawlService] {result}건 저장 완료")
            return result

        # crawl()이 아이템 목록을 반환하면 repository를 통해 DB에 저장한다.
        if not result:
            return 0

        if self.repository is None:
            logger.warning("[CrawlService] repository가 없어 저장을 건너뜁니다.")
            return 0

        count = self.repository.save_items(result)
        logger.info(f"[CrawlService] {count}건 저장 완료")
        return count


# 스케줄러를 관리하는 클래스이다.
class SchedulerService:
    JOB_ID = 'auto_crawling_job'

    def __init__(self, crawl_service: CrawlService):
        # 백그라운드 스케줄러 객체를 만든다.
        self.scheduler = BackgroundScheduler()

        # 스케줄러가 실행할 크롤링 서비스 객체를 주입받는다.
        # app.py에서 CrawlService(StationCrawler()) 등을 만들어 전달한다.
        self.service = crawl_service
    
    # 스케줄러를 시작하는 메소드이다.
    def start(self):
        # 스케줄러가 이미 실행 중인지 확인한다.
        # 실행 중이 아니면 시작한다.
        if not self.scheduler.running:
            self.scheduler.start()
    
    # 스케줄러를 종료하는 메소드이다.
    def shutdown(self):
        # 스케줄러가 이미 실행 중인지 확인한다.
        # 실행 중이면 종료한다.
        if self.scheduler.running:
            self.scheduler.shutdown()

    # 분 단위 interval 방식의 자동 실행 작업을 등록하는 메소드이다.
    def add_interval_job(self, minutes: int):
        # 기존에 등록된 작업이 있으면 먼저 삭제하여 중복을 방지한다.
        self.remove_job()

        # APScheduler에 작업을 등록한다.
        self.scheduler.add_job(
            func=self.service.crawl_and_save, # 실행할 함수
            trigger="interval", # interval 방식: 일정 간격으로 반복 실행한다.
            minutes=minutes, # 몇 분마다 실행할지 지정한다.
            id=self.JOB_ID, # 작업을 삭제하거나 조회할 때 사용한다.
            replace_existing=True, # 같은 ID의 작업이 있으면 교체한다.
            misfire_grace_time=300, # 작업이 예정보다 얼마나 늦게 실행되어도 허용할지 초 단위로 지정한다.
            coalesce=True, # 실행 시점이 밀린 작업들을 한 번만 실행한다.
            max_instances=1 # 같은 작업이 동시에 실행될 수 있는 개수를 제한한다.
        )

    # cron 방식의 자동 실행 작업을 등록한다.
    def add_cron_job(self, hour: int, minute: int):
        # 기존 작업이 있으면 먼저 삭제한다.
        self.remove_job()

        # APScheduler에 cron 작업을 등록한다.
        self.scheduler.add_job(
            func=self.service.crawl_and_save, # 실행할 함수
            trigger="cron", # cron 방식: 매일 특정 시각에 실행한다.
            hour=hour, # 실행할 시각
            minute=minute, # 실행할 분
            id=self.JOB_ID, # 작업을 삭제하거나 조회할 때 사용한다.
            replace_existing=True, # 같은 ID의 작업이 있으면 교체한다.
            misfire_grace_time=300, # 작업이 예정보다 얼마나 늦게 실행되어도 허용할지 초 단위로 지정한다.
            coalesce=True, # 실행 시점이 밀린 작업들을 한 번만 실행한다.
            max_instances=1 # 같은 작업이 동시에 실행될 수 있는 개수를 제한한다.
        )

    # 등록된 스케줄 작업을 삭제하는 메소드이다.
    def remove_job(self):
        # 지정한 ID의 작업을 찾는다.
        job = self.scheduler.get_job(self.JOB_ID)

        # 해당 작업이 존재하면 삭제한다.
        if job:
            self.scheduler.remove_job(self.JOB_ID)

    # 현재 등록된 모든 스케줄 작업을 반환하는 메소드이다.
    def get_jobs(self):
        return self.scheduler.get_jobs()

    # 등록된 job을 일시정지한다.
    def pause(self):
        job = self.scheduler.get_job(self.JOB_ID)
        if job:
            self.scheduler.pause_job(self.JOB_ID)

    # 일시정지된 job을 재개한다.
    def resume(self):
        job = self.scheduler.get_job(self.JOB_ID)
        if job:
            self.scheduler.resume_job(self.JOB_ID)

    # job이 등록되어 있고 일시정지 상태가 아니면 True를 반환한다.
    # APScheduler에서 일시정지된 job은 next_run_time 이 None 이 된다.
    def is_job_running(self) -> bool:
        job = self.scheduler.get_job(self.JOB_ID)
        return job is not None and job.next_run_time is not None

    # 현재 등록된 job의 실행 주기를 분 단위로 반환한다. job이 없으면 None.
    def get_interval_minutes(self) -> int | None:
        job = self.scheduler.get_job(self.JOB_ID)
        if job is None:
            return None
        try:
            return int(job.trigger.interval.total_seconds() / 60)
        except AttributeError:
            return None
