import React from "react"
import ReactDOM from "react-dom/client"
import { motion } from "framer-motion"
import {
  ArrowRight,
  BarChart3,
  CheckCircle2,
  ShieldCheck,
  Sparkles,
  Workflow,
} from "lucide-react"
import "./styles.css"

const agentSteps = [
  "경쟁사 가격 분석",
  "최소 안전 가격 계산",
  "후보 가격표 생성",
  "마진/할인 위험 검증",
  "AI 설명 생성",
  "관리자 승인 대기",
]

const candidates = [
  {
    name: "Balanced",
    desc: "시장 중앙값과 최소 마진을 균형 있게 반영",
    margin: "28%",
    risk: "낮음",
  },
  {
    name: "Margin-Protected",
    desc: "대형몰 최저가 추종보다 마진 보호를 우선",
    margin: "34%",
    risk: "매우 낮음",
  },
  {
    name: "Entry Competitive",
    desc: "소량 주문 구간을 더 경쟁력 있게 구성",
    margin: "23%",
    risk: "검토 필요",
  },
]

function Badge({ children }) {
  return (
    <span className="inline-flex items-center rounded-full border border-slate-200 bg-white/70 px-3 py-1 text-sm text-slate-600 shadow-sm">
      {children}
    </span>
  )
}

function Card({ children, className = "" }) {
  return (
    <div className={`rounded-3xl border border-slate-200 bg-white/80 p-6 shadow-soft backdrop-blur ${className}`}>
      {children}
    </div>
  )
}

function App() {
  return (
    <main className="min-h-screen bg-[#F7F7F8] text-slate-950">
      <section className="mx-auto flex max-w-7xl flex-col gap-16 px-6 py-8 lg:px-8">
        <nav className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-slate-950 text-white">
              <Sparkles size={20} />
            </div>
            <div>
              <p className="text-sm font-semibold tracking-tight">QuoteOps AI</p>
              <p className="text-xs text-slate-500">Pricing Agent Workspace</p>
            </div>
          </div>
          <div className="hidden items-center gap-6 text-sm text-slate-600 md:flex">
            <a href="#workflow">Workflow</a>
            <a href="#candidates">Candidates</a>
            <a href="#quote">Quote</a>
          </div>
        </nav>

        <section className="grid items-center gap-10 lg:grid-cols-[1.05fr_0.95fr]">
          <motion.div
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55 }}
            className="space-y-7"
          >
            <div className="flex flex-wrap gap-3">
              <Badge>소규모 인쇄·스티커 업체용</Badge>
              <Badge>Market-aware</Badge>
              <Badge>Margin-protected</Badge>
            </div>
            <div className="space-y-5">
              <h1 className="max-w-3xl text-5xl font-semibold leading-tight tracking-[-0.04em] md:text-7xl">
                대기업 최저가를 따라가지 않는 AI 가격 운영 에이전트.
              </h1>
              <p className="max-w-2xl text-lg leading-8 text-slate-600">
                경쟁사 가격, 자사 원가, 최소 마진, 지역 경쟁력을 함께 고려해
                수량별 가격표 후보를 생성하고 검증합니다. 최종 적용은 반드시
                관리자가 승인합니다.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <button className="inline-flex items-center gap-2 rounded-full bg-slate-950 px-6 py-3 text-sm font-semibold text-white shadow-soft">
                데모 플로우 보기 <ArrowRight size={16} />
              </button>
              <button className="rounded-full border border-slate-200 bg-white px-6 py-3 text-sm font-semibold text-slate-700">
                MVP 설계 확인
              </button>
            </div>
          </motion.div>

          <Card className="space-y-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500">Agent Recommendation</p>
                <h2 className="mt-1 text-2xl font-semibold tracking-tight">
                  Margin-Protected 후보 추천
                </h2>
              </div>
              <ShieldCheck className="text-emerald-600" />
            </div>
            <div className="rounded-2xl bg-slate-950 p-5 text-white">
              <p className="text-sm text-slate-300">AI 설명 요약</p>
              <p className="mt-3 leading-7">
                대형 온라인몰 가격을 그대로 따르면 1000매 이상 구간에서 최소
                마진이 깨질 수 있습니다. 지역 경쟁형 전략에서는 소량 구간은
                경쟁력 있게, 대량 구간은 마진 보호형 가격을 권장합니다.
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              {["시장 비교", "마진 보호", "승인 대기"].map((label) => (
                <div key={label} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <CheckCircle2 className="mb-3 text-emerald-600" size={20} />
                  <p className="text-sm font-medium">{label}</p>
                </div>
              ))}
            </div>
          </Card>
        </section>

        <section id="workflow" className="grid gap-6 lg:grid-cols-[0.8fr_1.2fr]">
          <div className="space-y-4">
            <Badge>Agent Timeline</Badge>
            <h2 className="text-3xl font-semibold tracking-tight">계산은 코드가, 설명은 AI가.</h2>
            <p className="leading-7 text-slate-600">
              LLM이 숫자를 찍지 않습니다. 가격 분석, 마진 계산, 후보 생성,
              위험 검증은 백엔드의 deterministic tool이 수행하고 AI는 결과를
              이해하기 쉽게 설명합니다.
            </p>
          </div>
          <Card>
            <div className="space-y-4">
              {agentSteps.map((step, index) => (
                <div key={step} className="flex items-center gap-4">
                  <div className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-950 text-sm font-semibold text-white">
                    {index + 1}
                  </div>
                  <div className="flex-1 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                    <p className="font-medium">{step}</p>
                    <p className="text-sm text-slate-500">tool call → observation → decision</p>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </section>

        <section id="candidates" className="space-y-6">
          <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
            <div>
              <Badge>Candidate Comparison</Badge>
              <h2 className="mt-4 text-3xl font-semibold tracking-tight">가격표 후보 3개를 비교하고 승인합니다.</h2>
            </div>
            <p className="max-w-xl text-slate-600">
              후보는 데모 UI 상태입니다. 실제 가격 계산은 다음 Phase에서
              FastAPI 서비스 모듈로 구현합니다.
            </p>
          </div>
          <div className="grid gap-5 lg:grid-cols-3">
            {candidates.map((candidate) => (
              <Card key={candidate.name} className="space-y-5">
                <div className="flex items-center justify-between">
                  <h3 className="text-xl font-semibold">{candidate.name}</h3>
                  <BarChart3 className="text-slate-500" />
                </div>
                <p className="min-h-14 text-slate-600">{candidate.desc}</p>
                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-2xl bg-slate-50 p-4">
                    <p className="text-xs text-slate-500">예상 마진</p>
                    <p className="mt-1 text-2xl font-semibold">{candidate.margin}</p>
                  </div>
                  <div className="rounded-2xl bg-slate-50 p-4">
                    <p className="text-xs text-slate-500">위험도</p>
                    <p className="mt-1 text-2xl font-semibold">{candidate.risk}</p>
                  </div>
                </div>
                <button className="w-full rounded-2xl bg-slate-950 py-3 text-sm font-semibold text-white">
                  후보 검토
                </button>
              </Card>
            ))}
          </div>
        </section>

        <section id="quote" className="grid gap-6 lg:grid-cols-2">
          <Card>
            <h2 className="text-2xl font-semibold tracking-tight">고객 견적 계산기</h2>
            <div className="mt-6 space-y-4">
              {["상품: A3 전단지", "옵션: 스노우지 100g / 단면 컬러", "수량: 500매"].map((item) => (
                <div key={item} className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-700">
                  {item}
                </div>
              ))}
            </div>
          </Card>
          <Card className="flex flex-col justify-between bg-slate-950 text-white">
            <div>
              <p className="text-sm text-slate-400">예상 견적</p>
              <p className="mt-3 text-5xl font-semibold tracking-tight">₩42,000</p>
              <p className="mt-4 leading-7 text-slate-300">
                승인된 가격표 버전을 기준으로 계산되는 고객용 견적 카드입니다.
              </p>
            </div>
            <button className="mt-8 rounded-2xl bg-white py-3 text-sm font-semibold text-slate-950">
              견적 요청하기
            </button>
          </Card>
        </section>
      </section>
    </main>
  )
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />)
