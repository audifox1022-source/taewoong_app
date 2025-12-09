import streamlit as st
import google.generativeai as genai
import json 
import os
import importlib.metadata
import time
from PIL import Image 
import io 

# --- 1. 앱 기본 설정 ---
st.set_page_config(page_title="영업부 수주 검토 지원 앱", layout="wide")
st.title("📄 AI 고객 스펙 검토 및 라우팅 지원 앱 (2.5 Flash 복구)")

# [진단용] 현재 상태 표시
try:
    current_version = importlib.metadata.version("google-generativeai")
except:
    current_version = "Unknown"
st.caption(f"System Status: google-generativeai v{current_version}")

st.markdown("""
**[사용 방법]**
* **모델 복구:** 작동이 확인된 **Gemini 2.5 Flash** 모델을 최우선으로 연결합니다.
* **출하 점검표:** 안정적인 생성을 위해 간소화된 목록 형식을 유지합니다.
""")

# --- 2. [핵심] 작동하는 모델 자동 탐색 (2.5 Flash 최우선) ---
def get_working_model():
    try:
        if "GOOGLE_API_KEY" not in st.secrets:
            st.error("⚠️ Streamlit Secrets에 GOOGLE_API_KEY가 없습니다.")
            return None, "API Key Missing"
            
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
    except:
        return None, "API Key Error"

    # [핵심 수정] 사용자 환경에서 작동했던 'gemini-2.5-flash'를 1순위로 복구합니다.
    # 404 오류 대비를 위해 구체적인 버전명도 백업으로 둡니다.
    candidates = [
        'gemini-2.5-flash',        # 사용자 확인 작동 모델 (1순위)
        'gemini-1.5-flash-latest', # 최신 1.5 (2순위)
        'gemini-1.5-flash-001',    # 고정 1.5 (3순위)
        'gemini-1.5-flash',        # 일반 1.5
        'gemini-pro'               # 구버전 백업
    ]
    
    # st.info(f"AI 모델 연결 시도 중... (후보: {len(candidates)}개)")
    
    for model_name in candidates:
        try:
            model = genai.GenerativeModel(model_name)
            # 타임아웃 없이 간단한 테스트
            model.generate_content("test")
            st.success(f"✅ AI 모델 연결 성공: {model_name}")
            return model, model_name
        except Exception as e:
            # st.warning(f"{model_name} 연결 실패.. 다음 시도")
            continue
            
    return None, "No Working Model Found"

# --- 3. Markdown 리포트 생성 함수 ---
def generate_markdown_report(document_blob):
    model, model_name = get_working_model()
    
    if not model:
        # 어떤 모델도 연결되지 않았을 때 후보 목록을 보여줍니다.
        return f"Error: 사용 가능한 AI 모델을 찾을 수 없습니다. (시도한 모델: gemini-2.5-flash 등)"

    # [프롬프트] 출하 점검표(Pre-Shipment Checklist) 포함
    prompt = """
    당신은 (주)태웅의 **영업 수주 기술 검토 및 출하 전문가**입니다.
    업로드된 고객 서류(계약서, 시방서, 도면)를 면밀히 분석하여, 다음 5가지 항목에 대한 결과를 **반드시 아래 마크다운 체크리스트 형식으로만** 출력하십시오.

    [검토 항목 및 지침]
    1. 재질 적합성: 요구 물성치(시방서 기준) 대비 투입 재질의 적합성 판단 (PASS/FAIL/WARNING).
    2. 입회 포인트: 고객 또는 TPI 입회가 필요한 공정 단계 목록.
    3. 검사 종류: 확정된 NDE 및 기계적 시험 목록과 요구 레벨.
    4. 고객 요구사항: 핵심 치수, 수량, 납기일 등 추출된 기본 정보.
    5. **출하 점검표**: 최종 출하 전 확인해야 할 필수 항목(마킹, 포장, 서류 등).

    [출력 포맷 시작]
    ## 📋 라우팅 및 출하 기술 검토 체크리스트

    | 항목 | 추출/판단 결과 | 근거 및 비고 |
    |:---|:---|:---|
    | **고객 요구 재질** | [고객 요구 재질 Spec] | [Final Dimensions, Quantity] |
    | **재질 적합성** | [PASS/FAIL/WARNING] | [요구 물성치 대비 실제 재질 적합 여부] |
    | **필수 입회 포인트** | [Forging, NDT Final 등 해당 단계 목록] | [시방서의 Witness/Hold Point 요구 근거] |
    | **확정 검사 종류** | UT Level [레벨], MPI [Required/N/A], Charpy [Required/N/A] | [요구된 검사 목록 확정] |
    | **핵심 고객 요구사항** | [치수, 수량, 납기일] | [도면/계약서 출처] |

    ---
    
    ### 📦 출하 전 최종 점검표 (Pre-Shipment Checklist)
    * **최종 검사 승인:** [O/X 확인란] (근거: 성적서 승인 여부)
    * **마킹 및 태그:** [O/X 확인란] (근거: [요구 마킹 사양 추출])
    * **포장 및 방청:** [O/X 확인란] (근거: [요구 포장 방식 추출])
    * **필수 제출 서류:** [MTC, CoC, Packing List 등 목록]

    **[종합 의견 및 다음 공정 라우팅 제안]**
    - **분석 상태:** [SUCCESS/WARNING/FAIL 중 하나 명시]
    - **라우팅 제안:** [다음 공정 순서 초안 제안]
    """
    
    with st.spinner(f"AI({model_name})가 문서를 상세 분석 중입니다..."):
        try:
            # 타임아웃 제한 해제 (2.5 모델은 빠르지만 안전을 위해)
            response = model.generate_content(
                contents=[prompt, document_blob]
            )
            return response.text
            
        except Exception as e:
            return f"Error: 분석 중 오류 발생: {str(e)}"

# --- 4. Streamlit 메인 화면 ---

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
                elif document_file.type == 'application/pdf':
                     # PDF 파일은 base64 인코딩하여 iframe으로 표시
                    base64_pdf = base64.b64encode(document_file.getvalue()).decode('utf-8')
                    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600px" type="application/pdf"></iframe>'
                    st.markdown(pdf_display, unsafe_allow_html=True)
                    st.caption(f"PDF 파일: {document_file.name} - AI가 내용을 직접 분석합니다.")
                else:
                    st.info(f"파일: {document_file.name} - AI 분석은 계속 진행합니다.")
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
                st.code(result_text, language="markdown")
