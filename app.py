import React, { useState, useEffect, useMemo } from 'react';
import { 
  FileText, 
  Upload, 
  Calculator, 
  AlertCircle, 
  CheckCircle2, 
  Loader2, 
  Info, 
  Copy,
  Box,
  Truck,
  Settings,
  Scale,
  FileSpreadsheet,
  File
} from 'lucide-react';

// --- API 설정 및 상수 ---
const API_KEY = ""; // 환경에서 자동 주입됨
const GEMINI_MODEL = "gemini-2.5-flash-preview-09-2025";
const SYSTEM_PROMPT = `당신은 (주)태웅의 글로벌 스펙 기술 검토, 공정, 물류 및 형상 분석 전문가입니다. 
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
6. 공정 코멘트: 단조, 열처리, 절단 시 형상적 특성에 따른 위험 요소 작성.`;

// --- 유틸리티 함수 ---
const fetchWithRetry = async (url, options, retries = 5, backoff = 1000) => {
  try {
    const response = await fetch(url, options);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return await response.json();
  } catch (error) {
    if (retries > 0) {
      await new Promise(resolve => setTimeout(resolve, backoff));
      return fetchWithRetry(url, options, retries - 1, backoff * 2);
    }
    throw error;
  }
};

const fileToBase64 = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = () => resolve(reader.result.split(',')[1]);
    reader.onerror = (error) => reject(error);
  });
};

// --- 메인 컴포넌트 ---
export default function App() {
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [analysisResult, setAnalysisResult] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // 계산기 상태
  const [calc, setCalc] = useState({
    od: 1000,
    id: 0,
    h: 500,
    density: 7.85,
    qty: 1,
    unitPrice: 2500
  });

  // 계산 결과 파생 변수
  const results = useMemo(() => {
    const { od, id, h, density, qty, unitPrice } = calc;
    if (od <= 0 || h <= 0) return null;
    
    const volume = (Math.PI * (Math.pow(od, 2) - Math.pow(id, 2)) / 4) * h;
    const weightPerEa = (volume * density) / 1000000;
    const totalWeight = weightPerEa * qty;
    const totalCost = totalWeight * unitPrice;

    return {
      weightPerEa,
      totalWeight,
      totalCost
    };
  }, [calc]);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      if (selectedFile.type.startsWith('image/')) {
        setPreviewUrl(URL.createObjectURL(selectedFile));
      } else {
        setPreviewUrl(null); // PDF나 Excel은 이미지 미리보기가 불가하므로 아이콘으로 대체
      }
      setError(null);
    }
  };

  const isExcel = (file) => {
    return file && (
      file.name.endsWith('.xlsx') || 
      file.name.endsWith('.xls') || 
      file.type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' ||
      file.type === 'application/vnd.ms-excel'
    );
  };

  const handleAnalyze = async () => {
    if (!file) {
      setError("분석할 파일을 먼저 업로드해 주세요.");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const base64Data = await fileToBase64(file);
      const payload = {
        contents: [{
          parts: [
            { text: "이 도면, 문서 또는 엑셀 파일을 분석하여 기술 검토 리포트를 작성해 주세요." },
            { inlineData: { mimeType: file.type || "application/octet-stream", data: base64Data } }
          ]
        }],
        systemInstruction: { parts: [{ text: SYSTEM_PROMPT }] }
      };

      const result = await fetchWithRetry(
        `https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent?key=${API_KEY}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        }
      );

      const text = result.candidates?.[0]?.content?.parts?.[0]?.text;
      if (text) {
        setAnalysisResult(text);
      } else {
        throw new Error("분석 결과를 가져오지 못했습니다.");
      }
    } catch (err) {
      setError(`분석 중 오류가 발생했습니다: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const copyToClipboard = () => {
    const textArea = document.createElement("textarea");
    textArea.value = analysisResult;
    document.body.appendChild(textArea);
    textArea.select();
    document.execCommand('copy');
    document.body.removeChild(textArea);
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans p-4 md:p-8">
      {/* Header */}
      <header className="max-w-7xl mx-auto mb-8 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-slate-800 flex items-center gap-3">
            <FileText className="text-blue-600 w-8 h-8" />
            AI 고객 스펙 검토 및 라우팅 지원
          </h1>
          <p className="text-slate-500 mt-1">도면, 문서 및 엑셀 기반 기술 검토 통합 플랫폼</p>
        </div>
        <div className="flex items-center gap-2 bg-white px-4 py-2 rounded-full shadow-sm border border-slate-200">
          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
          <span className="text-sm font-medium text-slate-600">AI 모델: {GEMINI_MODEL}</span>
        </div>
      </header>

      <main className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Upload & Calculator */}
        <div className="lg:col-span-5 space-y-6">
          {/* Upload Section */}
          <section className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Upload className="w-5 h-5 text-blue-500" />
              1. 문서 업로드 (이미지/PDF/엑셀)
            </h2>
            <div className={`relative border-2 border-dashed rounded-xl p-8 transition-colors ${file ? 'border-blue-200 bg-blue-50' : 'border-slate-200 hover:border-blue-400'}`}>
              <input 
                type="file" 
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" 
                onChange={handleFileChange}
                accept="image/*,application/pdf,.xlsx,.xls,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel"
              />
              <div className="text-center">
                {file ? (
                  <div className="space-y-3">
                    {previewUrl ? (
                      <img src={previewUrl} alt="Preview" className="max-h-48 mx-auto rounded-lg shadow-sm" />
                    ) : isExcel(file) ? (
                      <div className="flex flex-col items-center">
                        <FileSpreadsheet className="w-16 h-16 mx-auto text-green-600" />
                        <span className="inline-block mt-2 px-2 py-1 bg-green-100 text-green-700 text-xs font-bold rounded">EXCEL</span>
                      </div>
                    ) : (
                      <div className="flex flex-col items-center">
                        <FileText className="w-16 h-16 mx-auto text-blue-400" />
                        <span className="inline-block mt-2 px-2 py-1 bg-blue-100 text-blue-700 text-xs font-bold rounded">PDF/DOC</span>
                      </div>
                    )}
                    <p className="text-sm font-medium text-slate-700 truncate max-w-xs mx-auto">{file.name}</p>
                  </div>
                ) : (
                  <>
                    <div className="bg-blue-100 w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-3">
                      <Upload className="text-blue-600" />
                    </div>
                    <p className="text-slate-600 font-medium">클릭 또는 드래그하여 파일 업로드</p>
                    <p className="text-slate-400 text-xs mt-1">이미지, PDF, 엑셀(.xlsx, .xls) 지원</p>
                  </>
                )}
              </div>
            </div>
            <button
              onClick={handleAnalyze}
              disabled={isLoading || !file}
              className={`w-full mt-4 py-3 rounded-xl font-bold flex items-center justify-center gap-2 transition-all ${
                isLoading || !file 
                ? 'bg-slate-100 text-slate-400 cursor-not-allowed' 
                : 'bg-blue-600 text-white hover:bg-blue-700 active:scale-95 shadow-lg shadow-blue-200'
              }`}
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  파일 분석 중...
                </>
              ) : (
                <>
                  <Settings className="w-5 h-5" />
                  분석 시작
                </>
              )}
            </button>
            {error && (
              <div className="mt-3 p-3 bg-red-50 border border-red-100 text-red-600 rounded-lg text-sm flex items-start gap-2">
                <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                {error}
              </div>
            )}
          </section>

          {/* Calculator Section */}
          <section className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Calculator className="w-5 h-5 text-indigo-500" />
              스마트 중량/원가 계산기
            </h2>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider">외경 (OD, mm)</label>
                <input 
                  type="number" 
                  value={calc.od} 
                  onChange={(e) => setCalc({...calc, od: parseFloat(e.target.value) || 0})}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none transition-all"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider">내경 (ID, mm)</label>
                <input 
                  type="number" 
                  value={calc.id} 
                  onChange={(e) => setCalc({...calc, id: parseFloat(e.target.value) || 0})}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none transition-all"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider">높이 (H, mm)</label>
                <input 
                  type="number" 
                  value={calc.h} 
                  onChange={(e) => setCalc({...calc, h: parseFloat(e.target.value) || 0})}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none transition-all"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider">비중 (Density)</label>
                <input 
                  type="number" 
                  value={calc.density} 
                  onChange={(e) => setCalc({...calc, density: parseFloat(e.target.value) || 0})}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none transition-all"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider">수량 (EA)</label>
                <input 
                  type="number" 
                  value={calc.qty} 
                  onChange={(e) => setCalc({...calc, qty: parseInt(e.target.value) || 1})}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none transition-all"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider">kg당 단가 (원)</label>
                <input 
                  type="number" 
                  value={calc.unitPrice} 
                  onChange={(e) => setCalc({...calc, unitPrice: parseInt(e.target.value) || 0})}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none transition-all"
                />
              </div>
            </div>

            {results && (
              <div className="mt-6 p-4 rounded-xl bg-slate-900 text-white space-y-3">
                <div className="flex justify-between items-center border-b border-slate-700 pb-2">
                  <span className="text-slate-400 text-sm flex items-center gap-2"><Scale className="w-4 h-4" /> 개당 중량</span>
                  <span className="font-bold text-lg">{results.weightPerEa.toLocaleString(undefined, { maximumFractionDigits: 1 })} kg</span>
                </div>
                <div className="flex justify-between items-center border-b border-slate-700 pb-2">
                  <span className="text-slate-400 text-sm flex items-center gap-2"><Box className="w-4 h-4" /> 총 중량 ({calc.qty}EA)</span>
                  <span className="font-bold text-lg">{results.totalWeight.toLocaleString(undefined, { maximumFractionDigits: 1 })} kg</span>
                </div>
                <div className="flex justify-between items-center text-orange-400">
                  <span className="text-sm font-semibold uppercase tracking-tighter flex items-center gap-2">💰 총 예상 소재비</span>
                  <span className="font-black text-xl">{Math.floor(results.totalCost).toLocaleString()} 원</span>
                </div>
              </div>
            )}
          </section>
        </div>

        {/* Right Column: AI Analysis Report */}
        <div className="lg:col-span-7">
          <section className="bg-white h-full rounded-2xl shadow-sm border border-slate-200 flex flex-col min-h-[600px]">
            <div className="p-4 border-b border-slate-100 flex items-center justify-between">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-green-500" />
                2. AI 분석 리포트
              </h2>
              {analysisResult && (
                <button 
                  onClick={copyToClipboard}
                  className="p-2 hover:bg-slate-100 rounded-lg transition-colors text-slate-500 flex items-center gap-1 text-sm"
                  title="결과 복사"
                >
                  <Copy className="w-4 h-4" /> 복사
                </button>
              )}
            </div>

            <div className="flex-1 p-6 overflow-y-auto">
              {isLoading ? (
                <div className="h-full flex flex-col items-center justify-center text-slate-400 space-y-4">
                  <div className="relative">
                    <Loader2 className="w-12 h-12 animate-spin text-blue-500" />
                    <Settings className="w-6 h-6 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-blue-200" />
                  </div>
                  <div className="text-center">
                    <p className="font-medium text-slate-600">AI가 파일을 정밀 분석 중입니다...</p>
                    <p className="text-sm">엑셀 데이터 및 형상 정보를 대조하고 있습니다.</p>
                  </div>
                </div>
              ) : analysisResult ? (
                <div className="prose prose-slate max-w-none prose-headings:font-bold prose-h2:text-xl prose-h3:text-lg prose-table:border prose-table:rounded-xl prose-th:bg-slate-50 prose-th:p-2 prose-td:p-2 prose-td:border-t">
                  <div className="whitespace-pre-wrap text-slate-700 leading-relaxed font-mono text-sm bg-slate-50 p-4 rounded-xl border border-slate-100">
                    {analysisResult}
                  </div>
                </div>
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-slate-300 space-y-3 border-2 border-dashed border-slate-100 rounded-xl">
                  <Info className="w-12 h-12" />
                  <p className="font-medium">파일을 분석하면 결과가 여기에 표시됩니다.</p>
                </div>
              )}
            </div>

            {analysisResult && (
              <div className="p-4 bg-blue-50 border-t border-blue-100 rounded-b-2xl">
                <div className="flex items-center gap-2 text-blue-700 text-sm">
                  <Info className="w-4 h-4" />
                  <span>추출된 치수 정보를 확인한 후 왼쪽 계산기에 입력하여 정밀 검토를 완료하세요.</span>
                </div>
              </div>
            )}
          </section>
        </div>
      </main>

      {/* Footer Info */}
      <footer className="max-w-7xl mx-auto mt-8 text-center text-slate-400 text-xs">
        <div className="flex items-center justify-center gap-6 mb-4">
          <div className="flex items-center gap-1"><Scale className="w-3 h-3" /> 중량 자동화</div>
          <div className="flex items-center gap-1"><Truck className="w-3 h-3" /> 물류 조건 추출</div>
          <div className="flex items-center gap-1"><FileSpreadsheet className="w-3 h-3" /> 엑셀 데이터 분석</div>
        </div>
        &copy; 2024 (주)태웅 - AI 기반 영업 수주 검토 지원 시스템
      </footer>
    </div>
  );
}
