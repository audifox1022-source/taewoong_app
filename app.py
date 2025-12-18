import streamlit as st
import google.generativeai as genai
import math
import PIL.Image
import io

# --- 1. 앱 기본 설정 ---
st.set_page_config(page_title="영업부 수주 검토 지원 앱", layout="wide")

# 스타일 설정 (Lucide 아이콘 대신 이모지 사용 및 UI 정돈)
st.markdown("""
    <style>
    .main {
        background-color: #f8fafc;
    }
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        height: 3em;
        background-color: #2563eb;
        color: white;
        font-weight: bold;
    }
    .stNumberInput>div>div>input {
        border-radius: 8px;
    }
    .report-container {
        background-color: white;
        padding: 2rem;
        border-radius: 16px;
        border: 1px solid #e2e8f0;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. AI 설정 ---
# API 키는 환경 변수나 Streamlit secrets에서 가져옵니다.
API_KEY = "" # 실제 운영 환경에서는 st.secrets["GOOGLE_API_KEY"] 등을 사용하세요.
genai.configure(api_key=API_KEY)
GEMINI_MODEL_NAME = "gemini-2.5-flash-preview-09-2025"

SYSTEM_PROMPT = """당신은 (주)태웅의 글로벌 스펙 기술 검토, 공정, 물류 및 형상 분석 전문가입니다. 
업로드된 도면/문서/엑셀 파일을 분석하고, 아래 지침에 따라 결과를 출력하십시오.

[참조용 국제 표준 규격 데이터베이스]
1. ASME / ASTM: SA-105, SA-350 LF2, SA-182 F316
2. EN: P250GH, P355NH
3. JIS/KS: SF440A, SCM440

[검토 및 출력 지침]
1. 문서 식별: 문서 번호(Doc No.)와 개정 번호(Rev. No.) 필수 추출.
2. 형상 분석: 제품 형상 추론(예: 플랜지 샤프트, 링 등) 및 기하학적 특징 설명. (엑셀의 경우 데이터 시트의 치수 정보를 기반으로 형상 유추)
3. 규격 대조: 고객 요구 물성치가 국제 표준을 만족하는지 판단.
4. 치수 추출: 핵심 치수(OD, ID, H) 및 수량 추출.
5. 물류 및 출하: INCOTERMS, 포장 방식, 방청 요구사항 추출.
6. 공정 코멘트: 단조, 열처리, 절단 시 형상적 특성에 따른 위험 요소 작성."""

# --- 3. 메인 로직 ---
def main():
    st.title("📄 AI 고객 스펙 검토 및 라우팅 지원")
    st.caption("도면, 문서 및 엑셀 기반 기술 검토 통합 플랫폼")

    col1, col2 = st.columns([1, 1.2], gap="large")

    with col1:
        st.subheader("1️⃣ 문서 업로드")
        uploaded_file = st.file_uploader(
            "이미지, PDF, 엑셀 파일을 업로드하세요", 
            type=["png", "jpg", "jpeg", "pdf", "xlsx", "xls"]
        )

        if uploaded_file:
            if uploaded_file.type.startswith("image/"):
                st.image(uploaded_file, caption="업로드된 도면 미리보기", use_container_width=True)
            else:
                st.info(f"업로드된 파일: {uploaded_file.name}")

        if st.button("🚀 분석 시작"):
            if not uploaded_file:
                st.error("분석할 파일을 먼저 업로드해 주세요.")
            else:
                with st.spinner("AI가 파일을 정밀 분석 중입니다..."):
                    try:
                        model = genai.GenerativeModel(
                            model_name=GEMINI_MODEL_NAME,
                            system_instruction=SYSTEM_PROMPT
                        )
                        
                        # 파일 데이터 처리
                        file_bytes = uploaded_file.read()
                        content = [
                            "이 도면, 문서 또는 엑셀 파일을 분석하여 기술 검토 리포트를 작성해 주세요.",
                            {"mime_type": uploaded_file.type if uploaded_file.type else "application/octet-stream", "data": file_bytes}
                        ]
                        
                        response = model.generate_content(content)
                        st.session_state['analysis_result'] = response.text
                    except Exception as e:
                        st.error(f"분석 중 오류가 발생했습니다: {str(e)}")

        st.divider()
        st.subheader("⚖️ 스마트 중량/원가 계산기")
        
        with st.expander("계산기 입력 (AI 리포트 참조)", expanded=True):
            c1, c2 = st.columns(2)
            with c1:
                od = st.number_input("외경 (OD, mm)", value=1000.0)
                h = st.number_input("높이 (H, mm)", value=500.0)
                density = st.number_input("비중 (Density)", value=7.85)
            with c2:
                id_val = st.number_input("내경 (ID, mm)", value=0.0)
                qty = st.number_input("수량 (EA)", value=1, min_value=1)
                unit_price = st.number_input("kg당 단가 (원)", value=2500)

            if od > 0 and h > 0:
                volume = (math.pi * (od**2 - id_val**2) / 4) * h
                weight_per_ea = (volume * density) / 1000000
                total_weight = weight_per_ea * qty
                total_cost = total_weight * unit_price

                st.markdown(f"""
                <div style="background-color: #1e293b; padding: 1.5rem; border-radius: 12px; color: white;">
                    <p style="margin:0; font-size: 0.8rem; color: #94a3b8;">개당 중량</p>
                    <p style="margin:0; font-size: 1.2rem; font-weight: bold;">{weight_per_ea:,.1f} kg</p>
                    <hr style="border-color: #334155; margin: 0.5rem 0;">
                    <p style="margin:0; font-size: 0.8rem; color: #94a3b8;">총 중량 ({qty}EA)</p>
                    <p style="margin:0; font-size: 1.2rem; font-weight: bold;">{total_weight:,.1f} kg</p>
                    <hr style="border-color: #334155; margin: 0.5rem 0;">
                    <p style="margin:0; font-size: 0.8rem; color: #fb923c;">예상 소재비</p>
                    <p style="margin:0; font-size: 1.5rem; font-weight: 900; color: #fb923c;">{int(total_cost):,} 원</p>
                </div>
                """, unsafe_allow_html=True)

    with col2:
        st.subheader("2️⃣ AI 분석 리포트")
        if 'analysis_result' in st.session_state:
            st.markdown(f"""
            <div class="report-container">
                {st.session_state['analysis_result']}
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("📋 결과 복사 (Markdown)"):
                st.info("텍스트를 드래그하여 복사해 주세요.")
                st.code(st.session_state['analysis_result'], language="markdown")
        else:
            st.info("파일을 분석하면 결과가 여기에 표시됩니다.")

    st.markdown("---")
    st.caption("© 2024 (주)태웅 - AI 기반 영업 수주 검토 지원 시스템")

if __name__ == "__main__":
    main()
