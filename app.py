import streamlit as st
import google.generativeai as genai
import json
import os
import importlib.metadata
import time
# from google.generativeai import types  <-- 불필요한 충돌 방지 위해 제거

# JSON Schema for forced structured output (AI의 출력 양식)
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "analysis_status": {"type": "string", "description": "전체 검토 결과 (SUCCESS/WARNING/FAIL)."},
        "review_date": {"type": "string", "description": "오늘 날짜 (YYYY-MM-DD)."},
        "customer_requirements": {
            "type": "object",
            "properties": {
                "material_spec": {"type": "string", "description": "고객이 요구한 재질 규격 (예: ASTM A105)."},
                "final_dimensions": {"type": "string", "description": "도면상의 최종 치수 (예: OD 2500, T 300)."},
                "quantity": {"type": "integer", "description": "요구 수량."},
                "delivery_date": {"type": "string", "description": "요구 납기일 (YYYY-MM-DD)."}
            }
        },
        "material_selection": {
            "type": "object",
            "properties": {
                "design_property_check": {"type": "string", "description": "요구 물성치 대비 재질의 적합성 판단 결과 (PASS/FAIL/WARNING)."},
                "actual_material_grade": {"type": "string", "description": "실제 투입할 재질 등급 (예: A105)."}
            }
        },
        "witness_points": {
            "type": "array",
            "items": {"type": "string", "description": "입회가 필요한 공정 단계 (Forging, HeatTreatment_QT, NDT_Final 등)."},
            "description": "고객 입회 필수 공정 리스트."
        },
        "inspection_types": {
            "type": "object",
            "description": "확정된 검사 종류 및 레벨",
            "properties": {
                "UT_Level": {"type": "string", "description": "UT 검사 레벨 (Level 1, 2, N/A)."},
                "MPI": {"type": "string", "description": "MPI 요구 여부 (Required/N/A)."},
                "Charpy": {"type": "string", "description": "Charpy Test 요구 여부 (Required/N/A)."}
            }
        }
    },
    "required": ["analysis_status", "review_date", "customer_requirements", "material_selection", "witness_points", "inspection_types"]
}

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

# --- 3. JSON 출력 강제 함수 (Core Logic) ---
def generate_json_output(document_blob):
    model, model_name = get_working_model()
    
    if not model:
        return {"error": f"사용 가능한 AI 모델을 찾을 수 없습니다. ({model_name})"}

    system_instruction = """
    당신은 (주)태웅의 **영업 수주 기술 검토 전문가**입니다.
    업로드된 고객 서류(계약서, 시방서, 도면)를 면밀히 분석하여, 4가지 핵심 검토 항목(고객 요구사항, 재질 적합성, 입회 포인트, 검사 종류)에 대한 결과를 **반드시 JSON 형식으로만** 출력해야 합니다.

    [검토 지침]
    1. '재질 적합성(design_property_check)'은 요구 물성치(시방서에 기재된 강도, 경도 등) 대비 실제 투입 재질의 물성치를 비교하여 PASS/FAIL/WARNING 중 하나로 판단하십시오.
    2. JSON Schema를 엄격히 준수하며, JSON 블록 외부에 다른 텍스트나 설명을 절대 출력하지 마십시오.
    """
    
    with st.spinner(f"AI({model_name})가 고객 문서를 분석 중입니다..."):
        try:
            # Gemini API 호출 (JSON mode 활성화)
            response = model.generate_content(
                contents=[system_instruction, document_blob], # document_blob은 고객 서류
                # [수정된 부분]: genai.types.GenerateContentConfig를 직접 사용
                config=genai.types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=RESPONSE_SCHEMA
                )
            )
            return json.loads(response.text)
            
        except Exception as e:
            # AI가 JSON 형식을 맞추지 못했거나 기타 API 오류 발생 시
            # 원인 파악을 위해 자세한 에러 메시지를 출력합니다.
            return {"error": f"JSON 분석 중 오류 발생: {str(e)}"}

# --- 4. Streamlit 메인 화면 ---
st.set_page_config(page_title="영업부 수주 검토 지원 앱", layout="wide")
st.title("📄 AI 고객 스펙 검토 및 라우팅 지원 앱")

try:
    current_version = importlib.metadata.version("google-generativeai")
except:
    current_version = "Unknown"
st.caption(f"System Status: google-generativeai v{current_version}")

# 파일 업로더
document_file = st.file_uploader(
    "1️⃣ 고객 문서 업로드 (PDF/Image)", 
    type=["pdf", "jpg", "jpeg", "png"],
    help="도면, 시방서, 계약서 등 검토할 모든 문서를 올리세요."
)

if st.button("🚀 수주 검토 시작 및 JSON 생성", use_container_width=True):
    if not document_file:
        st.error("⚠️ 검토할 고객 문서를 업로드해주세요.")
    else:
        document_blob = {"mime_type": document_file.type, "data": document_file.getvalue()}
        
        result_data = generate_json_output(document_blob)
        
        st.divider()
        st.subheader("✅ 최종 검토 결과 (JSON 출력)")

        if "error" in result_data:
            st.error(f"분석 실패: {result_data['error']}")
        else:
            status = result_data.get('analysis_status', 'N/A')
            
            # 결과에 따른 시각적 피드백
            if status == "SUCCESS":
                st.success(f"SUCCESS: 고객 요구사항 분석 완료. 검토 상태: {status}")
            elif status == "WARNING":
                 st.warning(f"WARNING: 잠재적 위험 요소 발견. 검토 상태: {status}")
            else:
                st.error(f"FAIL: 검토 실패 또는 중요한 정보 누락. 검토 상태: {status}")

            st.markdown("### 📋 라우팅 확정 체크리스트")
            st.json(result_data)
            
            # 복사하기 쉬운 코드 블록 출력
            st.subheader("📝 핵심 정보 요약 (복사 및 공유용)")
            st.code(json.dumps(result_data, indent=2, ensure_ascii=False), language="json")
