import streamlit as st
import google.generativeai as genai
import json 
import os
import importlib.metadata
import time
from PIL import Image 
import io 
import base64

# --- 1. 앱 기본 설정 ---
st.set_page_config(page_title="영업부 수주 검토 지원 앱", layout="wide")
st.title("🌐 AI 글로벌 스펙 및 표준 규격 대조 앱")

# [진단용] 현재 상태 표시
try:
    current_version = importlib.metadata.version("google-generativeai")
except:
    current_version = "Unknown"
st.caption(f"System Status: google-generativeai v{current_version}")

st.markdown("""
**[업그레이드 기능]**
* **글로벌 표준 DB 탑재:** ASME, ASTM, EN, JIS, KS 등 주요 규격의 물성치 데이터를 AI가 참조합니다.
* **자동 규격 대조:** 고객 시방서의 요구치가 국제 표준 규격에 미달하는지 자동으로 감지합니다.
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

# --- 3. 글로벌 규격 데이터베이스 (Mini-DB) 정의 ---
# 실무에서 자주 쓰는 강종 데이터를 여기에 추가하면 AI가 더 똑똑해집니다.
STANDARD_SPECS_DB = """
[참조용 국제 표준 규격 데이터베이스 (Reference Standards)]

1. **ASME / ASTM (미국 표준)**
   - **SA-105 / A105 (Carbon Steel Forging)**
     - Yield Strength: Min 250 MPa (36 ksi)
     - Tensile Strength: Min 485 MPa (70 ksi)
     - Hardness: Max HB 187
   - **SA-350 LF2 Class 1 (Low Temp Carbon Steel)**
     - Yield Strength: Min 250 MPa (36 ksi)
     - Tensile Strength: 485-655 MPa (70-95 ksi)
     - Charpy Impact: Min 20J @ -46°C
   - **SA-182 F316/F316L (Stainless Steel)**
     - Yield Strength: Min 205 MPa (30 ksi)
     - Tensile Strength: Min 515 MPa (75 ksi)

2. **EN 10222-2 / EN 10028-3 (유럽 표준)**
   - **P250GH (Pressure Vessel Steel)**
     - Yield Strength: Min 250 MPa (for t<=16mm)
     - Tensile Strength: 410-540 MPa
     - Impact: Min 27J @ 20°C
   - **P355NH (Fine Grain Steel)**
     - Yield Strength: Min 355 MPa
     - Impact: Min 27J @ -20°C

3. **JIS / KS (일본/한국 표준)**
   - **SF440A (Carbon Steel Forging)**
     - Yield Strength: Min 245 MPa
     - Tensile Strength: 440-540 MPa
   - **SCM440 (Cr-Mo Steel)**
     - Yield Strength: Min 835 MPa (Quenched/Tempered)
     - Tensile Strength: Min 980 MPa

4. **API 6A (Wellhead Equipment)**
   - **60K Material**
     - Yield Strength: Min 414 MPa (60 ksi)
     - Tensile Strength: Min 586 MPa (85 ksi)
   - **75K Material**
     - Yield Strength: Min 517 MPa (75 ksi)
     - Tensile Strength: Min 655 MPa (95 ksi)

*지침: 위 데이터베이스에 없는 재질이라도, 당신의 내부 지식(ASME Sec.II, API 등)을 활용하여 표준 규격 적합성을 판단하시오.*
"""

# --- 4. Markdown 리포트 생성 함수 ---
def generate_markdown_report(document_blob):
    model, model_name = get_working_model()
    
    if not model:
        return f"Error: 사용 가능한 AI 모델을 찾을 수 없습니다."

    # [프롬프트] 규격 DB 주입 및 비교 분석 요청
    prompt = f"""
    당신은 (주)태웅의 **글로벌 스펙 기술 검토 전문가**입니다.
    업로드된 문서를 분석하고, 아래 제공된 **[참조용 국제 표준 규격 데이터베이스]**와 대조하여 적합성을 판단하십시오.

    {STANDARD_SPECS_DB}

    [검토 및 출력 지침]
    1. **규격 대조(Critical):** 고객 요구 물성치가 위 DB의 **표준값(Min/Max)**을 만족하는지 확인하십시오.
       - 예: 고객이 SA-105 재질에 Yield 200MPa를 요구했다면 -> "표준(250MPa) 이하이므로 적합(PASS)"이 아니라, "표준 미달 가능성 확인 필요" 등으로 기술적 판단을 하십시오.
    2. **출하 점검:** 최종 출하 전 확인해야 할 필수 항목을 목록화하십시오.

    [출력 포맷]
    ## 📋 글로벌 표준 규격 대조 및 기술 검토

    | 항목 | 고객 문서 요구값 (추출) | 국제 표준 기준값 (DB 참조) | 판정 (PASS/FAIL/WARNING) |
    |:---|:---|:---|:---|
    | **재질/Grade** | [예: SA-105] | [ASME SA-105] | - |
    | **항복강도(Yield)** | [예: Min 240 MPa] | [예: Min 250 MPa] | [FAIL - 표준 미달] |
    | **인장강도(Tensile)**| [예: Min 485 MPa] | [예: Min 485 MPa] | [PASS] |
    | **충격시험(Charpy)** | [예: 27J @ -20°C] | [예: N/A or Spec check] | [Check Required] |
    
    ---
    ### 🏭 주요 공정 및 검사 라우팅
    * **입회 포인트:** [Forging, Heat Treatment 등]
    * **필수 비파괴검사:** [UT, MT, PT 레벨]
    
    ### 📦 출하 전 최종 점검 목록
    * **마킹/스탬핑:** [요구사항 추출]
    * **포장 방식:** [요구사항 추출]
    * **제출 서류:** [MTC, 등]

    **[종합 의견]**
    - [표준 규격 대비 특이사항이 있는지 기술적 소견 작성]
    """
    
    with st.spinner(f"AI({model_name})가 국제 표준 규격과 대조 분석 중입니다..."):
        try:
            response = model.generate_content(
                contents=[prompt, document_blob]
            )
            return response.text
            
        except Exception as e:
            return f"Error: 분석 중 오류 발생: {str(e)}"

# --- 5. Streamlit 메인 화면 ---
# 파일 업로더
document_file = st.file_uploader(
    "1️⃣ 고객 문서 업로드 (PDF/Image)", 
    type=["pdf", "jpg", "jpeg", "png"],
    help="국제 표준(ASME, EN, JIS 등)과 대조할 문서를 올리세요."
)

if st.button("🚀 규격 대조 및 분석 시작", use_container_width=True):
    if not document_file:
        st.error("⚠️ 검토할 고객 문서를 업로드해주세요.")
    else:
        document_blob = {"mime_type": document_file.type, "data": document_file.getvalue()}
        
        col1, col2 = st.columns([1, 1.5])
        
        with col1:
            st.subheader("📄 문서 미리보기")
            try:
                if document_file.type.startswith('image'):
                    st.image(document_file, use_container_width=True)
                elif document_file.type == 'application/pdf':
                    try:
                        base64_pdf = base64.b64encode(document_file.getvalue()).decode('utf-8')
                        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600px" type="application/pdf"></iframe>'
                        st.markdown(pdf_display, unsafe_allow_html=True)
                    except:
                         st.success(f"✅ 업로드 완료 (미리보기 생략)")
                else:
                    st.info(f"파일 업로드 완료")
            except:
                 st.success("✅ 업로드 완료 (미리보기 생략)")
        
        with col2:
            result_text = generate_markdown_report(document_blob)
            
            st.subheader("✅ 규격 대조 결과 리포트")
            if result_text.startswith("Error"):
                st.error(result_text)
            else:
                st.markdown(result_text)
                st.success("분석 완료!")
                st.code(result_text, language="markdown")
