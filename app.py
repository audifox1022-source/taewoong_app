import streamlit as st
import google.generativeai as genai
from PIL import Image
import os
import importlib.metadata
import time

# --- [0. 초기 환경 설정] ---
# Streamlit의 st.rerun()을 사용하기 위해 sys와 subprocess 호출은 제거하고, 
# 라이브러리 설치는 requirements.txt에 위임합니다.
# (이전에 v0.8.5까지 확인되었으므로, 환경은 안정된 것으로 간주합니다.)

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
**[최종 규칙]**
* **형상 판단:** AI가 도면을 보고 형상을 자동으로 분류합니다.
* **여유치:** 표준서의 여유값은 **총합(Total)**으로 간주하여 도면 치수에 **1회만 단순 합산**됩니다.
""")

# --- 2. 사이드바 (자동화 모드) ---
with st.sidebar:
    st.header("⚙️ 작업 설정")
    
    # 도면 파일 업로드
    drawing_file = st.file_uploader(
        "1️⃣ 제품 도면 (JPG/PNG/PDF)", 
        type=["jpg", "jpeg", "png", "pdf"],
        help="캐드 파일은 PDF로 변환해서 올려주세요."
    )
    
    # [상태 표시] 표준 문서 로드 확인
    standard_path = "standard.pdf" 
    st.divider()
    if os.path.exists(standard_path):
        st.success("✅ 표준서 로드 완료")
    else:
        st.error("❌ 표준서 파일 없음!")

# --- 3. [핵심] 작동하는 모델 자동 탐색 ---
def get_working_model():
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
    except:
        return None, "API Key Error"

    # 가장 안정적인 모델 목록을 순서대로 테스트
    candidates = ['gemini-2.5-flash', 'gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
    
    for model_name in candidates:
        try:
            model = genai.GenerativeModel(model_name)
            return model, model_name
        except:
            continue
            
    return None, "No Working Model Found"

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

    # [최종 프롬프트] 자동 분류 및 총 여유값 단순 합산 로직 적용
    prompt = f"""
    당신은 (주)태웅의 **'단조 견적 및 중량 산출 전문가'**입니다.
    시스템에 내장된 **[PE-WS-1606-001 가공여유표준]**을 준수하여, 사용자가 업로드한 **[도면 파일]**의 견적을 산출하십시오.

    [작업 프로세스]
    1. **형상 자동 분류:** 도면을 분석하여 **Tube Sheet, Shaft, Ring, R-Bar, SQ-Bar 등** 표준서에 명시된 주요 형상 중 하나로 분류하십시오.
    2. **표준 매핑 및 여유값 탐색:** 분류된 형상에 해당하는 표준서 PDF 섹션을 찾아, 도면 치수(OD, T 등)에 맞는 **가공 여유 (총 여유값)**를 찾으십시오.
       - *근거 필수: "표준서 00페이지 표를 참조함"*
    3. **치수 및 중량 계산 (비중 7.85):**
       - **단조 치수:** 정삭 치수 + 여유값 (※ 여유값 자체가 총 가공량이므로, **단순 합산 1회만** 더합니다.)
       - **도면 중량:** 정삭 치수 부피 x 7.85 / 1,000
       - **단조 중량:** 단조 치수 부피 x 7.85 / 1,000

    [출력 포맷]
    | 구분 | 항목 | 내용 | 비고/근거 |
    |---|---|---|---|
    | **1. 기본 정보** | 제품 형상 | (AI가 자동 분류한 형상) | 표준서 참조 |
    | | 정삭(도면) 치수 | OD/W: 000, ID/T: 000, L: 000 (mm) | 도면 판독 |
    | | **도면 중량** | **0,000 kg** | 이론 계산 |
    | **2. 여유 적용** | 적용 기준 | **총 여유값 +00mm** | **표준서 Pg.00 [표 번호]** (※ 총합 1회 적용) |
    | **3. 단조 스펙** | 단조(소재) 치수 | OD/W: 000, ID/T: 000, L: 000 (mm) | 정삭 + 여유 |
    | | **단조 중량** | **0,000 kg** | 소재 중량 계산 |

    **[종합 의견]**
    - 특이사항이나 협의 사항이 있다면 명시.
    """
    
    with st.spinner(f"AI({model_name})가 도면을 분석하고 표준서를 탐색 중입니다..."):
        try:
            response = model.generate_content([prompt, drawing_blob, standard_blob])
            return response.text
        except Exception as e:
            return f"Error ({model_name} execution): {str(e)}"

# --- 5. 메인 실행 ---
if st.button("🚀 견적 산출 시작", use_container_width=True):
    if not drawing_file:
        st.error("⚠️ 제품 도면 파일을 업로드해주세요.")
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
                    st.info(f"PDF 도면: {drawing_file.name}")
            
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
