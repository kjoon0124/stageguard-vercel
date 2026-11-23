# Design Specification Document (design.md)
## 프로젝트명: StageGuard (무대 설비 작업 위험성 평가 및 동선 시뮬레이터)

### 1. 시스템 아키텍처 및 데이터 플로우 노드 맵 (Architecture & Data Flow)

```mermaid
flowchart TD
    subgraph UI_Sidebar ["사이드바 (Sidebar) - 사용자 입력"]
        IN1["작업 단계명 (task_name)"]
        IN2["무대 좌표 (x_coord, y_coord)"]
        IN3["작업 분류 및 위험 요소 (hazard_element)"]
        IN4["발생 가능성 L (1~5) & 피해 중대성 S (1~5)"]
        BTN["작업 데이터 추가 버튼"]
    end

    subgraph State ["상태 관리 (st.session_state)"]
        STATE_DATA["작업 데이터프레임 (Tasks DataFrame)"]
        STATE_SAMPLE["샘플 시나리오 로드 / 전체 삭제 / CSV 입출력"]
    end

    subgraph RiskEngine ["위험성 평가 엔진 (Risk Matrix Engine)"]
        CALC["점수 연산: risk_score = L × S"]
        JUDGE{"위험 등급 판정"}
        GRADE_RED["Red (고위험: 15~25점)"]
        GRADE_YELLOW["Yellow (중위험: 8~14점)"]
        GRADE_GREEN["Green (저위험: 1~7점)"]
    end

    subgraph VisEngine ["시각화 엔진 (Visualization Engine)"]
        STAGE_MAP["무대 평면도 2D 레이아웃 (본무대, 에이프런, 백스테이지)"]
        ROUTE_LINE["작업자 이동 동선 (Line)"]
        RISK_MARKER["위험도별 컬러 마커 (Scatter)"]
        HAZARD_ZONE["고위험(Red) 구간 2.5m 위험반경 서클 강조"]
    end

    subgraph GuideEngine ["안전 가이드라인 엔진 (Guideline Engine)"]
        PPE_REC["맞춤형 필수 개인보호구(PPE) 자동 추천"]
        CHECKLIST["위험요인별 작업 전 안전수칙 체크리스트"]
    end

    subgraph MainDashboard ["메인 화면 레이아웃 (Main Dashboard)"]
        D_TOP["상단: Dashboard Summary Metrics (총 작업수, 등급별 건수, 평균 위험도)"]
        D_MID["중단: Plotly 2D 인터랙티브 동선 맵 & 5x5 위험 매트릭스"]
        D_BOT_LEFT["하단 좌측: 전체 작업 데이터 시트 & CSV 다운로드"]
        D_BOT_RIGHT["하단 우측: 고위험 작업 대상 필수 안전수칙 체크리스트"]
    end

    %% 노드 간 데이터 및 제어 흐름 연결
    IN1 & IN2 & IN3 & IN4 --> BTN
    BTN --> STATE_DATA
    STATE_SAMPLE <--> STATE_DATA

    STATE_DATA --> CALC
    CALC --> JUDGE
    JUDGE -->|Score >= 15| GRADE_RED
    JUDGE -->|8 <= Score <= 14| GRADE_YELLOW
    JUDGE -->|Score <= 7| GRADE_GREEN

    GRADE_RED & GRADE_YELLOW & GRADE_GREEN --> RISK_MARKER
    STATE_DATA --> ROUTE_LINE
    STAGE_MAP & ROUTE_LINE & RISK_MARKER --> D_MID
    GRADE_RED -.->|고위험 반경 강조| HAZARD_ZONE --> D_MID

    GRADE_RED ==>|고위험 작업 감지 시 트리거| GuideEngine
    PPE_REC & CHECKLIST --> D_BOT_RIGHT

    STATE_DATA --> D_TOP
    STATE_DATA --> D_BOT_LEFT
```

### 2. 시스템 아키텍처 상세 (System Architecture)
- **Architecture Type:** Streamlit 기반 단일 파일/모듈형 로컬 웹 애플리케이션
- **Data Flow:** 
  1. 사용자 입력 (작업명, 위치 X/Y, 위험 요소, 가능성 L, 중대성 S)
  2. 위험성 평가 엔진 (Score = L × S 계산 및 Risk Grade 판정)
  3. 시각화 엔진 (Plotly 기반 2D 무대 평면도 맵 렌더링)
  4. 가이드라인 엔진 (고위험 요소 감지 시 안전 수칙 및 필수 PPE 팝업/출력)

### 3. 화면 레이아웃 구조 (UI Layout)
- **사이드바 (Sidebar):**
  - [입력 폼] 작업 단계 이름, 무대 내 X/Y 좌표, 작업 유형 선택
  - [위험성 평가] 발생 가능성 (1~5), 피해 중대성 (1~5) 슬라이더/드롭다운
  - [버튼] "작업 데이터 추가" 버튼
- **메인 영역 (Main Content Area):**
  - **상단 (Dashboard Summary):** 총 등록 작업 수, 고위험(Red) 작업 수, 위험도 지수 요약 카포(Metric)
  - **중단 (Visual Map):** Plotly 2D Scatter Plot (무대 레이아웃 상의 작업 위치 및 위험도별 색상 마커)
  - **하단 (Table & Guide):** 전체 작업 위험성 평가 데이터프레임(Table) 및 고위험 작업 대상 필수 안전 수칙 체크리스트

### 4. 데이터 구조 (Data Schema)
- **DataFrame Structure:**
  - `task_name` (str): 작업명 (예: 트러스 조립, 조명 타워 설치)
  - `x_coord` (float): 무대 X 좌표
  - `y_coord` (float): 무대 Y 좌표
  - `likelihood` (int): 발생 가능성 (1~5)
  - `severity` (int): 중대성 (1~5)
  - `risk_score` (int): 가능성 × 중대성
  - `risk_grade` (str): Red (>=15), Yellow (8~14), Green (<=7)
