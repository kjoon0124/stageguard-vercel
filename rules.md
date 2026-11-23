# Rules & Constraints Specification Document (rules.md)
## 프로젝트명: StageGuard

### 1. 환경 및 실행 방식 (Environment & Execution)
- **로컬 싱글 애플리케이션:** 클라우드/서버 배포용이 아닌, PC 로컬 환경에서 단독 실행되는 Streamlit 웹 앱 형태로 개발한다.
- **Python 버전:** 3.9 이상 권장
- **실행 명령:** `streamlit run app.py`

### 2. 기술 스택 및 라이브러리 (Tech Stack)
- **UI Framework:** Streamlit (`streamlit`)
- **Data Manipulation:** Pandas (`pandas`)
- **Visualization:** Plotly Express / Graphic Objects (`plotly`)
- **기타 외부 API 금지:** 외부 유료 API나 별도 DB 연결 없이, Streamlit `st.session_state` 및 로컬 메모리를 활용한다.

### 3. 코딩 표준 및 코드 스타일 (Coding Standards)
- **UI 언어:** 앱의 모든 레이아웃, 버튼명, 그래프 라벨, 메시지는 **한국어**로 작성한다.
- **모듈화:** 코드 작성 시 메인 파일(`app.py`) 하나에 작성하되, 함수(위험 점수 산출 함수, Plotly 그래프 생성 함수 등)로 구분을 명확히 한다.
- **예외 처리:** 사용자가 입력값을 누락하거나 빈 데이터 상태일 때 앱이 튕기지 않도록 `st.warning()` 또는 데이터 수 유효성 검사 로직을 포함한다.
- **데이터 저장:** 사용자가 입력한 위험성 평가 데이터는 메모리에 유지되며, 필요한 경우 CSV 파일 내보내기(`st.download_button`) 기능을 제공한다.