import streamlit as st
import google.generativeai as genai
from PIL import Image

# --- 1. 앱 기본 설정 ---
st.set_page_config(page_title="태웅 표준 견적 시스템", layout="wide")

st.title("🏭 태웅(TAEWOONG) AI 표준 견적 & 중량 산출기")
st.markdown("""
**[사용 가이드]**
1. 왼쪽 사이드바에 **Google API Key**를 입력하세요.
2. **[제품 도면]** (이미지 또는 PDF)과 **[가공여유표준 PDF]**를 업로드하세요.
3. AI가 표준서를 기준으로 도면을 분석하여 **[도면 vs 단조]** 스펙을 한글로 산출합니다.
""")

# --- 2. 사이드바 (설정 및 파일 업로드) ---
with st.sidebar:
    st.header("⚙️ 시스템 설정")
    
    # API 키 입력
    api_key = st.text_input("🔑 Google API Key", type="password")
    
    st.divider()
    st.subheader("📂 파일 업로드")
    
    # 1. 도면 파일 (PDF 포함)
    drawing_file = st.file_uploader(
        "1️⃣ 제품 도면 (JPG/PNG/PDF)", 
        type=["jpg", "jpeg", "png", "pdf"],
        help="캐드 파일은 PDF로 변환해서 올려주세요."
    )
    
    # 2. 표준 문서 (PDF)
    standard_file = st.file_uploader("2️⃣ 가공여유표준서 (PDF)", type=["pdf"])

# --- 3. AI 분석 로직 ---
def analyze_drawing_with_standard(drawing_blob, standard_blob):
    model = genai.GenerativeModel('gemini-1.5-pro')
    
    # [수정됨] 한글 출력 강화를 위한 프롬프트
    prompt = """
    당신은 (주)태웅의 **'단조 견적 및 중량 산출 전문가'**입니다.
    시스템에 탑재된 **[PE-WS-1606-001 가공여유표준]**을 법전처럼 준수하여, 사용자가 업로드한 **[도면 파일]**의 단조 스펙을 산출하십시오.

    [작업 프로세스]
    1. **형상 분류:** 도면을 보고 제품 형상(Ring, Shaft, Tube Sheet, Disc 등)을 판단하십시오.
    2. **표준 매핑:** 탑재된 표준서 PDF에서 해당 형상의 페이지를 찾아, 치수(OD, T 등)에 맞는 **가공 여유**를 찾으십시오.
       - *반드시 "표준서 00페이지 표를 참조함"이라고 근거를 대야 합니다.*
    3. **치수 및 중량 계산 (비중 7.85 적용):**
       - **도면 중량:** 정삭(Final) 치수 부피 x 7.85 / 1,000
       - **단조(소재) 치수:** 정삭 치수 + (여유값 x 2, 양측 기준)
         *길이(L)나 두께(T) 방향 여유가 다르면 각각 적용.*
       - **단조 중량:** 단조(Raw) 치수 부피 x 7.85 / 1,000

    [출력 원칙]
    - **언어:** 모든 설명, 비고, 근거, 종합 의견은 **반드시 자연스러운 한국어**로 작성하십시오.
    - **용어:** OD(외경), ID(내경), T(두께), L(길이) 등의 약어는 업계 표준이므로 사용하되, 필요시 한글 명칭을 괄호에 병기하십시오.
    - **숫자:** 천 단위 콤마(,)를 반드시 표기하십시오. (예: 12,345)

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
    - 이 견적의 특이사항이나 표준서의 '협의 사항(Remarks)'에 해당하는 내용이 있다면 **한글로** 명확히 명시해주세요.
    - 재질에 따른 추가 여유(예: SUS +5mm 등)가 적용되었는지 여부도 설명해주세요.
    """
    
    with st.spinner("AI가 표준서를 펼쳐보고, 도면을 분석 중입니다... (약 20초 소요)"):
        response = model.generate_content([prompt, drawing_blob, standard_blob])
        return response.text

# --- 4. 메인 실행 화면 ---
if st.button("🚀 표준 견적 산출 시작", use_container_width=True):
    if not api_key:
        st.error("⚠️ 왼쪽 사이드바에 Google API Key를 입력해주세요.")
    elif not drawing_file:
        st.error("⚠️ 제품 도면 파일을 업로드해주세요.")
    elif not standard_file:
        st.error("⚠️ 가공여유표준서(PDF) 파일을 업로드해주세요.")
    else:
        try:
            genai.configure(api_key=api_key)
            
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
            standard_blob = {"mime_type": standard_file.type, "data": standard_file.getvalue()}
            
            # 오른쪽: 분석 결과
            with col2:
                result_text = analyze_drawing_with_standard(drawing_blob, standard_blob)
                st.subheader("📋 AI 표준 견적 분석 결과")
                st.markdown(result_text)
                st.success("분석 완료! 내용을 확인해주세요.")
                
        except Exception as e:
            st.error(f"분석 중 오류가 발생했습니다: {e}")