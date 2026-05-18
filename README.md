# 물로간다

국토교통부 통계누리와 공공데이터 포털에서 수소차 등록 현황 및 수소충전소 데이터를 크롤링하여 MySQL에 저장하고, Streamlit으로 시각화하는 프로젝트입니다.

----------------------------------------------------------
## 1. 프로젝트 구조

```
SKN32-1st-3Team/
├─ app.py                   # 전국 수소충전소 지도 (Streamlit)
├─ common/
│  ├─ __init__.py
│  ├─ exceptions.py
│  └─ mysqlConnectTemplate.py
├─ crawling/
│  ├─ crawler_molit.py      # 국토교통부 수소차 등록 현황 크롤러
│  ├─ crawler_station.py    # 공공데이터 포털 수소충전소 크롤러
│  ├─ crawler_faq_ev.py       # EV 무공해차 통합누리집 FAQ 크롤러
│  ├─ load_station_csv.py   # 충전소 CSV → DB 수동 적재
│  ├─ db.py                 # MySQL 연결·스키마·조회 함수
│  ├─ models.py             # 데이터 클래스
│  ├─ molit_downloads/      # MOLIT 엑셀 임시 저장 (자동 생성)
│  └─ station_downloads/    # 충전소 CSV 저장 (자동 생성)
├─ data/
│  └─ __init__.py
├─ dbscript/
│  └─ dbscript.sql          # DB 스키마 SQL
├─ model/
│  └─ __init__.py
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
## 3. 환경 설정

### 가상환경 및 패키지 설치

```bash
cd SKN32-1st-3Team
python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt
playwright install chromium
```

### `.env` 파일

프로젝트 루트에 `.env` 파일을 생성하고 DB 접속 정보를 입력합니다.

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=your_user
DB_PASSWORD=your_password
DB_NAME=crawler_db
```

### DB 스키마 생성

`dbscript/dbscript.sql`을 MySQL에서 한 번 실행합니다.

```bash
mysql -u your_user -p < dbscript/dbscript.sql
```
또는 MySQL Workbench에서서 실행합니다.
```
1. 상단에서 Database → Connect to Database
   서버 선택 후 접속
2. 상단 메뉴에서 File → Open SQL Script
3. dbscript/dbscript.sql 파일 선택
4. SQL 에디터에 스크립트가 열리면
5. 상단 번개 아이콘(⚡) 또는 Ctrl + Shift + Enter (전체 스크립트 실행)
```

----------------------------------------------------------
## 4. 실행 방법

프로젝트 루트에서 실행합니다.

### 크롤러

```bash
# 수소충전소 데이터 크롤링 및 DB 저장
python -m crawling.crawler_station

# 수소차 등록 현황 크롤링 및 DB 저장
python -m crawling.crawler_molit

# EV 무공해차 통합누리집 FAQ 크롤링 및 DB 저장
python crawling/crawler_faq_ev.py

# CSV 수동 적재 (load_station_csv.py의 CSV_PATH 지정 후)
python -m crawling.load_station_csv
```

### 대시보드 (Streamlit)

```bash
# 충전소 지도
python -m streamlit run app.py
```

----------------------------------------------------------
## 4. ERD

![ERD](assets/ERD.png)
