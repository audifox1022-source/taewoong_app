import streamlit as st
import google.generativeai as genai
import os
import importlib.metadata
import base64 # PDF 미리보기를 위해 추가
from PIL import Image # 도면 미리보기를 위해 PIL 모듈 추가
import io 

# --- 1. 앱 기본 설정 ---
st.set_page_config(page_title="글로벌 영업 수주 기술 검토 앱", layout="wide")
st.title("🌐 AI 글로벌 스펙 검토 및 다국어 지원 앱 (최소 안정화 버전 - 2.5 Flash 적용)")

# [진단용] 현재 상태 표시
try:
    current_version = importlib.metadata.version("google-generativeai")
except:
    current_version = "Unknown"
st.caption(f"System Status: google-generativeai v{current_version}")

st.markdown("""
**[사용 방법]**
* 고객 문서를 업로드하면, AI가 **국제 표준 코드** 및 **INCOTERMS**를 기반으로 핵심 검토 항목을 분석합니다.
* **영문 문서는 자동으로 한글화**되어 보고서에 포함됩니다.
* **출하 조건 및 매도인/매수인 책임 범위**까지 분석합니다.
""")

# --- 2. [핵심] 작동하는 모델 자동 탐색 (2.5 Flash 단일 및 Time-out 20초) ---
def get_working_model():
    try:
        # ⚠️ 핵심 진단: Streamlit Secrets에 API 키가 있는지 확인
        if "GOOGLE_API_KEY" not in st.secrets:
            st.error("⚠️ Streamlit Secrets에 GOOGLE_API_KEY가 설정되어 있지 않습니다. 키를 설정해주세요.")
            return None, "API Key Missing in Secrets"
            
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
    except Exception as e:
        st.error(f"API Key 설정 또는 라이브러리 구성 오류: {e}")
        return None, "API Key Error"

    # 모델 후보 목록을 'gemini-2.5-flash'로 변경 (사용자 요청 반영)
    candidates = ['gemini-2.5-flash']
    
    st.info(f"AI 모델 연결 시도 중... 후보 모델: {', '.join(candidates)}")
    
    for model_name in candidates:
        try:
            model = genai.GenerativeModel(model_name)
            # Time-out 시간을 20초로 연장 유지
            model.generate_content("test", timeout=20) # 텍스트 생성 테스트
            st.success(f"✅ AI 모델 연결 성공: {model_name}")
            return model, model_name
        except Exception as e:
            # 이 시점에서 실패하면 API 키가 해당 모델을 사용할 권한이 없거나 네트워크 연결이 완전히 끊긴 것입니다.
            # st.warning(f"모델 {model_name} 연결 실패: {e}")
            continue
            
    return None, "No Working Model Found"

# --- 3. Markdown 리포트 생성 함수 (포장/출하 공정 통합 및 INCOTERMS 책임 강화) ---
def generate_global_markdown_report(document_blob):
    model, model_name = get_working_model()
    
    if not model:
        return f"Error: 사용 가능한 AI 모델을 찾을 수 없습니다. ({model_name})"

    # System Instruction: 포장 및 출하, INCOTERMS 책임 항목 추가
    prompt = f"""
    당신은 (주)태웅의 **글로벌 영업 수주 기술 및 물류 전문가**입니다.
    업로드된 고객 서류를 면밀히 분석하여, 다음 5가지 핵심 검토 항목에 대한 결과를 **반드시 아래 마크다운 체크리스트 형식으로만** 출력하십시오.

    **[최신 정보 및 국제 표준 CODE 적용]**
    - ASME, API, EN/ISO 등 주요 CODE 및 **INCOTERMS 2020**을 기반으로 기술적 적합성과 운송 조건을 판단하십시오.
    
    **[파일 유형별 상세 분석 지침]**
    - **PDF 문서**: 텍스트 내용을 심층적으로 분석하여 요구사항을 추출하고, 문맥을 이해하여 답변을 구성하십시오.
    - **도면 (이미지 파일)**: 도면 내 치수, 공차, 재질 마킹 등을 정밀하게 판독하여 분석에 반영하십시오. 시각적 정보를 텍스트 정보와 통합하여 판단하십시오.

    **[영문 내용의 한글화 지침]**
    - 주요 핵심 정보 및 분석 결과는 **자연스러운 한글로 번역**하여 보고서에 포함하십시오.
    - 전문 용어는 한글화하되, 필요시 괄호 안에 원문(영문)을 병기하여 명확성을 확보하십시오.

    [검토 항목 및 지침 (INCOTERMS 책임 상세 추가)]
    1. 재질 적합성: 고객 요구 물성치 대비 투입 재질의 적합성 판단. 주요 CODE를 근거로 제시.
    2. 입회 포인트: 고객 또는 TPI 입회가 필요한 공정 단계 목록. CODE 요구사항을 근거로 제시.
    3. 검사 종류: 확정된 NDE/DT 및 기계적 시험 목록과 요구 레벨.
    4. **포장 및 출하 조건**: 요구되는 **방청(Rust Prevention)**, **포장 방법(Crate/Box, ISPM-15)**, **마킹 요구사항**, 그리고 **INCOTERMS (예: FOB Busan, CIF Rotterdam)**를 추출하여 명시하십시오. **추출된 Incoterms 조건에 따라 매도인/매수인의 '리스크 이전 시점', '주 운송비 부담 주체', '보험 가입 의무'를 Incoterms 2020 기준에 따라 간결하게 요약하여 보고하십시오.**
    5. 핵심 고객 요구사항: 핵심 치수, 수량, 납기일, 기타 특이사항 추출.

    [출력 포맷 시작]
    ## 📋 글로벌 스펙 기술 및 출하 검토 체크리스트 (최종 보고서)

    | 항목 | 추출/판단 결과 (한글화 포함) | 근거 및 상세 비고 (CODE 및 파일 출처) |
    |:---|:---|:---|
    | **고객 요구 재질** | [고객 요구 재질 Spec. (예: SA-105N, EN 10222-2 P250GH)] | [Final Dimensions, Quantity. 도면/시방서 출처] |
    | **재질 적합성** | [PASS/FAIL/WARNING] | [요구 물성치 대비 실제 재질 적합 여부. ASME Sec. II 기준] |
    | **필수 입회 포인트** | [단조, 열처리, 최종 NDT, 수압시험 등 해당 단계 목록] | [CODE 요구 근거. API 6A, EN 10204 3.2 등] |
    | **확정 검사 종류** | UT Level [레벨], MPI [Required/N/A], Charpy Impact Test [Required/N/A] | [요구된 검사 목록 확정. ASME Sec. VIII Div.1 등] |
    | **포장 및 출하 조건** | **방청:** [장기 보존 오일/VCI], **포장:** [밀폐 목상자/ISPM-15 No.], **Incoterms:** [FOB Busan] | [계약서 또는 S/O 명시. 국제 물류 표준 근거] |
    | **INCOTERMS 책임 요약** | **매도인 의무:** [주 운송비: 없음, 리스크: 본선 적재까지, 보험: 없음] / **매수인 의무:** [주 운송비: 있음, 리스크: 본선 적재 후, 보험: 선택] | [Incoterms 2020 FOB 조건 기준] |
    | **핵심 고객 요구사항** | [핵심 치수, 수량, 납기일 등] | [도면 No. XXX-YYY 등 상세 출처] |

    **[종합 의견 및 최종 공정 라우팅 제안]**
    - **분석 상태:** [SUCCESS/WARNING/FAIL 중 하나 명시]
    - **라우팅 제안 (한글화):** [원재료 입고 -> 단조 -> 열처리 -> 가공 -> NDT -> 최종 검사 -> 방청 및 마킹 -> 특수 포장 -> 출하(Shipment)]
    """
    
    with st.spinner(f"AI({model_name})가 글로벌 스펙 및 출하 조건을 분석 중입니다..."):
        try:
            response = model.generate_content(
                contents=[prompt, document_blob]
            )
            return response.text
            
        except Exception as e:
            return f"Error: 분석 중 오류 발생: {str(e)}"

# --- 4. Streamlit 메인 화면 ---
st.header("📄 고객 문서 업로드 및 AI 분석")

# 파일 업로더
document_file = st.file_uploader(
    "1️⃣ 고객 문서 업로드 (PDF, 도면 이미지: JPG/PNG)", 
    type=["pdf", "jpg", "jpeg", "png"],
    help="도면, 시방서, 계약서 등 검토할 모든 기술 문서를 올려주세요."
)

if st.button("🚀 글로벌 수주 검토 시작 및 리포트 생성", use_container_width=True):
    if not document_file:
        st.error("⚠️ 검토할 고객 문서를 업로드해주세요.")
    else:
        document_blob = {"mime_type": document_file.type, "data": document_file.getvalue()}
        
        col1, col2 = st.columns([1, 1.5])
        
        with col1:
            st.subheader("🖼️ 문서 미리보기")
            try:
                if document_file.type.startswith('image'):
                    st.image(document_file, use_container_width=True, caption=document_file.name)
                elif document_file.type == 'application/pdf':
                    # PDF 파일은 base64 인코딩하여 iframe으로 표시
                    base64_pdf = base64.b64encode(document_file.getvalue()).decode('utf-8')
                    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600px" type="application/pdf"></iframe>'
                    st.markdown(pdf_display, unsafe_allow_html=True)
                    st.caption(f"PDF 파일: {document_file.name} - AI가 내용을 직접 분석합니다.")
                else:
                    st.info("지원하지 않는 파일 형식입니다. AI 분석은 시도됩니다.")
            except Exception as e:
                st.info(f"문서 미리보기 오류 발생: {e}. AI 분석은 계속 진행합니다.")
        
        with col2:
            result_text = generate_global_markdown_report(document_blob)
            
            st.subheader("✅ AI 최종 글로벌 검토 리포트")

            if result_text.startswith("Error"):
                st.error(result_text)
            else:
                st.markdown(result_text)
                st.success("글로벌 스펙 및 출하 조건 분석 완료!")
                
                st.subheader("📝 전체 리포트 복사 (Copyable Text)")
                st.code(result_text, language="markdown")
