import React, { useEffect, useMemo, useState } from "react"
import {
  API_BASE_URL,
  approveApprovalRequest,
  comparePriceTableSnapshots,
  comparePriceTables,
  cancelWorkflowJob,
  createApprovalRequest,
  createCandidatePrices,
  createFullDemoScenario,
  createHtmlReport,
  createCustomerQuoteCandidates,
  createCustomerQuotePreview,
  createCustomerQuoteRequest,
  createPricingSimulation,
  createQuoteExplanation,
  createQuotePreview,
  createPriceTableSnapshot,
  createScenarioComparison,
  createWorkflowJob,
  formatApiError,
  createStrategyTemplate,
  createStrategyTemplateCandidates,
  createStrategyTemplateSimulation,
  disableStrategyTemplate,
  downloadCsv,
  getAuditLogs,
  getApprovalRequests,
  getCurrentUser,
  getDashboardInsights,
  getDashboardSummary,
  getCustomerQuoteRequests,
  getDemoGuide,
  getDemoStatus,
  getDemoUsers,
  getHealth,
  getHealthReady,
  getHtmlReport,
  getHtmlReportContent,
  getHtmlReports,
  getProducts,
  getPriceTables,
  getPriceTableSnapshots,
  getPriceTableSummary,
  getPricingSimulations,
  getScenarioComparison,
  getScenarioComparisons,
  getStrategyTemplates,
  getSystemStatus,
  getWorkflowJobs,
  importCsv,
  login,
  rejectApprovalRequest,
  resetDemoData,
  runWorkflowJob,
  seedDemoData,
  setAccessToken,
  updateStrategyTemplate,
  updateCustomerQuoteRequestStatus,
  validatePrice,
} from "./api/client"

const emptyResult = {
  quotePreview: null,
  candidates: null,
  validation: null,
  explanation: null,
}

function toNumber(value) {
  return value === "" || value === null || value === undefined ? undefined : Number(value)
}

function formatMoney(value) {
  if (value === null || value === undefined) return "-"
  return new Intl.NumberFormat("ko-KR", { maximumFractionDigits: 2 }).format(value)
}

function formatRate(value) {
  if (value === null || value === undefined) return "-"
  return `${Math.round(Number(value) * 1000) / 10}%`
}

function parseMarginRates(value) {
  if (!value.trim()) return undefined
  return value
    .split(",")
    .map((item) => Number(item.trim()))
    .filter((item) => !Number.isNaN(item))
}

function parseIntegerList(value) {
  if (!value.trim()) return []
  return value
    .split(",")
    .map((item) => Number.parseInt(item.trim(), 10))
    .filter((item) => !Number.isNaN(item))
}

function isValidEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(value || "").trim())
}

function sanitizeApiUrl(value) {
  try {
    const url = new URL(value)
    url.username = ""
    url.password = ""
    return url.toString().replace(/\/$/, "")
  } catch {
    return "the configured API URL"
  }
}

function validateCommonPricingInputs({ selectedProductId, quantity, marginRates, proposedUnitPrice }) {
  if (!selectedProductId) return "상품을 선택한 뒤 가격 작업을 실행하세요."
  if (Number(quantity) <= 0) return "수량은 0보다 커야 합니다."
  if (proposedUnitPrice !== undefined && Number(proposedUnitPrice) <= 0) {
    return "제안 단가는 0보다 커야 합니다."
  }
  const rates = parseMarginRates(marginRates || "")
  if (marginRates && (!rates?.length || rates.some((rate) => rate < 0 || rate >= 1))) {
    return "마진율은 0 이상 1 미만의 숫자로 입력하세요."
  }
  return ""
}

function validateJson(value) {
  try {
    JSON.parse(value)
    return ""
  } catch {
    return "작업 입력값은 올바른 JSON이어야 합니다."
  }
}

const NAV_SECTIONS = [
  {
    key: "overview",
    label: "홈",
    description: "견적부터 가격 검증, 승인, 리포트까지 한눈에 확인합니다.",
  },
  {
    key: "quote-operations",
    label: "견적",
    description: "고객 요청을 바탕으로 견적과 설명을 준비합니다.",
  },
  {
    key: "pricing-tools",
    label: "가격",
    description: "가격 후보, 검증, 전략 템플릿, 가격표 비교를 확인합니다.",
  },
  {
    key: "approvals",
    label: "승인",
    description: "승인 대기 건과 감사 로그를 검토합니다.",
  },
  {
    key: "customer-requests",
    label: "고객 요청",
    description: "고객 견적 요청을 접수하고 상태를 관리합니다.",
  },
  {
    key: "simulations",
    label: "시뮬레이션",
    description: "가격 시뮬레이션과 시나리오 비교를 확인합니다.",
  },
  {
    key: "reports",
    label: "리포트",
    description: "대시보드, 가격, 검증 결과를 리포트로 정리합니다.",
  },
  {
    key: "admin-system",
    label: "운영",
    description: "시스템 상태, CSV, 감사 로그, 운영 도구를 관리합니다.",
  },
  {
    key: "demo-tools",
    label: "데모",
    description: "샘플 데이터와 데모 흐름을 확인합니다.",
  },
]

const OVERVIEW_WORKFLOW_CARDS = [
  {
    title: "견적 생성",
    text: "고객 요청을 바탕으로 견적을 준비합니다.",
    action: "견적 시작",
    section: "quote-operations",
  },
  {
    title: "가격 검증",
    text: "기준과 조건에 맞는지 확인합니다.",
    action: "가격 확인",
    section: "pricing-tools",
  },
  {
    title: "승인 관리",
    text: "승인 대기 건을 검토하고 처리합니다.",
    action: "승인 보기",
    section: "approvals",
  },
  {
    title: "리포트 생성",
    text: "결과를 정리해 공유합니다.",
    action: "리포트 보기",
    section: "reports",
  },
]

const CORE_WORKFLOW_STEPS = [
  "고객 요청",
  "견적 생성",
  "가격 계산",
  "가격 평가",
  "승인 요청",
  "리포트",
]

const WORKFLOW_ERROR_COPY = {
  quote: "견적 정보를 불러오지 못했습니다.",
  pricing: "가격 계산에 실패했습니다.",
  approval: "승인 목록을 불러오지 못했습니다.",
  retry: "다시 시도",
  reload: "다시 불러오기",
}

const OPTIONAL_COST_LABELS = {
  material_cost: "재료비",
  labor_cost: "인건비",
  overhead_cost: "간접비",
  target_margin_rate: "목표 마진율",
}

const CUSTOMER_QUOTE_FIELD_LABELS = {
  customer_name: "고객명",
  customer_email: "이메일",
  customer_company: "회사명",
  quantity: "수량",
  request_note: "요청 메모",
}

const DISPLAY_LABELS = {
  product_id: "상품 ID",
  product_name: "상품명",
  customer_name: "고객명",
  customer_email: "이메일",
  customer_company: "회사명",
  request_note: "요청 메모",
  quantity: "수량",
  unit_price: "단가",
  proposed_unit_price: "제안 단가",
  candidate_price: "가격안",
  candidate_prices: "추천 가격안",
  material_cost: "재료비",
  labor_cost: "인건비",
  overhead_cost: "간접비",
  target_margin_rate: "목표 마진율",
  margin_rate: "마진율",
  approval_request: "승인 요청",
  approval_status: "승인 상태",
  created_at: "생성일",
  updated_at: "수정일",
  status: "상태",
  reason: "사유",
  notes: "메모",
  result: "결과",
  score: "점수",
  risk: "위험도",
  warning: "경고",
  error: "오류",
}

const STATUS_LABELS = {
  pending: "대기",
  reviewing: "검토 중",
  approved: "승인됨",
  rejected: "반려됨",
  completed: "완료",
  failed: "실패",
  success: "성공",
  warning: "주의",
  error: "오류",
  ready: "준비 완료",
  ok: "정상",
  connected: "연결됨",
  configured: "설정됨",
  available: "확인됨",
  active: "활성",
  inactive: "비활성",
  draft: "임시 저장",
  passed: "통과",
  low: "낮음",
  medium: "보통",
  high: "높음",
  new: "신규",
  quoted: "견적 완료",
  closed: "종료",
  conservative: "보수적",
  balanced: "균형",
  aggressive: "공격적",
}

const JOB_TYPE_LABELS = {
  pricing_simulation: "가격 시뮬레이션",
  price_validation_batch: "가격 평가 일괄 작업",
  quote_request_review: "견적 요청 검토",
}

const REPORT_TYPE_LABELS = {
  dashboard_summary: "운영 요약 리포트",
  approval_request: "승인 요청 리포트",
  pricing_simulation: "가격 시뮬레이션 리포트",
  price_validation: "가격 평가 리포트",
  quote_preview: "견적 미리보기 리포트",
  scenario_comparison: "시나리오 비교 리포트",
}

const CSV_ENTITY_LABELS = {
  products: "상품",
  "cost-profiles": "원가 프로필",
  "competitor-prices": "경쟁사 가격",
}

function displayLabel(value) {
  return DISPLAY_LABELS[value] || value
}

function displayStatus(value) {
  if (value === null || value === undefined || value === "") return "-"
  return STATUS_LABELS[String(value)] || value
}

const ROLE_LABELS = {
  admin: "관리자",
  manager: "매니저",
  viewer: "조회자",
}

const ROLE_MODE_LABELS = {
  admin: "관리자 모드",
  manager: "매니저 모드",
  viewer: "조회자 모드",
}

const INTERNAL_CODE_LABELS = {
  low_margin: "낮은 마진율",
  target_margin: "기준 마진율",
  premium_margin: "프리미엄 마진율",
  standard_margin_custom: "기본 마진 전략",
  price_above_unit_cost: "단가가 원가보다 높음",
  margin_meets_minimum: "최소 마진 기준 충족",
  competitor_reference_below_average: "경쟁사 기준보다 낮음",
  auth_login_success: "로그인 완료",
  auth_login_failed: "로그인 실패",
  scenario_comparison_list_viewed: "시나리오 비교 조회",
  scenario_comparison_created: "시나리오 비교 생성",
  scenario_comparison_viewed: "시나리오 비교 상세 조회",
  csv_products_imported: "상품 CSV 가져오기",
  csv_cost_profiles_imported: "원가 CSV 가져오기",
  csv_competitor_prices_imported: "경쟁사 가격 CSV 가져오기",
  approval_request_created: "승인 요청 생성",
  approval_request_approved: "승인 처리",
  approval_request_rejected: "반려 처리",
  workflow_job_created: "작업 생성",
  workflow_job_completed: "작업 완료",
  workflow_job_cancelled: "작업 취소",
  product: "상품",
  products: "상품",
  cost_profile: "원가 프로필",
  competitor_price: "경쟁사 가격",
  approval_request: "승인 요청",
  scenario_comparison: "시나리오 비교",
  workflow_job: "작업",
  dashboard_summary: "운영 요약",
}

function displayRole(role) {
  return ROLE_LABELS[role] || role || "사용자"
}

function displayRoleMode(role) {
  return ROLE_MODE_LABELS[role] || `${displayRole(role)} 모드`
}

function displayCode(value) {
  if (value === null || value === undefined || value === "") return "-"
  const key = String(value)
  return INTERNAL_CODE_LABELS[key] || STATUS_LABELS[key] || DISPLAY_LABELS[key] || JOB_TYPE_LABELS[key] || REPORT_TYPE_LABELS[key] || key
}

function displayAction(value) {
  return displayCode(value)
}

function displayNote(note) {
  if (!note) return note
  const text = String(note)
  const lowered = text.toLowerCase()
  if (lowered.includes("comparison is deterministic") || lowered.includes("deterministic")) {
    return "기준에 따라 계산한 결과입니다."
  }
  if (lowered.includes("no ai-generated") || lowered.includes("ai-generated")) {
    return "자동 생성 가격이 아닌 계산 기준 결과입니다."
  }
  if (lowered.includes("human review") || lowered.includes("needs human review")) {
    return "검토가 필요한 항목입니다."
  }
  if (lowered.includes("approve") || lowered.includes("activate")) {
    return "승인 후 가격이 확정됩니다."
  }
  return displayCode(text)
}

function displayNotes(notes) {
  return notes?.map(displayNote)
}

function App() {
  const [health, setHealth] = useState(null)
  const [readiness, setReadiness] = useState(null)
  const [systemStatus, setSystemStatus] = useState(null)
  const [activeSection, setActiveSection] = useState("overview")
  const [products, setProducts] = useState([])
  const [selectedProductId, setSelectedProductId] = useState("")
  const [quantity, setQuantity] = useState(10)
  const [proposedUnitPrice, setProposedUnitPrice] = useState(4000)
  const [optionalCosts, setOptionalCosts] = useState({
    material_cost: "",
    labor_cost: "",
    overhead_cost: "",
    target_margin_rate: "",
  })
  const [marginRates, setMarginRates] = useState("0.25,0.35,0.45")
  const [includeCompetitors, setIncludeCompetitors] = useState(true)
  const [approvalRequests, setApprovalRequests] = useState([])
  const [reviewerName, setReviewerName] = useState("데모 매니저")
  const [reviewNote, setReviewNote] = useState("")
  const [results, setResults] = useState(emptyResult)
  const [loading, setLoading] = useState("")
  const [error, setError] = useState("")
  const [errorInfo, setErrorInfo] = useState(null)
  const [formError, setFormError] = useState("")
  const [lastAction, setLastAction] = useState(null)
  const [demoUsers, setDemoUsers] = useState([])
  const [demoStatus, setDemoStatus] = useState(null)
  const [demoGuide, setDemoGuide] = useState(null)
  const [demoSeedResult, setDemoSeedResult] = useState(null)
  const [demoResetResult, setDemoResetResult] = useState(null)
  const [demoScenario, setDemoScenario] = useState(null)
  const [auditLogs, setAuditLogs] = useState([])
  const [dashboardSummary, setDashboardSummary] = useState(null)
  const [dashboardInsights, setDashboardInsights] = useState(null)
  const [htmlReports, setHtmlReports] = useState([])
  const [activeHtmlReport, setActiveHtmlReport] = useState(null)
  const [htmlReportForm, setHtmlReportForm] = useState({
    report_type: "dashboard_summary",
    title: "현재 운영 리포트",
    source_id: "",
  })
  const [csvFiles, setCsvFiles] = useState({
    products: null,
    "cost-profiles": null,
    "competitor-prices": null,
  })
  const [csvImportResult, setCsvImportResult] = useState(null)
  const [simulationInputs, setSimulationInputs] = useState({
    name: "대량 주문 시뮬레이션",
    quantities: "1,10,50",
    margin_rates: "0.25,0.35,0.45",
    notes: "소량과 대량 주문 조건을 비교합니다.",
  })
  const [pricingSimulations, setPricingSimulations] = useState([])
  const [activeSimulation, setActiveSimulation] = useState(null)
  const [strategyTemplates, setStrategyTemplates] = useState([])
  const [selectedStrategyTemplateId, setSelectedStrategyTemplateId] = useState("")
  const [strategyTemplateForm, setStrategyTemplateForm] = useState({
    name: "기본 마진 전략",
    strategy_code: "standard_margin_custom",
    description: "일반 견적 운영에 맞춘 균형형 마진 전략입니다.",
    margin_rates: "0.25,0.35,0.45",
    default_quantities: "1,10,50",
    include_competitor_context_default: true,
    risk_preference: "balanced",
    active: true,
    notes: "사람이 정한 기준으로 사용하는 전략 템플릿입니다.",
  })
  const [strategyTemplateCandidates, setStrategyTemplateCandidates] = useState(null)
  const [strategyTemplateSimulation, setStrategyTemplateSimulation] = useState(null)
  const [scenarioComparisons, setScenarioComparisons] = useState([])
  const [activeScenarioComparison, setActiveScenarioComparison] = useState(null)
  const [scenarioComparisonForm, setScenarioComparisonForm] = useState({
    name: "대량 주문 가격 비교",
    description: "보수형, 표준형, 프리미엄 가격안을 비교합니다.",
    scenarios: "보수형,50,0.25\n표준형,50,0.35\n프리미엄,50,0.45",
    include_competitor_context: true,
  })
  const [customerQuoteForm, setCustomerQuoteForm] = useState({
    customer_name: "데모 고객",
    customer_email: "customer@example.com",
    customer_company: "데모 회사",
    quantity: 25,
    request_note: "25개 기준 견적을 요청합니다.",
  })
  const [customerQuoteRequests, setCustomerQuoteRequests] = useState([])
  const [quoteRequestStatus, setQuoteRequestStatus] = useState("reviewing")
  const [priceTables, setPriceTables] = useState([])
  const [selectedPriceTableId, setSelectedPriceTableId] = useState("")
  const [targetPriceTableId, setTargetPriceTableId] = useState("")
  const [priceTableSummary, setPriceTableSummary] = useState(null)
  const [priceTableSnapshots, setPriceTableSnapshots] = useState([])
  const [snapshotForm, setSnapshotForm] = useState({
    label: "가격 검토 전",
    note: "가격 비교 전 기준 스냅샷입니다.",
  })
  const [baseSnapshotId, setBaseSnapshotId] = useState("")
  const [targetSnapshotId, setTargetSnapshotId] = useState("")
  const [priceTableComparison, setPriceTableComparison] = useState(null)
  const [workflowJobForm, setWorkflowJobForm] = useState({
    job_type: "pricing_simulation",
    title: "대량 가격 시뮬레이션",
    description: "1개, 10개, 50개 기준 가격을 비교합니다.",
    input: '{\n  "product_id": 1,\n  "quantities": [1, 10, 50],\n  "margin_rates": [0.25, 0.35, 0.45],\n  "include_competitor_context": true\n}',
  })
  const [workflowJobs, setWorkflowJobs] = useState([])
  const [activeWorkflowJob, setActiveWorkflowJob] = useState(null)
  const [loginForm, setLoginForm] = useState({
    username: "manager",
    password: "manager-demo-password",
  })
  const [currentUser, setCurrentUser] = useState(null)
  const [entryPanel, setEntryPanel] = useState("demo")

  const selectedProduct = useMemo(
    () => products.find((product) => product.id === Number(selectedProductId)),
    [products, selectedProductId],
  )

  useEffect(() => {
    const savedToken = localStorage.getItem("quoteops_token")
    if (savedToken) {
      setAccessToken(savedToken)
      getCurrentUser()
        .then((user) => {
          setCurrentUser(user)
          refreshAuditLogs(user)
          getDashboardSummary().then(setDashboardSummary).catch(() => {})
          getDashboardInsights().then(setDashboardInsights).catch(() => {})
          getHtmlReports().then(setHtmlReports).catch(() => {})
          getPricingSimulations().then(setPricingSimulations).catch(() => {})
          getStrategyTemplates().then((templates) => {
            setStrategyTemplates(templates)
            if (templates.length > 0) setSelectedStrategyTemplateId(String(templates[0].id))
          }).catch(() => {})
          getScenarioComparisons().then(setScenarioComparisons).catch(() => {})
          getCustomerQuoteRequests().then(setCustomerQuoteRequests).catch(() => {})
          getWorkflowJobs().then(setWorkflowJobs).catch(() => {})
          getDemoStatus().then(setDemoStatus).catch(() => {})
          getDemoGuide().then(setDemoGuide).catch(() => {})
        })
        .catch(() => handleLogout())
    }
    loadInitialData()
  }, [])

  async function runAction(label, action) {
    setLoading(label)
    setError("")
    setErrorInfo(null)
    setFormError("")
    setLastAction(() => () => runAction(label, action))
    try {
      await action()
    } catch (err) {
      const safeError = formatApiError(err)
      setError(safeError.message)
      setErrorInfo(safeError)
    } finally {
      setLoading("")
    }
  }

  function stopForFormError(message) {
    setFormError(message)
    setError("")
    setErrorInfo(null)
    return true
  }

  function validatePricingForm({ requirePrice = false } = {}) {
    return validateCommonPricingInputs({
      selectedProductId,
      quantity,
      marginRates,
      proposedUnitPrice: requirePrice ? proposedUnitPrice : undefined,
    })
  }

  async function loadInitialData() {
    await runAction("초기 데이터를 불러오는 중", async () => {
      const [healthData, readinessData, statusData, productData, approvalData, demoUserData, priceTableData] = await Promise.all([
        getHealth(),
        getHealthReady(),
        getSystemStatus(),
        getProducts(),
        getApprovalRequests(),
        getDemoUsers(),
        getPriceTables(),
      ])
      setHealth(healthData)
      setReadiness(readinessData)
      setSystemStatus(statusData)
      setProducts(productData)
      setApprovalRequests(approvalData)
      setDemoUsers(demoUserData)
      setPriceTables(priceTableData)
      if (priceTableData.length > 0) {
        setSelectedPriceTableId(String(priceTableData[0].id))
        setTargetPriceTableId(String(priceTableData[Math.min(1, priceTableData.length - 1)].id))
      }
      if (productData.length > 0) {
        setSelectedProductId(String(productData[0].id))
      }
    })
  }

  async function completeLogin(credentials) {
    const data = await login(credentials)
    localStorage.setItem("quoteops_token", data.access_token)
    setAccessToken(data.access_token)
    setCurrentUser(data.user)
    setActiveSection("overview")
    await refreshAuditLogs(data.user)
    setDashboardSummary(await getDashboardSummary())
    setDashboardInsights(await getDashboardInsights())
    setHtmlReports(await getHtmlReports())
    setPricingSimulations(await getPricingSimulations())
    const templates = await getStrategyTemplates()
    setStrategyTemplates(templates)
    if (templates.length > 0) setSelectedStrategyTemplateId(String(templates[0].id))
    setScenarioComparisons(await getScenarioComparisons())
    setCustomerQuoteRequests(await getCustomerQuoteRequests())
    setWorkflowJobs(await getWorkflowJobs())
    setDemoStatus(await getDemoStatus())
    setDemoGuide(await getDemoGuide())
  }

  async function handleLogin(event) {
    event.preventDefault()
    await runAction("로그인 중", async () => completeLogin(loginForm))
  }

  function handleLogout() {
    localStorage.removeItem("quoteops_token")
    setAccessToken("")
    setCurrentUser(null)
    setAuditLogs([])
    setDashboardSummary(null)
    setDashboardInsights(null)
    setHtmlReports([])
    setActiveHtmlReport(null)
    setPricingSimulations([])
    setActiveSimulation(null)
    setStrategyTemplates([])
    setSelectedStrategyTemplateId("")
    setStrategyTemplateCandidates(null)
    setStrategyTemplateSimulation(null)
    setScenarioComparisons([])
    setActiveScenarioComparison(null)
    setCustomerQuoteRequests([])
    setWorkflowJobs([])
    setActiveWorkflowJob(null)
    setDemoStatus(null)
    setDemoGuide(null)
    setDemoSeedResult(null)
    setDemoResetResult(null)
    setDemoScenario(null)
  }

  async function refreshDemoStatusAndGuide() {
    if (!currentUser) return
    setDemoStatus(await getDemoStatus())
    setDemoGuide(await getDemoGuide())
    await refreshAuditLogs()
  }

  async function handleSeedDemoData() {
    await runAction("데모 데이터 준비 중", async () => {
      const result = await seedDemoData()
      setDemoSeedResult(result)
      setProducts(await getProducts())
      setPriceTables(await getPriceTables())
      setDemoStatus(await getDemoStatus())
      setScenarioComparisons(await getScenarioComparisons())
      setHtmlReports(await getHtmlReports())
      await refreshAuditLogs()
    })
  }

  async function handleCreateFullDemoScenario() {
    await runAction("데모 흐름 생성 중", async () => {
      const result = await createFullDemoScenario()
      setDemoScenario(result)
      setDemoStatus(await getDemoStatus())
      setDashboardSummary(await getDashboardSummary())
      setDashboardInsights(await getDashboardInsights())
      setScenarioComparisons(await getScenarioComparisons())
      setHtmlReports(await getHtmlReports())
      await refreshAuditLogs()
    })
  }

  async function handleResetDemoData() {
    await runAction("데모 데이터 초기화 중", async () => {
      const result = await resetDemoData()
      setDemoResetResult(result)
      setDemoStatus(await getDemoStatus())
      setProducts(await getProducts())
      setPriceTables(await getPriceTables())
      await refreshAuditLogs()
    })
  }

  async function refreshAuditLogs(user = currentUser) {
    if (!user || !["admin", "manager"].includes(user.role)) {
      setAuditLogs([])
      return
    }
    setAuditLogs(await getAuditLogs({ limit: 10 }))
  }

  async function refreshDashboardSummary() {
    if (!currentUser) return
    setDashboardSummary(await getDashboardSummary())
    setDashboardInsights(await getDashboardInsights())
    await refreshAuditLogs()
  }

  async function refreshDashboardInsights() {
    if (!currentUser) return
    setDashboardInsights(await getDashboardInsights())
    await refreshAuditLogs()
  }

  async function refreshHtmlReports() {
    if (!currentUser) return
    setHtmlReports(await getHtmlReports())
  }

  async function handleCreateHtmlReport() {
    if (!htmlReportForm.title.trim()) {
      if (stopForFormError("리포트 제목을 입력하세요.")) return
    }
    await runAction("리포트 생성 중", async () => {
      const payload = {
        report_type: htmlReportForm.report_type,
        title: htmlReportForm.title,
      }
      if (htmlReportForm.source_id !== "") {
        payload.source_id = Number(htmlReportForm.source_id)
      }
      const report = await createHtmlReport(payload)
      setActiveHtmlReport(report)
      setHtmlReports(await getHtmlReports())
      await refreshAuditLogs()
    })
  }

  async function handleViewHtmlReport(id) {
    await runAction("리포트를 불러오는 중", async () => {
      const report = await getHtmlReport(id)
      setActiveHtmlReport(report)
      await refreshAuditLogs()
    })
  }

  async function handleOpenHtmlReportContent(id) {
    await runAction("리포트를 여는 중", async () => {
      const content = await getHtmlReportContent(id)
      const url = window.URL.createObjectURL(new Blob([content], { type: "text/html" }))
      window.open(url, "_blank", "noopener,noreferrer")
      window.setTimeout(() => window.URL.revokeObjectURL(url), 1000)
      await refreshAuditLogs()
    })
  }

  async function handleCsvImport(entity) {
    if (!csvFiles[entity]) {
      stopForFormError("가져올 CSV 파일을 선택하세요.")
      return
    }
    await runAction(`${CSV_ENTITY_LABELS[entity] || entity} CSV 가져오는 중`, async () => {
      const result = await importCsv(entity, csvFiles[entity])
      setCsvImportResult(result)
      await refreshAuditLogs()
    })
  }

  async function handleCsvExport(entity, filename) {
    await runAction(`${CSV_ENTITY_LABELS[entity] || entity} CSV 내보내는 중`, async () => {
      await downloadCsv(entity, filename)
      await refreshAuditLogs()
    })
  }

  async function refreshPricingSimulations() {
    if (!currentUser) return
    setPricingSimulations(await getPricingSimulations())
  }

  async function refreshStrategyTemplates() {
    if (!currentUser) return
    const templates = await getStrategyTemplates()
    setStrategyTemplates(templates)
    if (!selectedStrategyTemplateId && templates.length > 0) {
      setSelectedStrategyTemplateId(String(templates[0].id))
    }
  }

  async function handlePricingSimulation() {
    const pricingError = validatePricingForm()
    if (pricingError && stopForFormError(pricingError)) return
    if (!simulationInputs.name.trim()) {
      if (stopForFormError("시뮬레이션 이름을 입력하세요.")) return
    }
    if (parseIntegerList(simulationInputs.quantities).some((item) => item <= 0)) {
      if (stopForFormError("시뮬레이션 수량은 0보다 커야 합니다.")) return
    }
    await runAction("가격 시뮬레이션 실행 중", async () => {
      const data = await createPricingSimulation({
        name: simulationInputs.name,
        product_id: Number(selectedProductId),
        quantities: parseIntegerList(simulationInputs.quantities),
        margin_rates: parseMarginRates(simulationInputs.margin_rates) || [],
        include_competitor_context: includeCompetitors,
        notes: simulationInputs.notes,
      })
      setActiveSimulation(data)
      setPricingSimulations(await getPricingSimulations())
      await refreshAuditLogs()
    })
  }

  function strategyTemplatePayload() {
    return {
      name: strategyTemplateForm.name,
      strategy_code: strategyTemplateForm.strategy_code,
      description: strategyTemplateForm.description,
      margin_rates: parseMarginRates(strategyTemplateForm.margin_rates) || [],
      default_quantities: parseIntegerList(strategyTemplateForm.default_quantities),
      include_competitor_context_default: strategyTemplateForm.include_competitor_context_default,
      risk_preference: strategyTemplateForm.risk_preference,
      active: strategyTemplateForm.active,
      notes: strategyTemplateForm.notes,
    }
  }

  async function handleCreateStrategyTemplate() {
    if (!strategyTemplateForm.name.trim()) {
      if (stopForFormError("전략 템플릿 이름을 입력하세요.")) return
    }
    await runAction("전략 템플릿 생성 중", async () => {
      const template = await createStrategyTemplate(strategyTemplatePayload())
      await refreshStrategyTemplates()
      setSelectedStrategyTemplateId(String(template.id))
      await refreshAuditLogs()
    })
  }

  async function handleUpdateStrategyTemplate() {
    if (!selectedStrategyTemplateId) {
      if (stopForFormError("수정할 전략 템플릿을 선택하세요.")) return
    }
    await runAction("전략 템플릿 수정 중", async () => {
      const template = await updateStrategyTemplate(selectedStrategyTemplateId, strategyTemplatePayload())
      await refreshStrategyTemplates()
      setSelectedStrategyTemplateId(String(template.id))
      await refreshAuditLogs()
    })
  }

  async function handleDisableStrategyTemplate() {
    if (!selectedStrategyTemplateId) {
      if (stopForFormError("비활성화할 전략 템플릿을 선택하세요.")) return
    }
    await runAction("전략 템플릿 비활성화 중", async () => {
      await disableStrategyTemplate(selectedStrategyTemplateId)
      await refreshStrategyTemplates()
      await refreshAuditLogs()
    })
  }

  async function handleStrategyTemplateCandidates() {
    const pricingError = validatePricingForm()
    if (pricingError && stopForFormError(pricingError)) return
    if (!selectedStrategyTemplateId) {
      if (stopForFormError("적용할 전략 템플릿을 선택하세요.")) return
    }
    await runAction("전략 기반 가격안 생성 중", async () => {
      const data = await createStrategyTemplateCandidates(selectedStrategyTemplateId, {
        product_id: Number(selectedProductId),
        quantity: Number(quantity),
        include_competitor_context: includeCompetitors,
      })
      setStrategyTemplateCandidates(data)
      setResults((current) => ({ ...current, candidates: data }))
      await refreshAuditLogs()
    })
  }

  async function handleStrategyTemplateSimulation() {
    if (!selectedProductId) {
      if (stopForFormError("상품을 선택한 뒤 템플릿 시뮬레이션을 실행하세요.")) return
    }
    if (!selectedStrategyTemplateId) {
      if (stopForFormError("시뮬레이션에 사용할 전략 템플릿을 선택하세요.")) return
    }
    await runAction("전략 템플릿 시뮬레이션 실행 중", async () => {
      const data = await createStrategyTemplateSimulation(selectedStrategyTemplateId, {
        name: `${strategyTemplateForm.name} simulation`,
        product_id: Number(selectedProductId),
        quantities: parseIntegerList(strategyTemplateForm.default_quantities),
        include_competitor_context: includeCompetitors,
      })
      setStrategyTemplateSimulation(data)
      setActiveSimulation(data)
      setPricingSimulations(await getPricingSimulations())
      await refreshAuditLogs()
    })
  }

  function parseScenarioRows(value) {
    return value
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line, index) => {
        const [label, quantity, marginRate] = line.split(",").map((item) => item.trim())
        return {
          label: label || `시나리오 ${index + 1}`,
          quantity: Number(quantity),
          margin_rate: Number(marginRate),
        }
      })
  }

  async function refreshScenarioComparisons() {
    if (!currentUser) return
    setScenarioComparisons(await getScenarioComparisons())
  }

  async function handleCreateScenarioComparison() {
    const pricingError = validatePricingForm()
    if (pricingError && stopForFormError(pricingError)) return
    if (!scenarioComparisonForm.name.trim()) {
      if (stopForFormError("시나리오 비교 이름을 입력하세요.")) return
    }
    const scenarioRows = parseScenarioRows(scenarioComparisonForm.scenarios)
    if (!scenarioRows.length) {
      if (stopForFormError("비교할 시나리오를 하나 이상 입력하세요.")) return
    }
    if (scenarioRows.some((row) => row.quantity <= 0 || row.margin_rate < 0 || row.margin_rate >= 1 || Number.isNaN(row.quantity) || Number.isNaN(row.margin_rate))) {
      if (stopForFormError("각 시나리오는 0보다 큰 수량과 0 이상 1 미만의 마진율이 필요합니다.")) return
    }
    await runAction("시나리오 비교 생성 중", async () => {
      const comparison = await createScenarioComparison({
        name: scenarioComparisonForm.name,
        description: scenarioComparisonForm.description,
        product_id: Number(selectedProductId),
        scenarios: scenarioRows,
        include_competitor_context: scenarioComparisonForm.include_competitor_context,
      })
      setActiveScenarioComparison(comparison)
      setScenarioComparisons(await getScenarioComparisons())
      await refreshAuditLogs()
    })
  }

  async function handleViewScenarioComparison(id) {
    await runAction("시나리오 비교 불러오는 중", async () => {
      const comparison = await getScenarioComparison(id)
      setActiveScenarioComparison(comparison)
      await refreshAuditLogs()
    })
  }

  async function refreshCustomerQuoteRequests() {
    if (!currentUser) return
    setCustomerQuoteRequests(await getCustomerQuoteRequests())
  }

  async function handleCreateCustomerQuoteRequest() {
    if (!selectedProductId) {
      if (stopForFormError("상품을 선택한 뒤 견적 요청을 등록하세요.")) return
    }
    if (!customerQuoteForm.customer_name.trim()) {
      if (stopForFormError("고객명을 입력하세요.")) return
    }
    if (!isValidEmail(customerQuoteForm.customer_email)) {
      if (stopForFormError("이메일 형식으로 입력하세요.")) return
    }
    if (Number(customerQuoteForm.quantity) <= 0) {
      if (stopForFormError("견적 수량은 0보다 커야 합니다.")) return
    }
    await runAction("고객 견적 요청 등록 중", async () => {
      await createCustomerQuoteRequest({
        ...customerQuoteForm,
        product_id: Number(selectedProductId),
        quantity: Number(customerQuoteForm.quantity),
      })
      await refreshCustomerQuoteRequests()
      await refreshAuditLogs()
    })
  }

  async function handleCustomerQuoteStatus(id) {
    await runAction("고객 견적 상태 변경 중", async () => {
      await updateCustomerQuoteRequestStatus(id, {
        status: quoteRequestStatus,
        assigned_to_username: currentUser?.username || "manager",
        internal_note: "프론트엔드에서 검토했습니다.",
      })
      await refreshCustomerQuoteRequests()
      await refreshAuditLogs()
    })
  }

  async function handleCustomerQuotePreview(id) {
    await runAction("요청 기반 견적 미리보기 생성 중", async () => {
      const data = await createCustomerQuotePreview(id)
      setResults((current) => ({ ...current, quotePreview: data }))
      await refreshAuditLogs()
    })
  }

  async function handleCustomerQuoteCandidates(id) {
    await runAction("요청 기반 가격안 생성 중", async () => {
      const data = await createCustomerQuoteCandidates(id, {
        margin_rates: parseMarginRates(marginRates),
        include_competitor_context: includeCompetitors,
      })
      setResults((current) => ({ ...current, candidates: data }))
      await refreshAuditLogs()
    })
  }

  async function handlePriceTableSummary() {
    if (!selectedPriceTableId) {
      if (stopForFormError("요약을 볼 가격표를 선택하세요.")) return
    }
    await runAction("가격표 요약 불러오는 중", async () => {
      const summary = await getPriceTableSummary(selectedPriceTableId)
      setPriceTableSummary(summary)
      setPriceTableSnapshots(await getPriceTableSnapshots(selectedPriceTableId))
      await refreshAuditLogs()
    })
  }

  async function handleCreateSnapshot() {
    if (!selectedPriceTableId) {
      if (stopForFormError("스냅샷을 만들 가격표를 선택하세요.")) return
    }
    if (!snapshotForm.label.trim()) {
      if (stopForFormError("스냅샷 이름을 입력하세요.")) return
    }
    await runAction("가격표 스냅샷 생성 중", async () => {
      await createPriceTableSnapshot(selectedPriceTableId, snapshotForm)
      const snapshots = await getPriceTableSnapshots(selectedPriceTableId)
      setPriceTableSnapshots(snapshots)
      if (snapshots.length > 0) {
        setBaseSnapshotId(String(snapshots[0].id))
        setTargetSnapshotId(String(snapshots[0].id))
      }
      await refreshAuditLogs()
    })
  }

  async function handleComparePriceTables() {
    if (!selectedPriceTableId || !targetPriceTableId) {
      if (stopForFormError("비교할 기준 가격표와 대상 가격표를 선택하세요.")) return
    }
    await runAction("가격표 비교 중", async () => {
      const comparison = await comparePriceTables({
        base_price_table_id: Number(selectedPriceTableId),
        target_price_table_id: Number(targetPriceTableId),
      })
      setPriceTableComparison(comparison)
      await refreshAuditLogs()
    })
  }

  async function handleCompareSnapshots() {
    if (!baseSnapshotId || !targetSnapshotId) {
      if (stopForFormError("비교할 기준 스냅샷과 대상 스냅샷을 선택하세요.")) return
    }
    await runAction("가격표 스냅샷 비교 중", async () => {
      const comparison = await comparePriceTableSnapshots({
        base_snapshot_id: Number(baseSnapshotId),
        target_snapshot_id: Number(targetSnapshotId),
      })
      setPriceTableComparison(comparison)
      await refreshAuditLogs()
    })
  }

  async function refreshWorkflowJobs() {
    if (!currentUser) return
    setWorkflowJobs(await getWorkflowJobs())
  }

  async function handleCreateWorkflowJob() {
    if (!workflowJobForm.title.trim()) {
      if (stopForFormError("작업 제목을 입력하세요.")) return
    }
    const jsonError = validateJson(workflowJobForm.input)
    if (jsonError && stopForFormError(jsonError)) return
    await runAction("작업 생성 중", async () => {
      const job = await createWorkflowJob({
        job_type: workflowJobForm.job_type,
        title: workflowJobForm.title,
        description: workflowJobForm.description,
        input: JSON.parse(workflowJobForm.input),
      })
      setActiveWorkflowJob(job)
      await refreshWorkflowJobs()
      await refreshAuditLogs()
    })
  }

  async function handleRunWorkflowJob(id) {
    await runAction("작업 실행 중", async () => {
      const job = await runWorkflowJob(id)
      setActiveWorkflowJob(job)
      await refreshWorkflowJobs()
      await refreshAuditLogs()
    })
  }

  async function handleCancelWorkflowJob(id) {
    await runAction("작업 취소 중", async () => {
      const job = await cancelWorkflowJob(id)
      setActiveWorkflowJob(job)
      await refreshWorkflowJobs()
      await refreshAuditLogs()
    })
  }

  async function useDemoUser(username) {
    const credentials = {
      username,
      password: `${username}-demo-password`,
    }
    setLoginForm(credentials)
    await runAction("로그인 중", async () => completeLogin(credentials))
  }

  function basePayload() {
    return {
      product_id: Number(selectedProductId),
      quantity: Number(quantity),
    }
  }

  async function handleQuotePreview() {
    const pricingError = validatePricingForm()
    if (pricingError && stopForFormError(pricingError)) return
    await runAction("견적 미리보기 생성 중", async () => {
      const data = await createQuotePreview({
        ...basePayload(),
        material_cost: toNumber(optionalCosts.material_cost),
        labor_cost: toNumber(optionalCosts.labor_cost),
        overhead_cost: toNumber(optionalCosts.overhead_cost),
        target_margin_rate: toNumber(optionalCosts.target_margin_rate),
      })
      setResults((current) => ({ ...current, quotePreview: data }))
      setProposedUnitPrice(data.suggested_unit_price)
      await refreshAuditLogs()
    })
  }

  async function handleCandidates() {
    const pricingError = validatePricingForm()
    if (pricingError && stopForFormError(pricingError)) return
    await runAction("가격안 생성 중", async () => {
      const data = await createCandidatePrices({
        ...basePayload(),
        margin_rates: parseMarginRates(marginRates),
        include_competitor_context: includeCompetitors,
      })
      setResults((current) => ({ ...current, candidates: data }))
      if (data.candidates?.length) {
        setProposedUnitPrice(data.candidates[0].unit_price)
      }
      await refreshAuditLogs()
    })
  }

  async function handleValidation() {
    const pricingError = validatePricingForm({ requirePrice: true })
    if (pricingError && stopForFormError(pricingError)) return
    await runAction("제안 가격 평가 중", async () => {
      const data = await validatePrice({
        ...basePayload(),
        candidate_unit_price: Number(proposedUnitPrice),
        include_competitor_context: includeCompetitors,
      })
      setResults((current) => ({ ...current, validation: data }))
      await refreshAuditLogs()
    })
  }

  async function handleCreateApproval() {
    const pricingError = validatePricingForm({ requirePrice: true })
    if (pricingError && stopForFormError(pricingError)) return
    await runAction("승인 요청 생성 중", async () => {
      await createApprovalRequest({
        ...basePayload(),
        proposed_unit_price: Number(proposedUnitPrice),
        submitted_note: "Frontend MVP approval request.",
      })
      setApprovalRequests(await getApprovalRequests())
      await refreshAuditLogs()
    })
  }

  async function handleReviewApproval(id, decision) {
    await runAction("승인 요청 검토 중", async () => {
      const payload = {
        reviewer_name: reviewerName,
        review_note:
          reviewNote ||
          (decision === "approve" ? "Approved in frontend MVP." : "Rejected in frontend MVP."),
      }
      if (decision === "approve") {
        await approveApprovalRequest(id, payload)
      } else {
        await rejectApprovalRequest(id, payload)
      }
      setApprovalRequests(await getApprovalRequests())
      await refreshAuditLogs()
    })
  }

  async function handleExplanation() {
    const pricingError = validatePricingForm({ requirePrice: true })
    if (pricingError && stopForFormError(pricingError)) return
    await runAction("설명 생성 중", async () => {
      const validation = results.validation
      const quote = results.quotePreview
      const data = await createQuoteExplanation({
        product_id: Number(selectedProductId),
        quantity: Number(quantity),
        unit_cost: validation?.unit_cost ?? quote?.unit_cost,
        proposed_unit_price: Number(proposedUnitPrice),
        estimated_margin_rate: validation?.estimated_margin_rate ?? quote?.estimated_margin_rate,
        validation_status: validation?.validation_status || "passed",
        risk_level: validation?.risk_level || "low",
        explanation_audience: "manager",
        explanation_style: "concise",
      })
      setResults((current) => ({ ...current, explanation: data }))
      await refreshAuditLogs()
    })
  }

  const activeSectionMeta = NAV_SECTIONS.find((section) => section.key === activeSection) || NAV_SECTIONS[0]
  const showSection = (...sectionKeys) => sectionKeys.includes(activeSection)
  const backendUnavailable = !loading && (!health || readiness?.status === "not_ready")
  const sectionNeedsSignIn = !currentUser && !["overview"].includes(activeSection)
  const safeApiBaseUrl = sanitizeApiUrl(API_BASE_URL)
  const latestActions = dashboardSummary?.audit_metrics?.latest_actions || []
  const pendingApprovalCount = dashboardSummary?.approval_metrics?.pending_approval_requests ?? approvalRequests.length
  const openRequestCount = dashboardSummary?.quote_metrics?.new_quote_requests ?? customerQuoteRequests.length
  const workflowPageMeta = {
    "quote-operations": {
      eyebrow: "견적",
      title: "견적 흐름",
      helper: "고객 요청부터 견적 미리보기까지 한 흐름으로 확인하세요.",
      primary: "새 견적",
      primarySection: "quote-operations",
      secondary: "요청 가져오기",
      secondarySection: "customer-requests",
      inputTitle: "견적 입력",
    },
    "customer-requests": {
      eyebrow: "고객 요청",
      title: "고객 요청",
      helper: "들어온 요청을 확인하고 견적으로 연결하세요.",
      primary: "견적 생성",
      primarySection: "quote-operations",
      secondary: "다시 불러오기",
      secondaryAction: refreshCustomerQuoteRequests,
      inputTitle: "요청 기준",
    },
    "pricing-tools": {
      eyebrow: "가격",
      title: "가격 도구",
      helper: "가격안을 계산하고 기준에 맞는지 평가하세요.",
      primary: "가격 계산",
      primaryAction: handleCandidates,
      secondary: "가격 평가",
      secondaryAction: handleValidation,
      inputTitle: "가격 기준",
    },
    approvals: {
      eyebrow: "승인",
      title: "승인 관리",
      helper: "승인 대기 건을 검토하고 처리하세요.",
      primary: "승인 요청",
      primaryAction: handleCreateApproval,
      secondary: "다시 불러오기",
      secondaryAction: loadInitialData,
      inputTitle: "승인 기준",
    },
    simulations: {
      eyebrow: "시뮬레이션",
      title: "시뮬레이션",
      helper: "조건을 바꿔 가격 결과를 비교하세요.",
      primary: "시뮬레이션 실행",
      primaryAction: handlePricingSimulation,
      secondary: "시나리오 비교",
      secondaryAction: refreshScenarioComparisons,
      inputTitle: "시뮬레이션 기준",
    },
    "admin-system": {
      eyebrow: "운영",
      title: "운영",
      helper: "데이터 작업, 시스템 상태, 작업 상태를 확인하세요.",
      primary: "상태 새로고침",
      primaryVariant: "secondary",
      primaryAction: loadInitialData,
      secondary: "작업 새로고침",
      secondaryAction: refreshWorkflowJobs,
      inputTitle: "운영 기준",
    },
  }[activeSection] || {
    eyebrow: activeSectionMeta.label,
    title: activeSectionMeta.label,
    helper: activeSectionMeta.description,
    primary: "다시 불러오기",
    primaryVariant: "secondary",
    primaryAction: loadInitialData,
    inputTitle: "작업 기준",
  }

  if (!currentUser) {
    return (
      <main className="public-shell">
        <div className="public-page">
          <header className="public-header">
            <div className="public-brand">
              <span className="public-brand-mark">Q</span>
              <span>QuoteOps AI</span>
            </div>
            <div className="public-header-actions">
              <button className="button button-ghost" type="button" onClick={() => setEntryPanel("login")}>로그인</button>
              <button className="button button-secondary" type="button" onClick={() => setEntryPanel("demo")}>데모 체험</button>
            </div>
          </header>

          {loading && <LoadingState message={`${loading}...`} />}
          {errorInfo && (
            <ErrorState
              title={errorInfo.title}
              message={errorInfo.message}
              status={errorInfo.status}
              onRetry={lastAction}
            />
          )}
          {!errorInfo && error && (
            <ErrorState
              title="요청을 완료하지 못했습니다"
              message={error}
              onRetry={lastAction}
            />
          )}
          {formError && <FormErrorMessage message={formError} />}

          <section className="public-hero">
            <div className="public-hero-copy">
              <p className="public-eyebrow">QuoteOps AI</p>
              <h1>견적부터 승인까지 한 흐름으로</h1>
              <p className="public-hero-text">견적 생성, 가격 평가, 승인, 리포트까지 한 번에 관리하세요.</p>
              <div className="public-cta-row">
                <button className="button button-primary public-cta" type="button" onClick={() => setEntryPanel("login")}>서비스 시작하기</button>
                <button className="button button-secondary public-cta" type="button" onClick={() => setEntryPanel("demo")}>데모 체험하기</button>
              </div>
              <p className="public-feature-line">견적 · 가격 평가 · 승인 · 시뮬레이션 · 리포트 · 감사 로그</p>
            </div>

            <aside className="public-entry-card" aria-label="QuoteOps AI entry">
              <div className="public-entry-tabs">
                <button className={`button compact ${entryPanel === "login" ? "" : "secondary"}`} type="button" onClick={() => setEntryPanel("login")}>로그인</button>
                <button className={`button compact ${entryPanel === "demo" ? "" : "secondary"}`} type="button" onClick={() => setEntryPanel("demo")}>데모 체험</button>
              </div>
              {entryPanel === "login" ? (
                <form className="public-login-form" onSubmit={handleLogin}>
                  <label className="field">
                    <span>아이디</span>
                    <input value={loginForm.username} onChange={(event) => setLoginForm((current) => ({ ...current, username: event.target.value }))} />
                  </label>
                  <label className="field">
                    <span>비밀번호</span>
                    <input type="password" value={loginForm.password} onChange={(event) => setLoginForm((current) => ({ ...current, password: event.target.value }))} />
                  </label>
                  <button className="button button-primary" type="submit">로그인</button>
                </form>
              ) : (
                <div className="public-demo-panel">
                  <p className="public-entry-helper">포트폴리오 데모용 계정</p>
                  <div className="public-demo-grid">
                    {demoUsers.map((user) => (
                      <button className="button button-secondary" key={user.username} type="button" onClick={() => useDemoUser(user.username)}>
                        {user.username === "admin" ? "관리자" : user.username === "manager" ? "매니저" : user.username === "viewer" ? "조회자" : user.username}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </aside>
          </section>

          <section className="public-flow-section" aria-label="QuoteOps AI workflow">
            {OVERVIEW_WORKFLOW_CARDS.map((card, index) => (
              <article className="public-flow-card" key={card.title}>
                <span>{index + 1}</span>
                <h2>{card.title}</h2>
                <p>{card.text}</p>
              </article>
            ))}
          </section>

          <section className="public-safety-card">
            <span className="badge badge-warning">자동 반영 없음</span>
            <div>
              <h2>최종 가격은 승인 후 확정</h2>
              <p>계산과 평가는 돕고, 결정은 사람이 합니다.</p>
            </div>
          </section>

          <p className="public-mvp-note">포트폴리오용 SaaS MVP입니다.</p>
        </div>
      </main>
    )
  }

  return (
    <main className="app-shell min-h-screen bg-slate-100 text-slate-950">
      <div className="app-main page-container mx-auto max-w-7xl px-5 py-6">
        <header className="app-header mb-6 flex flex-col gap-3 border-b border-slate-200 pb-5 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-sm font-semibold text-slate-500">QuoteOps AI</p>
            <h1 className="text-3xl font-semibold tracking-tight">견적 가격 운영</h1>
            <p className="mt-2 max-w-3xl text-sm text-slate-600">
              견적, 가격 검증, 승인, 리포트를 한 흐름으로 관리합니다.
            </p>
          </div>
          <div className="app-user-actions">
            {currentUser && (
              <div className="user-chip" aria-label="현재 사용자">
                <strong>{displayRoleMode(currentUser.role)}</strong>
                <span>{currentUser.display_name || displayRole(currentUser.role)}</span>
              </div>
            )}
            <button className="button compact secondary" onClick={loadInitialData} disabled={!!loading}>
              새로고침
            </button>
            {currentUser && <button className="button compact secondary" onClick={handleLogout}>로그아웃</button>}
          </div>
        </header>

        {loading && <LoadingState message={`${loading}...`} />}
        {errorInfo && (
          <ErrorState
            title={errorInfo.title}
            message={errorInfo.message}
            status={errorInfo.status}
            onRetry={lastAction}
          />
        )}
        {!errorInfo && error && (
          <ErrorState
            title="요청을 처리하지 못했습니다."
            message={error}
            onRetry={lastAction}
          />
        )}
        {formError && <FormErrorMessage message={formError} />}

        <nav className="app-nav mb-5 rounded-md border border-slate-200 bg-white p-3 shadow-sm" aria-label="Workspace sections">
          <div className="app-nav-list flex flex-wrap gap-2">
            {NAV_SECTIONS.map((section) => (
              <button
                className={`nav-pill ${activeSection === section.key ? "active" : ""}`}
                key={section.key}
                onClick={() => setActiveSection(section.key)}
                type="button"
              >
                {section.label}
              </button>
            ))}
          </div>
        </nav>

        {activeSection === "overview" ? (
          <section className="overview-home section">
            <div className="overview-hero card">
              <div className="overview-hero-copy">
                <span className="overview-eyebrow">QuoteOps AI</span>
                <h2>견적부터 승인까지 한 흐름으로</h2>
                <p>계산, 원가, 승인, 리포트까지 한 흐름으로</p>
                <div className="overview-actions">
                  <button className="button button-primary" type="button" onClick={() => setActiveSection("quote-operations")}>
                    견적 시작
                  </button>
                  <button className="button button-secondary" type="button" onClick={() => setActiveSection("demo-tools")}>
                    데모 보기
                  </button>
                </div>
              </div>
              <div className="overview-hero-status" aria-label="업무 요약">
                <div className="overview-status-item">
                  <span>승인 대기</span>
                  <strong className="badge badge-warning">{pendingApprovalCount}건</strong>
                </div>
                <div className="overview-status-item">
                  <span>신규 요청</span>
                  <strong className="badge badge-success">{openRequestCount}건</strong>
                </div>
                <div className="overview-status-item">
                  <span>다음 단계</span>
                  <strong className="badge">가격 평가</strong>
                </div>
              </div>
            </div>

            {backendUnavailable && (
              <ErrorState
                title="데이터를 불러오지 못했습니다"
                message={`백엔드 상태 또는 API URL을 확인하세요: ${safeApiBaseUrl}.`}
                onRetry={loadInitialData}
              />
            )}

            <div className="overview-grid">
              <section className="overview-workflow card">
                <div className="section-header">
                  <p className="text-sm font-semibold text-slate-500">주요 흐름</p>
                  <h3>견적부터 승인까지</h3>
                </div>
                <div className="workflow-grid">
                  {OVERVIEW_WORKFLOW_CARDS.map((card) => (
                    <article className="workflow-card" key={card.title}>
                      <h4>{card.title}</h4>
                      <p>{card.text}</p>
                      <button className="button compact secondary" type="button" onClick={() => setActiveSection(card.section)}>
                        {card.action}
                      </button>
                    </article>
                  ))}
                </div>
              </section>

              <aside className="overview-side">
                <section className="card overview-demo-card">
                  <div>
                    <p className="text-sm font-semibold text-slate-500">포트폴리오 데모용 계정</p>
                    <h3>데모 시작</h3>
                    <p>샘플 데이터로 흐름을 확인하세요.</p>
                  </div>
                  <div className="overview-actions">
                    <button className="button secondary" type="button" onClick={() => setActiveSection("demo-tools")}>
                      데모 보기
                    </button>
                    {currentUser && (
                      <button className="button compact" type="button" onClick={handleSeedDemoData}>
                        샘플 불러오기
                      </button>
                    )}
                  </div>
                </section>

                <section className="card overview-safety-card">
                  <span className="badge badge-warning">자동 반영 없음</span>
                  <h3>승인 전 자동 반영 없음</h3>
                  <p>가격 계산과 원가 검증을 지원하지만, 승인 없이 가격을 확정하거나 전송하지 않습니다.</p>
                </section>

                <section className="card overview-activity-card">
                  <div className="section-header">
                    <p className="text-sm font-semibold text-slate-500">다음 작업</p>
                    <h3>진행 상황</h3>
                  </div>
                  {latestActions.length > 0 ? (
                    <div className="overview-mini-list">
                      <p><strong>{pendingApprovalCount}</strong>건 승인 대기</p>
                      <p><strong>{openRequestCount}</strong>건 신규 요청</p>
                      <p>최근 작업: {displayAction(latestActions[0].action)}</p>
                    </div>
                  ) : (
                    <EmptyState
                      title="아직 진행 중인 작업이 없습니다."
                      message="첫 견적을 만들어 보세요."
                    />
                  )}
                </section>
              </aside>
            </div>
          </section>
        ) : (
          <section className="section card mb-5 rounded-md border border-slate-200 bg-white p-5 shadow-sm">
            <div className="section-header">
              <p className="text-sm font-semibold text-slate-500">{activeSectionMeta.label}</p>
              <h2 className="mt-1 text-2xl font-semibold tracking-tight">{activeSectionMeta.label}</h2>
            </div>
            <p className="mt-2 max-w-4xl text-sm text-slate-600">{activeSectionMeta.description}</p>
            {backendUnavailable && (
              <div className="mt-4">
                <ErrorState
                  title="백엔드에 연결할 수 없습니다."
                  message={`로컬 백엔드 실행 상태 또는 배포 API URL을 확인하세요: ${safeApiBaseUrl}.`}
                  onRetry={loadInitialData}
                />
              </div>
            )}
            {sectionNeedsSignIn && (
              <div className="mt-4">
                <EmptyState
                  title="로그인이 필요합니다."
                  message="이 섹션에 접근할 수 있는 역할로 로그인하세요."
                  action="로컬 데모 계정 또는 설정된 사용자 계정을 사용하세요."
                />
              </div>
            )}
          </section>
        )}

        <section className="section card-grid mb-5 grid gap-4 lg:grid-cols-[1fr_1.4fr]">

          {showSection("admin-system") && (
            <section className="status-grid grid gap-4 lg:grid-cols-4" aria-label="시스템 상태">
              <h2 className="sr-only">시스템 상태</h2>
                <StatusCard label="서비스 정상" value={health?.status === "ok" ? "정상" : health?.status || "-"} />
                <StatusCard label="DB 연결 정상" value={systemStatus?.database?.connection_ok || readiness?.status === "ready" ? "정상" : "확인"} />
                <StatusCard label="OpenAPI 확인" value={systemStatus?.features?.openapi_available ? "정상" : "확인"} />
                <StatusCard label="배포 연결" value={systemStatus?.cors?.configured ? "연결됨" : "로컬"} />
            </section>
          )}

          {showSection("overview") && currentUser && dashboardSummary && (
            <Panel title="운영 요약">
              <div className="flex flex-wrap gap-2">
                <button className="button compact" onClick={refreshDashboardSummary}>새로고침</button>
                <Badge>생성: {new Date(dashboardSummary.generated_at).toLocaleString()}</Badge>
              </div>
              <div className="grid gap-3 md:grid-cols-4">
                <StatusCard label="상품" value={dashboardSummary.summary.total_products} />
                <StatusCard label="진행 중 견적" value={dashboardSummary.summary.total_quote_requests} />
                <StatusCard label="승인 대기" value={dashboardSummary.approval_metrics.pending_approval_requests} />
                <StatusCard label="위험 검증" value={dashboardSummary.summary.high_risk_count} />
              </div>
              <div className="grid gap-4 xl:grid-cols-2">
                <DashboardMetricTable
                  title="견적 요청"
                  rows={[
                    ["신규", dashboardSummary.quote_metrics.new_quote_requests],
                    ["검토 중", dashboardSummary.quote_metrics.reviewing_quote_requests],
                    ["견적 완료", dashboardSummary.quote_metrics.quoted_quote_requests],
                    ["종료", dashboardSummary.quote_metrics.closed_quote_requests],
                    ["취소", dashboardSummary.quote_metrics.cancelled_quote_requests],
                  ]}
                />
                <DashboardMetricTable
                  title="승인 지표"
                  rows={[
                    ["검토 중", dashboardSummary.approval_metrics.pending_approval_requests],
                    ["승인됨", dashboardSummary.approval_metrics.approved_requests],
                    ["반려됨", dashboardSummary.approval_metrics.rejected_requests],
                    ["승인율", formatRate(dashboardSummary.approval_metrics.approval_rate)],
                    ["평균 마진", dashboardSummary.approval_metrics.average_estimated_margin_rate ?? "-"],
                  ]}
                />
                <DashboardMetricTable
                  title="검증과 위험"
                  rows={[
                    ["통과", dashboardSummary.validation_metrics.passed_validations],
                    ["주의", dashboardSummary.validation_metrics.warning_validations],
                    ["실패", dashboardSummary.validation_metrics.failed_validations],
                    ["낮은 위험", dashboardSummary.validation_metrics.low_risk_count],
                    ["높은 위험", dashboardSummary.validation_metrics.high_risk_count],
                  ]}
                />
                <DashboardMetricTable
                  title="작업 상태"
                  rows={[
                    ["대기", dashboardSummary.workflow_metrics.pending_jobs],
                    ["진행 중", dashboardSummary.workflow_metrics.running_jobs],
                    ["완료", dashboardSummary.workflow_metrics.completed_jobs],
                    ["실패", dashboardSummary.workflow_metrics.failed_jobs],
                    ["성공률", formatRate(dashboardSummary.workflow_metrics.job_success_rate)],
                  ]}
                />
              </div>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>최근 작업</th>
                      <th>작업자</th>
                      <th>생성일</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dashboardSummary.audit_metrics.latest_actions.length === 0 && (
                      <tr><td colSpan="3"><EmptyState title="표시할 요약 정보가 없습니다." message="데모 데이터를 불러오면 흐름을 확인할 수 있습니다." /></td></tr>
                    )}
                    {dashboardSummary.audit_metrics.latest_actions.map((action) => (
                      <tr key={`${action.action}-${action.created_at}`}>
                        <td>{displayAction(action.action)}</td>
                        <td>{action.actor_username}</td>
                        <td>{new Date(action.created_at).toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <Notes notes={displayNotes(dashboardSummary.dashboard_notes)} />
            </Panel>
          )}

          {showSection("overview") && currentUser && dashboardInsights && (
            <Panel title="분석 인사이트">
              <div className="flex flex-wrap gap-2">
                <button className="button compact" onClick={refreshDashboardInsights}>새로고침</button>
                <Badge>인사이트: {dashboardInsights.insight_count}</Badge>
                <Badge>생성: {new Date(dashboardInsights.generated_at).toLocaleString()}</Badge>
              </div>
              <div className="grid gap-3 xl:grid-cols-2">
                {dashboardInsights.insights.map((insight) => (
                  <div className="rounded-md border border-slate-200 bg-slate-50 p-4" key={`${insight.category}-${insight.title}`}>
                    <div className="mb-2 flex flex-wrap gap-2">
                      <Badge>{displayStatus(insight.severity)}</Badge>
                      <Badge>{displayCode(insight.category)}</Badge>
                    </div>
                    <p className="font-semibold">{insight.title}</p>
                    <p className="mt-1 text-sm text-slate-600">{insight.message}</p>
                    <p className="mt-3 text-sm font-semibold text-slate-700">권장 작업</p>
                    <p className="text-sm text-slate-600">{insight.recommended_action}</p>
                    <p className="mt-3 text-xs text-slate-500">{displayNote(insight.decision_boundary)}</p>
                  </div>
                ))}
              </div>
              <Notes notes={displayNotes(dashboardInsights.insight_notes)} />
            </Panel>
          )}

          {showSection("demo-tools") && currentUser && (
            <section className="support-page">
              <SupportPageHeader
                eyebrow="데모"
                title="데모 시작"
                helper="샘플 데이터로 전체 흐름을 빠르게 확인하세요."
                primary={["admin", "manager"].includes(currentUser.role) ? <button className="button compact" onClick={handleCreateFullDemoScenario}>데모 시작</button> : <button className="button compact secondary" onClick={refreshDemoStatusAndGuide}>다시 불러오기</button>}
                secondary={currentUser.role === "admin" ? <button className="button compact secondary" onClick={handleSeedDemoData}>샘플 불러오기</button> : null}
              />
              <Panel title="데모 흐름">
                <ol className="support-flow-list">
                  {["샘플 데이터 준비", "견적 생성", "가격 평가", "승인 처리", "리포트 확인"].map((step, index) => (
                    <li key={step}><span>{index + 1}</span>{step}</li>
                  ))}
                </ol>
              </Panel>
              <Panel title="데모 도구">
              <div className="flex flex-wrap gap-2">
                <button className="button compact secondary" onClick={refreshDemoStatusAndGuide}>다시 불러오기</button>
                {currentUser.role === "admin" && (
                  <button className="button compact" onClick={handleSeedDemoData}>샘플 불러오기</button>
                )}
                {["admin", "manager"].includes(currentUser.role) && (
                  <button className="button compact" onClick={handleCreateFullDemoScenario}>데모 시작</button>
                )}
                {currentUser.role === "admin" && (
                  <button className="button compact secondary border-red-200 text-red-700" onClick={handleResetDemoData}>데모 초기화</button>
                )}
              </div>

              {demoStatus && (
                <div className="grid gap-3 md:grid-cols-4">
                  <StatusCard label="데모 상태" value={demoStatus.demo_ready ? "준비됨" : "샘플 필요"} />
                  <StatusCard label="상품" value={demoStatus.counts.products} />
                  <StatusCard label="경쟁사" value={demoStatus.counts.competitors} />
                  <StatusCard label="시나리오" value={demoStatus.counts.scenario_comparisons} />
                </div>
              )}

              {demoScenario && (
                <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
                  <div className="mb-2 flex flex-wrap gap-2">
                    <Badge>{demoScenario.scenario_name}</Badge>
                    <Badge>{demoScenario.demo_product_sku}</Badge>
                    <Badge>{demoScenario.ready ? "샘플 데이터 준비" : "준비 필요"}</Badge>
                  </div>
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>단계</th>
                          <th>제목</th>
                        </tr>
                      </thead>
                      <tbody>
                        {demoScenario.steps.map((step) => (
                          <tr key={step.step}>
                            <td>{step.step}</td>
                            <td>{step.title}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <Notes title="결정 기준" notes={demoScenario.decision_boundaries} />
                  <Notes title="시나리오 메모" notes={demoScenario.demo_notes} />
                </div>
              )}

              {demoGuide && (
                <div className="grid gap-4 xl:grid-cols-2">
                  <div className="rounded-md border border-slate-200 bg-white p-3">
                    <p className="mb-2 font-semibold">데모 계정</p>
                    <div className="space-y-2 text-sm">
                      {demoGuide.demo_login_users.map((user) => (
                        <div className="flex flex-wrap gap-2" key={user.username}>
                          <Badge>{displayRole(user.role)}</Badge>
                          <span className="text-slate-600">{user.role === "viewer" ? "데모 조회자" : "데모 계정"}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="rounded-md border border-slate-200 bg-white p-3">
                    <Notes title="안전 기준" notes={demoGuide.business_safety_boundaries} />
                    <Notes title="말하지 않을 것" notes={demoGuide.what_not_to_claim} />
                  </div>
                </div>
              )}

              {(demoSeedResult || demoResetResult) && (
                <details className="advanced-details">
                  <summary>기술 정보</summary>
                  <div className="grid gap-3 md:grid-cols-2">
                    {demoSeedResult && (
                      <pre className="overflow-x-auto rounded-md bg-slate-950 p-4 text-sm text-white">{JSON.stringify(demoSeedResult.created_or_verified, null, 2)}</pre>
                    )}
                    {demoResetResult && (
                      <pre className="overflow-x-auto rounded-md bg-slate-950 p-4 text-sm text-white">{JSON.stringify(demoResetResult.deleted_or_disabled, null, 2)}</pre>
                    )}
                  </div>
                </details>
              )}
            </Panel>
            </section>
          )}

          {showSection("reports") && currentUser && (
            <section className="support-page">
              <SupportPageHeader
                eyebrow="리포트"
                title="리포트"
                helper="견적과 가격 검증 결과를 정리해 공유하세요."
                primary={["admin", "manager"].includes(currentUser.role) ? <button className="button compact" onClick={handleCreateHtmlReport}>리포트 생성</button> : null}
                secondary={<button className="button compact secondary" onClick={refreshHtmlReports}>최근 리포트</button>}
              />
            <Panel title="리포트 생성">
              <div className="grid gap-3 md:grid-cols-3">
                <label className="field">
                  <span>리포트 유형</span>
                  <select value={htmlReportForm.report_type} onChange={(event) => setHtmlReportForm((current) => ({ ...current, report_type: event.target.value }))}>
                    {["dashboard_summary", "approval_request", "pricing_simulation", "scenario_comparison", "quote_preview", "price_validation"].map((type) => (
                      <option key={type} value={type}>{REPORT_TYPE_LABELS[type] || type}</option>
                    ))}
                  </select>
                </label>
                <label className="field">
                  <span>제목</span>
                  <input value={htmlReportForm.title} onChange={(event) => setHtmlReportForm((current) => ({ ...current, title: event.target.value }))} />
                </label>
                <label className="field">
                  <span>대상 ID</span>
                  <input value={htmlReportForm.source_id} onChange={(event) => setHtmlReportForm((current) => ({ ...current, source_id: event.target.value }))} />
                </label>
              </div>
              <div className="flex flex-wrap gap-2">
                {["admin", "manager"].includes(currentUser.role) && (
                  <button className="button compact" onClick={handleCreateHtmlReport}>리포트 생성</button>
                )}
                <button className="button compact secondary" onClick={refreshHtmlReports}>다시 불러오기</button>
                {activeHtmlReport && (
                  <button className="button compact secondary" onClick={() => handleOpenHtmlReportContent(activeHtmlReport.id)}>리포트 보기</button>
                )}
              </div>
              {activeHtmlReport && (
                <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
                  <div className="mb-2 flex flex-wrap gap-2">
                    <Badge>{REPORT_TYPE_LABELS[activeHtmlReport.report_type] || activeHtmlReport.report_type}</Badge>
                    <Badge>출처: {activeHtmlReport.source_id || "없음"}</Badge>
                    <Badge>생성자: {activeHtmlReport.created_by_username}</Badge>
                  </div>
                  <p className="font-semibold">{activeHtmlReport.title}</p>
                  <p className="text-sm text-slate-600">{activeHtmlReport.summary_text}</p>
                  <Notes notes={displayNotes(activeHtmlReport.report_notes)} />
                </div>
              )}
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>유형</th>
                      <th>제목</th>
                      <th>출처</th>
                      <th>처리</th>
                    </tr>
                  </thead>
                  <tbody>
                    {htmlReports.length === 0 && (
                      <tr><td colSpan="5"><EmptyState title="생성된 리포트가 없습니다." message="첫 리포트를 만들어 보세요." /></td></tr>
                    )}
                    {htmlReports.slice(0, 8).map((report) => (
                      <tr key={report.id}>
                        <td>{report.id}</td>
                        <td>{REPORT_TYPE_LABELS[report.report_type] || report.report_type}</td>
                        <td>{report.title}</td>
                        <td>{report.source_id || "-"}</td>
                        <td>
                          <div className="flex flex-wrap gap-2">
                            <button className="button compact secondary" onClick={() => handleViewHtmlReport(report.id)}>보기</button>
                            <button className="button compact secondary" onClick={() => handleOpenHtmlReportContent(report.id)}>열기</button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Panel>
            </section>
          )}
        </section>

        {!showSection("overview", "demo-tools", "reports") && (
        <section className="workflow-page section">
          <WorkflowPageHeader meta={workflowPageMeta} setActiveSection={setActiveSection} />
          <WorkflowStepStrip steps={CORE_WORKFLOW_STEPS} />
          {showSection("quote-operations", "pricing-tools", "approvals", "customer-requests") && <SafetyBoundaryCard />}
          <div className="workflow-layout grid gap-5 lg:grid-cols-[360px_1fr]">
          <Panel title={workflowPageMeta.inputTitle}>
            <label className="field">
              <span>상품</span>
              <select value={selectedProductId} onChange={(event) => setSelectedProductId(event.target.value)}>
                {products.map((product) => (
                  <option key={product.id} value={product.id}>{product.name}</option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>수량</span>
              <input type="number" min="1" value={quantity} onChange={(event) => setQuantity(event.target.value)} />
            </label>
            <label className="field">
              <span>제안 단가</span>
              <input type="number" min="1" value={proposedUnitPrice} onChange={(event) => setProposedUnitPrice(event.target.value)} />
            </label>
            <div className="grid gap-3 sm:grid-cols-2">
              {Object.keys(optionalCosts).map((key) => (
                <label className="field" key={key}>
                  <span>{OPTIONAL_COST_LABELS[key]}</span>
                  <input value={optionalCosts[key]} onChange={(event) => setOptionalCosts((current) => ({ ...current, [key]: event.target.value }))} />
                </label>
              ))}
            </div>
            <label className="field">
              <span>후보 마진율</span>
              <input value={marginRates} onChange={(event) => setMarginRates(event.target.value)} />
            </label>
            <label className="checkbox">
              <input type="checkbox" checked={includeCompetitors} onChange={(event) => setIncludeCompetitors(event.target.checked)} />
              경쟁사 참고 포함
            </label>
            <p className="text-sm text-slate-500">선택: {selectedProduct?.name || "상품 없음"}</p>
          </Panel>

          <div className="grid gap-5">
            {showSection("quote-operations") && (
            <Panel title="견적 미리보기">
              <div className="workflow-panel-intro">
                <Badge>새 견적</Badge>
                <p>상품과 수량을 기준으로 견적 미리보기를 만듭니다.</p>
              </div>
              <ActionButton onClick={handleQuotePreview}>새 견적</ActionButton>
              <MetricGrid data={results.quotePreview} fields={["unit_cost", "total_cost", "suggested_unit_price", "suggested_total_price", "estimated_gross_profit", "estimated_margin_rate"]} />
              <Notes notes={results.quotePreview?.calculation_notes} />
            </Panel>
            )}

            {showSection("pricing-tools") && (
            <Panel title="가격안">
              <div className="workflow-panel-intro">
                <Badge>가격 계산</Badge>
                <p>원가와 마진 기준으로 가격 후보를 계산합니다.</p>
              </div>
              <ActionButton onClick={handleCandidates}>가격 계산</ActionButton>
              <div className="grid gap-3 md:grid-cols-3">
                {results.candidates?.candidates?.map((candidate) => (
                  <div className="rounded-md border border-slate-200 bg-slate-50 p-4" key={candidate.strategy}>
                    <h3 className="font-semibold">{displayCode(candidate.strategy)}</h3>
                    <p>Margin: {candidate.margin_rate}</p>
                    <p>Unit: {formatMoney(candidate.unit_price)}</p>
                    <p>Total: {formatMoney(candidate.total_price)}</p>
                    <Notes notes={candidate.notes} />
                  </div>
                ))}
              </div>
              <CompetitorContext context={results.candidates?.competitor_context} />
            </Panel>
            )}

            {showSection("pricing-tools") && (
            <Panel title="가격 평가">
              <div className="workflow-panel-intro">
                <Badge>가격 평가</Badge>
                <p>제안 단가가 기준과 조건에 맞는지 확인합니다.</p>
              </div>
              <ActionButton onClick={handleValidation}>가격 평가</ActionButton>
              {results.validation && (
                <div className="space-y-3">
                  <div className="flex flex-wrap gap-2">
                    <Badge>상태: {displayStatus(results.validation.validation_status)}</Badge>
                    <Badge>위험도: {displayStatus(results.validation.risk_level)}</Badge>
                    <Badge>margin: {results.validation.estimated_margin_rate}</Badge>
                  </div>
                  <ul className="space-y-2">
                    {results.validation.checks.map((check) => (
                      <li className="rounded-md border border-slate-200 bg-slate-50 p-3" key={check.code}>
                        <strong>{displayCode(check.code)}</strong> {check.passed ? "통과" : "검토 필요"} - {displayNote(check.message)}
                      </li>
                    ))}
                  </ul>
                  <CompetitorContext context={results.validation.competitor_context} />
                  <Notes notes={displayNotes(results.validation.calculation_notes)} />
                </div>
              )}
            </Panel>
            )}

            {showSection("simulations") && currentUser && (
              <Panel title="시뮬레이션">
                <div className="grid gap-3 md:grid-cols-2">
                  <label className="field">
                    <span>시뮬레이션 이름</span>
                    <input value={simulationInputs.name} onChange={(event) => setSimulationInputs((current) => ({ ...current, name: event.target.value }))} />
                  </label>
                  <label className="field">
                    <span>수량</span>
                    <input value={simulationInputs.quantities} onChange={(event) => setSimulationInputs((current) => ({ ...current, quantities: event.target.value }))} />
                  </label>
                  <label className="field">
                    <span>마진율</span>
                    <input value={simulationInputs.margin_rates} onChange={(event) => setSimulationInputs((current) => ({ ...current, margin_rates: event.target.value }))} />
                  </label>
                  <label className="field">
                    <span>메모</span>
                    <input value={simulationInputs.notes} onChange={(event) => setSimulationInputs((current) => ({ ...current, notes: event.target.value }))} />
                  </label>
                </div>
                {["admin", "manager"].includes(currentUser.role) && (
                  <ActionButton onClick={handlePricingSimulation}>시뮬레이션 실행</ActionButton>
                )}
                {activeSimulation && (
                  <div className="space-y-3">
                    <div className="flex flex-wrap gap-2">
                      <Badge>{activeSimulation.name}</Badge>
                      <Badge>scenarios: {activeSimulation.scenario_count}</Badge>
                      <Badge>unit cost: {formatMoney(activeSimulation.unit_cost)}</Badge>
                    </div>
                    <div className="table-wrap">
                      <table>
                        <thead>
                          <tr>
                            <th>수량</th>
                            <th>마진율</th>
                            <th>단가</th>
                            <th>합계</th>
                            <th>이익</th>
                            <th>상태</th>
                            <th>위험도</th>
                          </tr>
                        </thead>
                        <tbody>
                          {activeSimulation.scenarios.map((scenario) => (
                            <tr key={scenario.id}>
                              <td>{scenario.quantity}</td>
                              <td>{scenario.margin_rate}</td>
                              <td>{formatMoney(scenario.unit_price)}</td>
                              <td>{formatMoney(scenario.total_price)}</td>
                              <td>{formatMoney(scenario.estimated_gross_profit)}</td>
                              <td>{displayStatus(scenario.validation_status)}</td>
                              <td>{displayStatus(scenario.risk_level)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <Notes notes={displayNotes(activeSimulation.simulation_notes)} />
                  </div>
                )}
                {pricingSimulations.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {pricingSimulations.slice(0, 5).map((simulation) => (
                      <button className="button compact secondary" key={simulation.id} onClick={() => setActiveSimulation(simulation)}>
                        #{simulation.id} {simulation.name}
                      </button>
                    ))}
                  </div>
                )}
              </Panel>
            )}

            {showSection("pricing-tools", "simulations") && currentUser && (
              <Panel title="전략 템플릿">
                <div className="grid gap-3 md:grid-cols-2">
                  <label className="field">
                    <span>템플릿</span>
                    <select value={selectedStrategyTemplateId} onChange={(event) => setSelectedStrategyTemplateId(event.target.value)}>
                      {strategyTemplates.map((template) => (
                        <option key={template.id} value={template.id}>
                          #{template.id} {template.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="field">
                    <span>이름</span>
                    <input value={strategyTemplateForm.name} onChange={(event) => setStrategyTemplateForm((current) => ({ ...current, name: event.target.value }))} />
                  </label>
                  <details className="advanced-details">
                    <summary>고급 입력</summary>
                    <label className="field">
                      <span>전략 코드</span>
                      <input value={strategyTemplateForm.strategy_code} onChange={(event) => setStrategyTemplateForm((current) => ({ ...current, strategy_code: event.target.value }))} />
                    </label>
                  </details>
                  <label className="field">
                    <span>위험 선호도</span>
                    <select value={strategyTemplateForm.risk_preference} onChange={(event) => setStrategyTemplateForm((current) => ({ ...current, risk_preference: event.target.value }))}>
                      {["conservative", "balanced", "aggressive"].map((risk) => (
                        <option key={risk} value={risk}>{displayStatus(risk)}</option>
                      ))}
                    </select>
                  </label>
                  <label className="field">
                    <span>마진율</span>
                    <input value={strategyTemplateForm.margin_rates} onChange={(event) => setStrategyTemplateForm((current) => ({ ...current, margin_rates: event.target.value }))} />
                  </label>
                  <label className="field">
                    <span>기본 수량</span>
                    <input value={strategyTemplateForm.default_quantities} onChange={(event) => setStrategyTemplateForm((current) => ({ ...current, default_quantities: event.target.value }))} />
                  </label>
                  <label className="field">
                    <span>설명</span>
                    <input value={strategyTemplateForm.description} onChange={(event) => setStrategyTemplateForm((current) => ({ ...current, description: event.target.value }))} />
                  </label>
                  <label className="field">
                    <span>메모</span>
                    <input value={strategyTemplateForm.notes} onChange={(event) => setStrategyTemplateForm((current) => ({ ...current, notes: event.target.value }))} />
                  </label>
                </div>
                <div className="flex flex-wrap gap-3">
                  <label className="inline-flex items-center gap-2 text-sm text-slate-600">
                    <input
                      checked={strategyTemplateForm.include_competitor_context_default}
                      type="checkbox"
                      onChange={(event) => setStrategyTemplateForm((current) => ({ ...current, include_competitor_context_default: event.target.checked }))}
                    />
                    경쟁사 가격 맥락 기본 포함
                  </label>
                  <label className="inline-flex items-center gap-2 text-sm text-slate-600">
                    <input
                      checked={strategyTemplateForm.active}
                      type="checkbox"
                      onChange={(event) => setStrategyTemplateForm((current) => ({ ...current, active: event.target.checked }))}
                    />
                    활성
                  </label>
                </div>
                <div className="flex flex-wrap gap-2">
                  {["admin", "manager"].includes(currentUser.role) && (
                    <>
                      <button className="button compact" onClick={handleCreateStrategyTemplate}>템플릿 생성</button>
                      <button className="button compact secondary" onClick={handleUpdateStrategyTemplate}>선택 항목 수정</button>
                      <button className="button compact secondary" onClick={handleDisableStrategyTemplate}>선택 항목 비활성화</button>
                    </>
                  )}
                  <button className="button compact secondary" onClick={refreshStrategyTemplates}>템플릿 새로고침</button>
                  <button className="button compact" onClick={handleStrategyTemplateCandidates}>가격안에 적용</button>
                  <button className="button compact" onClick={handleStrategyTemplateSimulation}>시뮬레이션에 적용</button>
                </div>
                <div className="overflow-x-auto">
                  <table>
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>이름</th>
                        <th>코드</th>
                        <th>위험도</th>
                        <th>마진율</th>
                        <th>수량</th>
                        <th>활성</th>
                      </tr>
                    </thead>
                    <tbody>
                      {strategyTemplates.length === 0 && (
                        <tr><td colSpan="7"><EmptyState title="아직 전략 템플릿이 없습니다." message="가격안이나 시뮬레이션에 적용할 템플릿을 먼저 만드세요." /></td></tr>
                      )}
                      {strategyTemplates.map((template) => (
                        <tr key={template.id}>
                          <td>{template.id}</td>
                          <td>{template.name}</td>
                          <td>{displayCode(template.strategy_code)}</td>
                          <td>{displayStatus(template.risk_preference)}</td>
                          <td>{template.margin_rates.join(", ")}</td>
                          <td>{template.default_quantities.join(", ")}</td>
                          <td>{template.active ? "예" : "아니오"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {strategyTemplateCandidates && (
                  <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
                    <div className="mb-2 flex flex-wrap gap-2">
                      <Badge>템플릿 가격안</Badge>
                      <Badge>상품: {strategyTemplateCandidates.product_name}</Badge>
                      <Badge>수량: {strategyTemplateCandidates.quantity}</Badge>
                    </div>
                    <div className="grid gap-3 md:grid-cols-3">
                      {strategyTemplateCandidates.candidates.map((candidate) => (
                        <div className="rounded-md bg-white p-3" key={candidate.strategy}>
                          <strong>{displayCode(candidate.strategy)}</strong>
                          <p>마진율: {candidate.margin_rate}</p>
                          <p>단가: {formatMoney(candidate.unit_price)}</p>
                          <p>합계: {formatMoney(candidate.total_price)}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {strategyTemplateSimulation && (
                  <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
                    <div className="flex flex-wrap gap-2">
                      <Badge>{strategyTemplateSimulation.name}</Badge>
                      <Badge>시나리오: {strategyTemplateSimulation.scenario_count}</Badge>
                      <Badge>단위 원가: {formatMoney(strategyTemplateSimulation.unit_cost)}</Badge>
                    </div>
                  </div>
                )}
              </Panel>
            )}

            {showSection("simulations") && currentUser && (
              <Panel title="시나리오 비교">
                <div className="grid gap-3 md:grid-cols-2">
                  <label className="field">
                    <span>비교 이름</span>
                    <input value={scenarioComparisonForm.name} onChange={(event) => setScenarioComparisonForm((current) => ({ ...current, name: event.target.value }))} />
                  </label>
                  <label className="field">
                    <span>설명</span>
                    <input value={scenarioComparisonForm.description} onChange={(event) => setScenarioComparisonForm((current) => ({ ...current, description: event.target.value }))} />
                  </label>
                </div>
                <label className="field">
                  <span>시나리오</span>
                  <textarea rows="4" value={scenarioComparisonForm.scenarios} onChange={(event) => setScenarioComparisonForm((current) => ({ ...current, scenarios: event.target.value }))} />
                </label>
                <label className="checkbox">
                  <input
                    checked={scenarioComparisonForm.include_competitor_context}
                    type="checkbox"
                    onChange={(event) => setScenarioComparisonForm((current) => ({ ...current, include_competitor_context: event.target.checked }))}
                  />
                  경쟁사 가격 맥락 포함
                </label>
                <div className="flex flex-wrap gap-2">
                  {["admin", "manager"].includes(currentUser.role) && (
                    <button className="button compact" onClick={handleCreateScenarioComparison}>시나리오 비교</button>
                  )}
                  <button className="button compact secondary" onClick={refreshScenarioComparisons}>다시 불러오기</button>
                </div>
                {activeScenarioComparison && (
                  <div className="space-y-3">
                    <div className="flex flex-wrap gap-2">
                      <Badge>{activeScenarioComparison.name}</Badge>
                      <Badge>최고 마진: {activeScenarioComparison.summary.highest_margin_label}</Badge>
                      <Badge>최고 이익: {activeScenarioComparison.summary.highest_profit_label}</Badge>
                      <Badge>최저 위험: {activeScenarioComparison.summary.lowest_risk_label}</Badge>
                    </div>
                    <div className="table-wrap">
                      <table>
                        <thead>
                          <tr>
                            <th>라벨</th>
                            <th>수량</th>
                            <th>마진율</th>
                            <th>단가</th>
                            <th>총액</th>
                            <th>예상 이익</th>
                            <th>상태</th>
                            <th>위험도</th>
                          </tr>
                        </thead>
                        <tbody>
                          {activeScenarioComparison.scenarios.map((scenario) => (
                            <tr key={scenario.id}>
                              <td>{scenario.label}</td>
                              <td>{scenario.quantity}</td>
                              <td>{scenario.margin_rate}</td>
                              <td>{formatMoney(scenario.unit_price)}</td>
                              <td>{formatMoney(scenario.total_price)}</td>
                              <td>{formatMoney(scenario.estimated_gross_profit)}</td>
                              <td>{displayStatus(scenario.validation_status)}</td>
                              <td>{displayStatus(scenario.risk_level)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <Notes notes={displayNotes(activeScenarioComparison.comparison_notes)} />
                    <CompetitorContext context={activeScenarioComparison.competitor_context} />
                  </div>
                )}
                <div className="overflow-x-auto">
                  <table>
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>이름</th>
                        <th>상품</th>
                        <th>시나리오</th>
                        <th>처리</th>
                      </tr>
                    </thead>
                    <tbody>
                      {scenarioComparisons.length === 0 && (
                        <tr><td colSpan="5"><EmptyState title="아직 실행한 시나리오가 없습니다." message="조건을 바꿔 가격 결과를 비교해 보세요." /></td></tr>
                      )}
                      {scenarioComparisons.slice(0, 8).map((comparison) => (
                        <tr key={comparison.id}>
                          <td>{comparison.id}</td>
                          <td>{comparison.name}</td>
                          <td>{comparison.product_name}</td>
                          <td>{comparison.scenario_count}</td>
                          <td><button className="button compact secondary" onClick={() => handleViewScenarioComparison(comparison.id)}>보기</button></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Panel>
            )}

            {showSection("pricing-tools", "simulations") && currentUser && (
              <Panel title="가격표 이력과 비교">
                <div className="grid gap-3 md:grid-cols-2">
                  <label className="field">
                    <span>기준 가격표</span>
                    <select value={selectedPriceTableId} onChange={(event) => setSelectedPriceTableId(event.target.value)}>
                      {priceTables.map((table) => (
                        <option key={table.id} value={table.id}>{table.name}</option>
                      ))}
                    </select>
                  </label>
                  <label className="field">
                    <span>대상 가격표</span>
                    <select value={targetPriceTableId} onChange={(event) => setTargetPriceTableId(event.target.value)}>
                      {priceTables.map((table) => (
                        <option key={table.id} value={table.id}>{table.name}</option>
                      ))}
                    </select>
                  </label>
                  <label className="field">
                    <span>스냅샷 이름</span>
                    <input value={snapshotForm.label} onChange={(event) => setSnapshotForm((current) => ({ ...current, label: event.target.value }))} />
                  </label>
                  <label className="field">
                    <span>스냅샷 메모</span>
                    <input value={snapshotForm.note} onChange={(event) => setSnapshotForm((current) => ({ ...current, note: event.target.value }))} />
                  </label>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button className="button compact" onClick={handlePriceTableSummary}>요약 보기</button>
                  {["admin", "manager"].includes(currentUser.role) && (
                    <button className="button compact" onClick={handleCreateSnapshot}>스냅샷 생성</button>
                  )}
                  <button className="button compact secondary" onClick={handleComparePriceTables}>가격표 비교</button>
                </div>
                {priceTableSummary && (
                  <div className="grid gap-3 md:grid-cols-4">
                    <StatusCard label="항목 수" value={priceTableSummary.item_count} />
                    <StatusCard label="평균" value={formatMoney(priceTableSummary.average_price)} />
                    <StatusCard label="최소" value={formatMoney(priceTableSummary.min_price)} />
                    <StatusCard label="최대" value={formatMoney(priceTableSummary.max_price)} />
                  </div>
                )}
                {priceTableSnapshots.length > 0 && (
                  <div className="grid gap-3 md:grid-cols-[1fr_1fr_auto]">
                    <label className="field">
                      <span>기준 스냅샷</span>
                      <select value={baseSnapshotId} onChange={(event) => setBaseSnapshotId(event.target.value)}>
                        {priceTableSnapshots.map((snapshot) => (
                          <option key={snapshot.id} value={snapshot.id}>{snapshot.label}</option>
                        ))}
                      </select>
                    </label>
                    <label className="field">
                      <span>대상 스냅샷</span>
                      <select value={targetSnapshotId} onChange={(event) => setTargetSnapshotId(event.target.value)}>
                        {priceTableSnapshots.map((snapshot) => (
                          <option key={snapshot.id} value={snapshot.id}>{snapshot.label}</option>
                        ))}
                      </select>
                    </label>
                    <button className="button compact secondary" onClick={handleCompareSnapshots}>스냅샷 비교</button>
                  </div>
                )}
                {priceTableComparison && (
                  <div className="overflow-x-auto">
                    <table>
                      <thead>
                        <tr>
                          <th>상품</th>
                          <th>SKU</th>
                          <th>유형</th>
                          <th>기준</th>
                          <th>대상</th>
                          <th>차이</th>
                          <th>차이율</th>
                          <th>마진 차이</th>
                        </tr>
                      </thead>
                      <tbody>
                        {priceTableComparison.changes.map((change) => (
                          <tr key={`${change.product_id}-${change.change_type}`}>
                            <td>{change.product_name}</td>
                            <td>{change.product_sku}</td>
                            <td>{change.change_type}</td>
                            <td>{formatMoney(change.base_price)}</td>
                            <td>{formatMoney(change.target_price)}</td>
                            <td>{formatMoney(change.price_delta)}</td>
                            <td>{change.price_delta_rate ?? "-"}</td>
                            <td>{change.margin_delta ?? "-"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    <Notes notes={displayNotes(priceTableComparison.comparison_notes)} />
                  </div>
                )}
              </Panel>
            )}

            {showSection("approvals") && (
            <Panel title="승인 관리">
              <div className="workflow-panel-intro">
                <Badge>승인 대기</Badge>
                <p>승인 대기 건을 검토하고 승인 또는 반려합니다.</p>
              </div>
              <div className="grid gap-3 md:grid-cols-[1fr_1fr_auto]">
                <label className="field">
                  <span>검토자</span>
                  <input value={reviewerName} onChange={(event) => setReviewerName(event.target.value)} />
                </label>
                <label className="field">
                  <span>검토 메모</span>
                  <input value={reviewNote} onChange={(event) => setReviewNote(event.target.value)} />
                </label>
                <ActionButton onClick={handleCreateApproval}>승인 요청</ActionButton>
              </div>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>상품</th>
                      <th>단가</th>
                      <th>검증</th>
                      <th>위험</th>
                      <th>상태</th>
                      <th>처리</th>
                    </tr>
                  </thead>
                  <tbody>
                    {approvalRequests.length === 0 && (
                      <tr><td colSpan="7"><EmptyState title="승인 대기 건이 없습니다." message="가격 검증 후 승인 요청을 만들 수 있습니다." /></td></tr>
                    )}
                    {approvalRequests.map((request) => (
                      <tr key={request.id}>
                        <td>{request.id}</td>
                        <td>{request.product_name}</td>
                        <td>{formatMoney(request.proposed_unit_price)}</td>
                        <td>{displayStatus(request.validation_status)}</td>
                        <td>{displayStatus(request.risk_level)}</td>
                        <td>{displayStatus(request.status)}</td>
                        <td>
                          {request.status === "pending" ? (
                            <div className="flex gap-2">
                              <button className="button compact" onClick={() => handleReviewApproval(request.id, "approve")}>승인</button>
                              <button className="button compact secondary" onClick={() => handleReviewApproval(request.id, "reject")}>반려</button>
                            </div>
                          ) : request.review_note || "-"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Panel>
            )}

            {showSection("quote-operations", "pricing-tools") && (
            <Panel title="안전 설명">
              <ActionButton onClick={handleExplanation}>설명 만들기</ActionButton>
              {results.explanation && (
                <div className="space-y-3">
                  <p className="rounded-md bg-slate-950 p-4 text-white">{results.explanation.explanation_summary}</p>
                  <Notes notes={displayNotes(results.explanation.explanation_bullets)} />
                  <Notes title="결정 기준" notes={results.explanation.decision_boundaries} />
                  <Badge>출처: {results.explanation.explanation_source}</Badge>
                </div>
              )}
            </Panel>
            )}

            {showSection("quote-operations", "customer-requests") && currentUser && (
              <Panel title="고객 요청">
                <div className="workflow-panel-intro">
                  <Badge>고객 요청</Badge>
                  <p>들어온 요청을 확인하고 견적으로 연결하세요.</p>
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  {["customer_name", "customer_email", "customer_company", "quantity", "request_note"].map((field) => (
                    <label className="field" key={field}>
                      <span>{CUSTOMER_QUOTE_FIELD_LABELS[field]}</span>
                      <input value={customerQuoteForm[field]} onChange={(event) => setCustomerQuoteForm((current) => ({ ...current, [field]: event.target.value }))} />
                    </label>
                  ))}
                </div>
                <ActionButton onClick={handleCreateCustomerQuoteRequest}>요청 등록</ActionButton>
                <div className="grid gap-3 md:grid-cols-[1fr_auto]">
                  <label className="field">
                    <span>상태 변경</span>
                    <select value={quoteRequestStatus} onChange={(event) => setQuoteRequestStatus(event.target.value)}>
                      {["new", "reviewing", "quoted", "closed"].map((status) => (
                        <option key={status} value={status}>{displayStatus(status)}</option>
                      ))}
                    </select>
                  </label>
                  <button className="button compact secondary" onClick={refreshCustomerQuoteRequests}>다시 불러오기</button>
                </div>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>고객</th>
                        <th>상품</th>
                        <th>수량</th>
                        <th>상태</th>
                        <th>처리</th>
                      </tr>
                    </thead>
                    <tbody>
                      {customerQuoteRequests.length === 0 && (
                        <tr><td colSpan="6"><EmptyState title="들어온 요청이 없습니다." message="고객 요청을 등록하면 견적 흐름을 시작할 수 있습니다." /></td></tr>
                      )}
                      {customerQuoteRequests.map((request) => (
                        <tr key={request.id}>
                          <td>{request.id}</td>
                          <td>{request.customer_name}</td>
                          <td>{request.product_name}</td>
                          <td>{request.quantity}</td>
                          <td>{displayStatus(request.status)}</td>
                          <td>
                            <div className="flex flex-wrap gap-2">
                              {["admin", "manager"].includes(currentUser.role) && (
                                <>
                                  <button className="button compact" onClick={() => handleCustomerQuoteStatus(request.id)}>상태 변경</button>
                                  <button className="button compact secondary" onClick={() => handleCustomerQuotePreview(request.id)}>견적 미리보기</button>
                                  <button className="button compact secondary" onClick={() => handleCustomerQuoteCandidates(request.id)}>가격 계산</button>
                                </>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Panel>
            )}

            {showSection("admin-system") && currentUser && (
              <Panel title="데이터 관리">
                <div className="grid gap-3 md:grid-cols-3">
                  {[
                    ["products", "상품"],
                    ["cost-profiles", "원가 프로필"],
                    ["competitor-prices", "경쟁사 가격"],
                  ].map(([entity, label]) => (
                    <div className="rounded-md border border-slate-200 bg-slate-50 p-3" key={entity}>
                      <label className="field">
                        <span>{label} CSV</span>
                        <input
                          accept=".csv,text/csv"
                          type="file"
                          onChange={(event) => setCsvFiles((current) => ({ ...current, [entity]: event.target.files?.[0] || null }))}
                        />
                      </label>
                      <div className="flex flex-wrap gap-2">
                        {["admin", "manager"].includes(currentUser.role) && (
                          <button className="button compact" onClick={() => handleCsvImport(entity)}>데이터 가져오기</button>
                        )}
                        <button className="button compact secondary" onClick={() => handleCsvExport(entity, `${entity}.csv`)}>내보내기</button>
                      </div>
                    </div>
                  ))}
                </div>
                {csvImportResult && (
                  <div className="rounded-md border border-slate-200 bg-white p-3 text-sm">
                    <div className="flex flex-wrap gap-2">
                      <Badge>{CSV_ENTITY_LABELS[csvImportResult.entity_type] || csvImportResult.entity_type}</Badge>
                      <Badge>수신: {csvImportResult.received_rows}</Badge>
                      <Badge>생성: {csvImportResult.created_rows}</Badge>
                      <Badge>수정: {csvImportResult.updated_rows}</Badge>
                      <Badge>실패: {csvImportResult.failed_rows}</Badge>
                    </div>
                    <Notes notes={displayNotes(csvImportResult.notes)} />
                    <Notes title="가져오기 오류" notes={csvImportResult.errors?.map((item) => `${item.row_number}행: ${item.message}`)} />
                  </div>
                )}
              </Panel>
            )}

            {showSection("simulations", "admin-system") && currentUser && (
              <Panel title="작업 상태">
                <div className="grid gap-3 md:grid-cols-2">
                  <label className="field">
                    <span>작업 유형</span>
                    <select value={workflowJobForm.job_type} onChange={(event) => setWorkflowJobForm((current) => ({ ...current, job_type: event.target.value }))}>
                      {["pricing_simulation", "price_validation_batch", "quote_request_review"].map((jobType) => (
                        <option key={jobType} value={jobType}>{JOB_TYPE_LABELS[jobType]}</option>
                      ))}
                    </select>
                  </label>
                  <label className="field">
                    <span>제목</span>
                    <input value={workflowJobForm.title} onChange={(event) => setWorkflowJobForm((current) => ({ ...current, title: event.target.value }))} />
                  </label>
                  <label className="field">
                    <span>설명</span>
                    <input value={workflowJobForm.description} onChange={(event) => setWorkflowJobForm((current) => ({ ...current, description: event.target.value }))} />
                  </label>
                </div>
                <details className="advanced-details">
                  <summary>고급 입력</summary>
                  <label className="field">
                    <span>입력 JSON</span>
                    <textarea rows="8" value={workflowJobForm.input} onChange={(event) => setWorkflowJobForm((current) => ({ ...current, input: event.target.value }))} />
                  </label>
                </details>
                <div className="flex flex-wrap gap-2">
                  {["admin", "manager"].includes(currentUser.role) && (
                    <button className="button compact" onClick={handleCreateWorkflowJob}>작업 생성</button>
                  )}
                  <button className="button compact secondary" onClick={refreshWorkflowJobs}>다시 불러오기</button>
                </div>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>유형</th>
                        <th>제목</th>
                        <th>상태</th>
                        <th>처리</th>
                      </tr>
                    </thead>
                    <tbody>
                      {workflowJobs.length === 0 && (
                        <tr><td colSpan="5"><EmptyState title="시스템 운영 정보가 없습니다." message="작업을 생성하면 상태를 확인할 수 있습니다." /></td></tr>
                      )}
                      {workflowJobs.map((job) => (
                        <tr key={job.id}>
                          <td>{job.id}</td>
                          <td>{JOB_TYPE_LABELS[job.job_type] || job.job_type}</td>
                          <td>{job.title}</td>
                          <td>{displayStatus(job.status)}</td>
                          <td>
                            <div className="flex flex-wrap gap-2">
                              <button className="button compact secondary" onClick={() => setActiveWorkflowJob(job)}>보기</button>
                              {job.status === "pending" && ["admin", "manager"].includes(currentUser.role) && (
                                <>
                                  <button className="button compact" onClick={() => handleRunWorkflowJob(job.id)}>실행</button>
                                  <button className="button compact secondary" onClick={() => handleCancelWorkflowJob(job.id)}>취소</button>
                                </>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {activeWorkflowJob && (
                  <details className="advanced-details">
                    <summary>기술 정보</summary>
                    <pre className="overflow-x-auto rounded-md bg-slate-950 p-4 text-sm text-white">{JSON.stringify(activeWorkflowJob.result || { error: activeWorkflowJob.error_message, status: activeWorkflowJob.status }, null, 2)}</pre>
                  </details>
                )}
              </Panel>
            )}

            {showSection("approvals", "admin-system") && currentUser && ["admin", "manager"].includes(currentUser.role) && (
              <Panel title="감사 로그">
                <ActionButton onClick={() => refreshAuditLogs()}>감사 로그 새로고침</ActionButton>
                <div className="overflow-x-auto">
                  <table>
                    <thead>
                      <tr>
                        <th>작업</th>
                        <th>사용자</th>
                        <th>대상</th>
                        <th>요약</th>
                        <th>생성일</th>
                      </tr>
                    </thead>
                    <tbody>
                      {auditLogs.length === 0 && (
                        <tr><td colSpan="5"><EmptyState title="감사 로그가 없습니다." message="로그인 후 작업을 실행하고 감사 로그를 새로고침하세요." /></td></tr>
                      )}
                      {auditLogs.map((log) => (
                        <tr key={log.id}>
                          <td>{displayAction(log.action)}</td>
                          <td>{log.actor_username}</td>
                          <td>{displayCode(log.entity_type)}</td>
                          <td>{log.summary}</td>
                          <td>{new Date(log.created_at).toLocaleString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Panel>
            )}
          </div>
          </div>
        </section>
        )}
      </div>
    </main>
  )
}

function WorkflowPageHeader({ meta, setActiveSection }) {
  const runPrimary = () => {
    if (meta.primaryAction) {
      meta.primaryAction()
      return
    }
    if (meta.primarySection) setActiveSection(meta.primarySection)
  }
  const runSecondary = () => {
    if (meta.secondaryAction) {
      meta.secondaryAction()
      return
    }
    if (meta.secondarySection) setActiveSection(meta.secondarySection)
  }

  return (
    <section className="workflow-header card">
      <div>
        <p className="overview-eyebrow">{meta.eyebrow}</p>
        <h2>{meta.title}</h2>
        <p>{meta.helper}</p>
      </div>
      <div className="overview-actions">
        {meta.primary && <button className={`button ${meta.primaryVariant === "secondary" ? "button-secondary" : "button-primary"}`} type="button" onClick={runPrimary}>{meta.primary}</button>}
        {meta.secondary && <button className="button button-secondary" type="button" onClick={runSecondary}>{meta.secondary}</button>}
      </div>
    </section>
  )
}

function WorkflowStepStrip({ steps }) {
  return (
    <ol className="workflow-step-strip card" aria-label="견적 흐름">
      {steps.map((step, index) => (
        <li key={step}>
          <span>{index + 1}</span>
          <strong>{step}</strong>
        </li>
      ))}
    </ol>
  )
}

function SafetyBoundaryCard() {
  return (
    <section className="workflow-safety card">
      <span className="badge badge-warning">자동 반영 없음</span>
      <div>
        <h3>승인 전 자동 반영 없음</h3>
        <p>승인 없이 가격을 확정하거나 전송하지 않습니다.</p>
      </div>
    </section>
  )
}

function SupportPageHeader({ eyebrow, title, helper, primary, secondary }) {
  return (
    <section className="support-header card">
      <div>
        <p className="overview-eyebrow">{eyebrow}</p>
        <h2>{title}</h2>
        <p>{helper}</p>
      </div>
      <div className="overview-actions">
        {primary}
        {secondary}
      </div>
    </section>
  )
}

function StatusCard({ label, value }) {
  return (
    <div className="card status-card rounded-md border border-slate-200 bg-white p-4">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-1 font-semibold">{value}</p>
    </div>
  )
}

function LoadingState({ message = "작업 데이터를 불러오는 중입니다..." }) {
  return (
    <div className="card mb-5 rounded-md border border-slate-200 bg-white p-4 text-sm text-slate-600">
      <p className="font-semibold text-slate-800">처리 중</p>
      <p className="mt-1">{message}</p>
    </div>
  )
}

function RetryButton({ onRetry }) {
  if (!onRetry) return null
  return <button className="button compact secondary" onClick={onRetry}>다시 시도</button>
}

function ErrorState({ title = "데이터를 불러오지 못했습니다.", message, status, onRetry }) {
  return (
    <div className="error-state mb-5 rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-semibold">{title}</p>
          <p className="mt-1">{message || "백엔드 상태를 확인한 뒤 다시 시도하세요."}</p>
          {status && <p className="mt-1 text-xs text-red-600">상태: {status}</p>}
          <p className="mt-2 text-xs text-red-600">문제가 계속되면 이 섹션을 새로고침하거나 백엔드 실행 상태를 확인하세요.</p>
        </div>
        <RetryButton onRetry={onRetry} />
      </div>
    </div>
  )
}

function EmptyState({ title = "아직 데이터가 없습니다.", message, action }) {
  return (
    <div className="empty-state rounded-md border border-dashed border-slate-300 bg-slate-50 p-4 text-sm text-slate-600">
      <p className="font-semibold text-slate-800">{title}</p>
      {message && <p className="mt-1">{message}</p>}
      {action && <p className="mt-2 text-xs text-slate-500">{action}</p>}
    </div>
  )
}

function FormErrorMessage({ message }) {
  if (!message) return null
  return (
    <div className="mb-5 rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
      <p className="font-semibold">입력값을 확인하세요</p>
      <p className="mt-1">{message}</p>
    </div>
  )
}

function StatusBadge({ children }) {
  return <span className="badge rounded-full bg-slate-100 px-3 py-1 text-sm text-slate-700">{children}</span>
}

function ResultPanel({ children }) {
  return <div className="card rounded-md border border-slate-200 bg-slate-50 p-4">{children}</div>
}

function Panel({ title, children }) {
  return (
    <section className="card rounded-md border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="mb-4 text-lg font-semibold">{title}</h2>
      <div className="space-y-4">{children}</div>
    </section>
  )
}

function ActionButton({ children, onClick }) {
  return <button className="button" onClick={onClick}>{children}</button>
}

function Badge({ children }) {
  return <StatusBadge>{children}</StatusBadge>
}

function MetricGrid({ data, fields }) {
  if (!data) {
    return (
      <EmptyState
        title="아직 견적이 없습니다."
        message="첫 견적을 만들어 보세요."
      />
    )
  }
  return (
    <ResultPanel>
      <div className="grid gap-3 md:grid-cols-3">
        {fields.map((field) => (
          <div className="rounded-md bg-white p-3" key={field}>
            <p className="text-xs text-slate-500">{displayLabel(field)}</p>
            <p className="font-semibold">{formatMoney(data[field])}</p>
          </div>
        ))}
      </div>
    </ResultPanel>
  )
}

function DashboardMetricTable({ title, rows }) {
  return (
    <div className="table-wrap overflow-x-auto rounded-md border border-slate-200">
      <table>
        <thead>
          <tr>
            <th colSpan="2">{title}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([label, value]) => (
            <tr key={label}>
              <td>{label}</td>
              <td>{value}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function Notes({ title = "메모", notes }) {
  if (!notes?.length) return null
  return (
    <div>
      <p className="mb-1 text-sm font-semibold text-slate-600">{title}</p>
      <ul className="list-disc space-y-1 pl-5 text-sm text-slate-600">
        {notes.map((note) => <li key={note}>{note}</li>)}
      </ul>
    </div>
  )
}

function CompetitorContext({ context }) {
  if (!context) return null
  return (
    <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm">
      <p className="font-semibold">경쟁사 가격 맥락: {context.available ? "확인됨" : "없음"}</p>
      <p>참고 가격 수: {context.reference_price_count}</p>
      <p>평균: {formatMoney(context.average_reference_price)}</p>
    </div>
  )
}

export default App
