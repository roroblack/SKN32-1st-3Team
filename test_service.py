from data.service import CrawlService

from common.constants import ALLOWED_MODELS

# 모듈 테스트
if __name__ == '__main__':
    service = CrawlService()
    # service.crawl_and_save()

    print(service.repository.find_all(ALLOWED_MODELS[1]))
