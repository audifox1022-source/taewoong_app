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
# [DELETED] pandas, xlsxwriter, re 모듈은 Excel 기능을 위해 삭제됨

# --- 1. 앱 기본 설정 ---
st.set_page_config(page_title="영업부 수주 검토 지원 앱", layout="wide")
st.title("📄 AI 고객 스펙 검토 및 라우팅 지원 앱 (출하/포장 통합)")

# [진단용] 현재 상태 표시
try:
    current_version = importlib.metadata.version("google-generativeai")
except:
    current_version = "Unknown"
st.caption(f"System Status: google-generativeai v{current_version}")

st.markdown("""
**[최종 기능]**
* **📦 출하/포장 필수 검토:** INCOTERMS, 방청, ISPM-15, 마킹 요구사항을 필수적으로 분석합니다.
* **추적성, 중량/원가 계산기, 공정 코멘트** 기능 유지.
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

# --- 4. Markdown 리포트 생성 함수 (출하/포장 통합) ---
def generate_markdown_report(document_blob):
    model, model_name = get_working_model()
    
    if not model:
        return f"Error: 사용 가능한 AI 모델을 찾을 수 없습니다."

    # [프롬프트] 출하/포장 항목 통합 및 추적성, 공정 코멘트 의무화
    prompt = f"""
    당신은 (주)태웅의 **글로벌 스펙 기술 검토, 공정 및 물류 전문가**입니다.
    업로드된 문서를 분석하고, 아래 지침에 따라 결과를 출력하십시오.

    {STANDARD_SPECS_DB}

    [검토 및 출력 지침]
    1. **문서 식별:** 분석된 정보의 출처 **문서 번호(Doc No.)와 개정 번호(Rev. No.)**를 필수로 추출하십시오.
    2. **규격 대조:** 고객 요구 물성치가 국제 표준값(Min/Max)을 만족하는지 판단하십시오.
    3. **치수 추출:** 계산기 입력을 위해 제품의 핵심 치수(OD, ID, H)를 명확히 찾아주십시오.
    4. **물류 및 출하 조건:** **INCOTERMS (예: FOB Busan)**, **포장 방식 (목상자, 파렛트)**, **방청(Rust Prevention) 요구사항**을 필수적으로 추출하십시오.
    5. **주요 공정 품질 코멘트:** 단조, 열처리, 절단 작업 시 재질 특성을 고려하여 위험 요소를 작성하십시오.

    [출력 포맷]
    ## 📋 글로벌 표준 규격 대조 및 기술 검토

    | 항목 | 고객 문서 요구값 (추출) | 문서 참조 (Doc Ref) | 판정 (PASS/FAIL/WARNING) |
    |:---|:---|:---|:---|
    | **문서 번호/개정** | [Doc No: XXX-YYY] | [Rev: A] | - |
    | **재질/Grade** | [예: SA-105] | [Spec Page 3] | - |
    | **항복강도** | [값] | [Spec Sec 4.1] | [판정] |
    | **인장강도** | [값] | [Spec Sec 4.1] | [판정] |
    | **충격시험** | [값] | [Drawing Note 5] | [판정] |

    ---
    ### 📦 출하 및 물류 필수 검토 사항
    * **INCOTERMS (2020 기준):** [예: FOB Busan, Incoterms 2020]
    * **포장 방식:** [예: 밀폐형 목상자, 파렛트 포장]
    * **목재 포장 규정:** [예: ISPM-15 Heat Treatment 필수 여부]
    * **방청 처리:** [요구되는 방청 오일, VCI Paper 등]
    * **마킹 요구사항:** [선적 마크, 고객사 로고 등 상세 요구사항]

    ### 🚨 주요 공정별 위험 및 품질 코멘트
    * **단조(Forging):** [코멘트]
    * **열처리(Heat Treatment):** [코멘트]
    * **절단/분리(Cutting):** [코멘트]

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
    # [수정 완료] st.uploader -> st.file_uploader
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
            st.success("분석 완료!")
            
            st.markdown("---")
            st.subheader("📝 전체 결과 (Copyable Text)")
            st.code(result_text, language="markdown")
