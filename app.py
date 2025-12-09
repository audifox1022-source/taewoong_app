import streamlit as st
import google.generativeai as genai
import json 
import os
import importlib.metadata
import time
from PIL import Image 
import io 
import base64
import math 
# 엑셀 관련 라이브러리(pandas, xlsxwriter, re)는 삭제된 상태 유지

# --- 1. 앱 기본 설정 ---
st.set_page_config(page_title="영업부 수주 검토 지원 앱", layout="wide")
st.title("📄 AI 고객 스펙 검토 및 라우팅 지원 앱 (형상 분석 통합)")

# [진단용] 현재 상태 표시
try:
    current_version = importlib.metadata.version("google-generativeai")
except:
    current_version = "Unknown"
st.caption(f"System Status: google-generativeai v{current_version}")

st.markdown("""
**[최종 업그레이드 기능]**
* **🔺 형상 분석 및 추론:** 도면을 분석하여 제품의 3D 형상과 주요 지오메트리 특징을 설명합니다.
* **추적성, 중량/원가 계산기, 공정 코멘트, 출하/포장** 기능 유지.
""")

# --- 2. [핵심] 작동하는 모델 자동 탐색 ---
def get_working_model():
    try:
        if "GOOGLE_API_KEY" not in st.secrets:
            st.error("⚠️ Streamlit Secrets에 GOOGLE_API_KEY가 없습니다.")
            return None, "API Key Missing"
            
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
    except:
        return None, "API Key Error"

    candidates = ['gemini-2.5-flash', 'gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
    
    for model_name in candidates:
        try:
            model = genai.GenerativeModel(model_name)
            return model, model_name
        except:
            continue
            
    return None, "No Working Model Found"

# --- 3. 글로벌 규격 데이터베이스 (Mini-DB) ---
STANDARD_SPECS_DB = """
[참조용 국제 표준 규격 데이터베이스 (Reference Standards)]
1. ASME / ASTM: SA-105, SA-350 LF2, SA-182 F316
2. EN: P250GH, P355NH
3. JIS/KS: SF440A, SCM440
(상세 물성치 생략 - AI는 내부 지식 활용 가능)
"""

# --- 4. Markdown 리포트 생성 함수 (형상 분석 통합) ---
def generate_markdown_report(document_blob):
    model, model_name = get_working_model()
    
    if not model:
        return f"Error: 사용 가능한 AI 모델을 찾을 수 없습니다."

    # [프롬프트 강화] 형상 분석 및 지오메트리 추출 의무화
    prompt = f"""
    당신은 (주)태웅의 **글로벌 스펙 기술 검토, 공정, 물류 및 형상 분석 전문가**입니다.
    업로드된 도면/문서를 분석하고, 아래 지침에 따라 결과를 출력하십시오.

    {STANDARD_SPECS_DB}

    [검토 및 출력 지침]
    1. **문서 식별:** 분석된 정보의 출처 **문서 번호(Doc No.)와 개정 번호(Rev. No.)**를 필수로 추출하십시오.
    2. **형상 분석:** 도면의 2D 뷰를 기반으로 **추론된 제품 형상(예: 플랜지 샤프트, 링, 밸브 바디 등)**을 설명하고, 주요 기하학적 특징(예: 필렛 R5, 챔퍼 C1.5, 테이퍼 각도)을 추출하십시오.
    3. **규격 대조:** 고객 요구 물성치가 국제 표준값(Min/Max)을 만족하는지 판단하십시오.
    4. **치수 추출:** 계산기 입력을 위해 제품의 핵심 치수(OD, ID, H)를 명확히 찾아주십시오.
    5. **물류 및 출하 조건:** **INCOTERMS, 포장 방식, 방청 요구사항**을 필수적으로 추출하십시오.
    6. **주요 공정 품질 코멘트:** 단조, 열처리, 절단 작업 시 **형상적 특성을 고려**하여 위험 요소를 작성하십시오.

    [출력 포맷]
    ## 📋 글로벌 표준 규격 대조 및 기술 검토

    | 항목 | 고객 문서 요구값 (추출) | 문서 참조 (Doc Ref) | 판정 (PASS/FAIL/WARNING) |
    |:---|:---|:---|:---|
    | **문서 번호/개정** | [Doc No: XXX-YYY] | [Rev: A] | - |
    | **재질/Grade** | [예: SA-105] | [Spec Page 3] | - |
    | **항복강도** | [값] | [Spec Sec 4.1] | [판정] |
    | **충격시험** | [값] | [Drawing Note 5] | [판정] |

    ---
    ### 🔺 형상 및 주요 지오메트리 분석
    * **추론된 제품 형상:** [예: 외경이 큰 링 플랜지 형태이며, 한쪽 면에 8개의 볼트 구멍이 있다.]
    * **주요 특징:** [예: 모든 모서리에 R3 필렛 적용, 표면 거칠기 N8 요구]
    * **특이사항/제조 난이도 코멘트:** [예: 비대칭 형상으로 단조 시 편심 발생 위험 높음.]
    
    ### 📦 출하 및 물류 필수 검토 사항
    * **INCOTERMS (2020 기준):** [예: FOB Busan, Incoterms 2020]
    * **포장 방식:** [예: 밀폐형 목상자, 파렛트 포장]

    ### 🚨 주요 공정별 위험 및 품질 코멘트
    * **단조(Forging):** [코멘트]
    * **열처리(Heat Treatment):** [코멘트]

    ### 📏 견적용 추출 치수 (계산기 입력용)
    * **외경 (OD):** [   ] mm
    * **내경 (ID):** [   ] mm
    * **높이 (H):** [   ] mm
    * **수량 (Q'ty):** [   ] EA
    """
    
    with st.spinner(f"AI({model_name})가 문서를 분석 중입니다..."):
        try:
            response = model.generate_content(
                contents=[prompt, document_blob]
            )
            return response.text
            
        except Exception as e:
            return f"Error: 분석 중 오류 발생: {str(e)}"

# --- 5. Streamlit 메인 화면 구성 ---
col1, col2 = st.columns([1, 1.2])

# Left Column (Upload & Calculator)
with col1:
    st.header("1️⃣ 문서 업로드")
    document_file = st.file_uploader("고객 문서 (PDF/Image)", type=["pdf", "jpg", "png"])
    
    # 중량 계산기 섹션 
    st.markdown("---")
    st.header("⚖️ 스마트 중량/원가 계산기")
    st.info("AI 리포트의 '추출 치수'를 보고 입력하세요.")
    
    with st.container(border=True):
        c1, c2 = st.columns(2)
        with c1:
            od = st.number_input("외경 (OD, mm)", min_value=0.0, value=1000.0)
            h = st.number_input("높이/길이 (H, mm)", min_value=0.0, value=500.0)
            density = st.number_input("비중 (Density)", value=7.85, help="철: 7.85, SUS: 7.93")
        with c2:
            id = st.number_input("내경 (ID, mm)", min_value=0.0, value=0.0)
            qty = st.number_input("수량 (EA)", min_value=1, value=1)
            unit_price = st.number_input("kg당 단가 (원)", min_value=0, value=2500)

        # 자동 계산 로직
        if od > 0:
            volume = (math.pi * (od**2 - id**2) / 4) * h
            weight_per_ea = (volume * density) / 1000000
            total_weight = weight_per_ea * qty
            total_cost = total_weight * unit_price
            
            st.markdown(f"### 📊 계산 결과")
            st.success(f"**개당 중량:** {weight_per_ea:,.1f} kg")
            st.info(f"**총 중량 ({qty}EA):** {total_weight:,.1f} kg")
            st.error(f"**💰 총 예상 소재비:** {int(total_cost):,} 원")
        else:
            st.warning("치수를 입력하면 계산됩니다.")

# Right Column (Report)
with col2:
    st.header("2️⃣ AI 분석 리포트")
    
    if 'report_text' not in st.session_state:
        st.session_state.report_text = ""
    
    if st.button("🚀 문서 분석 시작", use_container_width=True):
        if not document_file:
            st.error("⚠️ 문서를 먼저 업로드해주세요.")
        else:
            document_blob = {"mime_type": document_file.type, "data": document_file.getvalue()}
            st.session_state.report_text = generate_markdown_report(document_blob)
            
    # 결과 출력 및 다운로드 버튼 생성
    if st.session_state.report_text:
        result_text = st.session_state.report_text
        
        if result_text.startswith("Error"):
            st.error(result_text)
        else:
            st.markdown(result_text)
            st.success("분석 완료! 이제 형상 분석 결과를 확인하세요.")
            
            st.markdown("---")
            st.subheader("📝 전체 결과 (Copyable Text)")
            st.code(result_text, language="markdown")
