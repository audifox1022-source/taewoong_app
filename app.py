import streamlit as st
import google.generativeai as genai
from PIL import Image
import os

# --- 1. 앱 기본 설정 ---
st.set_page_config(page_title="태웅 표준 견적 시스템", layout="wide")

st.title("🏭 태웅(TAEWOONG) AI 표준 견적 & 중량 산출기")
st.markdown("""
**[사용 방법]**
1. **[제품 도면]** (이미지 또는 PDF)을 업로드하세요.
2. **'견적 산출 시작'** 버튼을 누르세요.
   *(가공여유표준서는 시스템에 내장되어 있어 자동 적용됩니다)*
""")

# --- 2. 사이드바 ---
with st.sidebar:
    st.header("📂 도면 업로드")
    
    # 도면 파일
    drawing_file = st.file_uploader(
        "1️⃣ 제품 도면 (JPG/PNG/PDF)", 
        type=["jpg", "jpeg", "png", "pdf"],
        help="캐드 파일은 PDF로 변환해서 올려주세요."
    )
    
    # 표준 문서 로드 확인
    standard_path = "standard.pdf" 
    
    st.divider()
    if os.path.exists(standard_path):
        st.success("✅ 표준서(standard.pdf) 로드 완료")
    else:
        st.error("❌ 표준서 파일이 없습니다!")
        st.info("GitHub 저장소에 'standard.pdf' 파일을 업로드해주세요.")

# --- 3. AI 분석 로직 ---
def analyze_drawing_with_standard(drawing_blob):
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
    except:
        st.error("⚠️ 서버에 API 키가 설정되지 않았습니다.")
        return "Error"

    # [수정됨] 가장 표준적인 모델명 사용 + 실패 시 구형 모델로 자동 전환
    model_name = 'gemini-1.5-flash'
    
    try:
        model = genai.GenerativeModel(model_name)
    except:
        # 만약 1.5 Flash가 안 되면 구형 Pro 모델 시도
        model = genai.GenerativeModel('gemini-pro')

    # 내장된 표준서 파일 읽기
    try:
        with open("standard.pdf", "rb") as f:
            standard_data = f.read()
        standard_blob = {"mime_type": "application/pdf", "data": standard_data}
    except FileNotFoundError:
        return "Error: GitHub에 standard.pdf 파일이 없습니다."

    prompt = """
    당신은 (주)태웅의 **'단조 견적 및 중량 산출 전문가'**입니다.
    시스템에 내장된 **[PE-WS-1606-001 가공여유표준]**을 법전처럼 준수하여, 사용자가 업로드한 **[도면 파일]**의 단조 스펙을 산출하십시오.

    [작업 프로세스]
    1. **형상 분류:** 도면을 보고 제품 형상(Ring, Shaft, Tube Sheet, Disc 등)을 판단하십시오.
    2. **표준 매핑:** 내장된 표준서 PDF에서 해당 형상의 페이지를 찾아, 치수(OD, T 등)에 맞는 **가공 여유**를 찾으십시오.
       - *반드시 "표준서 00페이지 표를 참조함"이라고 근거를 대야 합니다.*
    3. **치수 및 중량 계산 (비중 7.85 적용):**
       - **도면 중량:** 정삭(Final) 치수 부피 x 7.85 / 1,000
       - **단조(소재) 치수:** 정삭 치수 + (여유값 x 2, 양측 기준)
         *길이(L)나 두께(T) 방향 여유가 다르면 각각 적용.*
       - **단조 중량:** 단조(Raw) 치수 부피 x 7.85 / 1,000

    [출력 원칙]
    - **언어:** 자연스러운 한국어로 작성.
    - **숫자:** 천 단위 콤마(,) 표기 필수.

    [출력 포맷]
    결과는 아래 마크다운 표 형식으로 작성하십시오.

    | 구분 | 항목 | 내용 | 비고/근거 |
    |---|---|---|---|
    | **1. 기본 정보** | 제품 형상 | (예: TUBE SHEET) | 표준서 참조 |
    | | 정삭(도면) 치수 | OD: 000, ID: 000, T: 000 (mm) | 도면 판독 |
    | | **도면 중량** | **0,000 kg** | 이론 중량 계산 |
    | **2. 여유 적용** | 적용 기준 | **편측 +00mm (Total +00mm)** | **표준서 Pg.00 [표 번호]**<br>구간: 00~00 적용 |
    | **3. 단조 스펙** | 단조(소재) 치수 | OD: 000, ID: 000, T: 000 (mm) | 정삭 + 여유 |
    | | **단조 중량** | **0,000 kg** | 소재 중량 계산 |

    **[종합 의견]**
    - 표준서의 '협의 사항'이나 특이사항이 있다면 한글로 명확히 명시해주세요.
    """
    
    with st.spinner("AI가 내장된 표준서를 검토하고 도면을 분석 중입니다... (약 10초 소요)"):
        try:
            response = model.generate_content([prompt, drawing_blob, standard_blob])
            return response.text
        except Exception as e:
            # 상세한 에러 메시지 출력
            return f"Error ({model_name}): {str(e)}"

# --- 4. 메인 실행 화면 ---
if st.button("🚀 표준 견적 산출 시작", use_container_width=True):
    if not drawing_file:
        st.error("⚠️ 제품 도면 파일을 업로드해주세요.")
    elif not os.path.exists("standard.pdf"):
        st.error("⚠️ 시스템 오류: GitHub에 'standard.pdf' 파일이 없습니다. 관리자에게 문의하세요.")
    else:
        try:
            # 화면 분할
            col1, col2 = st.columns([1, 1.5])
            
            # 왼쪽: 도면 미리보기
            with col1:
                st.subheader("📄 업로드된 도면")
                if drawing_file.type.startswith('image'):
                    img = Image.open(drawing_file)
                    st.image(img, use_container_width=True)
                elif drawing_file.type == 'application/pdf':
                    st.info(f"📂 PDF 도면 파일이 업로드되었습니다:\n{drawing_file.name}")
                    st.markdown("*(PDF 도면 내용은 AI가 직접 열람하여 분석합니다)*")
            
            # 데이터 준비
            drawing_blob = {"mime_type": drawing_file.type, "data": drawing_file.getvalue()}
            
            # 오른쪽: 분석 결과
            with col2:
                result_text = analyze_drawing_with_standard(drawing_blob)
                if "Error" not in result_text:
                    st.subheader("📋 AI 표준 견적 분석 결과")
                    st.markdown(result_text)
                    st.success("분석 완료!")
                else:
                    st.error(f"분석 실패: {result_text}")
                
        except Exception as e:
            st.error(f"시스템 오류가 발생했습니다: {e}")
