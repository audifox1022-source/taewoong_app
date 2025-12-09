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
# [NEW] 엑셀 다운로드 기능을 위해 추가된 라이브러리
import pandas as pd
import re # 정규 표현식 모듈 추가 (Markdown 테이블 추출용)

# --- 1. 앱 기본 설정 ---
st.set_page_config(page_title="영업부 수주 검토 지원 앱", layout="wide")
st.title("📄 AI 고객 스펙 검토 및 라우팅 지원 앱 (Excel 리포트)")

# [진단용] 현재 상태 표시
try:
    current_version = importlib.metadata.version("google-generativeai")
except:
    current_version = "Unknown"
st.caption(f"System Status: google-generativeai v{current_version}")

st.markdown("""
**[최종 업그레이드 기능]**
* **✅ Excel 다운로드:** AI 분석의 핵심 결과표를 **.xlsx 파일**로 다운로드하여 데이터베이스로 즉시 활용 가능합니다.
* **📄 문서 추적성, 중량/원가 계산기, 공정 코멘트** 기능 유지.
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

    # [프롬프트] 추적성 및 공정 코멘트 의무화
    prompt = f"""
    당신은 (주)태웅의 **글로벌 스펙 기술 검토 및 공정 전문가**입니다.
    업로드된 문서를 분석하고, 아래 지침에 따라 결과를 출력하십시오.

    {STANDARD_SPECS_DB}

    [검토 및 출력 지침]
    1. **문서 식별:** 분석된 정보의 출처 **문서 번호(Doc No.)와 개정 번호(Rev. No.)**를 필수로 추출하십시오.
    2. **규격 대조:** 고객 요구 물성치가 국제 표준값(Min/Max)을 만족하는지 판단하십시오.
    3. **치수 추출:** 계산기 입력을 위해 제품의 핵심 치수(OD, ID, H)를 명확히 찾아주십시오.
    4. **주요 공정 품질 코멘트:** 단조, 열처리, 절단 작업 시 재질 특성과 시방서 요구사항을 고려하여 생산 부서가 주의해야 할 핵심 위험 요소(품질, 변형, 안전)를 최소 3가지 이상 작성하십시오.
    5. **중요:** 첫 번째 표(## 📋 글로벌 표준 규격 대조...)는 **가장 중요한 데이터**이며, 이 표를 추출하기 쉬운 **정확한 Markdown 형식**으로 출력해야 합니다.

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

# --- 5. [NEW] Markdown 테이블을 DataFrame으로 변환하는 함수 ---
def markdown_table_to_df(markdown_text):
    """
    Markdown 텍스트에서 첫 번째 테이블을 찾아 Pandas DataFrame으로 변환합니다.
    """
    try:
        # 1. Markdown 테이블을 찾기 위한 정규 표현식
        # 테이블은 |로 시작하고, 그 다음 줄에 |---|로 구분선이 있는 패턴을 찾습니다.
        table_match = re.search(r'(\|.*\|(?:\s*\|---[^|\r\n]*\|)+[\s\S]*?)(?=\n\n|\Z)', markdown_text, re.MULTILINE)
        
        if not table_match:
            return None

        table_string = table_match.group(1).strip()
        lines = table_string.split('\n')
        
        # 헤더 라인과 데이터 라인 추출
        header_line = lines[0].strip()
        data_lines = [line.strip() for line in lines if not line.startswith('|---')]
        
        # 헤더 추출 (첫 번째 라인)
        headers = [h.strip() for h in data_lines[0].split('|') if h.strip()]
        
        # 데이터 추출 (세 번째 라인부터)
        data = []
        for line in data_lines[2:]: # 0:헤더, 1:구분선, 2:첫 데이터
             if line:
                row = [d.strip() for d in line.split('|') if d.strip()]
                if len(row) == len(headers):
                    data.append(row)

        df = pd.DataFrame(data, columns=headers)
        return df
        
    except Exception as e:
        st.warning(f"테이블 변환 중 오류 발생: {e}")
        return None

# --- 6. Streamlit 메인 화면 구성 ---
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
            st.success("분석 완료!")
            
            # [NEW] 엑셀 다운로드 처리
            df_report = markdown_table_to_df(result_text)
            if df_report is not None and not df_report.empty:
                # 엑셀 파일로 변환
                @st.cache_data
                def convert_df_to_excel(df):
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        df.to_excel(writer, index=False, sheet_name='AI_검토결과')
                    return output.getvalue()

                excel_data = convert_df_to_excel(df_report)
                
                st.download_button(
                    label="💾 Excel (.xlsx) 핵심 데이터 다운로드",
                    data=excel_data,
                    file_name=f"수주검토_핵심데이터_{time.strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            
            st.markdown("---")
            st.subheader("📝 전체 결과 (Copyable Text)")
            st.code(result_text, language="markdown")
