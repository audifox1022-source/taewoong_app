import streamlit as st
import google.generativeai as genai
import json # JSON.loads는 에러 출력 시 필요하므로 유지
import os
import importlib.metadata
import time
from PIL import Image # 도면 미리보기를 위해 PIL 모듈 추가 (Image 타입 처리용)

# --- 1. 앱 기본 설정 ---
st.set_page_config(page_title="영업부 수주 검토 지원 앱", layout="wide")
st.title("📄 AI 고객 스펙 검토 및 라우팅 지원 앱 (Markdown)")

# [진단용] 현재 상태 표시
try:
    current_version = importlib.metadata.version("google-generativeai")
except:
    current_version = "Unknown"
st.caption(f"System Status: google-generativeai v{current_version}")

st.markdown("""
**[사용 방법]**
* **JSON 오류 방지**를 위해 **Markdown 표** 출력 방식으로 변경되었습니다.
* 고객 문서를 업로드하면, AI가 4가지 핵심 검토 항목을 분석하여 리포트를 생성합니다.
""")

# --- 2. [핵심] 작동하는 모델 자동 탐색 ---
def get_working_model():
    try:
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

# --- 3. Markdown 리포트 생성 함수 (JSON 의존성 제거) ---
def generate_markdown_report(document_blob):
    model, model_name = get_working_model()
    
    if not model:
        return f"Error: 사용 가능한 AI 모델을 찾을 수 없습니다. ({model_name})"

    # System Instruction: Markdown Checklist 출력 강제
    prompt = """
    당신은 (주)태웅의 **영업 수주 기술 검토 전문가**입니다.
    업로드된 고객 서류(계약서, 시방서, 도면)를 면밀히 분석하여, 다음 4가지 핵심 검토 항목에 대한 결과를 **반드시 아래 마크다운 체크리스트 형식으로만** 출력하십시오.

    [검토 항목 및 지침]
    1. 재질 적합성: 요구 물성치(시방서 기준) 대비 투입 재질의 적합성 판단 (PASS/FAIL/WARNING 중 하나로 명시).
    2. 입회 포인트: 고객 또는 TPI 입회가 필요한 공정 단계 목록 (Forging, Heat Treatment, NDT 등).
    3. 검사 종류: 확정된 NDE 및 기계적 시험 목록과 요구 레벨.
    4. 고객 요구사항: 핵심 치수, 수량, 납기일 등 추출된 기본 정보.

    [출력 포맷 시작]
    ## 📋 라우팅 확정 기술 검토 체크리스트

    | 항목 | 추출/판단 결과 | 근거 및 비고 |
    |:---|:---|:---|
    | **고객 요구 재질** | [고객 요구 재질 Spec] | [Final Dimensions, Quantity] |
    | **재질 적합성** | [PASS/FAIL/WARNING] | [요구 물성치 대비 실제 재질 적합 여부] |
    | **필수 입회 포인트** | [Forging, NDT Final 등 해당 단계 목록] | [시방서의 Witness/Hold Point 요구 근거] |
    | **확정 검사 종류** | UT Level [레벨], MPI [Required/N/A], Charpy [Required/N/A] | [요구된 검사 목록 확정] |

    **[종합 의견 및 다음 공정 라우팅 제안]**
    - **분석 상태:** [SUCCESS/WARNING/FAIL 중 하나 명시]
    - **라우팅 제안:** [다음 공정 순서 초안 제안]
    """
    
    with st.spinner(f"AI({model_name})가 고객 문서를 분석 중입니다..."):
        try:
            # Markdown 출력이므로 response_mime_type 설정 제거
            response = model.generate_content(
                contents=[prompt, document_blob]
            )
            return response.text
            
        except Exception as e:
            return f"Error: 분석 중 오류 발생: {str(e)}"

# --- 4. Streamlit 메인 화면 ---
st.set_page_config(page_title="영업부 수주 검토 지원 앱", layout="wide")
st.title("📄 AI 고객 스펙 검토 및 라우팅 지원 앱 (Markdown)")

# 파일 업로더
document_file = st.file_uploader(
    "1️⃣ 고객 문서 업로드 (PDF/Image)", 
    type=["pdf", "jpg", "jpeg", "png"],
    help="도면, 시방서, 계약서 등 검토할 모든 문서를 올리세요."
)

if st.button("🚀 수주 검토 시작 및 리포트 생성", use_container_width=True):
    if not document_file:
        st.error("⚠️ 검토할 고객 문서를 업로드해주세요.")
    else:
        # 파일 데이터를 Blob 형태로 변환
        document_blob = {"mime_type": document_file.type, "data": document_file.getvalue()}
        
        col1, col2 = st.columns([1, 1.5])
        
        with col1:
            st.subheader("📄 문서 미리보기")
            try:
                if document_file.type.startswith('image'):
                    st.image(document_file, use_container_width=True)
                else: # PDF
                    st.info(f"PDF 파일: {document_file.name} - AI가 내용을 직접 분석합니다.")
            except Exception:
                 st.info("문서 미리보기 오류. AI 분석은 계속 진행합니다.")
        
        with col2:
            result_text = generate_markdown_report(document_blob)
            
            st.subheader("✅ 최종 검토 결과 리포트")

            if result_text.startswith("Error"):
                st.error(result_text)
            else:
                st.markdown(result_text)
                st.success("분석 완료!")
                
                st.subheader("📝 전체 결과 복사 (Copyable Text)")
                st.code(result_text, language="markdown") # Markdown 코드 블록으로 복사 용이하게 출력

위 코드를 분석해서 어떤 앱인지 알아볼수있겠어?
