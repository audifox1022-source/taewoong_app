import streamlit as st
import google.generativeai as genai
import json 
import os
import importlib.metadata
import time
from PIL import Image 
import io 
import base64
import math # 수학 계산용

# --- 1. 앱 기본 설정 ---
st.set_page_config(page_title="영업부 수주 검토 지원 앱", layout="wide")
st.title("🌐 AI 글로벌 스펙 검토 & 자동 견적 계산기")

# [진단용] 현재 상태 표시
try:
    current_version = importlib.metadata.version("google-generativeai")
except:
    current_version = "Unknown"
st.caption(f"System Status: google-generativeai v{current_version}")

st.markdown("""
**[업그레이드 기능]**
* **글로벌 표준 DB 탑재:** 국제 표준 규격(ASME 등) 대조 기능 포함.
* **⚖️ 스마트 중량/원가 계산기:** 제품 치수를 입력하면 중량과 예상 소재비를 즉시 계산합니다.
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

# --- 4. Markdown 리포트 생성 함수 ---
def generate_markdown_report(document_blob):
    model, model_name = get_working_model()
    
    if not model:
        return f"Error: 사용 가능한 AI 모델을 찾을 수 없습니다."

    prompt = f"""
    당신은 (주)태웅의 **글로벌 스펙 기술 검토 및 견적 전문가**입니다.
    업로드된 문서를 분석하고, 아래 지침에 따라 결과를 출력하십시오.

    {STANDARD_SPECS_DB}

    [검토 및 출력 지침]
    1. **규격 대조:** 고객 요구 물성치가 국제 표준값(Min/Max)을 만족하는지 판단하십시오.
    2. **치수 추출:** 계산기 입력을 위해 **제품의 핵심 치수(외경 OD, 내경 ID, 길이/높이 H)**를 명확히 찾아주십시오.
    3. **출하 점검:** 최종 출하 전 확인해야 할 필수 항목을 목록화하십시오.

    [출력 포맷]
    ## 📋 글로벌 표준 규격 대조 및 기술 검토

    | 항목 | 고객 문서 요구값 (추출) | 국제 표준 기준값 | 판정 (PASS/FAIL) |
    |:---|:---|:---|:---|
    | **재질/Grade** | [예: SA-105] | [ASME SA-105] | - |
    | **항복강도** | [값] | [값] | [판정] |
    | **인장강도** | [값] | [값] | [판정] |
    
    ### 📏 견적용 추출 치수 (계산기 입력용)
    * **외경 (OD):** [   ] mm
    * **내경 (ID):** [   ] mm (없으면 0)
    * **높이 (H):** [   ] mm
    * **수량 (Q'ty):** [   ] EA

    ---
    ### 📦 출하 전 최종 점검 목록
    * 마킹/스탬핑: [요구사항]
    * 포장 방식: [요구사항]
    * 제출 서류: [MTC 등]
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

# 레이아웃 분할: 왼쪽(파일&설정), 오른쪽(결과&계산기)
col1, col2 = st.columns([1, 1.2])

with col1:
    st.header("1️⃣ 문서 업로드")
    document_file = st.file_uploader("고객 문서 (PDF/Image)", type=["pdf", "jpg", "png"])
    
    # [NEW] 중량 계산기 섹션 (사이드바 대신 메인 화면 왼쪽에 배치하여 접근성 높임)
    st.markdown("---")
    st.header("⚖️ 스마트 중량/원가 계산기")
    st.info("AI 리포트의 '추출 치수'를 보고 입력하세요.")
    
    with st.container(border=True):
        # 입력 폼
        c1, c2 = st.columns(2)
        with c1:
            od = st.number_input("외경 (OD, mm)", min_value=0.0, value=1000.0)
            h = st.number_input("높이/길이 (H, mm)", min_value=0.0, value=500.0)
            density = st.number_input("비중 (Density)", value=7.85, help="철: 7.85, SUS: 7.93")
        with c2:
            id = st.number_input("내경 (ID, mm)", min_value=0.0, value=0.0)
            qty = st.number_input("수량 (EA)", min_value=1, value=1)
            unit_price = st.number_input("kg당 단가 (원)", min_value=0, value=2500)

        # 자동 계산 로직 (원통형/링형 기준)
        if od > 0:
            # 부피(mm3) = (OD^2 - ID^2) * pi / 4 * H
            # 중량(kg) = 부피 * 비중 / 1,000,000
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

with col2:
    st.header("2️⃣ AI 분석 리포트")
    
    if st.button("🚀 문서 분석 시작", use_container_width=True):
        if not document_file:
            st.error("⚠️ 문서를 먼저 업로드해주세요.")
        else:
            document_blob = {"mime_type": document_file.type, "data": document_file.getvalue()}
            result_text = generate_markdown_report(document_blob)
            
            if result_text.startswith("Error"):
                st.error(result_text)
            else:
                st.markdown(result_text)
                st.success("분석 완료! 왼쪽 계산기에 치수를 입력해보세요.")
                st.code(result_text, language="markdown")
