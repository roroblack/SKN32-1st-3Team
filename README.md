# 물로간다

----------------------------------------------------------
## 1. 프로젝트 구조

```
SKN32-1st-3Team/
├─ app.py                   # 전국 수소충전소 지도 (Streamlit)
├─ assets/
│  ├─ ERD.png
├─ crawling/
│  ├─ __init__.py
│  ├─ crawler_molit.py      # 국토교통부 수소차 등록 현황 크롤러
│  ├─ crawler_station.py    # 공공데이터 포털 수소충전소 크롤러
│  ├─ crawler_faq_ev.py       # EV 무공해차 통합누리집 FAQ 크롤러
│  ├─ models.py             # 데이터 클래스
│  ├─ molit_downloads/      # MOLIT 엑셀 임시 저장 (자동 생성)
│  └─ station_downloads/    # 충전소 CSV 저장 (자동 생성)
├─ data/
│  ├─ __init__.py
│  ├─ db.py                 # MySQL 연결·스키마·조회 함수
│  ├─ repository.py
│  └─ service.py
├─ dbscript/
│  ├─ __init__.py
│  └─ dbscript_table.sql          # DB 스키마 SQL
├─ requirements.txt
└─ README.md
```

----------------------------------------------------------
## 2. 개발 환경

### 하드웨어 스펙

|   항목    |                   사양                    |
|-----------|-------------------------------------------|
| CPU       | Intel Core i5-1135G7 @ 2.40GHz (11th Gen) |
| RAM       | 16GB                                      |
| GPU       | Intel Iris Xe Graphics (공유 메모리 1GB)  |
| 저장장치  | SAMSUNG MZVLQ256HAJD (NVMe SSD, 256GB)    |
| OS        | Microsoft Windows 11 Pro (64비트)         |

### 소프트웨어 스펙

|         항목          |   버전    |
|-----------------------|-----------|
| Visual Studio Code    | 1.120.0   |
| Python                | 3.12.7    |
| pip                   | 26.1.1    |
| Streamlit             | 1.57.0    |
| APScheduler           | 3.11.2    |
| Playwright            | 1.59.0    |
| BeautifulSoup4        | 4.14.3    |
| lxml                  | 6.1.0     |
| SQLAlchemy            | 2.0.49    |
| PyMySQL               | 1.1.3     |
| Pandas                | 3.0.3     |
| Plotly                | 6.7.0     |
| requests              | 2.34.2    |
| openpyxl              | 3.1.5     |
| python-dotenv         | 1.2.2     |

----------------------------------------------------------
## 3. 실행 방법

```bash
cd SKN32-1st-2Team
python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt
playwright install chromium

streamlit run app.py
```
