import streamlit as st
import google.generativeai as genai
import os
import importlib.metadata
import base64
from PIL import Image 
import io 

# --- (이전 설정 및 함수는 동일하게 유지) ---

# --- 2. [핵심] 작동하는 모델 자동 탐색 ---
def get_working_model():
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
    except Exception as e:
        st.error(f"API Key 설정 오류: {e}")
        return None, "API Key Error"

    candidates = ['gemini-1.5-flash-001', 'gemini-1.5-pro-001', 'gemini-pro']
    for model_name in candidates:
        try:
            model = genai.GenerativeModel(model_name)
            test_response = model.generate_content("hello", timeout=5)
            if test_response.text:
                return model, model_name
        except Exception:
            continue
            
    return None, "No Working Model Found"

# --- 3. Markdown 리포트 생성 함수 (포장/출하 공정 통합) ---
def generate_global_markdown_report(document_blob):
    model, model_name = get_working_model()
    
    if not model:
        return f"Error: 사용 가능한 AI 모델을 찾을 수 없습니다. ({model_name})"

    # System Instruction: 포장 및 출하 항목 추가 및 최종 라우팅에 반영 지시
    prompt = f"""
    당신은 (주)태웅의 **글로벌 영업 수주 기술 및 물류 전문가**입니다.
    업로드된 고객 서류를 면밀히 분석하여, 다음 5가지 핵심 검토 항목에 대한 결과를 **반드시 아래 마크다운 체크리스트 형식으로만** 출력하십시오.

    **[최신 정보 및 국제 표준 CODE 적용]**
    - ASME, API, EN/ISO 등 주요 CODE 및 **INCOTERMS (국제 무역 조건)**를 기반으로 기술적 적합성과 운송 조건을 판단하십시오.
    
    **[파일 유형별 상세 분석 지침]** (PDF, 도면 이미지 포함)

    **[영문 내용의 한글화 지침]** (핵심 정보 한글화 및 병기)

    [검토 항목 및 지침 (포장/출하 항목 추가)]
    1. 재질 적합성: 고객 요구 물성치 대비 투입 재질의 적합성 판단.
    2. 입회 포인트: 고객 또는 TPI 입회가 필요한 공정 단계 목록.
    3. 검사 종류: 확정된 NDE/DT 및 기계적 시험 목록과 요구 레벨.
    4. **포장 및 출하 조건**: 요구되는 **방청(Rust Prevention)**, **포장 방법(Crate/Box, ISPM-15)**, **마킹 요구사항**, 그리고 **INCOTERMS (예: FOB Busan, CIF Rotterdam)**를 추출하여 명시하십시오.
    5. 핵심 고객 요구사항: 핵심 치수, 수량, 납기일, 기타 특이사항 추출.

    [출력 포맷 시작]
    ## 📋 글로벌 스펙 기술 및 출하 검토 체크리스트 (최종 보고서)

    | 항목 | 추출/판단 결과 (한글화 포함) | 근거 및 상세 비고 (CODE 및 파일 출처) |
    |:---|:---|:---|
    | **고객 요구 재질** | [고객 요구 재질 Spec.] | [Final Dimensions, Quantity. 도면/시방서 출처] |
    | **재질 적합성** | [PASS/FAIL/WARNING] | [요구 물성치 대비 실제 재질 적합 여부. ASME Sec. II 기준] |
    | **필수 입회 포인트** | [단조, 열처리, 최종 NDT, 수압시험 등 해당 단계 목록] | [CODE 요구 근거. API 6A, EN 10204 3.2 등] |
    | **확정 검사 종류** | UT Level [레벨], MPI [Required/N/A], Charpy Impact Test [Required/N/A] | [요구된 검사 목록 확정. ASME Sec. VIII Div.1 등] |
    | **포장 및 출하 조건** | **방청:** [장기 보존 오일/VCI], **포장:** [밀폐 목상자/ISPM-15 No.], **Incoterms:** [FOB/CIF 등] | [계약서 또는 S/O 명시. 국제 물류 표준 근거] |
    | **핵심 고객 요구사항** | [핵심 치수, 수량, 납기일 등] | [도면 No. XXX-YYY 등 상세 출처] |

    **[종합 의견 및 최종 공정 라우팅 제안]**
    - **분석 상태:** [SUCCESS/WARNING/FAIL 중 하나 명시]
    - **라우팅 제안 (한글화):** [**원재료 입고 -> 단조 -> 열처리 -> 가공 -> NDT -> 최종 검사 -> 방청 및 마킹 -> 특수 포장 -> 출하(Shipment)**]
    """
    
    with st.spinner(f"AI({model_name})가 글로벌 스펙 및 출하 조건을 분석 중입니다..."):
        try:
            response = model.generate_content(
                contents=[prompt, document_blob]
            )
            return response.text
            
        except Exception as e:
            return f"Error: 분석 중 오류 발생: {str(e)}"

# --- 4. Streamlit 메인 화면 (코드 구조는 동일) ---
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
                # PDF 미리보기 로직 (base64 iframe) 또는 이미지 미리보기
                if document_file.type.startswith('image'):
                    st.image(document_file, use_container_width=True, caption=document_file.name)
                elif document_file.type == 'application/pdf':
                    base64_pdf = base64.b64encode(document_file.getvalue()).decode('utf-8')
                    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600px" type="application/pdf"></iframe>'
                    st.markdown(pdf_display, unsafe_allow_html=True)
                    st.caption(f"PDF 파일: {document_file.name} - AI가 내용을 직접 분석합니다.")
                else:
                    st.info("지원하지 않는 파일 형식입니다. AI 분석은 시도됩니다.")
            except Exception as e:
                st.info(f"문서 미리보기 오류 발생. AI 분석은 계속 진행합니다.")
        
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

---

### ⚠️ 주의사항

**물류 전문성 요구**:
* 포장 및 출하 조건은 **물류 및 무역 전문가**의 영역을 포함합니다. AI가 계약서나 시방서에서 **INCOTERMS 2020**과 같은 조건을 추출할 수는 있지만, **실제 물류 비용 최적화**나 **관세/통관 문제** 등은 AI 분석의 범위를 벗어납니다.
* **대응 방안**: `WARNING` 시에는 반드시 **사내 물류 팀 또는 계약 담당 부서**의 최종 확인을 거치도록 업무 플로우를 설정해야 합니다.

---

### **후속 업무 제안**
추가로 처리가 필요한 업무가 있으시면 지시해 주십시오:

**[1]** AI가 INCOTERMS (FOB, CIF 등) 추출 시, 해당 조건에 따른 **'매도인/매수인의 책임 범위'**를 요약하여 추가 보고하도록 프롬프트 강화
**[2]** **출하 전 최종 점검표(Pre-Shipment Checklist)**를 AI 리포트 말미에 자동으로 생성하는 기능 추가
**[3]** 앱 사용자가 검토를 마친 후, **'물류/기술/영업 담당자'에게 분석 결과 이메일 자동 발송** 기능 구현 검토

숫자 1, 2, 3 중 하나를 입력하거나 새로운 업무를 지시해 주시면 즉시 처리하겠습니다.
