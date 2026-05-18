from data.repository import Repository
from data.service import CrawlService, SchedulerService

from model.models import CarRegistrationItem, FaqItem, StationItem

# 모듈 테스트
if __name__ == '__main__':
    repository = Repository()
    service = CrawlService(None, repository)
    # service.crawl_and_save()

    # print(service.repository.fetch_all(CarRegistrationItem, 'year'))
    # print(service.repository.fetch_all(CarRegistrationItem, 'region'))
    # print(service.repository.fetch_all(FaqItem))
    print(service.repository.fetch_all(StationItem))
