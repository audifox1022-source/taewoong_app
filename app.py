import streamlit as st
import google.generativeai as genai
from PIL import Image
import os
import importlib.metadata

# --- 1. 앱 기본 설정 ---
st.set_page_config(page_title="태웅 표준 견적 시스템", layout="wide")
st.title("🏭 태웅(TAEWOONG) AI 표준 견적 & 중량 산출기")

# [진단용] 현재 상태 표시
try:
    current_version = importlib.metadata.version("google-generativeai")
except:
    current_version = "Unknown"
st.caption(f"System Status: google-generativeai v{current_version}")

st.markdown("""
**[사용 방법]**
1. **[제품 도면]**을 업로드하세요.
2. **'견적 산출 시작'** 버튼을 누르세요.
   *(가공여유표준서는 시스템에 내장되어 있어 자동 적용됩니다)*
""")

# --- 2. 사이드바 ---
with st.sidebar:
    st.header("📂 도면 업로드")
    drawing_file = st.file_uploader(
        "1️⃣ 제품 도면 (JPG/PNG/PDF)", 
        type=["jpg", "jpeg", "png", "pdf"],
        help="캐드 파일은 PDF로 변환해서 올려주세요."
    )
    
    standard_path = "standard.pdf" 
    st.divider()
    if os.path.exists(standard_path):
        st.success("✅ 표준서 로드 완료")
    else:
        st.error("❌ 표준서 파일 없음!")

# --- 3. [핵심] 작동하는 모델 자동 탐색 ---
def get_working_model():
    # API 키 설정
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
    except:
        return None, "API Key Error"

    # 모델 목록을 API에 직접 요청하여 찾기
    st.warning("🔄 AI 모델 목록을 서버에서 확인 중입니다...")
    
    try:
        # gemini-1.5-flash가 안 될 경우를 대비해, API가 제공하는 목록 중 가장 최신 모델을 찾습니다.
        for m in genai.list_models():
            # Multimodal 분석이 가능하고, "1.5" 버전이 포함된 모델을 우선합니다.
            if 'generateContent' in m.supported_generation_methods and 'gemini-1.5' in m.name:
                return genai.GenerativeModel(m.name), m.name
            
        # 1.5 모델이 없으면, 구형 모델 중 Vision 기능이 있는 모델을 찾습니다.
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods and ('pro' in m.name or 'flash' in m.name):
                return genai.GenerativeModel(m.name), m.name
                
    except Exception as e:
        return None, f"API List Error: {e}"

    return None, "사용 가능한 모델이 없습니다."

# --- 4. AI 분석 로직 ---
def analyze_drawing_with_standard(drawing_blob):
    model, model_name = get_working_model()
    
    if not model:
        return f"Error: 사용 가능한 AI 모델을 찾을 수 없습니다. ({model_name})"

    # 표준서 읽기
    try:
        with open("standard.pdf", "rb") as f:
            standard_data = f.read()
        standard_blob = {"mime_type": "application/pdf", "data": standard_data}
    except FileNotFoundError:
        return "Error: standard.pdf 파일이 없습니다."

    # Prompt (규칙 유지)
    prompt = """
    당신은 (주)태웅의 **'단조 견적 및 중량 산출 전문가'**입니다.
    시스템에 내장된 **[PE-WS-1606-001 가공여유표준]**을 준수하여, 사용자가 업로드한 **[도면 파일]**의 견적을 산출하십시오.

    [작업 절차]
    1. **형상 분류:** 도면을 보고 제품 형상(Ring, Shaft, Tube Sheet, Disc 등)을 판단하십시오.
    2. **표준 매핑:** 내장된 표준서 PDF에서 해당 형상의 페이지를 찾아, 치수(OD, T 등)에 맞는 **가공 여유**를 찾으십시오.
       - *근거 필수: "표준서 00페이지 표를 참조함"*
    3. **치수 및 중량 계산 (비중 7.85):**
       - **도면 중량:** 정삭 치수 부피 x 7.85 / 1,000
       - **단조 치수:** 정삭 치수 + (여유값 x 2)
       - **단조 중량:** 단조 치수 부피 x 7.85 / 1,000

    [출력 포맷]
    | 구분 | 항목 | 내용 | 비고/근거 |
    |---|---|---|---|
    | **1. 기본 정보** | 제품 형상 | (예: TUBE SHEET) | 표준서 참조 |
    | | 정삭(도면) 치수 | OD: 000, T: 000 (mm) | 도면 판독 |
    | | **도면 중량** | **0,000 kg** | 이론 계산 |
    | **2. 여유 적용** | 적용 기준 | **Total +00mm** | **표준서 Pg.00 [표 번호]** |
    | **3. 단조 스펙** | 단조(소재) 치수 | OD: 000, ID: 000, T: 000 (mm) | 정삭 + 여유 |
    | | **단조 중량** | **0,000 kg** | 소재 중량 계산 |

    **[종합 의견]**
    - 특이사항이나 협의 사항이 있다면 명시.
    """
    
    with st.spinner(f"AI({model_name})가 분석 중입니다..."):
        try:
            # [model]과 [standard_blob]을 함께 전송
            response = model.generate_content([prompt, drawing_blob, standard_blob])
            return response.text
        except Exception as e:
            return f"Error ({model_name} execution): {str(e)}"

# --- 5. 메인 실행 ---
if st.button("🚀 표준 견적 산출 시작", use_container_width=True):
    if not drawing_file:
        st.error("⚠️ 도면 파일을 업로드해주세요.")
    elif not os.path.exists("standard.pdf"):
        st.error("⚠️ GitHub에 standard.pdf 파일이 없습니다.")
    else:
        try:
            col1, col2 = st.columns([1, 1.5])
            with col1:
                st.subheader("📄 도면 미리보기")
                if drawing_file.type.startswith('image'):
                    st.image(drawing_file, use_container_width=True)
                elif drawing_file.type == 'application/pdf':
                    st.info(f"PDF 파일: {drawing_file.name}")
            
            drawing_blob = {"mime_type": drawing_file.type, "data": drawing_file.getvalue()}
            
            with col2:
                result_text = analyze_drawing_with_standard(drawing_blob)
                if "Error" not in result_text:
                    st.subheader("📋 분석 결과")
                    st.markdown(result_text)
                    st.success("분석 완료!")
                else:
                    st.error(f"분석 실패: {result_text}")
        except Exception as e:
            st.error(f"시스템 오류: {e}")
