import streamlit as st
import os
import sys
import subprocess

# --- [비상 조치] 강제 라이브러리 업데이트 ---
# requirements.txt가 작동 안 할 때를 대비해 코드에서 강제로 설치합니다.
try:
    import google.generativeai as genai
    # 버전이 너무 낮으면 강제 업데이트 시도
    version = genai.__version__
    if version < "0.8.3":
        st.warning(f"⚠️ 구버전 감지됨 ({version}). 최신 버전으로 강제 업데이트 중...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "google-generativeai>=0.8.3"])
        import google.generativeai as genai
        st.success("✅ 업데이트 완료! 앱을 다시 실행합니다.")
        st.stop() # 업데이트 후 리로드 유도
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "google-generativeai>=0.8.3"])
    import google.generativeai as genai

from PIL import Image

# --- 1. 앱 기본 설정 ---
st.set_page_config(page_title="태웅 표준 견적 시스템", layout="wide")

st.title("🏭 태웅(TAEWOONG) AI 표준 견적 & 중량 산출기")

# [진단용] 현재 라이브러리 버전 표시 (작게)
st.caption(f"System Status: google-generativeai v{genai.__version__}")

st.markdown("""
**[사용 방법]**
1. **[제품 도면]** (이미지 또는 PDF)을 업로드하세요.
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
        st.info("GitHub에 'standard.pdf'를 올려주세요.")

# --- 3. [핵심] 작동하는 모델 찾기 ---
def get_working_model():
    # 사용 가능한 모델을 순서대로 테스트
    candidates = [
        'gemini-1.5-flash',
        'gemini-1.5-flash-latest',
        'gemini-1.5-pro',
        'gemini-pro' # 최후의 수단 (구형)
    ]
    
    # API 키 설정 확인
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
    except:
        return None, "API Key Error"

    # 모델 찾기
    for model_name in candidates:
        try:
            model = genai.GenerativeModel(model_name)
            return model, model_name
        except:
            continue
    
    return None, "No Model Found"

# --- 4. AI 분석 로직 ---
def analyze_drawing_with_standard(drawing_blob):
    model, model_name = get_working_model()
    
    if not model:
        return f"Error: 사용 가능한 AI 모델을 찾을 수 없습니다. ({model_name})"

    # 내장된 표준서 읽기
    try:
        with open("standard.pdf", "rb") as f:
            standard_data = f.read()
        standard_blob = {"mime_type": "application/pdf", "data": standard_data}
    except FileNotFoundError:
        return "Error: standard.pdf 파일이 없습니다."

    prompt = f"""
    당신은 (주)태웅의 **'단조 견적 및 중량 산출 전문가'**입니다.
    시스템에 내장된 **[PE-WS-1606-001 가공여유표준]**을 준수하여, 사용자가 업로드한 **[도면 파일]**의 단조 스펙을 산출하십시오.

    [작업 프로세스]
    1. **형상 분류:** 도면을 보고 제품 형상(Ring, Shaft, Tube Sheet, Disc 등)을 판단하십시오.
    2. **표준 매핑:** 내장된 표준서 PDF에서 해당 형상의 페이지를 찾아 **가공 여유**를 찾으십시오.
       - *근거 필수: "표준서 00페이지 표를 참조함"*
    3. **치수 및 중량 계산 (비중 7.85):**
       - **도면 중량:** 정삭 치수 부피 x 7.85 / 1,000
       - **단조 치수:** 정삭 치수 + (여유값 x 2)
       - **단조 중량:** 단조 치수 부피 x 7.85 / 1,000

    [출력 원칙]
    - 언어: 한국어
    - 숫자: 천 단위 콤마(,) 표기

    [출력 포맷]
    | 구분 | 항목 | 내용 | 비고/근거 |
    |---|---|---|---|
    | **1. 기본 정보** | 제품 형상 | (예: TUBE SHEET) | 표준서 참조 |
    | | 정삭(도면) 치수 | OD: 000, T: 000 (mm) | 도면 판독 |
    | | **도면 중량** | **0,000 kg** | 이론 계산 |
    | **2. 여유 적용** | 적용 기준 | **Total +00mm** | **표준서 Pg.00 [표 번호]** |
    | **3. 단조 스펙** | 단조(소재) 치수 | OD: 000, T: 000 (mm) | 정삭 + 여유 |
    | | **단조 중량** | **0,000 kg** | 소재 중량 계산 |

    **[종합 의견]**
    - 특이사항이나 협의 사항이 있다면 명시.
    """
    
    with st.spinner(f"AI({model_name})가 분석 중입니다..."):
        try:
            response = model.generate_content([prompt, drawing_blob, standard_blob])
            return response.text
        except Exception as e:
            return f"Error: {str(e)}"

# --- 5. 메인 실행 ---
if st.button("🚀 표준 견적 산출 시작", use_container_width=True):
    if not drawing_file:
        st.error("⚠️ 도면 파일을 업로드해주세요.")
    elif not os.path.exists("standard.pdf"):
        st.error("⚠️ GitHub에 standard.pdf가 없습니다.")
    else:
        try:
            col1, col2 = st.columns([1, 1.5])
            with col1:
                st.subheader("📄 도면 미리보기")
                if drawing_file.type.startswith('image'):
                    st.image(drawing_file, use_container_width=True)
                else:
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
            st.error(f"오류: {e}")
