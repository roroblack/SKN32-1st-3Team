# 물로간다

----------------------------------------------------------
## 1. 프로젝트 구조

```
SKN32-1st-3Team/
├─ common/
│  ├─ __init__.py
│  ├─ exceptions.py
│  └─ mysqlConnectTemplate.py
├─ crawling/
│  └─ __init__.py
├─ data/
│  └─ __init__.py
├─ dbscript/
│  └─ __init__.py
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
## 3. 실행 방법

```bash
cd SKN32-1st-2Team
python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt
playwright install chromium

streamlit run app.py
```

----------------------------------------------------------
## 4. ERD

![ERD](assets/ERD.png)
