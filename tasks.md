# Tasks Specification Document (tasks.md)
## 프로젝트명: StageGuard

- [x] **Task 1: 개발 환경 설정 및 프로젝트 기본 프레임 구축**
  - Streamlit, Pandas, Plotly 라이브러리 가상환경 설치
  - 메인 파이썬 실행 파일(`app.py`) 생성 및 기본 제목/레이아웃(페이지 설정, 메인 타이틀) 작성

- [x] **Task 2: 사이드바 입력 UI 및 데이터 세션 관리 구현**
  - 사이드바에 작업명, 위치(X, Y), 위험 요소, 가능성(1~5), 중대성(1~5) 입력 필드 구성
  - Streamlit의 `st.session_state`를 활용하여 사용자가 추가한 작업 데이터를 메모리에 누적 저장하는 로직 구현

- [x] **Task 3: 위험성 평가(Risk Matrix) 산출 로직 구현**
  - 위험 점수(`risk_score = likelihood * severity`) 연산 파이썬 함수 구현
  - 점수별 위험 등급(15점 이상 Red, 8~14점 Yellow, 7점 이하 Green) 판정 로직 작성
  - 메인 화면 상단에 총 작업 수, 고위험 작업 수 등을 보여주는 요약 카포(Metric)배치

- [x] **Task 4: 무대 레이아웃 및 2D 동선 시각화(Plotly) 구현**
  - Plotly Scatter Plot을 사용하여 무대 평면 좌표계 상에 작업 위치 렌더링
  - 위험 등급(Red/Yellow/Green)에 따른 마커 색상 차별화 및 작업 이동 동선 연결 시각화

- [x] **Task 5: 고위험 안전 가이드라인 출력 및 데이터 내보내기**
  - Red 등급 판정 작업 감지 시 하단에 필수 개인보호구(PPE) 및 안전 수칙 체크리스트 출력
  - 수집된 위험성 평가 데이터프레임을 CSV 파일로 다운로드할 수 있는 버튼 구현
