import streamlit as st
import os
import sys
import subprocess
import time

# --- [비상 조치] 라이브러리 강제 업데이트 및 재설치 ---
# 서버가 requirements.txt를 무시할 경우를 대비해 코드에서 직접 설치 명령을 내립니다.
def install_package(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", package])

try:
    import google.generativeai as genai
    import importlib.metadata
    
    # 현재 설치된 버전 확인
    current_version = importlib.metadata.version("google-generativeai")
    
    # 0.8.3 미만이면 강제로 업데이트 실행
    if current_version < "0.8.3":
        st.warning(f"⚠️ 구버전 라이브러리(v{current_version}) 감지됨. 최신 버전으로 강제 업데이트 중...")
        install_package("google-generativeai>=0.8.3")
        st.success("✅ 업데이트 완료! 앱을 재실행합니다.")
        time.sleep(2)
        st.rerun() # 앱 스스로 새로고침
        
except ImportError:
    # 라이브러리가 아예 없으면 설치
    st.warning("⚠️ AI 라이브러리가 없습니다. 설치 중...")
    install_package("google-generativeai>=0.8.3")
    st.rerun()

from PIL import Image

# --- 1. 앱 기본 설정 ---
st.set_page_config(page_title="태웅 표준 견적 시스템", layout="wide")
st.title("🏭 태웅(TAEWOONG) AI 표준 견적 & 중량 산출기")

# [진단용] 현재 상태 표시 (이 숫자가 0.8.3 이상이어야 정상)
st.caption(f"System Status: google-generativeai v{importlib.metadata.version('google-generativeai')}")

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
        st.success("✅ 표준서(standard.pdf) 로드 완료")
    else:
        st.error("❌ 표준서 파일 없음!")
        st.info("GitHub 저장소에 'standard.pdf' 파일을 업로드해주세요.")

# --- 3. [핵심] 작동하는 모델 자동 탐색 ---
def get_working_model():
    # API 키 확인
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
    except:
        return None, "API Key Error"

    # 사용 가능한 모델 후보군 (최신순)
    candidates = [
        'gemini-1.5-flash',
        'gemini-1.5-flash-latest',
        'gemini-1.5-pro',
        'gemini-pro'
    ]
    
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
        return f"Error: 사용 가능한 AI 모델을 찾을 수 없습니다. (API Key 확인 필요)"

    # 표준서 읽기
    try:
        with open("standard.pdf", "rb") as f:
            standard_data = f.read()
        standard_blob = {"mime_type": "application/pdf", "data": standard_data}
    except FileNotFoundError:
        return "Error: GitHub에 standard.pdf 파일이 없습니다."

    prompt = f"""
    당신은 (주)태웅의 **'단조 견적 및 중량 산출 전문가'**입니다.
    [cite_start]내장된 **[PE-WS-1606-001 가공여유표준]**을 준수하여, 사용자가 업로드한 **[도면 파일]**의 견적을 산출하십시오. [cite: 4]

    [작업 절차]
    1. [cite_start]**형상 분류:** 제품 형상(Ring, Shaft, Tube Sheet, Disc 등) 판단. [cite: 35, 36, 39]
    2. [cite_start]**표준 매핑:** 해당 형상 페이지의 표에서 치수(OD, T 등)에 맞는 **가공 여유** 탐색. [cite: 47, 71, 111]
       - *근거 필수: "표준서 00페이지 표를 참조함"*
    3. **계산 (비중 7.85):**
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
    | **3. 단조 스펙** | 단조(소재) 치수 | OD: 000, T: 000 (mm) | 정삭 + 여유 |
    | | **단조 중량** | **0,000 kg** | 소재 중량 계산 |
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
        st.error("⚠️ GitHub에 standard.pdf 파일이 없습니다.")
    else:
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
