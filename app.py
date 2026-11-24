"""
StageGuard - 무대 설비 작업 위험성 평가 및 동선 시뮬레이터
=========================================================
작성 목적: 방송·공연 무대 설치/해체 현장에서 작업자의 동선과 위험 요소를
          정량적으로 평가하고 시각화하여 현장 안전사고를 예방합니다.
기술 스택: Python, Streamlit, Pandas, Plotly
"""

import io
import os
import re
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ==============================================================================
# 1. 페이지 설정 및 전역 스타일 (Page Configuration & Custom Styling)
# ==============================================================================
st.set_page_config(
    page_title="StageGuard - 무대 설비 작업 위험성 평가 및 동선 시뮬레이터",
    page_icon="🎭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 커스텀 CSS (세련된 다크/라이트 안전 관제 대시보드 UI)
st.markdown(
    """
    <style>
    /* 메인 타이틀 배너 */
    .main-header {
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
        color: #F8FAFC;
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        border-left: 6px solid #EF4444;
    }
    .main-header h1 {
        color: #FFFFFF;
        font-size: 1.85rem;
        font-weight: 700;
        margin-bottom: 0.3rem;
    }
    .main-header p {
        color: #94A3B8;
        font-size: 0.95rem;
        margin-bottom: 0;
    }
    
    /* 위험 등급 배지 */
    .badge-red {
        background-color: #FEE2E2;
        color: #991B1B;
        font-weight: 700;
        padding: 3px 8px;
        border-radius: 6px;
        border: 1px solid #F87171;
    }
    .badge-yellow {
        background-color: #FEF3C7;
        color: #92400E;
        font-weight: 700;
        padding: 3px 8px;
        border-radius: 6px;
        border: 1px solid #FBBF24;
    }
    .badge-green {
        background-color: #D1FAE5;
        color: #065F46;
        font-weight: 700;
        padding: 3px 8px;
        border-radius: 6px;
        border: 1px solid #34D399;
    }
    
    /* 안전 체크리스트 카드 */
    .checklist-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-left: 5px solid #EF4444;
        border-radius: 8px;
        padding: 1rem 1.25rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .checklist-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #0F172A;
        margin-bottom: 0.5rem;
    }
    .ppe-tag {
        display: inline-block;
        background-color: #EFF6FF;
        color: #1D4ED8;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-right: 6px;
        margin-bottom: 4px;
        border: 1px solid #BFDBFE;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==============================================================================
# 2. 비즈니스 로직 및 모듈화 함수 (Core Logic & Modules)
# ==============================================================================

def calculate_risk(likelihood: int, severity: int) -> tuple[int, str, str, str]:
    """
    발생 가능성(Likelihood, 1~5)과 피해 중대성(Severity, 1~5)을 기반으로
    위험 점수(Score = L x S) 및 등급(Red/Yellow/Green)을 산출합니다.
    
    - Red (고위험): 15점 이상
    - Yellow (중위험): 8 ~ 14점
    - Green (저위험): 7점 이하
    
    Returns:
        (risk_score, risk_grade, hex_color, label_kr)
    """
    try:
        score = int(likelihood) * int(severity)
    except (ValueError, TypeError):
        score = 1
        
    if score >= 15:
        return score, "Red", "#EF4444", "고위험 (즉시 개선/특별관리)"
    elif score >= 8:
        return score, "Yellow", "#F59E0B", "중위험 (주의 및 안전조치)"
    else:
        return score, "Green", "#10B981", "저위험 (일반 관리)"


def get_ppe_and_guidelines(hazard_element: str, risk_grade: str) -> dict:
    """
    위험 요소 및 위험 등급에 따라 맞춤형 필수 개인보호구(PPE) 및
    현장 안전 수칙 체크리스트 항목을 반환합니다.
    """
    # 기본 공통 PPE
    ppe_list = ["산업안전모(턱끈체결)", "안전화(발등보호)"]
    guidelines = [
        "작업 전 TBM(Tool Box Meeting) 실시 및 작업 내용 공유",
        "비상 연락망 및 현장 비상정지 스위치 위치 사전 확인",
    ]
    
    # 위험 요소별 맞춤 대책
    if "추락" in hazard_element or "고소" in hazard_element:
        ppe_list.extend(["안전대(전신 하네스+이중 죔줄)", "추락방지대"])
        guidelines.extend([
            "2m 이상 고소작업 시 반드시 안전대 걸이시설 체결 후 작업",
            "이동식 비계/고소작업대(렌탈) 사용 전 아웃트리거 고정 상태 점검",
            "상부 작업자 2인 1조 작업 및 하부 통제자(신호수) 필수 배치",
        ])
    elif "낙하" in hazard_element or "중량물" in hazard_element or "인양" in hazard_element:
        ppe_list.extend(["보안경", "충격흡수 가죽장갑"])
        guidelines.extend([
            "크레인/호이스트 인양 반경 내 하부 작업자 출입 통제선(바리케이드) 설치",
            "슬링벨트, 샤클, 와이어로프의 마모·변형 상태 사전 점검",
            "수공구 및 부품 낙하 방지용 공구 걸이고리(Lanyard) 체결",
        ])
    elif "감전" in hazard_element or "전기" in hazard_element or "배선" in hazard_element:
        ppe_list.extend(["절연장갑(내전압)", "절연 안전화"])
        guidelines.extend([
            "작업 전 분전반 전원 차단(LOTO: Lock-Out, Tag-Out) 및 검전기로 무전압 확인",
            "임시 배선 피복 손상 여부 및 누전차단기 정상 작동(월간 점검) 확인",
            "모든 조명·음향 기기 외함 접지(Grounding) 상태 필수 점검",
        ])
    elif "협착" in hazard_element or "끼임" in hazard_element or "기계" in hazard_element:
        ppe_list.extend(["내절단 장갑", "밀착형 작업복"])
        guidelines.extend([
            "무대 리프트/승강장치/턴테이블 구동 전 인터록 및 방호가드 점검",
            "작동 중 신체 일부 진입 금지 및 비상정지버튼(E-Stop) 조작원 배치",
            "헐렁한 복장 착용 금지 및 머리카락 묶기 준수",
        ])
    elif "화재" in hazard_element or "폭발" in hazard_element or "특수효과" in hazard_element:
        ppe_list.extend(["방염 작업복", "방진/방독 마스크"])
        guidelines.extend([
            "작업 구역 5m 이내 ABC 분말소화기(2대 이상) 전진 배치",
            "화기 작업 허가서 발급 확인 및 인근 가연물(커튼, 목재) 차단 조치",
            "특수효과(화약, CO2) 배관 가스 누출 여부 점검",
        ])
    else:
        # 일반/기타
        ppe_list.extend(["작업용 면장갑/코팅장갑"])
        guidelines.extend([
            "무대 이동 동선 상 케이블 트렌치/커버 설치로 전도 위험 제거",
            "무대 개구부 및 단차 구간 경고 테이프 부착 및 조도(조명) 확보",
        ])
        
    return {
        "ppe": list(dict.fromkeys(ppe_list)),  # 중복 제거
        "guidelines": guidelines,
    }


def validate_input(task_name: str, x: float, y: float, likelihood: int, severity: int) -> tuple[bool, str]:
    """사용자 입력값에 대한 무결성 및 범위 유효성 검사를 수행합니다."""
    if not task_name or not task_name.strip():
        return False, "작업 단계 이름을 입력해주세요."
    
    if not (-30.0 <= x <= 30.0):
        return False, "X 좌표는 무대 규격(-30m ~ 30m) 범위 내여야 합니다."
        
    if not (-10.0 <= y <= 35.0):
        return False, "Y 좌표는 무대 깊이(-10m ~ 35m) 범위 내여야 합니다."
        
    if not (1 <= likelihood <= 5):
        return False, "발생 가능성은 1에서 5 사이의 값이어야 합니다."
        
    if not (1 <= severity <= 5):
        return False, "피해 중대성은 1에서 5 사이의 값이어야 합니다."
        
    return True, ""


# ==============================================================================
# 3. Plotly 무대 평면도 및 동선 시각화 엔진 (Visualization Engine)
# ==============================================================================

def create_stage_map(df: pd.DataFrame) -> go.Figure:
    """
    무대 평면도(Main Stage, Apron, Backstage, Wings, 객석) 배경 위에
    작업 위치와 이동 동선(Line), 위험도별 색상 마커를 Plotly 2D Scatter로 렌더링합니다.
    """
    fig = go.Figure()

    # --- 1) 무대 평면도 구역 정의 (Layout Shapes) ---
    # 메인 무대 (Main Stage): X [-12, 12], Y [4, 18]
    fig.add_shape(
        type="rect",
        x0=-12, y0=4, x1=12, y1=18,
        line=dict(color="#334155", width=2),
        fillcolor="rgba(241, 245, 249, 0.6)",
        layer="below"
    )
    # 앞무대 (Apron / Front Stage): X [-10, 10], Y [0, 4]
    fig.add_shape(
        type="rect",
        x0=-10, y0=0, x1=10, y1=4,
        line=dict(color="#475569", width=2, dash="dot"),
        fillcolor="rgba(226, 232, 240, 0.4)",
        layer="below"
    )
    # 백스테이지 (Backstage / Rear): X [-12, 12], Y [18, 24]
    fig.add_shape(
        type="rect",
        x0=-12, y0=18, x1=12, y1=24,
        line=dict(color="#64748B", width=1.5, dash="dash"),
        fillcolor="rgba(248, 250, 252, 0.4)",
        layer="below"
    )
    # 좌측 무대 (Stage Left / Wing SL): X [-17, -12], Y [4, 18]
    fig.add_shape(
        type="rect",
        x0=-17, y0=4, x1=-12, y1=18,
        line=dict(color="#94A3B8", width=1, dash="dot"),
        fillcolor="rgba(241, 245, 249, 0.3)",
        layer="below"
    )
    # 우측 무대 (Stage Right / Wing SR): X [12, 17], Y [4, 18]
    fig.add_shape(
        type="rect",
        x0=12, y0=4, x1=17, y1=18,
        line=dict(color="#94A3B8", width=1, dash="dot"),
        fillcolor="rgba(241, 245, 249, 0.3)",
        layer="below"
    )
    # 오케스트라 피트 / 관객석 방향 (Audience): Y < 0
    fig.add_shape(
        type="rect",
        x0=-15, y0=-5, x1=15, y1=-0.5,
        line=dict(color="#CBD5E1", width=1),
        fillcolor="rgba(203, 213, 225, 0.2)",
        layer="below"
    )

    # --- 2) 구역 라벨 주석 (Stage Area Labels) ---
    area_annotations = [
        dict(x=0, y=11, text="<b>본 무대 (Main Stage)</b>", showarrow=False, font=dict(color="#475569", size=14)),
        dict(x=0, y=2, text="앞무대 (Apron)", showarrow=False, font=dict(color="#64748B", size=11)),
        dict(x=0, y=21, text="후무대 (Backstage)", showarrow=False, font=dict(color="#64748B", size=11)),
        dict(x=-14.5, y=11, text="상수 (SL)", showarrow=False, font=dict(color="#94A3B8", size=11)),
        dict(x=14.5, y=11, text="하수 (SR)", showarrow=False, font=dict(color="#94A3B8", size=11)),
        dict(x=0, y=-2.8, text="▼ 객석 방향 (Audience Area) ▼", showarrow=False, font=dict(color="#94A3B8", size=12)),
    ]
    for ann in area_annotations:
        fig.add_annotation(ann)

    # --- 3) 데이터 렌더링 (동선 및 위험 마커) ---
    if df is not None and not df.empty:
        # 작업 순서(순번) 부여
        df_sorted = df.copy()
        if "step_no" not in df_sorted.columns:
            df_sorted["step_no"] = range(1, len(df_sorted) + 1)

        # 3-1. 작업자 이동 동선 (Line Trace)
        fig.add_trace(
            go.Scatter(
                x=df_sorted["x_coord"],
                y=df_sorted["y_coord"],
                mode="lines",
                line=dict(color="#475569", width=2.5, dash="dash"),
                name="작업 이동 동선",
                hoverinfo="skip",
            )
        )

        # 3-2. 고위험(Red) 구간 위험 반경(Hazard Zone) 강조 서클 표시
        red_tasks = df_sorted[df_sorted["risk_grade"] == "Red"]
        for _, row in red_tasks.iterrows():
            fig.add_shape(
                type="circle",
                x0=row["x_coord"] - 2.5,
                y0=row["y_coord"] - 2.5,
                x1=row["x_coord"] + 2.5,
                y1=row["y_coord"] + 2.5,
                line=dict(color="rgba(239, 68, 68, 0.8)", width=1.5, dash="dot"),
                fillcolor="rgba(239, 68, 68, 0.18)",
                layer="below",
            )

        # 3-3. 위험 등급별 개별 마커 Trace (범례 및 툴팁 분리)
        grade_configs = [
            ("Red", "고위험 (Red, >=15)", "#EF4444", 20, "rgba(239, 68, 68, 0.4)"),
            ("Yellow", "중위험 (Yellow, 8~14)", "#F59E0B", 16, "rgba(245, 158, 11, 0.3)"),
            ("Green", "저위험 (Green, <=7)", "#10B981", 13, "rgba(16, 185, 129, 0.2)"),
        ]

        for grade, label, color, marker_size, border_color in grade_configs:
            subset = df_sorted[df_sorted["risk_grade"] == grade]
            if not subset.empty:
                hover_texts = []
                for _, r in subset.iterrows():
                    hover_html = (
                        f"<b>[단계 {r['step_no']}] {r['task_name']}</b><br>"
                        f"--------------------------------<br>"
                        f"• 작업 유형: {r.get('task_type', '일반')}<br>"
                        f"• 주요 위험요소: <b>{r.get('hazard_element', '미정')}</b><br>"
                        f"• 무대 위치: (X: {r['x_coord']}m, Y: {r['y_coord']}m)<br>"
                        f"• 평가: 가능성({r['likelihood']}) × 중대성({r['severity']}) = <b>{r['risk_score']}점</b><br>"
                        f"• 위험 등급: <span style='color:{color}; font-weight:bold;'>{grade}</span>"
                    )
                    hover_texts.append(hover_html)

                fig.add_trace(
                    go.Scatter(
                        x=subset["x_coord"],
                        y=subset["y_coord"],
                        mode="markers+text",
                        marker=dict(
                            size=marker_size,
                            color=color,
                            line=dict(color="#FFFFFF", width=2),
                            symbol="circle",
                        ),
                        text=[str(num) for num in subset["step_no"]],
                        textposition="middle center",
                        textfont=dict(color="#FFFFFF", size=10, family="Arial Black"),
                        name=label,
                        hovertext=hover_texts,
                        hoverinfo="text",
                    )
                )

    # --- 4) 레이아웃 스타일 설정 ---
    fig.update_layout(
        title=dict(
            text="<b>무대 2D 평면도 작업 동선 및 위험 지역 매핑</b>",
            font=dict(size=16, color="#0F172A"),
            x=0.02,
            y=0.96,
        ),
        xaxis=dict(
            title="무대 좌우 폭 (m, 중심=0)",
            range=[-20, 20],
            zeroline=True,
            zerolinecolor="#94A3B8",
            gridcolor="#E2E8F0",
            dtick=5,
        ),
        yaxis=dict(
            title="무대 깊이 (m, 무대 전면=0)",
            range=[-6, 26],
            zeroline=True,
            zerolinecolor="#94A3B8",
            gridcolor="#E2E8F0",
            scaleanchor="x",
            scaleratio=1,  # 1:1 종횡비로 실제 무대 평면도 비례 유지
            dtick=5,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(255, 255, 255, 0.8)",
            bordercolor="#CBD5E1",
            borderwidth=1,
        ),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        margin=dict(l=40, r=40, t=60, b=40),
        height=580,
    )

    return fig


def create_risk_matrix_heatmap(df: pd.DataFrame) -> go.Figure:
    """
    산업안전보건공단 5x5 위험성 평가 매트릭스 그리드를 생성하고,
    현재 등록된 작업들의 분포를 시각화합니다.
    """
    matrix_colors = []
    text_matrix = []
    
    # 5x5 격자 색상 및 텍스트 구성 (Y축: Severity 5->1, X축: Likelihood 1->5)
    for s in range(5, 0, -1):
        color_row = []
        text_row = []
        for l in range(1, 6):
            score = l * s
            if score >= 15:
                color_row.append("#FCA5A5")  # Red 영역
            elif score >= 8:
                color_row.append("#FDE68A")  # Yellow 영역
            else:
                color_row.append("#A7F3D0")  # Green 영역
            
            # 해당 셀에 포함된 작업 수 카운트
            if df is not None and not df.empty:
                count = len(df[(df["likelihood"] == l) & (df["severity"] == s)])
                text_row.append(f"{score}점<br><b>({count}건)</b>" if count > 0 else f"{score}점")
            else:
                text_row.append(f"{score}점")
        matrix_colors.append(color_row)
        text_matrix.append(text_row)

    fig = go.Figure(
        data=go.Heatmap(
            z=[[l * s for l in range(1, 6)] for s in range(5, 0, -1)],
            x=["1 (극히드묾)", "2 (드묾)", "3 (보통)", "4 (높음)", "5 (매우높음)"],
            y=["5 (치명적/사망)", "4 (중상/장해)", "3 (휴업/치료)", "2 (경상)", "1 (경미)"],
            colorscale=[
                [0.0, "#A7F3D0"],
                [0.28, "#A7F3D0"],
                [0.29, "#FDE68A"],
                [0.56, "#FDE68A"],
                [0.57, "#FCA5A5"],
                [1.0, "#EF4444"],
            ],
            showscale=False,
            text=text_matrix,
            texttemplate="%{text}",
            textfont=dict(size=12, color="#0F172A"),
            hoverinfo="x+y+z",
        )
    )

    fig.update_layout(
        title="<b>5×5 정량적 위험성 평가 매트릭스 (Risk Matrix) 분포</b>",
        xaxis_title="발생 가능성 (Likelihood)",
        yaxis_title="피해 중대성 (Severity)",
        height=380,
        margin=dict(l=40, r=40, t=50, b=40),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
    )
    return fig


# ==============================================================================
# 4. 세션 상태 관리 및 샘플 데이터 (Session State & Sample Data)
# ==============================================================================

def get_sample_tasks() -> list[dict]:
    """무대 설치 현장의 실제 시나리오를 반영한 기본 샘플 데이터셋을 반환합니다."""
    return [
        {
            "step_no": 1,
            "task_name": "본무대 중앙 메인 트러스 인양 및 리깅",
            "task_type": "무대 기계/구조",
            "hazard_element": "고소 추락 및 중량물 낙하",
            "x_coord": 0.0,
            "y_coord": 10.0,
            "likelihood": 4,
            "severity": 5,
            "risk_score": 20,
            "risk_grade": "Red",
            "description": "천장 호이스트를 이용한 3톤 트러스 리깅 작업",
        },
        {
            "step_no": 2,
            "task_name": "상수(SL) 조명 타워 무빙라이트 배선 및 포커싱",
            "task_type": "조명/전기",
            "hazard_element": "고소 사다리 작업 및 누전·감전 위험",
            "x_coord": -10.0,
            "y_coord": 7.5,
            "likelihood": 3,
            "severity": 4,
            "risk_score": 12,
            "risk_grade": "Yellow",
            "description": "타워 상부 6m 지점 배선 점검 및 각도 세팅",
        },
        {
            "step_no": 3,
            "task_name": "하수(SR) 음향 라인어레이 스피커 와이어 결속",
            "task_type": "음향/영상",
            "hazard_element": "중량물 인양 중 와이어 단선/낙하 충격",
            "x_coord": 10.5,
            "y_coord": 7.0,
            "likelihood": 3,
            "severity": 5,
            "risk_score": 15,
            "risk_grade": "Red",
            "description": "하수 스피커 클러스터 8통 인양 작업",
        },
        {
            "step_no": 4,
            "task_name": "후무대(Backstage) LED 스크린 백드롭 조립",
            "task_type": "음향/영상",
            "hazard_element": "패널 조립 시 손가락 협착 및 전도",
            "x_coord": 0.0,
            "y_coord": 19.5,
            "likelihood": 2,
            "severity": 3,
            "risk_score": 6,
            "risk_grade": "Green",
            "description": "500x500 LED 모듈 월 조립 및 테스트",
        },
        {
            "step_no": 5,
            "task_name": "앞무대(Apron) 모니터 스피커 및 마이크 배선 정리",
            "task_type": "바닥/통로",
            "hazard_element": "배선 노출로 인한 작업자 걸림/전도",
            "x_coord": 2.0,
            "y_coord": 1.5,
            "likelihood": 3,
            "severity": 2,
            "risk_score": 6,
            "risk_grade": "Green",
            "description": "무대 전면부 케이블 트렌치 설치 및 테이핑",
        },
    ]


# ------------------------------------------------------------------------------
# Supabase 연동 (클라우드 저장소). 미설정/오류 시 자동으로 로컬(세션) 모드로 동작합니다.
# 테이블: risk_assessments (task_name, x_coord, y_coord, likelihood, severity,
#                           risk_score, risk_grade, memo)
# memo 형식: "[작업분류|위험요소] 상세내용"  (모바일 앱 등 다른 클라이언트가 넣은
#            일반 메모도 그대로 읽을 수 있습니다)
# ------------------------------------------------------------------------------
DB_TABLE = "risk_assessments"
GRADE_DB_LABEL = {"Red": "Red (고위험)", "Yellow": "Yellow (중위험)", "Green": "Green (저위험)"}


@st.cache_resource(show_spinner=False)
def get_supabase():
    """Supabase 클라이언트를 반환합니다. 설정이 없거나 실패하면 None."""
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
    except Exception:
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_KEY", "")
    if not url or not key:
        return None
    try:
        from supabase import create_client
        return create_client(url, key)
    except Exception:
        return None


def db_active() -> bool:
    """Supabase가 연결되어 있고 조회에 성공한 상태인지 여부"""
    return get_supabase() is not None and st.session_state.get("db_ok", False)


def _row_to_task(row: dict, idx: int) -> dict:
    memo = str(row.get("memo") or "")
    m = re.match(r"^\[(.*?)\|(.*?)\]\s*(.*)$", memo, re.S)
    if m:
        task_type, hazard, desc = m.group(1), m.group(2), m.group(3)
    else:
        task_type, hazard, desc = "기타", "기타 일반 위험", memo
    likelihood = int(row.get("likelihood") or 1)
    severity = int(row.get("severity") or 1)
    score, grade, _, _ = calculate_risk(likelihood, severity)
    return {
        "id": row.get("id"),
        "step_no": idx,
        "task_name": str(row.get("task_name") or ""),
        "task_type": task_type,
        "hazard_element": hazard,
        "x_coord": float(row.get("x_coord") or 0.0),
        "y_coord": float(row.get("y_coord") or 0.0),
        "likelihood": likelihood,
        "severity": severity,
        "risk_score": score,
        "risk_grade": grade,
        "description": desc,
    }


def _task_to_row(task: dict) -> dict:
    score, grade, _, _ = calculate_risk(task["likelihood"], task["severity"])
    desc = task.get("description", "") or ""
    memo = f"[{task.get('task_type', '기타')}|{task.get('hazard_element', '기타 일반 위험')}] {desc}".strip()
    return {
        "task_name": task["task_name"],
        "x_coord": float(task["x_coord"]),
        "y_coord": float(task["y_coord"]),
        "likelihood": int(task["likelihood"]),
        "severity": int(task["severity"]),
        "risk_score": int(score),
        "risk_grade": GRADE_DB_LABEL[grade],
        "memo": memo,
    }


def load_tasks_from_db():
    """DB에서 전체 작업을 읽어 리스트로 반환. 실패 시 None (오류는 session_state['db_error'])"""
    sb = get_supabase()
    if sb is None:
        return None
    try:
        try:
            res = sb.table(DB_TABLE).select("*").order("id").execute()
        except Exception:
            res = sb.table(DB_TABLE).select("*").execute()
        st.session_state["db_error"] = ""
        return [_row_to_task(r, i) for i, r in enumerate(res.data or [], 1)]
    except Exception as e:
        st.session_state["db_error"] = str(e)[:200]
        return None


def refresh_tasks_from_db() -> bool:
    tasks = load_tasks_from_db()
    st.session_state["db_ok"] = tasks is not None
    if tasks is not None:
        st.session_state["tasks"] = tasks
        return True
    return False


def db_insert_tasks(tasks: list) -> tuple:
    """DB 모드에서 작업 여러 건을 한 번에 저장합니다. (ok, 오류메시지)"""
    try:
        get_supabase().table(DB_TABLE).insert([_task_to_row(t) for t in tasks]).execute()
        return True, ""
    except Exception as e:
        return False, str(e)[:200]


def db_delete_task(task: dict) -> tuple:
    task_id = task.get("id")
    if task_id is None:
        return False, "행 id가 없어 삭제할 수 없습니다."
    try:
        res = get_supabase().table(DB_TABLE).delete().eq("id", task_id).execute()
        if not res.data:
            return False, "삭제된 행이 없습니다. Supabase RLS의 delete 정책을 확인하세요."
        return True, ""
    except Exception as e:
        return False, str(e)[:200]


def db_clear_all() -> tuple:
    try:
        sb = get_supabase()
        ids = [r["id"] for r in (sb.table(DB_TABLE).select("id").execute().data or [])]
        if ids:
            res = sb.table(DB_TABLE).delete().in_("id", ids).execute()
            if not res.data:
                return False, "삭제된 행이 없습니다. Supabase RLS의 delete 정책을 확인하세요."
        return True, ""
    except Exception as e:
        return False, str(e)[:200]


def add_task(task: dict) -> tuple:
    """작업 1건 추가: DB 모드면 클라우드에 저장 후 재조회, 아니면 세션에만 추가"""
    if not db_active():
        st.session_state["tasks"].append(task)
        return True, ""
    ok, err = db_insert_tasks([task])
    if ok:
        refresh_tasks_from_db()
    return ok, err


def replace_all_tasks(tasks: list) -> tuple:
    """전체 교체 (샘플 복원·CSV 가져오기·전체 삭제용)"""
    if not db_active():
        st.session_state["tasks"] = tasks
        return True, ""
    ok, err = db_clear_all()
    if ok and tasks:
        ok, err = db_insert_tasks(tasks)
    refresh_tasks_from_db()
    return ok, err


def init_session_state():
    """세션 상태를 초기화합니다. Supabase가 연결되면 DB 데이터를, 아니면 샘플을 적재합니다."""
    if "tasks" not in st.session_state:
        st.session_state["db_error"] = ""
        if not refresh_tasks_from_db():
            st.session_state["tasks"] = get_sample_tasks()

    if "checked_rules" not in st.session_state:
        st.session_state["checked_rules"] = set()


# ==============================================================================
# 5. UI 렌더링 컴포넌트 (UI Rendering Components)
# ==============================================================================

def render_sidebar():
    """사이드바 입력 폼 및 데이터 관리 컨트롤을 렌더링합니다."""
    with st.sidebar:
        st.markdown("### 📝 작업 단계 등록 폼")
        st.caption("현장 작업 단계와 위험 요소를 입력해 위험성을 평가합니다.")

        with st.form(key="task_input_form", clear_on_submit=False):
            task_name = st.text_input(
                "작업 단계명 *",
                placeholder="예: 메인 트러스 조립 및 인양",
                help="진행할 무대 설비 작업 명칭을 입력하세요.",
            )

            col_type1, col_type2 = st.columns(2)
            with col_type1:
                task_type = st.selectbox(
                    "작업 분류",
                    ["무대 기계/구조", "조명/전기", "음향/영상", "특수효과/소품", "바닥/통로", "기타"],
                )
            with col_type2:
                hazard_element = st.selectbox(
                    "주요 위험 요소",
                    [
                        "고소 추락 위험",
                        "중량물 낙하/충격",
                        "감전/누전 위험",
                        "기계 협착/끼임",
                        "전도/미끄러짐",
                        "화재/폭발 위험",
                        "기타 일반 위험",
                    ],
                )

            st.markdown("##### 📍 무대 좌표 (X, Y)")
            col_x, col_y = st.columns(2)
            with col_x:
                x_coord = st.number_input(
                    "X 좌표 (m)",
                    min_value=-20.0,
                    max_value=20.0,
                    value=0.0,
                    step=0.5,
                    help="무대 중심=0m, 좌측(SL) 음수, 우측(SR) 양수",
                )
            with col_y:
                y_coord = st.number_input(
                    "Y 좌표 (m)",
                    min_value=-5.0,
                    max_value=25.0,
                    value=10.0,
                    step=0.5,
                    help="앞무대=0m, 안쪽(Backstage)으로 갈수록 증가",
                )

            st.markdown("##### ⚠️ 위험성 평가 (Likelihood × Severity)")
            likelihood = st.slider(
                "발생 가능성 (L: 1~5)",
                min_value=1,
                max_value=5,
                value=3,
                help="1(극히드묾) ~ 5(매우높음/상시발생)",
            )
            severity = st.slider(
                "피해 중대성 (S: 1~5)",
                min_value=1,
                max_value=5,
                value=3,
                help="1(경미/응급처치) ~ 5(치명적/사망)",
            )

            # 실시간 계산 프리뷰
            preview_score, preview_grade, preview_color, preview_label = calculate_risk(
                likelihood, severity
            )
            st.markdown(
                f"<div style='padding: 8px; border-radius: 6px; background-color: {preview_color}20; border-left: 4px solid {preview_color}; font-size: 0.88rem; margin-top: 5px; margin-bottom: 10px;'>"
                f"<b>예상 점수:</b> {preview_score}점 | <b style='color:{preview_color};'>{preview_grade}</b> ({preview_label})"
                f"</div>",
                unsafe_allow_html=True,
            )

            description = st.text_input("작업 상세 내용 (선택)", placeholder="예: 2인 1조 작업 진행")

            submitted = st.form_submit_button("➕ 작업 데이터 추가", use_container_width=True, type="primary")

            if submitted:
                is_valid, err_msg = validate_input(task_name, x_coord, y_coord, likelihood, severity)
                if not is_valid:
                    st.error(f"⚠️ {err_msg}")
                else:
                    new_step = len(st.session_state["tasks"]) + 1
                    score, grade, _, _ = calculate_risk(likelihood, severity)
                    new_task = {
                        "step_no": new_step,
                        "task_name": task_name.strip(),
                        "task_type": task_type,
                        "hazard_element": hazard_element,
                        "x_coord": float(x_coord),
                        "y_coord": float(y_coord),
                        "likelihood": int(likelihood),
                        "severity": int(severity),
                        "risk_score": score,
                        "risk_grade": grade,
                        "description": description.strip() if description else "",
                    }
                    ok, err = add_task(new_task)
                    if not ok:
                        st.error(f"☁️ 클라우드 저장에 실패했습니다: {err}")
                    else:
                        st.toast(f"✅ '{task_name}' 작업이 추가되었습니다!")
                        st.rerun()

        st.markdown("---")
        st.markdown("### ⚙️ 데이터 관리")

        if db_active():
            st.caption("☁️ Supabase 연결됨 — 웹/모바일 데이터가 공유됩니다.")
        elif get_supabase() is not None:
            st.warning(f"⚠️ Supabase 조회 실패 → 로컬 모드: {st.session_state.get('db_error', '')}")
        else:
            st.caption("💻 로컬 모드 (Supabase 미연결 — 새로고침하면 데이터가 사라집니다)")

        if get_supabase() is not None:
            if st.button("☁️ 클라우드에서 새로고침", use_container_width=True):
                if refresh_tasks_from_db():
                    st.toast("최신 데이터를 불러왔습니다.")
                st.rerun()

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("🔄 샘플 복원", use_container_width=True, help="기본 시나리오 5개 데이터로 재설정합니다."):
                ok, err = replace_all_tasks(get_sample_tasks())
                st.session_state["checked_rules"] = set()
                if ok:
                    st.rerun()
                else:
                    st.error(f"☁️ 처리 실패: {err}")
        with col_btn2:
            if st.button("🗑️ 전체 삭제", use_container_width=True, help="등록된 모든 작업을 삭제합니다."):
                ok, err = replace_all_tasks([])
                st.session_state["checked_rules"] = set()
                if ok:
                    st.rerun()
                else:
                    st.error(f"☁️ 처리 실패: {err}")

        # CSV 업로드 기능
        uploaded_file = st.file_uploader("📥 작업 CSV 파일 가져오기", type=["csv"])
        csv_key = f"{uploaded_file.name}-{uploaded_file.size}" if uploaded_file is not None else None
        if uploaded_file is not None and st.session_state.get("last_csv") != csv_key:
            try:
                csv_df = pd.read_csv(uploaded_file)
                required_cols = {"task_name", "x_coord", "y_coord", "likelihood", "severity"}
                if not required_cols.issubset(set(csv_df.columns)):
                    st.error(f"CSV 파일에 필수 컬럼이 누락되었습니다: {required_cols - set(csv_df.columns)}")
                else:
                    imported_tasks = []
                    for idx, row in csv_df.iterrows():
                        score, grade, _, _ = calculate_risk(row["likelihood"], row["severity"])
                        imported_tasks.append({
                            "step_no": idx + 1,
                            "task_name": str(row["task_name"]),
                            "task_type": str(row.get("task_type", "기타")),
                            "hazard_element": str(row.get("hazard_element", "일반")),
                            "x_coord": float(row["x_coord"]),
                            "y_coord": float(row["y_coord"]),
                            "likelihood": int(row["likelihood"]),
                            "severity": int(row["severity"]),
                            "risk_score": score,
                            "risk_grade": grade,
                            "description": str(row.get("description", "")),
                        })
                    st.session_state["last_csv"] = csv_key
                    ok, err = replace_all_tasks(imported_tasks)
                    if ok:
                        st.toast(f"총 {len(imported_tasks)}건의 작업 데이터를 불러왔습니다.")
                        st.rerun()
                    else:
                        st.error(f"☁️ 클라우드 저장에 실패했습니다: {err}")
            except Exception as e:
                st.error(f"CSV 파일 파싱 중 오류가 발생했습니다: {str(e)}")


def render_dashboard_metrics(df: pd.DataFrame):
    """대시보드 상단 요약 카포 (총 작업 수, 등급별 건수, 평균 위험도 지수)를 렌더링합니다."""
    total_count = len(df) if df is not None else 0

    if total_count == 0:
        red_count = 0
        yellow_count = 0
        green_count = 0
        avg_score = 0.0
        max_score = 0
    else:
        red_count = len(df[df["risk_grade"] == "Red"])
        yellow_count = len(df[df["risk_grade"] == "Yellow"])
        green_count = len(df[df["risk_grade"] == "Green"])
        avg_score = df["risk_score"].mean()
        max_score = df["risk_score"].max()

    m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)

    with m_col1:
        st.metric(
            label="📋 총 등록 작업",
            value=f"{total_count} 단계",
            help="현재 등록된 총 무대 설치/해체 작업 단계 수",
        )
    with m_col2:
        st.metric(
            label="🚨 고위험 (Red)",
            value=f"{red_count} 건",
            delta=f"{red_count}건 집중 관리" if red_count > 0 else "위험 없음",
            delta_color="inverse" if red_count > 0 else "normal",
            help="위험 점수 15점 이상 - 즉시 안전대책 및 특별 관리 필요",
        )
    with m_col3:
        st.metric(
            label="⚠️ 중위험 (Yellow)",
            value=f"{yellow_count} 건",
            help="위험 점수 8~14점 - 표준 안전 작업 지침 준수",
        )
    with m_col4:
        st.metric(
            label="✅ 저위험 (Green)",
            value=f"{green_count} 건",
            help="위험 점수 7점 이하 - 일반 일상 안전관리",
        )
    with m_col5:
        st.metric(
            label="📊 평균 위험 점수",
            value=f"{avg_score:.1f} / 25점",
            delta=f"최고 {max_score}점" if total_count > 0 else None,
            delta_color="off",
            help="등록된 모든 작업의 위험도 평균 (가능성 x 중대성)",
        )


def render_safety_guidelines(df: pd.DataFrame):
    """고위험(Red) 작업에 대한 필수 PPE 및 맞춤형 안전 수칙 체크리스트를 렌더링합니다."""
    st.markdown("### 🚨 고위험 작업 대상 집중 안전 대책 및 수칙 체크리스트")

    if df is None or df.empty:
        st.info("등록된 작업 데이터가 없습니다. 사이드바에서 작업을 등록해주세요.")
        return

    red_tasks = df[df["risk_grade"] == "Red"]

    if red_tasks.empty:
        st.success(
            "🎉 **현재 고위험(Red, 15점 이상)으로 분류된 작업이 없습니다!**<br>"
            "표준 안전 작업 절차를 준수하며 안전하게 작업을 진행해 주십시오.",
            icon="🛡️",
        )
        return

    st.warning(
        f"⚠️ 현재 **총 {len(red_tasks)}건의 고위험(Red) 작업**이 감지되었습니다. "
        "작업 착수 전 아래 필수 개인보호구(PPE) 구비 및 안전 수칙 체크리스트 점검을 완료하십시오.",
        icon="⚠️",
    )

    for _, row in red_tasks.iterrows():
        task_id = row.get("step_no", 0)
        t_name = row["task_name"]
        hazard = row.get("hazard_element", "위험 요소 미지정")
        score = row["risk_score"]
        
        guideline_data = get_ppe_and_guidelines(hazard, "Red")
        ppe_items = guideline_data["ppe"]
        safety_rules = guideline_data["guidelines"]

        with st.expander(f"🔴 [단계 {task_id}] {t_name} — 위험 점수: {score}점 ({hazard})", expanded=True):
            col_left, col_right = st.columns([1, 1.4])

            with col_left:
                st.markdown("##### 🦺 필수 착용 개인보호구 (PPE)")
                ppe_html = "".join([f"<span class='ppe-tag'>✓ {item}</span>" for item in ppe_items])
                st.markdown(f"<div>{ppe_html}</div>", unsafe_allow_html=True)

                st.markdown("##### 📍 작업 위치 정보")
                st.markdown(
                    f"- **무대 좌표:** X: `{row['x_coord']}m`, Y: `{row['y_coord']}m`<br>"
                    f"- **작업 분류:** `{row.get('task_type', '기타')}`<br>"
                    f"- **위험도:** 발생 가능성 `{row['likelihood']}` × 중대성 `{row['severity']}` = **{score}점**",
                    unsafe_allow_html=True,
                )

            with col_right:
                st.markdown("##### 📋 현장 작업 전 필수 안전 점검 체크리스트")
                for r_idx, rule in enumerate(safety_rules):
                    rule_key = f"chk_{task_id}_{r_idx}"
                    # 체크리스트 상태 기억
                    is_checked = rule_key in st.session_state.get("checked_rules", set())
                    chk = st.checkbox(
                        rule,
                        value=is_checked,
                        key=rule_key,
                    )
                    if chk:
                        st.session_state["checked_rules"].add(rule_key)
                    else:
                        st.session_state["checked_rules"].discard(rule_key)


def render_data_table(df: pd.DataFrame):
    """전체 작업 위험성 평가 데이터프레임 및 다운로드/개별 삭제를 제공합니다."""
    st.markdown("### 📋 전체 작업 위험성 평가 데이터 시트")

    if df is None or df.empty:
        st.info("등록된 작업 데이터가 없습니다.")
        return

    # 표시용 데이터프레임 구성
    display_df = df.copy()
    display_df.rename(
        columns={
            "step_no": "작업 순번",
            "task_name": "작업 단계명",
            "task_type": "작업 분류",
            "hazard_element": "주요 위험 요소",
            "x_coord": "X 좌표 (m)",
            "y_coord": "Y 좌표 (m)",
            "likelihood": "가능성 (L)",
            "severity": "중대성 (S)",
            "risk_score": "위험 점수",
            "risk_grade": "위험 등급",
            "description": "상세 내용",
        },
        inplace=True,
    )

    # 데이터프레임 인터랙티브 테이블 표시
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "위험 점수": st.column_config.ProgressColumn(
                "위험 점수",
                help="가능성 x 중대성 (최대 25점)",
                format="%d점",
                min_value=1,
                max_value=25,
            ),
            "위험 등급": st.column_config.TextColumn(
                "위험 등급",
                help="Red(>=15), Yellow(8~14), Green(<=7)",
            ),
        },
    )

    # 하단 액션 버튼 (CSV 다운로드 및 행 삭제)
    col_dl, col_del = st.columns([1, 1])
    with col_dl:
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False, encoding="utf-8-sig")
        st.download_button(
            label="💾 위험성 평가 결과 CSV 다운로드",
            data=csv_buffer.getvalue(),
            file_name="StageGuard_위험성평가_결과.csv",
            mime="text/csv",
            type="primary",
            use_container_width=True,
        )

    with col_del:
        with st.expander("🗑️ 특정 작업 개별 삭제"):
            task_options = [f"[{r['step_no']}] {r['task_name']}" for _, r in df.iterrows()]
            selected_task = st.selectbox("삭제할 작업을 선택하세요", task_options)
            if st.button("선택한 작업 삭제", type="secondary", use_container_width=True):
                target_step = int(selected_task.split("]")[0].replace("[", ""))
                target = next(
                    (t for t in st.session_state["tasks"] if t.get("step_no") == target_step), None
                )
                if db_active():
                    ok, err = db_delete_task(target) if target else (False, "대상을 찾을 수 없습니다.")
                    if ok:
                        refresh_tasks_from_db()
                else:
                    st.session_state["tasks"] = [
                        t for t in st.session_state["tasks"] if t.get("step_no") != target_step
                    ]
                    # 순번 재정렬
                    for new_idx, t in enumerate(st.session_state["tasks"], 1):
                        t["step_no"] = new_idx
                    ok, err = True, ""
                if ok:
                    st.toast("해당 작업이 삭제되었습니다.")
                    st.rerun()
                else:
                    st.error(f"☁️ 삭제 실패: {err}")


# ==============================================================================
# 6. 메인 애플리케이션 진입점 (Main Entrypoint)
# ==============================================================================

def main():
    """StageGuard 애플리케이션의 메인 루틴"""
    # 1) 세션 상태 초기화
    init_session_state()

    # 2) 메인 헤더 배너 렌더링
    st.markdown(
        """
        <div class="main-header">
            <h1>🎭 StageGuard : 무대 설비 작업 위험성 평가 및 동선 시뮬레이터</h1>
            <p>방송·공연 무대 설치 및 해체 현장의 안전사고 예방을 위한 작업 동선 2D 시각화 및 정량적 위험성(Risk Matrix) 관리 시스템</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 3) 사이드바 렌더링
    render_sidebar()

    # 4) 데이터 변환 및 유효성 검증
    tasks_data = st.session_state.get("tasks", [])
    df = pd.DataFrame(tasks_data) if tasks_data else pd.DataFrame()

    # 5) 상단 대시보드 요약 메트릭
    render_dashboard_metrics(df)

    st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)

    # 6) 중단: 2D 시각화 맵 및 위험 매트릭스 탭
    tab_map, tab_matrix = st.tabs(["🗺️ 무대 2D 평면도 및 동선 시뮬레이션", "📊 5×5 위험 매트릭스 분석"])

    with tab_map:
        if df.empty:
            st.warning("등록된 작업 단계가 없습니다. 좌측 사이드바에서 작업을 추가해주세요.")
        else:
            fig_map = create_stage_map(df)
            st.plotly_chart(fig_map, use_container_width=True)
            
            # 동선 분석 및 위험 구간 알림 캡션
            red_in_map = df[df["risk_grade"] == "Red"]
            if not red_in_map.empty:
                st.markdown(
                    f"💡 **안전 가이드:** 붉은색 원형 점선 영역(반경 2.5m)은 **고위험(Red) 집중 관리 구역**입니다. "
                    f"해당 구역 작업 시 하부 통제선을 설치하고 신호수를 배치하십시오."
                )

    with tab_matrix:
        fig_matrix = create_risk_matrix_heatmap(df)
        st.plotly_chart(fig_matrix, use_container_width=True)
        st.caption(
            "※ 위험 등급 판정 기준: 가능성(1~5) × 중대성(1~5) | Red(15점 이상: 고위험) | Yellow(8~14점: 중위험) | Green(7점 이하: 저위험)"
        )

    st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)

    # 7) 하단: 데이터 시트 및 안전 대책/체크리스트 (2개 컬럼 또는 상하 분할)
    col_bottom_left, col_bottom_right = st.columns([1.1, 0.9])

    with col_bottom_left:
        render_data_table(df)

    with col_bottom_right:
        render_safety_guidelines(df)


if __name__ == "__main__":
    main()
