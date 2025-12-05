import streamlit as st
import google.generativeai as genai
from PIL import Image
import os
import importlib.metadata
import time

# --- [비상 조치] 라이브러리 강제 업데이트 및 재설치 (이전 코드 유지) ---
def install_package(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", package])
    
try:
    import google.generativeai as genai
    import importlib.metadata
except ImportError:
    st.warning("⚠️ AI 라이브러리가 없어 설치 중입니다...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "google-generativeai>=0.8.3"])
    import google.generativeai as genai
    st.experimental_rerun() # 업데이트 후 리로드

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
1. 왼쪽 사이드바에서 **제품 형상**을 먼저 선택하세요.
2. **[제품 도면]**을 업로드하세요.
3. **'견적 산출 시작'** 버튼을 누르세요.
""")

# --- 2. 사이드바 (핵심 변경 부분) ---
with st.sidebar:
    st.header("⚙️ 작업 설정")
    
    # [핵심 수정 부분 A] selected_shape 값을 st.selectbox가 직접 반환하도록 합니다.
    shape_options = [
        "TUBE SHEET & DISC", 
        "SHAFT (PRO/INTER)", 
        "RING (TOWER FLANGE/CARBON/ALLOY)", 
        "SHELL / PIPE", 
        "R-BAR / SQ-BAR", 
        "HALF RING"
    ]
    # **KeyError 해결:** st.selectbox의 반환값(selected_shape)을 직접 사용합니다.
    selected_shape = st.selectbox(
        "1️⃣ 제품 형상 선택", 
        options=shape_options, 
        help="표준서 PE-WS-1606-001의 섹션에 맞춰 선택해 주세요."
    )
    
    st.divider()
    
    # 2. 도면 파일 업로드
    drawing_file = st.file_uploader(
        "2️⃣ 제품 도면 (JPG/PNG/PDF)", 
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
    # API 키 설정
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
    except:
        return None, "API Key Error"

    # 모델 목록을 순서대로 테스트 (최신 버전 0.8.5에서도 작동하는 안정적인 방식)
    candidates = [
        'gemini-1.5-flash',
        'gemini-1.5-pro', 
        'gemini-pro'
    ]
    
    for model_name in candidates:
        try:
            model = genai.GenerativeModel(model_name)
            # 모델이 생성 가능한지 테스트 (성능 테스트 대신 존재 여부만 확인)
            return model, model_name
        except:
            continue
            
    return None, "No Working Model Found"

# --- 4. AI 분석 로직 ---
def analyze_drawing_with_standard(drawing_blob, selected_shape):
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

    # Prompt (사용자 선택 형상을 최우선 적용)
    prompt = f"""
    당신은 (주)태웅의 **'단조 견적 및 중량 산출 전문가'**입니다.
    사용자가 지정한 제품 형상은 **'{selected_shape}'**입니다. 도면의 시각적 판단보다 이 형상을 최우선으로 간주하여 견적을 산출하십시오.
    
    [작업 프로세스]
    1. **형상 분류:** **'{selected_shape}'** 형상으로 간주하고 분석을 진행하십시오.
    2. **표준 매핑:** 내장된 표준서 PDF에서 해당 '{selected_shape}' 형상의 섹션을 찾아, 도면 치수(OD, T 등)에 맞는 **가공 여유**를 찾으십시오.
       - *근거 필수: "표준서 00페이지 표를 참조함"*
    3. **치수 및 중량 계산 (비중 7.85):**
       - **도면 중량:** 정삭 치수 부피 x 7.85 / 1,000
       - **단조 치수:** 정삭 치수 + (여유값 x 2)
       - **단조 중량:** 단조 치수 부피 x 7.85 / 1,000

    [출력 포맷]
    | 구분 | 항목 | 내용 | 비고/근거 |
    |---|---|---|---|
    | **1. 기본 정보** | 제품 형상 | **{selected_shape}** | **사용자 지정** |
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
            response = model.generate_content([prompt, drawing_blob, standard_blob])
            return response.text
        except Exception as e:
            return f"Error ({model_name} execution): {str(e)}"

# --- 5. 메인 실행 ---
if st.button("🚀 견적 산출 시작", use_container_width=True):
    # [핵심 수정 부분 B] 세션 상태 관련 복잡한 로직을 모두 제거하고 selected_shape 변수를 직접 사용합니다.
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
                # selected_shape 변수(st.selectbox의 반환값)를 인수로 넘김
                result_text = analyze_drawing_with_standard(drawing_blob, selected_shape) 
                
                if "Error" not in result_text:
                    st.subheader("📋 분석 결과")
                    st.markdown(result_text)
                    st.success("분석 완료!")
                else:
                    st.error(f"분석 실패: {result_text}")
        except Exception as e:
            st.error(f"시스템 오류: {e}")
