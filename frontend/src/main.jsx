import React, { useEffect, useMemo, useState } from "react"
import { createRoot } from "react-dom/client"
import axios from "axios"
import { motion } from "framer-motion"
import {
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  Database,
  FileText,
  Lock,
  Loader2,
  RefreshCw,
  ShieldCheck,
  Sparkles,
} from "lucide-react"
import "./styles.css"

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000"

const defaultOptionSummary = "A3 / snow paper / single-sided / full color"
const stickerOptionSummary = "50mm circle / standard paper / matte coating"
const defaultQuantities = "100,500,1000"

function formatCurrency(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-"
  return `${Math.round(Number(value)).toLocaleString("ko-KR")}원`
}

function formatPercent(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-"
  return `${Math.round(Number(value) * 1000) / 10}%`
}

function normalizeDetail(detail) {
  if (Array.isArray(detail)) {
    return detail
      .map((item) => item.msg || item.message || JSON.stringify(item))
      .join(" / ")
  }
  if (typeof detail === "object" && detail !== null) return detail.message || JSON.stringify(detail)
  return detail
}

function friendlyError(error, fallback = "요청을 처리하지 못했습니다.") {
  if (!error) return fallback
  if (!error.response) {
    return "백엔드 서버에 연결할 수 없습니다. VITE_API_BASE_URL 설정과 백엔드 실행 상태를 확인해 주세요."
  }
  const status = error.response.status
  const detail = normalizeDetail(error.response.data?.detail)
  if (status === 401) return "관리자 로그인이 필요합니다. 다시 로그인한 뒤 시도해 주세요."
  if (status === 403) return "현재 계정 권한으로는 이 작업을 수행할 수 없습니다. 필요한 경우 owner 계정으로 다시 시도해 주세요."
  if (status === 404) return detail || "요청한 데이터를 찾을 수 없습니다."
  if (status === 422) return detail || "입력값을 다시 확인해 주세요. 필수 항목이 비어 있거나 형식이 올바르지 않습니다."
  return detail || fallback
}

function validateRequired(fields) {
  const missing = fields.filter(([_, value]) => value === null || value === undefined || String(value).trim() === "")
  return missing.length ? `${missing.map(([label]) => label).join(", ")} 항목을 입력해 주세요.` : ""
}

function authHeaders(token) {
  return token ? { Authorization: `Bearer ${token}` } : {}
}

function canMutate(role) {
  return role === "owner" || role === "manager"
}

function canApprove(role) {
  return role === "owner"
}

function severityTone(severity) {
  if (severity === "critical") return "danger"
  if (severity === "warning") return "warning"
  return "info"
}

function Badge({ children, tone = "neutral" }) {
  const tones = {
    neutral: "border-slate-200 bg-slate-50 text-slate-700",
    success: "border-emerald-200 bg-emerald-50 text-emerald-700",
    warning: "border-amber-200 bg-amber-50 text-amber-700",
    danger: "border-rose-200 bg-rose-50 text-rose-700",
    info: "border-blue-200 bg-blue-50 text-blue-700",
  }
  return <span className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-medium ${tones[tone]}`}>{children}</span>
}

function Card({ children, className = "", testId }) {
  return (
    <motion.section
      data-testid={testId}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={`rounded-3xl border border-slate-200 bg-white p-6 shadow-sm ${className}`}
    >
      {children}
    </motion.section>
  )
}

function StateNotice({ type = "info", title, children, action }) {
  const map = {
    loading: { icon: Loader2, tone: "text-slate-600", border: "border-slate-200 bg-slate-50" },
    empty: { icon: FileText, tone: "text-slate-600", border: "border-slate-200 bg-slate-50" },
    error: { icon: AlertTriangle, tone: "text-rose-700", border: "border-rose-200 bg-rose-50" },
    permission: { icon: Lock, tone: "text-amber-700", border: "border-amber-200 bg-amber-50" },
    success: { icon: CheckCircle2, tone: "text-emerald-700", border: "border-emerald-200 bg-emerald-50" },
    info: { icon: Sparkles, tone: "text-blue-700", border: "border-blue-200 bg-blue-50" },
  }
  const state = map[type] || map.info
  const Icon = state.icon
  return (
    <div className={`rounded-2xl border p-4 ${state.border}`}>
      <div className={`flex items-start gap-3 ${state.tone}`}>
        <Icon className={`mt-0.5 h-5 w-5 shrink-0 ${type === "loading" ? "animate-spin" : ""}`} />
        <div className="min-w-0 flex-1">
          <p className="font-semibold">{title}</p>
          {children ? <div className="mt-1 text-sm leading-6 text-slate-600">{children}</div> : null}
          {action ? <div className="mt-3">{action}</div> : null}
        </div>
      </div>
    </div>
  )
}

function EmptyState({ title = "아직 표시할 데이터가 없습니다.", children }) {
  return <StateNotice type="empty" title={title}>{children || "먼저 샘플 데이터를 준비하거나 관련 항목을 추가해 주세요."}</StateNotice>
}

function LoadingState({ title = "데이터를 불러오는 중입니다." }) {
  return <StateNotice type="loading" title={title}>잠시만 기다려 주세요.</StateNotice>
}

function ErrorState({ message, onRetry }) {
  return (
    <StateNotice
      type="error"
      title="데이터를 불러오지 못했습니다."
      action={onRetry ? <button className="rounded-xl border border-rose-200 px-3 py-2 text-sm font-semibold text-rose-700" onClick={onRetry}>다시 시도</button> : null}
    >
      {message || "백엔드 상태와 네트워크 연결을 확인해 주세요."}
    </StateNotice>
  )
}

function PermissionNotice({ role, action = "이 작업" }) {
  return (
    <StateNotice type="permission" title="권한이 필요한 작업입니다.">
      현재 역할은 <strong>{role || "알 수 없음"}</strong>입니다. {action}은 필요한 권한이 있는 관리자만 수행할 수 있습니다.
      백엔드 권한 검사가 최종 기준이며, AI는 승인 결정을 내리지 않습니다.
    </StateNotice>
  )
}

function Field({ label, children, error }) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-slate-700">{label}</span>
      {children}
      {error ? <span className="mt-1 block text-xs text-rose-600">{error}</span> : null}
    </label>
  )
}

function Input(props) {
  return <input {...props} className={`w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none focus:border-slate-400 ${props.className || ""}`} />
}

function Select(props) {
  return <select {...props} className={`w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none focus:border-slate-400 ${props.className || ""}`} />
}

function PrimaryButton({ children, disabled, title, ...props }) {
  return (
    <button
      {...props}
      disabled={disabled}
      title={title}
      className="inline-flex items-center justify-center gap-2 rounded-2xl bg-slate-950 px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
    >
      {children}
    </button>
  )
}

function SecondaryButton({ children, disabled, title, ...props }) {
  return (
    <button
      {...props}
      disabled={disabled}
      title={title}
      className="inline-flex items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-800 transition hover:border-slate-300 disabled:cursor-not-allowed disabled:text-slate-400"
    >
      {children}
    </button>
  )
}

function DataTable({ columns, rows, emptyText }) {
  if (!rows?.length) return <EmptyState>{emptyText}</EmptyState>
  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200">
      <table className="w-full text-left text-sm">
        <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
          <tr>{columns.map((column) => <th key={column.key} className="px-4 py-3">{column.label}</th>)}</tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rows.map((row, index) => (
            <tr key={row.id || index} className="align-top">
              {columns.map((column) => <td key={column.key} className="px-4 py-3 text-slate-700">{column.render ? column.render(row) : row[column.key]}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function App() {
  const [admin, setAdmin] = useState(null)
  const [token, setToken] = useState(() => localStorage.getItem("quoteops_token") || "")
  const [loginForm, setLoginForm] = useState({ email: "admin@quoteops.local", password: "quoteops-demo-admin" })
  const [loginError, setLoginError] = useState("")
  const [loginLoading, setLoginLoading] = useState(false)

  const [products, setProducts] = useState([])
  const [competitors, setCompetitors] = useState([])
  const [competitorPrices, setCompetitorPrices] = useState([])
  const [costProfiles, setCostProfiles] = useState([])
  const [priceTables, setPriceTables] = useState([])
  const [productOptions, setProductOptions] = useState([])
  const [categories, setCategories] = useState([])
  const [ladders, setLadders] = useState([])
  const [kpis, setKpis] = useState(null)
  const [dashboardInsights, setDashboardInsights] = useState(null)
  const [systemStatus, setSystemStatus] = useState(null)
  const [quotePreview, setQuotePreview] = useState(null)
  const [marketReference, setMarketReference] = useState(null)
  const [strategyTemplates, setStrategyTemplates] = useState([])
  const [quoteRequests, setQuoteRequests] = useState([])
  const [jobs, setJobs] = useState([])
  const [auditLogs, setAuditLogs] = useState([])
  const [agentLogs, setAgentLogs] = useState([])
  const [approvals, setApprovals] = useState([])

  const [initialLoading, setInitialLoading] = useState(true)
  const [loadError, setLoadError] = useState("")
  const [actionError, setActionError] = useState("")
  const [formError, setFormError] = useState("")
  const [statusMessage, setStatusMessage] = useState("")

  const [candidateForm, setCandidateForm] = useState({
    product_slug: "product-sticker",
    option_summary: stickerOptionSummary,
    quantities: "100,500",
    strategy_name: "balanced_market",
  })
  const [candidateResult, setCandidateResult] = useState(null)
  const [validationResult, setValidationResult] = useState(null)
  const [explanation, setExplanation] = useState(null)
  const [approvalNote, setApprovalNote] = useState("관리자가 검증 결과를 확인했습니다.")
  const [working, setWorking] = useState("")

  const [quoteRequestForm, setQuoteRequestForm] = useState({
    product_id: "",
    quantity: 100,
    option_summary: defaultOptionSummary,
    requester_name: "",
    requester_email: "",
    requester_phone: "",
    company_name: "",
    request_note: "",
  })

  const [simulationResult, setSimulationResult] = useState(null)
  const [comparisonResult, setComparisonResult] = useState(null)
  const [scenarioComparisonResult, setScenarioComparisonResult] = useState(null)
  const [scenarioForm, setScenarioForm] = useState({
    base_type: "price_table",
    base_id: "",
    compare_type: "candidate_table",
    compare_id: "",
  })
  const [csvResult, setCsvResult] = useState(null)
  const [reportHtml, setReportHtml] = useState("")
  const [reportTitle, setReportTitle] = useState("")

  const role = admin?.role
  const activeProduct = products.find((product) => product.slug === candidateForm.product_slug) || products[0]
  const activePriceTables = priceTables.filter((table) => table.status === "active")
  const latestCandidateId = candidateResult?.candidate_table_id
  const latestCandidateName = candidateResult?.candidate_table_name || (latestCandidateId ? `Candidate table #${latestCandidateId}` : "")

  const dashboardMetrics = useMemo(() => {
    const pricing = kpis?.pricing || {}
    const operations = kpis?.operations || {}
    return [
      ["총 상품", pricing.total_products ?? products.length],
      ["활성 상품", pricing.active_products ?? products.filter((p) => p.is_active).length],
      ["경쟁사 가격", pricing.total_competitor_prices ?? competitorPrices.length],
      ["원가 프로필", pricing.total_cost_profiles ?? costProfiles.length],
      ["활성 가격표", pricing.active_price_tables ?? activePriceTables.length],
      ["감사 로그", operations.total_audit_logs ?? auditLogs.length],
    ]
  }, [kpis, products, competitorPrices, costProfiles, activePriceTables.length, auditLogs.length])

  useEffect(() => {
    axios.defaults.baseURL = API_BASE_URL
    loadPublicData()
  }, [])

  useEffect(() => {
    if (token) {
      axios.defaults.headers.common.Authorization = `Bearer ${token}`
      loadCurrentAdmin(token)
    } else {
      delete axios.defaults.headers.common.Authorization
    }
  }, [token])

  async function loadPublicData() {
    setInitialLoading(true)
    setLoadError("")
    try {
      const [productsRes, competitorsRes, pricesRes, costsRes, tablesRes, kpisRes, insightsRes, statusRes] = await Promise.allSettled([
        axios.get("/api/products"),
        axios.get("/api/competitors"),
        axios.get("/api/competitor-prices"),
        axios.get("/api/cost-profiles"),
        axios.get("/api/price-tables"),
        axios.get("/api/dashboard/kpis"),
        axios.get("/api/dashboard/insights"),
        axios.get("/api/system/status"),
      ])
      if (productsRes.status === "fulfilled") {
        setProducts(productsRes.value.data)
        if (!quoteRequestForm.product_id && productsRes.value.data[0]) {
          setQuoteRequestForm((prev) => ({ ...prev, product_id: productsRes.value.data[0].id }))
        }
      }
      if (competitorsRes.status === "fulfilled") setCompetitors(competitorsRes.value.data)
      if (pricesRes.status === "fulfilled") setCompetitorPrices(pricesRes.value.data)
      if (costsRes.status === "fulfilled") setCostProfiles(costsRes.value.data)
      if (tablesRes.status === "fulfilled") setPriceTables(tablesRes.value.data)
      if (kpisRes.status === "fulfilled") setKpis(kpisRes.value.data)
      if (insightsRes.status === "fulfilled") setDashboardInsights(insightsRes.value.data)
      if (statusRes.status === "fulfilled") setSystemStatus(statusRes.value.data)
      const firstError = [productsRes, competitorsRes, pricesRes, costsRes, tablesRes, kpisRes, insightsRes, statusRes].find((result) => result.status === "rejected")
      if (firstError) setLoadError(friendlyError(firstError.reason))
      await loadDemoPreview()
    } catch (error) {
      setLoadError(friendlyError(error))
    } finally {
      setInitialLoading(false)
    }
  }

  async function loadProtectedData(nextToken = token) {
    const headers = authHeaders(nextToken)
    const requests = [
      axios.get("/api/product-options").then((res) => setProductOptions(res.data)),
      axios.get("/api/product-categories").then((res) => setCategories(res.data)),
      axios.get("/api/quantity-ladders").then((res) => setLadders(res.data)),
      axios.get("/api/strategy-templates").then((res) => setStrategyTemplates(res.data)),
      axios.get("/api/quote-requests").then((res) => setQuoteRequests(res.data)),
      axios.get("/api/jobs").then((res) => setJobs(res.data.items || [])),
      axios.get("/api/audit-logs").then((res) => setAuditLogs(res.data.items || res.data)),
      axios.get("/api/agent-logs").then((res) => setAgentLogs(res.data)),
      axios.get("/api/approvals", { headers }).then((res) => setApprovals(res.data)),
    ]
    await Promise.allSettled(requests)
  }

  async function loadCurrentAdmin(nextToken) {
    try {
      const response = await axios.get("/api/auth/me", { headers: authHeaders(nextToken) })
      setAdmin(response.data)
      await loadProtectedData(nextToken)
    } catch (error) {
      setLoginError(friendlyError(error))
      localStorage.removeItem("quoteops_token")
      setToken("")
      setAdmin(null)
    }
  }

  async function loadDemoPreview() {
    try {
      const quote = await axios.post("/api/quotes/preview", {
        product_slug: "product-sticker",
        quantity: 100,
        option_summary: stickerOptionSummary,
      })
      setQuotePreview(quote.data)
    } catch {
      setQuotePreview(null)
    }
    try {
      const market = await axios.get("/api/market-reference", {
        params: { product_slug: "product-sticker", quantity: 100, option_summary: stickerOptionSummary },
      })
      setMarketReference(market.data)
    } catch {
      setMarketReference(null)
    }
  }

  async function loginAdmin(event) {
    event.preventDefault()
    setLoginError("")
    const validation = validateRequired([["이메일", loginForm.email], ["비밀번호", loginForm.password]])
    if (validation) {
      setLoginError(validation)
      return
    }
    setLoginLoading(true)
    try {
      const response = await axios.post("/api/auth/login", loginForm)
      localStorage.setItem("quoteops_token", response.data.access_token)
      setToken(response.data.access_token)
      setAdmin(response.data.admin)
      await loadProtectedData(response.data.access_token)
    } catch (error) {
      setLoginError(friendlyError(error, "로그인에 실패했습니다."))
    } finally {
      setLoginLoading(false)
    }
  }

  async function logoutAdmin() {
    try {
      if (token) await axios.post("/api/auth/logout", {}, { headers: authHeaders(token) })
    } catch {
      // Logout is best effort on the client.
    }
    localStorage.removeItem("quoteops_token")
    setToken("")
    setAdmin(null)
  }

  async function generateCandidate() {
    setActionError("")
    setFormError("")
    if (!canMutate(role)) {
      setActionError("후보 가격표 생성은 owner 또는 manager 권한이 필요합니다.")
      return
    }
    const validation = validateRequired([["상품", candidateForm.product_slug], ["옵션 요약", candidateForm.option_summary], ["수량", candidateForm.quantities]])
    if (validation) {
      setFormError(validation)
      return
    }
    const quantities = candidateForm.quantities.split(",").map((item) => Number(item.trim())).filter(Boolean)
    if (!quantities.length || quantities.some((quantity) => quantity <= 0)) {
      setFormError("수량은 0보다 큰 숫자 목록으로 입력해 주세요.")
      return
    }
    setWorking("generate")
    try {
      const response = await axios.post(
        "/api/candidate-prices/generate",
        { ...candidateForm, quantities },
        { headers: authHeaders(token) },
      )
      setCandidateResult(response.data)
      setValidationResult(null)
      setExplanation(null)
      setStatusMessage("후보 가격표가 generated 상태로 저장되었습니다")
      await loadProtectedData()
    } catch (error) {
      setActionError(friendlyError(error, "후보 가격표를 생성하지 못했습니다."))
    } finally {
      setWorking("")
    }
  }

  async function validateCandidate() {
    setActionError("")
    if (!latestCandidateId) {
      setActionError("먼저 후보 가격표를 생성해 주세요.")
      return
    }
    setWorking("validate")
    try {
      const response = await axios.post(`/api/candidate-prices/${latestCandidateId}/validate`, {}, { headers: authHeaders(token) })
      setValidationResult(response.data)
      setStatusMessage("검증 결과가 저장되었습니다.")
      await loadProtectedData()
    } catch (error) {
      setActionError(friendlyError(error, "후보 검증을 실행하지 못했습니다."))
    } finally {
      setWorking("")
    }
  }

  async function explainCandidate() {
    setActionError("")
    if (!latestCandidateId) {
      setActionError("먼저 후보 가격표를 생성해 주세요.")
      return
    }
    setWorking("explain")
    try {
      const response = await axios.post(`/api/candidate-prices/${latestCandidateId}/explain`, {}, { headers: authHeaders(token) })
      setExplanation(response.data)
      setStatusMessage("AI 설명 패널을 업데이트했습니다.")
      await loadProtectedData()
    } catch (error) {
      setActionError(friendlyError(error, "AI 설명을 생성하지 못했습니다."))
    } finally {
      setWorking("")
    }
  }

  async function approveCandidate() {
    setActionError("")
    if (!canApprove(role)) {
      setActionError("후보 승인과 활성화는 owner 권한이 필요합니다.")
      return
    }
    if (!latestCandidateId) {
      setActionError("승인할 후보 가격표가 없습니다.")
      return
    }
    setWorking("approve")
    try {
      const response = await axios.post(
        `/api/candidate-prices/${latestCandidateId}/approve`,
        { reviewer_note: approvalNote },
        { headers: authHeaders(token) },
      )
      setStatusMessage(response.data.message || "후보 가격표가 승인되고 활성화되었습니다.")
      await loadPublicData()
      await loadProtectedData()
    } catch (error) {
      setActionError(friendlyError(error, "승인을 완료하지 못했습니다."))
    } finally {
      setWorking("")
    }
  }

  async function rejectCandidate() {
    setActionError("")
    if (!canApprove(role)) {
      setActionError("후보 반려는 owner 권한이 필요합니다.")
      return
    }
    if (!latestCandidateId) {
      setActionError("반려할 후보 가격표가 없습니다.")
      return
    }
    setWorking("reject")
    try {
      await axios.post(`/api/candidate-prices/${latestCandidateId}/reject`, { reviewer_note: approvalNote }, { headers: authHeaders(token) })
      setStatusMessage("후보 가격표가 반려되었습니다.")
      await loadProtectedData()
    } catch (error) {
      setActionError(friendlyError(error, "반려를 완료하지 못했습니다."))
    } finally {
      setWorking("")
    }
  }

  async function submitQuoteRequest(event) {
    event.preventDefault()
    setActionError("")
    const validation = validateRequired([
      ["상품", quoteRequestForm.product_id],
      ["수량", quoteRequestForm.quantity],
      ["옵션 요약", quoteRequestForm.option_summary],
      ["이름", quoteRequestForm.requester_name],
      ["이메일", quoteRequestForm.requester_email],
    ])
    if (validation) {
      setActionError(validation)
      return
    }
    try {
      await axios.post("/api/quote-requests", {
        ...quoteRequestForm,
        product_id: Number(quoteRequestForm.product_id),
        quantity: Number(quoteRequestForm.quantity),
      })
      setStatusMessage("견적 요청이 접수되었습니다.")
      await loadProtectedData()
    } catch (error) {
      setActionError(friendlyError(error, "견적 요청을 접수하지 못했습니다."))
    }
  }

  async function runSimulation() {
    setActionError("")
    if (!latestCandidateId) {
      setActionError("시뮬레이션할 후보 가격표가 필요합니다.")
      return
    }
    try {
      const response = await axios.post("/api/simulations/pricing", {
        product_slug: candidateForm.product_slug,
        candidate_table_id: latestCandidateId,
        option_summary: candidateForm.option_summary,
      })
      setSimulationResult(response.data)
    } catch (error) {
      setActionError(friendlyError(error, "시뮬레이션을 실행하지 못했습니다."))
    }
  }

  async function runComparison() {
    setActionError("")
    const comparisonId = activePriceTables[0]?.id || priceTables[0]?.id
    if (!comparisonId) {
      setActionError("비교할 가격표가 없습니다.")
      return
    }
    try {
      const response = await axios.get(`/api/price-tables/${comparisonId}/compare`)
      setComparisonResult(response.data)
    } catch (error) {
      setActionError(friendlyError(error, "가격표 비교를 실행하지 못했습니다."))
    }
  }

  function resolveScenarioId(type, value) {
    if (value) return Number(value)
    if (type === "candidate_table") return latestCandidateId ? Number(latestCandidateId) : null
    return activePriceTables[0]?.id || priceTables[0]?.id || null
  }

  async function runScenarioComparison() {
    setActionError("")
    const baseId = resolveScenarioId(scenarioForm.base_type, scenarioForm.base_id)
    const compareId = resolveScenarioId(scenarioForm.compare_type, scenarioForm.compare_id)
    if (!baseId || !compareId) {
      setActionError("비교할 가격표 또는 후보 가격표를 먼저 선택해 주세요.")
      return
    }
    try {
      const response = await axios.post("/api/pricing-scenarios/compare", {
        base: {
          scenario_type: scenarioForm.base_type,
          scenario_id: baseId,
        },
        compare: {
          scenario_type: scenarioForm.compare_type,
          scenario_id: compareId,
        },
      })
      setScenarioComparisonResult(response.data)
    } catch (error) {
      setActionError(friendlyError(error, "가격 시나리오 비교를 실행하지 못했습니다."))
    }
  }

  async function exportCsv(path) {
    setActionError("")
    try {
      const response = await axios.get(path, { responseType: "text", headers: authHeaders(token) })
      setCsvResult({ status: "exported", preview: String(response.data).slice(0, 240) })
    } catch (error) {
      setActionError(friendlyError(error, "CSV 내보내기를 완료하지 못했습니다."))
    }
  }

  async function openReport(path, title) {
    setActionError("")
    try {
      const response = await axios.get(path, { responseType: "text", headers: authHeaders(token) })
      const html = String(response.data)
      setReportHtml(html)
      setReportTitle(title)
      const blob = new Blob([html], { type: "text/html;charset=utf-8" })
      const url = URL.createObjectURL(blob)
      window.open(url, "_blank", "noopener,noreferrer")
      window.setTimeout(() => URL.revokeObjectURL(url), 60000)
      setStatusMessage("HTML 보고서를 생성했습니다. 새 탭에서 인쇄하거나 PDF로 저장할 수 있습니다.")
      await loadProtectedData()
    } catch (error) {
      setActionError(friendlyError(error, "보고서를 생성하지 못했습니다."))
    }
  }

  async function openCandidateReport(type) {
    if (!latestCandidateId) {
      setActionError("보고서를 만들 후보 가격표가 없습니다. 먼저 후보 가격표를 생성해 주세요.")
      return
    }
    const paths = {
      candidate: [`/api/reports/candidate/${latestCandidateId}`, "후보 가격표 보고서"],
      validation: [`/api/reports/validation/${latestCandidateId}`, "검증 보고서"],
      approval: [`/api/reports/approval/${latestCandidateId}`, "승인 증빙 보고서"],
    }
    const [path, title] = paths[type]
    await openReport(path, title)
  }

  async function openScenarioReport() {
    const baseId = resolveScenarioId(scenarioForm.base_type, scenarioForm.base_id)
    const compareId = resolveScenarioId(scenarioForm.compare_type, scenarioForm.compare_id)
    if (!baseId || !compareId) {
      setActionError("시나리오 비교 보고서를 만들 가격표 또는 후보 가격표를 먼저 선택해 주세요.")
      return
    }
    const params = new URLSearchParams({
      base_type: scenarioForm.base_type,
      base_id: String(baseId),
      compare_type: scenarioForm.compare_type,
      compare_id: String(compareId),
    })
    await openReport(`/api/reports/scenario-comparison?${params.toString()}`, "가격 시나리오 비교 보고서")
  }

  if (!admin) {
    return (
      <main data-testid="quoteops-app" className="min-h-screen bg-[#f7f7f8] px-6 py-10">
        <div className="mx-auto grid max-w-6xl gap-8 lg:grid-cols-[1.1fr_0.9fr]">
          <section className="flex flex-col justify-center">
            <Badge tone="info">QuoteOps AI</Badge>
            <h1 className="mt-6 text-5xl font-semibold tracking-tight text-slate-950">
              AI는 계산 결과를 설명하고, 가격 숫자는 백엔드가 결정합니다.
            </h1>
            <p className="mt-5 max-w-2xl text-lg leading-8 text-slate-600">
              경쟁사 가격, 내부 원가, 최소 마진, 전략 템플릿을 함께 검토해 안전한 가격표 운영을 돕는 한국어 우선 SaaS 워크스페이스입니다.
            </p>
            <div className="mt-8 grid gap-3 text-sm text-slate-700 sm:grid-cols-2">
              {[
                "AI는 가격 숫자를 생성하지 않습니다.",
                "가격은 백엔드 계산식으로 산출됩니다.",
                "경쟁사 가격은 참고 데이터입니다.",
                "최저가를 무조건 따라가지 않습니다.",
                "후보 가격표는 관리자 승인 전까지 적용되지 않습니다.",
                "승인된 가격표만 실제 견적에 사용됩니다.",
              ].map((item) => (
                <span key={item} className="rounded-2xl border border-slate-200 bg-white px-4 py-3">{item}</span>
              ))}
            </div>
          </section>

          <Card testId="login-card">
            <h2 className="text-2xl font-semibold text-slate-950">관리자 로그인</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              관리자 계정으로 로그인해야 가격표를 승인하거나 변경할 수 있습니다. AI는 승인 결정을 내리지 않으며, 최종 결정은 관리자에게 있습니다.
            </p>
            <form onSubmit={loginAdmin} className="mt-6 space-y-4">
              <Field label="이메일">
                <Input value={loginForm.email} onChange={(event) => setLoginForm({ ...loginForm, email: event.target.value })} />
              </Field>
              <Field label="비밀번호">
                <Input type="password" value={loginForm.password} onChange={(event) => setLoginForm({ ...loginForm, password: event.target.value })} />
              </Field>
              {loginError ? <ErrorState message={loginError} /> : null}
              <PrimaryButton type="submit" disabled={loginLoading}>
                {loginLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                로그인
              </PrimaryButton>
            </form>
          </Card>
        </div>
      </main>
    )
  }

  return (
    <main data-testid="quoteops-app" className="min-h-screen bg-[#f7f7f8] text-slate-950">
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/85 px-6 py-4 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-sm font-semibold text-slate-500">QuoteOps AI 운영 워크스페이스</p>
            <h1 className="text-2xl font-semibold">AI는 계산 결과를 설명하고, 관리자가 최종 승인합니다.</h1>
          </div>
          <div className="flex items-center gap-3">
            <Badge tone={role === "owner" ? "success" : role === "manager" ? "info" : "neutral"}>{admin.display_name || admin.email} · {role}</Badge>
            <SecondaryButton onClick={logoutAdmin}>로그아웃</SecondaryButton>
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl gap-6 px-6 py-8 lg:grid-cols-[260px_1fr]">
        <aside className="lg:sticky lg:top-24 lg:h-fit">
          <Card className="p-4">
            <nav className="space-y-2 text-sm">
              {[
                ["dashboard", "대시보드"],
                ["products", "상품 카탈로그"],
                ["pricing-data", "가격 데이터"],
                ["price-tables", "가격표"],
                ["candidate-generation", "후보 생성"],
                ["approval", "검증/승인"],
                ["strategy-templates", "전략 템플릿"],
                ["quote-requests", "견적 요청"],
                ["simulation", "시뮬레이션"],
                ["comparison", "가격표 비교"],
                ["reports", "보고서"],
                ["csv", "CSV 작업"],
                ["jobs", "작업 모니터"],
                ["audit-logs", "감사 로그"],
                ["role-access", "권한 안내"],
                ["system-status", "시스템 상태"],
              ].map(([id, label]) => (
                <a key={id} href={`#${id}`} aria-label={`${label} 섹션으로 이동`} className="block rounded-2xl px-3 py-2 text-slate-700 hover:bg-slate-100">
                  {label}
                </a>
              ))}
            </nav>
          </Card>
        </aside>

        <div className="space-y-6">
          <Card>
            <div className="grid gap-3 text-sm text-slate-700 sm:grid-cols-2 lg:grid-cols-3">
              {[
                "AI는 가격 숫자를 생성하지 않습니다.",
                "가격은 백엔드 계산식으로 산출됩니다.",
                "경쟁사 가격은 참고 데이터입니다.",
                "최저가를 무조건 따라가지 않습니다.",
                "후보 가격표는 관리자 승인 전까지 적용되지 않습니다.",
                "승인된 가격표만 실제 견적에 사용됩니다.",
              ].map((item) => (
                <span key={item} className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">{item}</span>
              ))}
            </div>
          </Card>

          {initialLoading ? <LoadingState /> : null}
          {loadError ? <ErrorState message={loadError} onRetry={loadPublicData} /> : null}
          {actionError ? <ErrorState message={actionError} /> : null}
          {formError ? <StateNotice type="error" title="입력값을 다시 확인해 주세요.">{formError}</StateNotice> : null}
          {statusMessage ? <StateNotice type="success" title={statusMessage} /> : null}

          <section id="dashboard">
            <Card testId="operations-kpi-dashboard">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-2xl font-semibold">운영 대시보드</h2>
                  <p className="mt-2 text-sm text-slate-600">모든 지표는 저장된 데이터에서 계산됩니다. AI는 KPI 숫자를 생성하지 않습니다.</p>
                </div>
                <BarChart3 className="h-6 w-6 text-slate-400" />
              </div>
              <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {dashboardMetrics.map(([label, value]) => (
                  <div key={label} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <p className="text-sm text-slate-500">{label}</p>
                    <p className="mt-2 text-3xl font-semibold">{value ?? "-"}</p>
                  </div>
                ))}
              </div>
              <div data-testid="dashboard-insights" className="mt-8 border-t border-slate-100 pt-6">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <h3 className="text-xl font-semibold">운영 인사이트</h3>
                    <p className="mt-2 text-sm leading-6 text-slate-600">
                      가격 운영에서 먼저 확인해야 할 항목을 요약합니다. 모든 숫자는 저장된 데이터에서 계산되며,
                      AI는 가격, 검증 결과, 승인 여부를 결정하지 않습니다.
                    </p>
                  </div>
                  <Badge tone={dashboardInsights?.data_quality?.ready_for_pricing_workflow ? "success" : "warning"}>
                    {dashboardInsights?.data_quality?.ready_for_pricing_workflow ? "운영 데이터 준비됨" : "데이터 보강 필요"}
                  </Badge>
                </div>

                {!dashboardInsights ? (
                  <div className="mt-5"><LoadingState title="운영 인사이트를 계산하는 중입니다." /></div>
                ) : (
                  <div className="mt-5 space-y-5">
                    <div>
                      <div className="mb-3 flex items-center justify-between gap-3">
                        <p className="font-semibold">먼저 확인할 항목</p>
                        <span className="text-xs text-slate-500">최근 {dashboardInsights.recent_window_days}일 기준</span>
                      </div>
                      {dashboardInsights.attention_items?.length ? (
                        <div className="grid gap-3 lg:grid-cols-2">
                          {dashboardInsights.attention_items.map((item) => (
                            <a
                              key={`${item.related_area}-${item.title}`}
                              href={item.route || "#dashboard"}
                              className="rounded-2xl border border-slate-200 bg-slate-50 p-4 transition hover:border-slate-300"
                            >
                              <div className="flex items-start justify-between gap-3">
                                <div>
                                  <p className="font-semibold text-slate-900">{item.title}</p>
                                  <p className="mt-1 text-sm leading-6 text-slate-600">{item.message}</p>
                                </div>
                                <Badge tone={severityTone(item.severity)}>{item.severity}</Badge>
                              </div>
                              {item.count !== null && item.count !== undefined ? (
                                <p className="mt-3 text-2xl font-semibold">{item.count}</p>
                              ) : null}
                            </a>
                          ))}
                        </div>
                      ) : (
                        <EmptyState title="현재 주의가 필요한 항목이 없습니다.">
                          데이터가 충분하지 않아 일부 인사이트를 계산할 수 없을 수 있습니다.
                        </EmptyState>
                      )}
                    </div>

                    <div className="grid gap-4 lg:grid-cols-4">
                      <div className="rounded-2xl border border-slate-200 p-4">
                        <p className="text-sm font-semibold">승인 대기</p>
                        <p className="mt-2 text-3xl font-semibold">{dashboardInsights.approval_queue.pending_candidate_tables}</p>
                        <p className="mt-2 text-xs leading-5 text-slate-500">후보 가격표는 owner가 직접 승인해야 적용됩니다.</p>
                      </div>
                      <div className="rounded-2xl border border-slate-200 p-4">
                        <p className="text-sm font-semibold">검증 위험</p>
                        <p className="mt-2 text-3xl font-semibold">{dashboardInsights.validation_summary.fail_count + dashboardInsights.validation_summary.warning_count}</p>
                        <p className="mt-2 text-xs leading-5 text-slate-500">기존 검증 결과만 집계합니다. 새 검증 규칙은 추가하지 않습니다.</p>
                      </div>
                      <div className="rounded-2xl border border-slate-200 p-4">
                        <p className="text-sm font-semibold">견적 후속</p>
                        <p className="mt-2 text-3xl font-semibold">{dashboardInsights.quote_request_summary.pending + dashboardInsights.quote_request_summary.reviewing}</p>
                        <p className="mt-2 text-xs leading-5 text-slate-500">접수 또는 검토 중인 고객 견적 요청입니다.</p>
                      </div>
                      <div className="rounded-2xl border border-slate-200 p-4">
                        <p className="text-sm font-semibold">작업 실패</p>
                        <p className="mt-2 text-3xl font-semibold">{dashboardInsights.job_health.failed}</p>
                        <p className="mt-2 text-xs leading-5 text-slate-500">기존 워크플로 작업 기록에서 계산됩니다.</p>
                      </div>
                    </div>

                    <div className="grid gap-4 lg:grid-cols-2">
                      <div className="rounded-2xl border border-slate-200 p-4">
                        <p className="font-semibold">데이터 준비도</p>
                        <p className="mt-2 text-sm text-slate-600">
                          가격 운영을 시작하려면 상품, 원가, 경쟁사 기준 데이터가 필요합니다.
                        </p>
                        <div className="mt-4 grid gap-2 sm:grid-cols-2">
                          {Object.entries(dashboardInsights.data_quality)
                            .filter(([key]) => key !== "ready_for_pricing_workflow")
                            .map(([key, value]) => (
                              <div key={key} className="flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2 text-sm">
                                <span className="text-slate-600">{key.replaceAll("_", " ")}</span>
                                <Badge tone={value.exists ? "success" : "warning"}>{value.count}</Badge>
                              </div>
                            ))}
                        </div>
                      </div>
                      <div className="rounded-2xl border border-slate-200 p-4">
                        <p className="font-semibold">최근 운영 활동</p>
                        <p className="mt-2 text-sm text-slate-600">
                          감사 로그와 권한 차단 이벤트를 안전한 필드만 사용해 요약합니다.
                        </p>
                        <div className="mt-4 grid gap-2 text-sm">
                          <div className="flex justify-between rounded-xl bg-slate-50 px-3 py-2">
                            <span>최근 감사 로그</span>
                            <strong>{dashboardInsights.audit_activity.recent_audit_log_count}</strong>
                          </div>
                          <div className="flex justify-between rounded-xl bg-slate-50 px-3 py-2">
                            <span>권한 차단</span>
                            <strong>{dashboardInsights.audit_activity.recent_blocked_permission_count}</strong>
                          </div>
                          <div className="flex justify-between rounded-xl bg-slate-50 px-3 py-2">
                            <span>승인/반려 이벤트</span>
                            <strong>{dashboardInsights.audit_activity.recent_approval_event_count}</strong>
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="rounded-2xl border border-slate-200 p-4">
                      <p className="font-semibold">시스템 준비 상태</p>
                      <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
                        <Badge tone="info">DB: {dashboardInsights.system_readiness.database_type}</Badge>
                        <Badge tone={dashboardInsights.system_readiness.openai_configured ? "success" : "warning"}>
                          AI 설명: {dashboardInsights.system_readiness.openai_configured ? "OpenAI" : "fallback"}
                        </Badge>
                        <Badge tone={dashboardInsights.system_readiness.audit_logging_available ? "success" : "danger"}>감사 로그</Badge>
                        <Badge tone={dashboardInsights.system_readiness.job_system_available ? "success" : "danger"}>작업 시스템</Badge>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </Card>
          </section>

          <section id="products">
            <Card testId="product-catalog-admin">
              <h2 className="text-2xl font-semibold">상품 카탈로그</h2>
              <p className="mt-2 text-sm text-slate-600">상품 구조를 먼저 정의해야 원가, 경쟁사 가격, 후보 가격표를 안정적으로 관리할 수 있습니다.</p>
              {!canApprove(role) ? <div className="mt-4"><PermissionNotice role={role} action="상품 생성/수정" /></div> : null}
              <div className="mt-5 grid gap-4 lg:grid-cols-2">
                <DataTable
                  rows={products}
                  emptyText="A3 Flyer와 Product Sticker 시드 데이터가 없다면 백엔드 시드 상태를 확인해 주세요."
                  columns={[
                    { key: "name", label: "상품" },
                    { key: "slug", label: "슬러그" },
                    { key: "is_active", label: "상태", render: (row) => <Badge tone={row.is_active ? "success" : "neutral"}>{row.is_active ? "활성" : "비활성"}</Badge> },
                  ]}
                />
                <div className="space-y-4">
                  <div className="rounded-2xl bg-slate-50 p-4">
                    <p className="font-semibold">옵션 요약 도움말</p>
                    <p className="mt-2 text-sm leading-6 text-slate-600">새 상품도 동일한 가격 흐름을 사용합니다. 원가 프로필, 경쟁사 가격, 후보 생성, 검증, AI 설명, 관리자 승인 순서가 유지됩니다.</p>
                  </div>
                  <DataTable
                    rows={productOptions.slice(0, 5)}
                    emptyText="아직 상품 옵션 데이터가 없습니다."
                    columns={[
                      { key: "option_name", label: "옵션" },
                      { key: "option_value", label: "값" },
                    ]}
                  />
                  <p className="text-xs text-slate-500">카테고리 {categories.length}개 · 수량 프리셋 {ladders.length}개</p>
                </div>
              </div>
            </Card>
          </section>

          <section id="pricing-data">
            <Card testId="workspace-overview">
              <h2 className="text-2xl font-semibold">가격 데이터 요약</h2>
              <div className="mt-5 grid gap-4 lg:grid-cols-2">
                <div data-testid="product-count" className="rounded-2xl border border-slate-200 p-4">{products.length}</div>
                <div className="rounded-2xl border border-slate-200 p-4">{products.map((product) => product.name).join(" · ") || "상품 없음"}</div>
                <div data-testid="market-reference-card" className="rounded-2xl border border-slate-200 p-4">
                  <p className="font-semibold">경쟁사 참고 데이터</p>
                  <p className="mt-2 text-sm text-slate-600">수동 입력된 참고 데이터만 사용합니다. 최저가를 무조건 따라가지 않습니다.</p>
                  <p className="mt-3 text-2xl font-semibold">{marketReference?.summary?.count ?? competitorPrices.length}</p>
                </div>
                <div data-testid="cost-margin-card" className="rounded-2xl border border-slate-200 p-4">
                  <p className="font-semibold">원가·마진 설정</p>
                  <p className="mt-2 text-sm text-slate-600">최소 마진은 수익성을 보호하기 위한 내부 기준입니다.</p>
                  <p className="mt-3 text-2xl font-semibold">{costProfiles.length}</p>
                </div>
                <div data-testid="quote-preview-card" className="rounded-2xl border border-slate-200 p-4 lg:col-span-2">
                  <p className="font-semibold">결정론적 견적</p>
                  <p className="mt-2 text-sm text-slate-600">견적 금액은 활성 가격표 또는 원가 기준 계산식으로 산출됩니다.</p>
                  <p data-testid="quote-preview-price" className="mt-3 text-3xl font-semibold">{formatCurrency(quotePreview?.quote_price)}</p>
                </div>
              </div>
            </Card>
          </section>

          <section id="price-tables">
            <Card testId="active-price-table-card">
              <h2 className="text-2xl font-semibold">가격표 관리</h2>
              <p className="mt-2 text-sm text-slate-600">내부 가격표는 수동 관리되며, 후보 가격표는 승인 전까지 적용되지 않습니다.</p>
              <div className="mt-5">
                <DataTable
                  rows={priceTables}
                  emptyText="아직 가격표가 없습니다."
                  columns={[
                    { key: "name", label: "이름" },
                    { key: "status", label: "상태", render: (row) => <Badge tone={row.status === "active" ? "success" : row.status === "draft" ? "warning" : "neutral"}>{row.status}</Badge> },
                    { key: "items", label: "행", render: (row) => row.items?.length || 0 },
                  ]}
                />
              </div>
            </Card>
          </section>

          <section id="candidate-generation">
            <Card testId="candidate-generation">
              <h2 className="text-2xl font-semibold">후보 가격표 생성</h2>
              <p className="mt-2 text-sm text-slate-600">후보 가격표는 백엔드 계산식으로 생성되며 자동 활성화되지 않습니다.</p>
              {!canMutate(role) ? <div className="mt-4"><PermissionNotice role={role} action="후보 가격표 생성" /></div> : null}
              <div className="mt-5 grid gap-4 lg:grid-cols-2">
                <Field label="상품">
                  <Select value={candidateForm.product_slug} onChange={(event) => setCandidateForm({ ...candidateForm, product_slug: event.target.value })}>
                    {products.map((product) => <option key={product.slug} value={product.slug}>{product.name}</option>)}
                  </Select>
                </Field>
                <Field label="전략">
                  <Select value={candidateForm.strategy_name} onChange={(event) => setCandidateForm({ ...candidateForm, strategy_name: event.target.value })}>
                    <option value="balanced_market">balanced_market</option>
                    <option value="margin_protect">margin_protect</option>
                    <option value="premium_local">premium_local</option>
                  </Select>
                </Field>
                <Field label="옵션 요약">
                  <Input value={candidateForm.option_summary} onChange={(event) => setCandidateForm({ ...candidateForm, option_summary: event.target.value })} />
                </Field>
                <Field label="수량 목록">
                  <Input value={candidateForm.quantities} onChange={(event) => setCandidateForm({ ...candidateForm, quantities: event.target.value })} />
                </Field>
              </div>
              <div className="mt-5 flex flex-wrap gap-3">
                <PrimaryButton onClick={generateCandidate} disabled={!canMutate(role) || working === "generate"} title={!canMutate(role) ? "owner 또는 manager 권한이 필요합니다." : ""}>
                  {working === "generate" ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                  후보 생성
                </PrimaryButton>
                <SecondaryButton onClick={validateCandidate} disabled={!latestCandidateId || working === "validate"}>후보 검증</SecondaryButton>
                <SecondaryButton onClick={explainCandidate} disabled={!latestCandidateId || working === "explain"}>AI 설명 생성</SecondaryButton>
              </div>
              {candidateResult ? (
                <div className="mt-5 rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <h3 className="font-semibold">후보 가격</h3>
                  <p className="mt-1 text-sm text-slate-600">후보 #{candidateResult.candidate_table_id} · {candidateResult.status}</p>
                  <DataTable
                    rows={candidateResult.items || []}
                    columns={[
                      { key: "quantity", label: "수량" },
                      { key: "candidate_price", label: "후보 가격", render: (row) => formatCurrency(row.candidate_price) },
                      { key: "estimated_margin_rate", label: "예상 마진", render: (row) => formatPercent(row.estimated_margin_rate) },
                    ]}
                  />
                </div>
              ) : <div className="mt-5"><EmptyState title="아직 생성된 후보 가격표가 없습니다.">상품, 옵션, 수량을 확인한 뒤 후보 생성을 실행해 주세요.</EmptyState></div>}
            </Card>
          </section>

          <section id="approval">
            <Card>
              <h2 className="text-2xl font-semibold">검증 / AI 설명 / 승인</h2>
              <p className="mt-2 text-sm text-slate-600">후보 가격표는 관리자 승인 전까지 실제 가격표로 적용되지 않습니다.</p>
              <div className="mt-5 grid gap-4 lg:grid-cols-3">
                <div className="rounded-2xl border border-slate-200 p-4">
                  <p className="font-semibold">검증 결과</p>
                  {validationResult ? (
                    <div className="mt-3 space-y-2">
                      <Badge tone={validationResult.overall_status === "fail" ? "danger" : validationResult.overall_status === "pass_with_warnings" ? "warning" : "success"}>{validationResult.overall_status}</Badge>
                      <p className="text-sm text-slate-600">위험도: {validationResult.risk_level}</p>
                    </div>
                  ) : <EmptyState title="검증 결과가 없습니다.">후보 검증을 실행하면 위험 코드와 행별 결과가 표시됩니다.</EmptyState>}
                </div>
                <div className="rounded-2xl border border-slate-200 p-4">
                  <p className="font-semibold">AI 설명 패널</p>
                  {explanation ? (
                    <div className="mt-3 space-y-2 text-sm text-slate-600">
                      <Badge tone={explanation.source === "fallback" ? "warning" : "info"}>{explanation.source}</Badge>
                      <p>{explanation.explanation}</p>
                      {(explanation.warnings || []).map((warning) => <Badge key={warning} tone="warning">{warning}</Badge>)}
                    </div>
                  ) : (
                    <StateNotice type="info" title="OpenAI API 키가 없으면 기본 설명 모드로 동작합니다.">
                      AI 설명은 가격 숫자를 생성하지 않습니다. 기존 계산 결과와 검증 내용을 한국어로 요약합니다.
                    </StateNotice>
                  )}
                </div>
                <div className="rounded-2xl border border-slate-200 p-4">
                  <p className="font-semibold">관리자 승인 패널</p>
                  {!canApprove(role) ? <div className="mt-3"><PermissionNotice role={role} action="후보 승인/반려" /></div> : null}
                  <Field label="검토 메모">
                    <Input value={approvalNote} onChange={(event) => setApprovalNote(event.target.value)} />
                  </Field>
                  <div className="mt-4 flex flex-wrap gap-2">
                    <PrimaryButton onClick={approveCandidate} disabled={!canApprove(role) || !latestCandidateId || working === "approve"}>승인하고 활성화</PrimaryButton>
                    <SecondaryButton onClick={rejectCandidate} disabled={!canApprove(role) || !latestCandidateId || working === "reject"}>거절</SecondaryButton>
                  </div>
                </div>
              </div>
              <div className="mt-5 grid gap-4 lg:grid-cols-2">
                <div>
                  <h3 className="mb-3 font-semibold">승인 이력</h3>
                  <DataTable
                    rows={approvals.slice(0, 5)}
                    emptyText="아직 승인 또는 반려 이력이 없습니다."
                    columns={[
                      { key: "action", label: "작업" },
                      { key: "reviewer_name", label: "관리자" },
                      { key: "status", label: "상태" },
                    ]}
                  />
                </div>
                <div>
                  <h3 className="mb-3 font-semibold">백엔드 실행 로그</h3>
                  <DataTable
                    rows={agentLogs.slice(0, 5)}
                    emptyText="아직 Agent Timeline 로그가 없습니다."
                    columns={[
                      { key: "step_type", label: "단계" },
                      { key: "message", label: "메시지" },
                    ]}
                  />
                </div>
              </div>
            </Card>
          </section>

          <section id="strategy-templates">
            <Card testId="strategy-template-management">
              <h2 className="text-2xl font-semibold">전략 템플릿</h2>
              <p className="mt-2 text-sm text-slate-600">전략 템플릿은 후보 생성 설정을 재사용하기 위한 도구이며, 가격표를 자동 적용하지 않습니다.</p>
              <DataTable
                rows={strategyTemplates}
                emptyText="아직 전략 템플릿이 없습니다."
                columns={[
                  { key: "name", label: "이름" },
                  { key: "strategy_name", label: "전략" },
                  { key: "is_active", label: "상태", render: (row) => <Badge tone={row.is_active ? "success" : "neutral"}>{row.is_active ? "활성" : "보관"}</Badge> },
                ]}
              />
            </Card>
          </section>

          <section id="quote-requests">
            <Card testId="quote-request-flow">
              <h2 className="text-2xl font-semibold">고객 견적 요청</h2>
              <p className="mt-2 text-sm text-slate-600">견적 요청을 남기면 관리자가 확인 후 답변합니다. 표시되는 가격은 내부 가격표와 원가 기준에 따라 계산됩니다.</p>
              <form onSubmit={submitQuoteRequest} className="mt-5 grid gap-4 lg:grid-cols-2">
                <Field label="상품"><Select value={quoteRequestForm.product_id} onChange={(event) => setQuoteRequestForm({ ...quoteRequestForm, product_id: event.target.value })}>{products.map((product) => <option key={product.id} value={product.id}>{product.name}</option>)}</Select></Field>
                <Field label="수량"><Input type="number" min="1" value={quoteRequestForm.quantity} onChange={(event) => setQuoteRequestForm({ ...quoteRequestForm, quantity: event.target.value })} /></Field>
                <Field label="옵션 요약"><Input value={quoteRequestForm.option_summary} onChange={(event) => setQuoteRequestForm({ ...quoteRequestForm, option_summary: event.target.value })} /></Field>
                <Field label="요청자 이름"><Input value={quoteRequestForm.requester_name} onChange={(event) => setQuoteRequestForm({ ...quoteRequestForm, requester_name: event.target.value })} /></Field>
                <Field label="요청자 이메일"><Input value={quoteRequestForm.requester_email} onChange={(event) => setQuoteRequestForm({ ...quoteRequestForm, requester_email: event.target.value })} /></Field>
                <Field label="요청 메모"><Input value={quoteRequestForm.request_note} onChange={(event) => setQuoteRequestForm({ ...quoteRequestForm, request_note: event.target.value })} /></Field>
                <PrimaryButton type="submit">견적 요청 접수</PrimaryButton>
              </form>
              <div className="mt-5">
                <DataTable
                  rows={quoteRequests.slice(0, 6)}
                  emptyText="아직 고객 견적 요청이 없습니다."
                  columns={[
                    { key: "requester_name", label: "이름" },
                    { key: "requester_email", label: "이메일" },
                    { key: "status", label: "상태" },
                  ]}
                />
              </div>
            </Card>
          </section>

          <section id="simulation">
            <Card testId="pricing-simulation-dashboard">
              <h2 className="text-2xl font-semibold">가격 시뮬레이션</h2>
              <p className="mt-2 text-sm text-slate-600">시뮬레이션은 가격표를 자동 적용하지 않습니다. 후보 가격표 적용 전 매출과 마진 변화를 비교합니다.</p>
              <div className="mt-5 flex gap-3">
                <SecondaryButton onClick={runSimulation}>시뮬레이션 실행</SecondaryButton>
              </div>
              <div className="mt-5">
                {simulationResult ? <pre className="max-h-64 overflow-auto rounded-2xl bg-slate-950 p-4 text-xs text-white">{JSON.stringify(simulationResult.summary || simulationResult, null, 2)}</pre> : <EmptyState title="아직 시뮬레이션 결과가 없습니다." />}
              </div>
            </Card>
          </section>

          <section id="comparison">
            <Card testId="price-table-comparison">
              <h2 className="text-2xl font-semibold">가격 시나리오 비교</h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                활성 가격표와 후보 가격표의 차이를 비교합니다. 모든 비교 수치는 저장된 가격 데이터와 검증 결과에서 계산되며,
                AI는 가격 차이, 마진, 승인 여부를 결정하지 않습니다. 승인 여부는 owner가 직접 검토해야 합니다.
              </p>
              <div className="mt-5 grid gap-4 lg:grid-cols-2">
                <div className="rounded-2xl border border-slate-200 p-4">
                  <p className="mb-3 font-semibold">기준 시나리오</p>
                  <Field label="유형">
                    <Select value={scenarioForm.base_type} onChange={(event) => setScenarioForm({ ...scenarioForm, base_type: event.target.value, base_id: "" })}>
                      <option value="price_table">가격표</option>
                      <option value="candidate_table">후보 가격표</option>
                    </Select>
                  </Field>
                  <Field label="대상">
                    <Select value={scenarioForm.base_id} onChange={(event) => setScenarioForm({ ...scenarioForm, base_id: event.target.value })}>
                      <option value="">자동 선택</option>
                      {scenarioForm.base_type === "price_table"
                        ? priceTables.map((table) => <option key={table.id} value={table.id}>{table.name} · {table.status}</option>)
                        : latestCandidateId ? <option value={latestCandidateId}>{latestCandidateName}</option> : null}
                    </Select>
                  </Field>
                </div>
                <div className="rounded-2xl border border-slate-200 p-4">
                  <p className="mb-3 font-semibold">비교 시나리오</p>
                  <Field label="유형">
                    <Select value={scenarioForm.compare_type} onChange={(event) => setScenarioForm({ ...scenarioForm, compare_type: event.target.value, compare_id: "" })}>
                      <option value="candidate_table">후보 가격표</option>
                      <option value="price_table">가격표</option>
                    </Select>
                  </Field>
                  <Field label="대상">
                    <Select value={scenarioForm.compare_id} onChange={(event) => setScenarioForm({ ...scenarioForm, compare_id: event.target.value })}>
                      <option value="">자동 선택</option>
                      {scenarioForm.compare_type === "price_table"
                        ? priceTables.map((table) => <option key={table.id} value={table.id}>{table.name} · {table.status}</option>)
                        : latestCandidateId ? <option value={latestCandidateId}>{latestCandidateName}</option> : null}
                    </Select>
                  </Field>
                </div>
              </div>
              <div className="mt-5 flex flex-wrap gap-3">
                <SecondaryButton onClick={runScenarioComparison}>시나리오 비교 실행</SecondaryButton>
                <SecondaryButton onClick={runComparison}>기존 가격표 비교 실행</SecondaryButton>
                <a href="#approval" className="rounded-2xl border border-slate-200 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50">
                  {canApprove(role) ? "승인 화면으로 이동" : "검증/승인 상태 확인"}
                </a>
              </div>
              <div className="mt-5">
                {scenarioComparisonResult ? (
                  <div className="space-y-5">
                    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                      {[
                        ["비교 행", scenarioComparisonResult.summary.total_compared_items],
                        ["일치 행", scenarioComparisonResult.summary.matching_item_count],
                        ["평균 차이", formatCurrency(scenarioComparisonResult.summary.average_price_difference)],
                        ["경고", scenarioComparisonResult.summary.warning_count],
                      ].map(([label, value]) => (
                        <div key={label} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                          <p className="text-sm text-slate-500">{label}</p>
                          <p className="mt-2 text-2xl font-semibold">{value}</p>
                        </div>
                      ))}
                    </div>
                    <div className="grid gap-4 lg:grid-cols-2">
                      {[["기준", scenarioComparisonResult.base], ["비교", scenarioComparisonResult.compare]].map(([label, scenario]) => (
                        <div key={label} className="rounded-2xl border border-slate-200 p-4">
                          <div className="flex items-center justify-between gap-3">
                            <p className="font-semibold">{label}: {scenario.name}</p>
                            <Badge tone={scenario.approval_readiness.ready_for_owner_review ? "success" : scenario.validation?.overall_status === "fail" ? "danger" : "info"}>
                              {scenario.status}
                            </Badge>
                          </div>
                          <p className="mt-2 text-sm text-slate-600">{scenario.scenario_type} #{scenario.scenario_id} · {scenario.strategy_name}</p>
                          <p className="mt-2 text-sm text-slate-600">
                            검증: {scenario.validation?.overall_status || "검증 결과 없음"} · 승인 검토: {scenario.approval_readiness.ready_for_owner_review ? "owner 검토 가능" : "추가 확인 필요"}
                          </p>
                        </div>
                      ))}
                    </div>
                    {scenarioComparisonResult.validation_comparison.notes?.length ? (
                      <StateNotice type="info" title="검증 결과가 없는 시나리오가 있습니다.">
                        승인 전에 검증을 먼저 실행해 주세요.
                      </StateNotice>
                    ) : null}
                    <DataTable
                      rows={scenarioComparisonResult.item_differences.slice(0, 8)}
                      emptyText="비교 가능한 항목이 없습니다."
                      columns={[
                        { key: "quantity", label: "수량" },
                        { key: "option_summary", label: "옵션" },
                        { key: "base_price", label: "기준 가격", render: (row) => formatCurrency(row.base_price) },
                        { key: "compare_price", label: "비교 가격", render: (row) => formatCurrency(row.compare_price) },
                        { key: "price_difference", label: "차이", render: (row) => formatCurrency(row.price_difference) },
                        { key: "margin_difference", label: "마진 차이", render: (row) => formatPercent(row.margin_difference) },
                        { key: "match_status", label: "상태", render: (row) => <Badge tone={row.warnings?.length ? "warning" : "success"}>{row.match_status}</Badge> },
                      ]}
                    />
                    {scenarioComparisonResult.warnings?.length ? (
                      <div className="flex flex-wrap gap-2">
                        {scenarioComparisonResult.warnings.map((warning) => <Badge key={warning} tone="warning">{warning}</Badge>)}
                      </div>
                    ) : null}
                  </div>
                ) : comparisonResult ? (
                  <pre className="max-h-64 overflow-auto rounded-2xl bg-slate-950 p-4 text-xs text-white">{JSON.stringify(comparisonResult.summary || comparisonResult, null, 2)}</pre>
                ) : (
                  <EmptyState title="아직 시나리오 비교 결과가 없습니다.">
                    후보 가격표를 생성한 뒤 활성 가격표와 비교해 보세요.
                  </EmptyState>
                )}
              </div>
            </Card>
          </section>

          <section id="reports">
            <Card testId="report-export-section">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <h2 className="text-2xl font-semibold">보고서 내보내기</h2>
                  <p className="mt-2 text-sm leading-6 text-slate-600">
                    가격 운영 결과를 검토용 HTML 보고서로 생성합니다. 모든 수치는 저장된 데이터에서 계산되며,
                    AI는 가격 숫자나 승인 여부를 결정하지 않습니다. HTML 보고서는 브라우저에서 인쇄하거나 PDF로 저장할 수 있습니다.
                  </p>
                </div>
                <FileText className="h-6 w-6 text-slate-400" />
              </div>
              <div className="mt-5 grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
                <div className="space-y-4">
                  <StateNotice type="info" title="보고서는 기존 데이터를 요약합니다.">
                    후보 가격표, 검증 결과, 시나리오 비교, 승인 증빙, 운영 스냅샷을 읽기 전용으로 내보냅니다.
                    보고서 생성은 가격표 승인, 활성화, 가격 변경을 수행하지 않습니다.
                  </StateNotice>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <SecondaryButton onClick={() => openCandidateReport("candidate")} disabled={!latestCandidateId}>
                      후보 가격표 보고서
                    </SecondaryButton>
                    <SecondaryButton onClick={() => openCandidateReport("validation")} disabled={!latestCandidateId}>
                      검증 보고서
                    </SecondaryButton>
                    <SecondaryButton onClick={openScenarioReport}>
                      시나리오 비교 보고서
                    </SecondaryButton>
                    <SecondaryButton onClick={() => openCandidateReport("approval")} disabled={!latestCandidateId}>
                      승인 증빙 보고서
                    </SecondaryButton>
                    <SecondaryButton onClick={() => openReport("/api/reports/operations-snapshot", "운영 스냅샷 보고서")}>
                      운영 스냅샷 보고서
                    </SecondaryButton>
                  </div>
                  <p className="text-xs leading-5 text-slate-500">
                    보고서를 생성할 데이터가 부족하면 먼저 후보 가격표, 검증 결과 또는 비교 결과를 생성해 주세요.
                    비밀 환경 변수, 토큰, DATABASE_URL, OpenAI API 키는 보고서에 포함하지 않습니다.
                  </p>
                </div>
                <div>
                  {reportHtml ? (
                    <div className="overflow-hidden rounded-2xl border border-slate-200">
                      <div className="flex items-center justify-between gap-3 border-b border-slate-200 bg-slate-50 px-4 py-3">
                        <p className="font-semibold">{reportTitle}</p>
                        <Badge tone="success">HTML</Badge>
                      </div>
                      <iframe
                        title={reportTitle || "QuoteOps AI report preview"}
                        srcDoc={reportHtml}
                        className="h-[420px] w-full bg-white"
                      />
                    </div>
                  ) : (
                    <EmptyState title="아직 생성된 보고서가 없습니다.">
                      왼쪽 버튼으로 HTML 보고서를 생성하면 여기에서 미리보기를 확인할 수 있습니다.
                    </EmptyState>
                  )}
                </div>
              </div>
            </Card>
          </section>

          <section id="csv">
            <Card testId="bulk-operations">
              <h2 className="text-2xl font-semibold">CSV 가져오기 / 내보내기</h2>
              <p className="mt-2 text-sm text-slate-600">CSV 업로드는 수동으로 정리한 데이터를 빠르게 입력하기 위한 기능입니다. 잘못된 가격이나 원가 데이터는 자동 반영되지 않습니다.</p>
              {!canMutate(role) ? <div className="mt-4"><PermissionNotice role={role} action="CSV 가져오기/내보내기" /></div> : null}
              <div className="mt-5 flex flex-wrap gap-3">
                <SecondaryButton disabled={!canMutate(role)} onClick={() => exportCsv("/api/export/competitor-prices")}>경쟁사 가격 CSV 내보내기</SecondaryButton>
                <SecondaryButton disabled={!canMutate(role)} onClick={() => exportCsv("/api/export/cost-profiles")}>원가 프로필 CSV 내보내기</SecondaryButton>
              </div>
              <div className="mt-5">{csvResult ? <StateNotice type="success" title="CSV 작업이 완료되었습니다."><pre className="mt-2 whitespace-pre-wrap text-xs">{csvResult.preview}</pre></StateNotice> : <EmptyState title="아직 CSV 작업 결과가 없습니다." />}</div>
            </Card>
          </section>

          <section id="jobs">
            <Card testId="workflow-job-monitor">
              <h2 className="text-2xl font-semibold">작업 모니터</h2>
              <p className="mt-2 text-sm text-slate-600">작업 기록은 승인이나 가격 활성화를 대신하지 않습니다.</p>
              <DataTable
                rows={jobs}
                emptyText="아직 워크플로 작업이 없습니다."
                columns={[
                  { key: "job_type", label: "유형" },
                  { key: "status", label: "상태" },
                  { key: "created_at", label: "생성일" },
                ]}
              />
            </Card>
          </section>

          <section id="audit-logs">
            <Card testId="audit-log-viewer">
              <h2 className="text-2xl font-semibold">감사 로그</h2>
              <p className="mt-2 text-sm text-slate-600">감사 로그는 가격, 원가, 승인, CSV 작업 등 중요한 운영 변경 이력을 기록합니다. AI가 로그를 생성하거나 조작하지 않습니다.</p>
              <DataTable
                rows={auditLogs.slice(0, 10)}
                emptyText="아직 감사 로그가 없습니다."
                columns={[
                  { key: "action", label: "작업" },
                  { key: "entity_type", label: "대상" },
                  { key: "actor_name", label: "관리자" },
                  { key: "created_at", label: "시각" },
                ]}
              />
            </Card>
          </section>

          <section id="role-access">
            <Card testId="role-access-panel">
              <div className="flex items-start gap-3">
                <ShieldCheck className="mt-1 h-6 w-6 text-slate-400" />
                <div>
                  <h2 className="text-2xl font-semibold">권한 안내</h2>
                  <p className="mt-2 text-sm text-slate-600">
                    viewer는 읽기 전용, manager는 가격 운영 가능, owner는 후보 승인과 활성화를 수행할 수 있습니다. 프론트엔드 표시는 편의 기능이며 백엔드 권한 검사가 최종 기준입니다.
                  </p>
                </div>
              </div>
            </Card>
          </section>

          <section id="system-status">
            <Card testId="system-status-panel">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <h2 className="text-2xl font-semibold">System Status</h2>
                  <p className="mt-2 text-sm text-slate-600">상태 패널은 안전한 상태값만 보여 주며 DATABASE_URL, 토큰, OpenAI 키 같은 비밀값을 노출하지 않습니다.</p>
                </div>
                <SecondaryButton onClick={loadPublicData}><RefreshCw className="h-4 w-4" />새로고침</SecondaryButton>
              </div>
              {systemStatus ? (
                <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  <div className="rounded-2xl border border-slate-200 p-4"><p className="text-sm text-slate-500">백엔드</p><p className="mt-2 font-semibold">{systemStatus.backend?.status}</p></div>
                  <div className="rounded-2xl border border-slate-200 p-4"><p className="text-sm text-slate-500">DB</p><p className="mt-2 font-semibold">{systemStatus.database?.type} / {systemStatus.database?.connectivity}</p></div>
                  <div className="rounded-2xl border border-slate-200 p-4"><p className="text-sm text-slate-500">AI 설명</p><p className="mt-2 font-semibold">{systemStatus.configuration?.openai_configured ? "OpenAI" : "fallback"}</p></div>
                  <div className="rounded-2xl border border-slate-200 p-4"><p className="text-sm text-slate-500">작업 시스템</p><p className="mt-2 font-semibold">{String(systemStatus.features?.job_system_enabled)}</p></div>
                </div>
              ) : (
                <StateNotice type="error" title="백엔드 상태를 확인할 수 없습니다.">
                  VITE_API_BASE_URL 설정과 백엔드 실행 상태를 확인해 주세요.
                </StateNotice>
              )}
            </Card>
          </section>

          <Card>
            <div className="flex items-start gap-3">
              <Database className="mt-1 h-5 w-5 text-slate-400" />
              <p className="text-sm leading-6 text-slate-600">
                PR-31은 오류, 빈 상태, 로딩, 권한 안내, OpenAI fallback 메시지를 다듬는 작업입니다.
                가격 계산식, 후보 생성, 검증, 승인 규칙, 데이터베이스 동작은 변경하지 않습니다.
              </p>
            </div>
          </Card>
        </div>
      </div>
    </main>
  )
}

createRoot(document.getElementById("root")).render(<App />)
