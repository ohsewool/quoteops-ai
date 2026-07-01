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
  if (!selectedProductId) return "Choose a product before running this pricing workflow."
  if (Number(quantity) <= 0) return "Quantity must be greater than 0."
  if (proposedUnitPrice !== undefined && Number(proposedUnitPrice) <= 0) {
    return "Proposed unit price must be greater than 0."
  }
  const rates = parseMarginRates(marginRates || "")
  if (marginRates && (!rates?.length || rates.some((rate) => rate < 0 || rate >= 1))) {
    return "Margin rates must be numbers greater than or equal to 0 and less than 1."
  }
  return ""
}

function validateJson(value) {
  try {
    JSON.parse(value)
    return ""
  } catch {
    return "Input JSON must be valid JSON before creating a workflow job."
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
  const [reviewerName, setReviewerName] = useState("Demo Manager")
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
    title: "Current KPI dashboard report",
    source_id: "",
  })
  const [csvFiles, setCsvFiles] = useState({
    products: null,
    "cost-profiles": null,
    "competitor-prices": null,
  })
  const [csvImportResult, setCsvImportResult] = useState(null)
  const [simulationInputs, setSimulationInputs] = useState({
    name: "Demo simulation for bulk order",
    quantities: "1,10,50",
    margin_rates: "0.25,0.35,0.45",
    notes: "Compare small and bulk order scenarios.",
  })
  const [pricingSimulations, setPricingSimulations] = useState([])
  const [activeSimulation, setActiveSimulation] = useState(null)
  const [strategyTemplates, setStrategyTemplates] = useState([])
  const [selectedStrategyTemplateId, setSelectedStrategyTemplateId] = useState("")
  const [strategyTemplateForm, setStrategyTemplateForm] = useState({
    name: "Standard Margin Strategy",
    strategy_code: "standard_margin_custom",
    description: "Balanced margin strategy for normal quote operations.",
    margin_rates: "0.25,0.35,0.45",
    default_quantities: "1,10,50",
    include_competitor_context_default: true,
    risk_preference: "balanced",
    active: true,
    notes: "Human-defined deterministic strategy template.",
  })
  const [strategyTemplateCandidates, setStrategyTemplateCandidates] = useState(null)
  const [strategyTemplateSimulation, setStrategyTemplateSimulation] = useState(null)
  const [scenarioComparisons, setScenarioComparisons] = useState([])
  const [activeScenarioComparison, setActiveScenarioComparison] = useState(null)
  const [scenarioComparisonForm, setScenarioComparisonForm] = useState({
    name: "Bulk order pricing comparison",
    description: "Compare conservative, standard, and premium pricing.",
    scenarios: "Conservative,50,0.25\nStandard,50,0.35\nPremium,50,0.45",
    include_competitor_context: true,
  })
  const [customerQuoteForm, setCustomerQuoteForm] = useState({
    customer_name: "Demo Customer",
    customer_email: "customer@example.com",
    customer_company: "Demo Company",
    quantity: 25,
    request_note: "Please provide a quote for 25 units.",
  })
  const [customerQuoteRequests, setCustomerQuoteRequests] = useState([])
  const [quoteRequestStatus, setQuoteRequestStatus] = useState("reviewing")
  const [priceTables, setPriceTables] = useState([])
  const [selectedPriceTableId, setSelectedPriceTableId] = useState("")
  const [targetPriceTableId, setTargetPriceTableId] = useState("")
  const [priceTableSummary, setPriceTableSummary] = useState(null)
  const [priceTableSnapshots, setPriceTableSnapshots] = useState([])
  const [snapshotForm, setSnapshotForm] = useState({
    label: "Before price review",
    note: "Snapshot before deterministic comparison.",
  })
  const [baseSnapshotId, setBaseSnapshotId] = useState("")
  const [targetSnapshotId, setTargetSnapshotId] = useState("")
  const [priceTableComparison, setPriceTableComparison] = useState(null)
  const [workflowJobForm, setWorkflowJobForm] = useState({
    job_type: "pricing_simulation",
    title: "Bulk pricing simulation",
    description: "Compare 1, 10, and 50 unit pricing.",
    input: '{\n  "product_id": 1,\n  "quantities": [1, 10, 50],\n  "margin_rates": [0.25, 0.35, 0.45],\n  "include_competitor_context": true\n}',
  })
  const [workflowJobs, setWorkflowJobs] = useState([])
  const [activeWorkflowJob, setActiveWorkflowJob] = useState(null)
  const [loginForm, setLoginForm] = useState({
    username: "manager",
    password: "manager-demo-password",
  })
  const [currentUser, setCurrentUser] = useState(null)

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
    await runAction("Loading initial data", async () => {
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

  async function handleLogin(event) {
    event.preventDefault()
    await runAction("Logging in", async () => {
      const data = await login(loginForm)
      localStorage.setItem("quoteops_token", data.access_token)
      setAccessToken(data.access_token)
      setCurrentUser(data.user)
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
    })
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
    await runAction("Seeding demo data", async () => {
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
    await runAction("Creating full demo scenario", async () => {
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
    await runAction("Resetting known demo data", async () => {
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
      if (stopForFormError("Report title cannot be empty.")) return
    }
    await runAction("Creating HTML report", async () => {
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
    await runAction("Loading HTML report", async () => {
      const report = await getHtmlReport(id)
      setActiveHtmlReport(report)
      await refreshAuditLogs()
    })
  }

  async function handleOpenHtmlReportContent(id) {
    await runAction("Opening HTML report", async () => {
      const content = await getHtmlReportContent(id)
      const url = window.URL.createObjectURL(new Blob([content], { type: "text/html" }))
      window.open(url, "_blank", "noopener,noreferrer")
      window.setTimeout(() => window.URL.revokeObjectURL(url), 1000)
      await refreshAuditLogs()
    })
  }

  async function handleCsvImport(entity) {
    if (!csvFiles[entity]) {
      stopForFormError("Choose a CSV file before importing.")
      return
    }
    await runAction(`Importing ${entity} CSV`, async () => {
      const result = await importCsv(entity, csvFiles[entity])
      setCsvImportResult(result)
      await refreshAuditLogs()
    })
  }

  async function handleCsvExport(entity, filename) {
    await runAction(`Exporting ${entity} CSV`, async () => {
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
      if (stopForFormError("Simulation name cannot be empty.")) return
    }
    if (parseIntegerList(simulationInputs.quantities).some((item) => item <= 0)) {
      if (stopForFormError("Simulation quantities must be greater than 0.")) return
    }
    await runAction("Running pricing simulation", async () => {
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
      if (stopForFormError("Strategy template name cannot be empty.")) return
    }
    await runAction("Creating strategy template", async () => {
      const template = await createStrategyTemplate(strategyTemplatePayload())
      await refreshStrategyTemplates()
      setSelectedStrategyTemplateId(String(template.id))
      await refreshAuditLogs()
    })
  }

  async function handleUpdateStrategyTemplate() {
    if (!selectedStrategyTemplateId) {
      if (stopForFormError("Choose a strategy template before updating.")) return
    }
    await runAction("Updating strategy template", async () => {
      const template = await updateStrategyTemplate(selectedStrategyTemplateId, strategyTemplatePayload())
      await refreshStrategyTemplates()
      setSelectedStrategyTemplateId(String(template.id))
      await refreshAuditLogs()
    })
  }

  async function handleDisableStrategyTemplate() {
    if (!selectedStrategyTemplateId) {
      if (stopForFormError("Choose a strategy template before disabling.")) return
    }
    await runAction("Disabling strategy template", async () => {
      await disableStrategyTemplate(selectedStrategyTemplateId)
      await refreshStrategyTemplates()
      await refreshAuditLogs()
    })
  }

  async function handleStrategyTemplateCandidates() {
    const pricingError = validatePricingForm()
    if (pricingError && stopForFormError(pricingError)) return
    if (!selectedStrategyTemplateId) {
      if (stopForFormError("Choose a strategy template before applying it.")) return
    }
    await runAction("Generating strategy template candidates", async () => {
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
      if (stopForFormError("Choose a product before running a template simulation.")) return
    }
    if (!selectedStrategyTemplateId) {
      if (stopForFormError("Choose a strategy template before running a simulation.")) return
    }
    await runAction("Running strategy template simulation", async () => {
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
          label: label || `Scenario ${index + 1}`,
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
      if (stopForFormError("Scenario comparison name cannot be empty.")) return
    }
    const scenarioRows = parseScenarioRows(scenarioComparisonForm.scenarios)
    if (!scenarioRows.length) {
      if (stopForFormError("Add at least one scenario row before creating a comparison.")) return
    }
    if (scenarioRows.some((row) => row.quantity <= 0 || row.margin_rate < 0 || row.margin_rate >= 1 || Number.isNaN(row.quantity) || Number.isNaN(row.margin_rate))) {
      if (stopForFormError("Each scenario needs a quantity greater than 0 and a margin rate between 0 and 1.")) return
    }
    await runAction("Creating scenario comparison", async () => {
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
    await runAction("Loading scenario comparison", async () => {
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
      if (stopForFormError("Choose a product before submitting a quote request.")) return
    }
    if (!customerQuoteForm.customer_name.trim()) {
      if (stopForFormError("Customer name cannot be empty.")) return
    }
    if (!isValidEmail(customerQuoteForm.customer_email)) {
      if (stopForFormError("Customer email should look like an email address.")) return
    }
    if (Number(customerQuoteForm.quantity) <= 0) {
      if (stopForFormError("Customer quote quantity must be greater than 0.")) return
    }
    await runAction("Creating customer quote request", async () => {
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
    await runAction("Updating customer quote request status", async () => {
      await updateCustomerQuoteRequestStatus(id, {
        status: quoteRequestStatus,
        assigned_to_username: currentUser?.username || "manager",
        internal_note: "Reviewed in frontend MVP.",
      })
      await refreshCustomerQuoteRequests()
      await refreshAuditLogs()
    })
  }

  async function handleCustomerQuotePreview(id) {
    await runAction("Creating quote preview from request", async () => {
      const data = await createCustomerQuotePreview(id)
      setResults((current) => ({ ...current, quotePreview: data }))
      await refreshAuditLogs()
    })
  }

  async function handleCustomerQuoteCandidates(id) {
    await runAction("Generating candidate prices from request", async () => {
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
      if (stopForFormError("Choose a price table before loading its summary.")) return
    }
    await runAction("Loading price table summary", async () => {
      const summary = await getPriceTableSummary(selectedPriceTableId)
      setPriceTableSummary(summary)
      setPriceTableSnapshots(await getPriceTableSnapshots(selectedPriceTableId))
      await refreshAuditLogs()
    })
  }

  async function handleCreateSnapshot() {
    if (!selectedPriceTableId) {
      if (stopForFormError("Choose a price table before creating a snapshot.")) return
    }
    if (!snapshotForm.label.trim()) {
      if (stopForFormError("Snapshot label cannot be empty.")) return
    }
    await runAction("Creating price table snapshot", async () => {
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
      if (stopForFormError("Choose both base and target price tables before comparing.")) return
    }
    await runAction("Comparing price tables", async () => {
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
      if (stopForFormError("Choose both snapshots before comparing.")) return
    }
    await runAction("Comparing price table snapshots", async () => {
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
      if (stopForFormError("Workflow job title cannot be empty.")) return
    }
    const jsonError = validateJson(workflowJobForm.input)
    if (jsonError && stopForFormError(jsonError)) return
    await runAction("Creating workflow job", async () => {
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
    await runAction("Running workflow job", async () => {
      const job = await runWorkflowJob(id)
      setActiveWorkflowJob(job)
      await refreshWorkflowJobs()
      await refreshAuditLogs()
    })
  }

  async function handleCancelWorkflowJob(id) {
    await runAction("Cancelling workflow job", async () => {
      const job = await cancelWorkflowJob(id)
      setActiveWorkflowJob(job)
      await refreshWorkflowJobs()
      await refreshAuditLogs()
    })
  }

  function useDemoUser(username) {
    setLoginForm({
      username,
      password: `${username}-demo-password`,
    })
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
    await runAction("Creating quote preview", async () => {
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
    await runAction("Generating candidate prices", async () => {
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
    await runAction("Validating proposed price", async () => {
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
    await runAction("Creating approval request", async () => {
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
    await runAction(`Reviewing approval request`, async () => {
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
    await runAction("Generating explanation", async () => {
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
  const overviewStatusItems = [
    {
      label: "서비스 정상",
      value: health?.status === "ok" ? "정상" : "확인 필요",
      tone: health?.status === "ok" ? "success" : "warning",
    },
    {
      label: "DB 연결 정상",
      value: systemStatus?.database?.connection_ok || readiness?.status === "ready" ? "정상" : "확인 필요",
      tone: systemStatus?.database?.connection_ok || readiness?.status === "ready" ? "success" : "warning",
    },
    {
      label: "OpenAPI 확인",
      value: systemStatus?.features?.openapi_available ? "확인" : "대기",
      tone: systemStatus?.features?.openapi_available ? "success" : "warning",
    },
    {
      label: "배포 연결",
      value: systemStatus?.cors?.configured ? "연결됨" : "로컬",
      tone: systemStatus?.cors?.configured ? "success" : "info",
    },
  ]
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
          <button className="button compact secondary" onClick={loadInitialData} disabled={!!loading}>
            새로고침
          </button>
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
            title="Could not complete request"
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
                <h2>견적 가격 운영의 시작점에서</h2>
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
              <div className="overview-hero-status" aria-label="Overview system status">
                {overviewStatusItems.map((item) => (
                  <div className="overview-status-item" key={item.label}>
                    <span>{item.label}</span>
                    <strong className={`badge badge-${item.tone}`}>{item.value}</strong>
                  </div>
                ))}
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
                      <p>최근 작업: {latestActions[0].action}</p>
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
                  title="Backend is not reachable"
                  message={`Start the backend locally or check the deployed API URL: ${safeApiBaseUrl}.`}
                  onRetry={loadInitialData}
                />
              </div>
            )}
            {sectionNeedsSignIn && (
              <div className="mt-4">
                <EmptyState
                  title="Sign in to use this section"
                  message="You need to sign in with a role that can access this section."
                  action="Use a local demo account or your configured user credentials."
                />
              </div>
            )}
          </section>
        )}

        <section className="section card-grid mb-5 grid gap-4 lg:grid-cols-[1fr_1.4fr]">
          <Panel title="데모 계정">
            {currentUser ? (
              <div className="space-y-3">
                <div className="flex flex-wrap gap-2">
                  <Badge>{currentUser.display_name}</Badge>
                  <Badge>권한: {currentUser.role}</Badge>
                </div>
                <button className="button secondary" onClick={handleLogout}>로그아웃</button>
              </div>
            ) : (
              <form className="form-grid grid gap-3 md:grid-cols-[1fr_1fr_auto]" onSubmit={handleLogin}>
                <label className="field">
                  <span>아이디</span>
                  <input value={loginForm.username} onChange={(event) => setLoginForm((current) => ({ ...current, username: event.target.value }))} />
                </label>
                <label className="field">
                  <span>비밀번호</span>
                  <input type="password" value={loginForm.password} onChange={(event) => setLoginForm((current) => ({ ...current, password: event.target.value }))} />
                </label>
                <button className="button" type="submit">로그인</button>
              </form>
            )}
            <div className="flex flex-wrap gap-2">
              {demoUsers.map((user) => (
                <button className="button compact secondary" key={user.username} onClick={() => useDemoUser(user.username)}>
                  {user.username === "admin" ? "관리자" : user.username === "manager" ? "매니저" : user.username === "viewer" ? "조회자" : user.username}
                </button>
              ))}
            </div>
            <p className="text-sm text-slate-500">포트폴리오 데모용 계정입니다.</p>
          </Panel>

          <section className="status-grid grid gap-4 lg:grid-cols-4" aria-label="System Status">
            <h2 className="sr-only">System Status</h2>
            <StatusCard label="서비스 정상" value={health?.status === "ok" ? "정상" : health?.status || "-"} />
            <StatusCard label="DB 연결 정상" value={systemStatus?.database?.connection_ok || readiness?.status === "ready" ? "정상" : "확인"} />
            <StatusCard label="OpenAPI 확인" value={systemStatus?.features?.openapi_available ? "확인" : "대기"} />
            <StatusCard label="배포 연결" value={systemStatus?.cors?.configured ? "연결됨" : "로컬"} />
          </section>

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
                    ["new", dashboardSummary.quote_metrics.new_quote_requests],
                    ["reviewing", dashboardSummary.quote_metrics.reviewing_quote_requests],
                    ["quoted", dashboardSummary.quote_metrics.quoted_quote_requests],
                    ["closed", dashboardSummary.quote_metrics.closed_quote_requests],
                    ["cancelled", dashboardSummary.quote_metrics.cancelled_quote_requests],
                  ]}
                />
                <DashboardMetricTable
                  title="승인 지표"
                  rows={[
                    ["pending", dashboardSummary.approval_metrics.pending_approval_requests],
                    ["approved", dashboardSummary.approval_metrics.approved_requests],
                    ["rejected", dashboardSummary.approval_metrics.rejected_requests],
                    ["approval rate", formatRate(dashboardSummary.approval_metrics.approval_rate)],
                    ["avg margin", dashboardSummary.approval_metrics.average_estimated_margin_rate ?? "-"],
                  ]}
                />
                <DashboardMetricTable
                  title="검증과 위험"
                  rows={[
                    ["passed", dashboardSummary.validation_metrics.passed_validations],
                    ["warning", dashboardSummary.validation_metrics.warning_validations],
                    ["failed", dashboardSummary.validation_metrics.failed_validations],
                    ["low risk", dashboardSummary.validation_metrics.low_risk_count],
                    ["high risk", dashboardSummary.validation_metrics.high_risk_count],
                  ]}
                />
                <DashboardMetricTable
                  title="작업 상태"
                  rows={[
                    ["pending", dashboardSummary.workflow_metrics.pending_jobs],
                    ["running", dashboardSummary.workflow_metrics.running_jobs],
                    ["completed", dashboardSummary.workflow_metrics.completed_jobs],
                    ["failed", dashboardSummary.workflow_metrics.failed_jobs],
                    ["success rate", formatRate(dashboardSummary.workflow_metrics.job_success_rate)],
                  ]}
                />
              </div>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Recent action</th>
                      <th>Actor</th>
                      <th>Created</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dashboardSummary.audit_metrics.latest_actions.length === 0 && (
                      <tr><td colSpan="3"><EmptyState title="표시할 요약 정보가 없습니다." message="데모 데이터를 불러오면 흐름을 확인할 수 있습니다." /></td></tr>
                    )}
                    {dashboardSummary.audit_metrics.latest_actions.map((action) => (
                      <tr key={`${action.action}-${action.created_at}`}>
                        <td>{action.action}</td>
                        <td>{action.actor_username}</td>
                        <td>{new Date(action.created_at).toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <Notes notes={dashboardSummary.dashboard_notes} />
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
                      <Badge>{insight.severity}</Badge>
                      <Badge>{insight.category}</Badge>
                    </div>
                    <p className="font-semibold">{insight.title}</p>
                    <p className="mt-1 text-sm text-slate-600">{insight.message}</p>
                    <p className="mt-3 text-sm font-semibold text-slate-700">Recommended action</p>
                    <p className="text-sm text-slate-600">{insight.recommended_action}</p>
                    <p className="mt-3 text-xs text-slate-500">{insight.decision_boundary}</p>
                  </div>
                ))}
              </div>
              <Notes notes={dashboardInsights.insight_notes} />
            </Panel>
          )}

          {showSection("demo-tools") && currentUser && (
            <section className="support-page">
              <SupportPageHeader
                eyebrow="데모"
                title="데모"
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
                    <Badge>{demoScenario.ready ? "ready" : "not ready"}</Badge>
                  </div>
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Step</th>
                          <th>Title</th>
                          <th>API</th>
                        </tr>
                      </thead>
                      <tbody>
                        {demoScenario.steps.map((step) => (
                          <tr key={step.step}>
                            <td>{step.step}</td>
                            <td>{step.title}</td>
                            <td>{step.api}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <Notes title="Decision boundaries" notes={demoScenario.decision_boundaries} />
                  <Notes title="Scenario notes" notes={demoScenario.demo_notes} />
                </div>
              )}

              {demoGuide && (
                <div className="grid gap-4 xl:grid-cols-2">
                  <div className="rounded-md border border-slate-200 bg-white p-3">
                    <p className="mb-2 font-semibold">데모 계정</p>
                    <div className="space-y-2 text-sm">
                      {demoGuide.demo_login_users.map((user) => (
                        <div className="flex flex-wrap gap-2" key={user.username}>
                          <Badge>{user.username}</Badge>
                          <Badge>{user.role}</Badge>
                          <span className="text-slate-600">{user.password_hint}</span>
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
                <div className="grid gap-3 md:grid-cols-2">
                  {demoSeedResult && (
                    <pre className="overflow-x-auto rounded-md bg-slate-950 p-4 text-sm text-white">{JSON.stringify(demoSeedResult.created_or_verified, null, 2)}</pre>
                  )}
                  {demoResetResult && (
                    <pre className="overflow-x-auto rounded-md bg-slate-950 p-4 text-sm text-white">{JSON.stringify(demoResetResult.deleted_or_disabled, null, 2)}</pre>
                  )}
                </div>
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
                      <option key={type} value={type}>{type}</option>
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
                    <Badge>{activeHtmlReport.report_type}</Badge>
                    <Badge>source: {activeHtmlReport.source_id || "none"}</Badge>
                    <Badge>created by: {activeHtmlReport.created_by_username}</Badge>
                  </div>
                  <p className="font-semibold">{activeHtmlReport.title}</p>
                  <p className="text-sm text-slate-600">{activeHtmlReport.summary_text}</p>
                  <Notes notes={activeHtmlReport.report_notes} />
                </div>
              )}
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Type</th>
                      <th>Title</th>
                      <th>Source</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {htmlReports.length === 0 && (
                      <tr><td colSpan="5"><EmptyState title="생성된 리포트가 없습니다." message="첫 리포트를 만들어 보세요." /></td></tr>
                    )}
                    {htmlReports.slice(0, 8).map((report) => (
                      <tr key={report.id}>
                        <td>{report.id}</td>
                        <td>{report.report_type}</td>
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
                    <h3 className="font-semibold">{candidate.strategy}</h3>
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
                    <Badge>status: {results.validation.validation_status}</Badge>
                    <Badge>risk: {results.validation.risk_level}</Badge>
                    <Badge>margin: {results.validation.estimated_margin_rate}</Badge>
                  </div>
                  <ul className="space-y-2">
                    {results.validation.checks.map((check) => (
                      <li className="rounded-md border border-slate-200 bg-slate-50 p-3" key={check.code}>
                        <strong>{check.code}</strong> {check.passed ? "passed" : "needs review"} - {check.message}
                      </li>
                    ))}
                  </ul>
                  <CompetitorContext context={results.validation.competitor_context} />
                  <Notes notes={results.validation.calculation_notes} />
                </div>
              )}
            </Panel>
            )}

            {showSection("simulations") && currentUser && (
              <Panel title="시뮬레이션">
                <div className="grid gap-3 md:grid-cols-2">
                  <label className="field">
                    <span>Simulation name</span>
                    <input value={simulationInputs.name} onChange={(event) => setSimulationInputs((current) => ({ ...current, name: event.target.value }))} />
                  </label>
                  <label className="field">
                    <span>Quantities</span>
                    <input value={simulationInputs.quantities} onChange={(event) => setSimulationInputs((current) => ({ ...current, quantities: event.target.value }))} />
                  </label>
                  <label className="field">
                    <span>Margin rates</span>
                    <input value={simulationInputs.margin_rates} onChange={(event) => setSimulationInputs((current) => ({ ...current, margin_rates: event.target.value }))} />
                  </label>
                  <label className="field">
                    <span>Notes</span>
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
                            <th>Qty</th>
                            <th>Margin</th>
                            <th>Unit price</th>
                            <th>Total</th>
                            <th>Profit</th>
                            <th>Status</th>
                            <th>Risk</th>
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
                              <td>{scenario.validation_status}</td>
                              <td>{scenario.risk_level}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <Notes notes={activeSimulation.simulation_notes} />
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
              <Panel title="Strategy Templates">
                <div className="grid gap-3 md:grid-cols-2">
                  <label className="field">
                    <span>Template</span>
                    <select value={selectedStrategyTemplateId} onChange={(event) => setSelectedStrategyTemplateId(event.target.value)}>
                      {strategyTemplates.map((template) => (
                        <option key={template.id} value={template.id}>
                          #{template.id} {template.name} ({template.strategy_code})
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="field">
                    <span>Name</span>
                    <input value={strategyTemplateForm.name} onChange={(event) => setStrategyTemplateForm((current) => ({ ...current, name: event.target.value }))} />
                  </label>
                  <label className="field">
                    <span>Strategy code</span>
                    <input value={strategyTemplateForm.strategy_code} onChange={(event) => setStrategyTemplateForm((current) => ({ ...current, strategy_code: event.target.value }))} />
                  </label>
                  <label className="field">
                    <span>Risk preference</span>
                    <select value={strategyTemplateForm.risk_preference} onChange={(event) => setStrategyTemplateForm((current) => ({ ...current, risk_preference: event.target.value }))}>
                      {["conservative", "balanced", "aggressive"].map((risk) => (
                        <option key={risk} value={risk}>{risk}</option>
                      ))}
                    </select>
                  </label>
                  <label className="field">
                    <span>Margin rates</span>
                    <input value={strategyTemplateForm.margin_rates} onChange={(event) => setStrategyTemplateForm((current) => ({ ...current, margin_rates: event.target.value }))} />
                  </label>
                  <label className="field">
                    <span>Default quantities</span>
                    <input value={strategyTemplateForm.default_quantities} onChange={(event) => setStrategyTemplateForm((current) => ({ ...current, default_quantities: event.target.value }))} />
                  </label>
                  <label className="field">
                    <span>Description</span>
                    <input value={strategyTemplateForm.description} onChange={(event) => setStrategyTemplateForm((current) => ({ ...current, description: event.target.value }))} />
                  </label>
                  <label className="field">
                    <span>Notes</span>
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
                    Include competitor context by default
                  </label>
                  <label className="inline-flex items-center gap-2 text-sm text-slate-600">
                    <input
                      checked={strategyTemplateForm.active}
                      type="checkbox"
                      onChange={(event) => setStrategyTemplateForm((current) => ({ ...current, active: event.target.checked }))}
                    />
                    Active
                  </label>
                </div>
                <div className="flex flex-wrap gap-2">
                  {["admin", "manager"].includes(currentUser.role) && (
                    <>
                      <button className="button compact" onClick={handleCreateStrategyTemplate}>Create template</button>
                      <button className="button compact secondary" onClick={handleUpdateStrategyTemplate}>Update selected</button>
                      <button className="button compact secondary" onClick={handleDisableStrategyTemplate}>Disable selected</button>
                    </>
                  )}
                  <button className="button compact secondary" onClick={refreshStrategyTemplates}>Refresh templates</button>
                  <button className="button compact" onClick={handleStrategyTemplateCandidates}>Apply to candidates</button>
                  <button className="button compact" onClick={handleStrategyTemplateSimulation}>Apply to simulation</button>
                </div>
                <div className="overflow-x-auto">
                  <table>
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>Name</th>
                        <th>Code</th>
                        <th>Risk</th>
                        <th>Margins</th>
                        <th>Quantities</th>
                        <th>Active</th>
                      </tr>
                    </thead>
                    <tbody>
                      {strategyTemplates.length === 0 && (
                        <tr><td colSpan="7"><EmptyState title="No strategy templates yet" message="Create a reusable deterministic strategy template before applying it to candidates or simulations." /></td></tr>
                      )}
                      {strategyTemplates.map((template) => (
                        <tr key={template.id}>
                          <td>{template.id}</td>
                          <td>{template.name}</td>
                          <td>{template.strategy_code}</td>
                          <td>{template.risk_preference}</td>
                          <td>{template.margin_rates.join(", ")}</td>
                          <td>{template.default_quantities.join(", ")}</td>
                          <td>{template.active ? "yes" : "no"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {strategyTemplateCandidates && (
                  <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
                    <div className="mb-2 flex flex-wrap gap-2">
                      <Badge>template candidates</Badge>
                      <Badge>product: {strategyTemplateCandidates.product_name}</Badge>
                      <Badge>quantity: {strategyTemplateCandidates.quantity}</Badge>
                    </div>
                    <div className="grid gap-3 md:grid-cols-3">
                      {strategyTemplateCandidates.candidates.map((candidate) => (
                        <div className="rounded-md bg-white p-3" key={candidate.strategy}>
                          <strong>{candidate.strategy}</strong>
                          <p>Margin: {candidate.margin_rate}</p>
                          <p>Unit: {formatMoney(candidate.unit_price)}</p>
                          <p>Total: {formatMoney(candidate.total_price)}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {strategyTemplateSimulation && (
                  <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
                    <div className="flex flex-wrap gap-2">
                      <Badge>{strategyTemplateSimulation.name}</Badge>
                      <Badge>scenarios: {strategyTemplateSimulation.scenario_count}</Badge>
                      <Badge>unit cost: {formatMoney(strategyTemplateSimulation.unit_cost)}</Badge>
                    </div>
                  </div>
                )}
              </Panel>
            )}

            {showSection("simulations") && currentUser && (
              <Panel title="시나리오 비교">
                <div className="grid gap-3 md:grid-cols-2">
                  <label className="field">
                    <span>Comparison name</span>
                    <input value={scenarioComparisonForm.name} onChange={(event) => setScenarioComparisonForm((current) => ({ ...current, name: event.target.value }))} />
                  </label>
                  <label className="field">
                    <span>Description</span>
                    <input value={scenarioComparisonForm.description} onChange={(event) => setScenarioComparisonForm((current) => ({ ...current, description: event.target.value }))} />
                  </label>
                </div>
                <label className="field">
                  <span>Scenarios</span>
                  <textarea rows="4" value={scenarioComparisonForm.scenarios} onChange={(event) => setScenarioComparisonForm((current) => ({ ...current, scenarios: event.target.value }))} />
                </label>
                <label className="checkbox">
                  <input
                    checked={scenarioComparisonForm.include_competitor_context}
                    type="checkbox"
                    onChange={(event) => setScenarioComparisonForm((current) => ({ ...current, include_competitor_context: event.target.checked }))}
                  />
                  Include competitor context
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
                      <Badge>highest margin: {activeScenarioComparison.summary.highest_margin_label}</Badge>
                      <Badge>highest profit: {activeScenarioComparison.summary.highest_profit_label}</Badge>
                      <Badge>lowest risk: {activeScenarioComparison.summary.lowest_risk_label}</Badge>
                    </div>
                    <div className="table-wrap">
                      <table>
                        <thead>
                          <tr>
                            <th>Label</th>
                            <th>Qty</th>
                            <th>Margin</th>
                            <th>Unit price</th>
                            <th>Total price</th>
                            <th>Gross profit</th>
                            <th>Status</th>
                            <th>Risk</th>
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
                              <td>{scenario.validation_status}</td>
                              <td>{scenario.risk_level}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <Notes notes={activeScenarioComparison.comparison_notes} />
                    <CompetitorContext context={activeScenarioComparison.competitor_context} />
                  </div>
                )}
                <div className="overflow-x-auto">
                  <table>
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>Name</th>
                        <th>Product</th>
                        <th>Scenarios</th>
                        <th>Action</th>
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
              <Panel title="Price Table History and Comparison">
                <div className="grid gap-3 md:grid-cols-2">
                  <label className="field">
                    <span>Base price table</span>
                    <select value={selectedPriceTableId} onChange={(event) => setSelectedPriceTableId(event.target.value)}>
                      {priceTables.map((table) => (
                        <option key={table.id} value={table.id}>{table.name}</option>
                      ))}
                    </select>
                  </label>
                  <label className="field">
                    <span>Target price table</span>
                    <select value={targetPriceTableId} onChange={(event) => setTargetPriceTableId(event.target.value)}>
                      {priceTables.map((table) => (
                        <option key={table.id} value={table.id}>{table.name}</option>
                      ))}
                    </select>
                  </label>
                  <label className="field">
                    <span>Snapshot label</span>
                    <input value={snapshotForm.label} onChange={(event) => setSnapshotForm((current) => ({ ...current, label: event.target.value }))} />
                  </label>
                  <label className="field">
                    <span>Snapshot note</span>
                    <input value={snapshotForm.note} onChange={(event) => setSnapshotForm((current) => ({ ...current, note: event.target.value }))} />
                  </label>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button className="button compact" onClick={handlePriceTableSummary}>View summary</button>
                  {["admin", "manager"].includes(currentUser.role) && (
                    <button className="button compact" onClick={handleCreateSnapshot}>Create snapshot</button>
                  )}
                  <button className="button compact secondary" onClick={handleComparePriceTables}>Compare tables</button>
                </div>
                {priceTableSummary && (
                  <div className="grid gap-3 md:grid-cols-4">
                    <StatusCard label="Items" value={priceTableSummary.item_count} />
                    <StatusCard label="Average" value={formatMoney(priceTableSummary.average_price)} />
                    <StatusCard label="Min" value={formatMoney(priceTableSummary.min_price)} />
                    <StatusCard label="Max" value={formatMoney(priceTableSummary.max_price)} />
                  </div>
                )}
                {priceTableSnapshots.length > 0 && (
                  <div className="grid gap-3 md:grid-cols-[1fr_1fr_auto]">
                    <label className="field">
                      <span>Base snapshot</span>
                      <select value={baseSnapshotId} onChange={(event) => setBaseSnapshotId(event.target.value)}>
                        {priceTableSnapshots.map((snapshot) => (
                          <option key={snapshot.id} value={snapshot.id}>{snapshot.label}</option>
                        ))}
                      </select>
                    </label>
                    <label className="field">
                      <span>Target snapshot</span>
                      <select value={targetSnapshotId} onChange={(event) => setTargetSnapshotId(event.target.value)}>
                        {priceTableSnapshots.map((snapshot) => (
                          <option key={snapshot.id} value={snapshot.id}>{snapshot.label}</option>
                        ))}
                      </select>
                    </label>
                    <button className="button compact secondary" onClick={handleCompareSnapshots}>Compare snapshots</button>
                  </div>
                )}
                {priceTableComparison && (
                  <div className="overflow-x-auto">
                    <table>
                      <thead>
                        <tr>
                          <th>Product</th>
                          <th>SKU</th>
                          <th>Type</th>
                          <th>Base</th>
                          <th>Target</th>
                          <th>Delta</th>
                          <th>Delta rate</th>
                          <th>Margin delta</th>
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
                    <Notes notes={priceTableComparison.comparison_notes} />
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
                        <td>{request.validation_status}</td>
                        <td>{request.risk_level}</td>
                        <td>{request.status}</td>
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
                  <Notes notes={results.explanation.explanation_bullets} />
                  <Notes title="Decision boundaries" notes={results.explanation.decision_boundaries} />
                  <Badge>source: {results.explanation.explanation_source}</Badge>
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
                        <option key={status} value={status}>{status}</option>
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
                          <td>{request.status}</td>
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
                    ["products", "Products"],
                    ["cost-profiles", "Cost profiles"],
                    ["competitor-prices", "Competitor prices"],
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
                      <Badge>{csvImportResult.entity_type}</Badge>
                      <Badge>received: {csvImportResult.received_rows}</Badge>
                      <Badge>created: {csvImportResult.created_rows}</Badge>
                      <Badge>updated: {csvImportResult.updated_rows}</Badge>
                      <Badge>failed: {csvImportResult.failed_rows}</Badge>
                    </div>
                    <Notes notes={csvImportResult.notes} />
                    <Notes title="Import errors" notes={csvImportResult.errors?.map((item) => `row ${item.row_number}: ${item.message}`)} />
                  </div>
                )}
              </Panel>
            )}

            {showSection("simulations", "admin-system") && currentUser && (
              <Panel title="작업 상태">
                <div className="grid gap-3 md:grid-cols-2">
                  <label className="field">
                    <span>Job type</span>
                    <select value={workflowJobForm.job_type} onChange={(event) => setWorkflowJobForm((current) => ({ ...current, job_type: event.target.value }))}>
                      {["pricing_simulation", "price_validation_batch", "quote_request_review"].map((jobType) => (
                        <option key={jobType} value={jobType}>{jobType}</option>
                      ))}
                    </select>
                  </label>
                  <label className="field">
                    <span>Title</span>
                    <input value={workflowJobForm.title} onChange={(event) => setWorkflowJobForm((current) => ({ ...current, title: event.target.value }))} />
                  </label>
                  <label className="field">
                    <span>Description</span>
                    <input value={workflowJobForm.description} onChange={(event) => setWorkflowJobForm((current) => ({ ...current, description: event.target.value }))} />
                  </label>
                </div>
                <label className="field">
                  <span>Input JSON</span>
                  <textarea rows="8" value={workflowJobForm.input} onChange={(event) => setWorkflowJobForm((current) => ({ ...current, input: event.target.value }))} />
                </label>
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
                        <th>Type</th>
                        <th>Title</th>
                        <th>Status</th>
                        <th>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {workflowJobs.length === 0 && (
                        <tr><td colSpan="5"><EmptyState title="시스템 운영 정보가 없습니다." message="작업을 생성하면 상태를 확인할 수 있습니다." /></td></tr>
                      )}
                      {workflowJobs.map((job) => (
                        <tr key={job.id}>
                          <td>{job.id}</td>
                          <td>{job.job_type}</td>
                          <td>{job.title}</td>
                          <td>{job.status}</td>
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
                  <pre className="overflow-x-auto rounded-md bg-slate-950 p-4 text-sm text-white">{JSON.stringify(activeWorkflowJob.result || { error: activeWorkflowJob.error_message, status: activeWorkflowJob.status }, null, 2)}</pre>
                )}
              </Panel>
            )}

            {showSection("approvals", "admin-system") && currentUser && ["admin", "manager"].includes(currentUser.role) && (
              <Panel title="Audit Logs">
                <ActionButton onClick={() => refreshAuditLogs()}>Refresh audit logs</ActionButton>
                <div className="overflow-x-auto">
                  <table>
                    <thead>
                      <tr>
                        <th>Action</th>
                        <th>Actor</th>
                        <th>Entity</th>
                        <th>Summary</th>
                        <th>Created</th>
                      </tr>
                    </thead>
                    <tbody>
                      {auditLogs.length === 0 && (
                        <tr><td colSpan="5"><EmptyState title="No audit logs loaded" message="Refresh audit logs after running an authenticated workflow." /></td></tr>
                      )}
                      {auditLogs.map((log) => (
                        <tr key={log.id}>
                          <td>{log.action}</td>
                          <td>{log.actor_username}</td>
                          <td>{log.entity_type}</td>
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

function LoadingState({ message = "Loading workspace data..." }) {
  return (
    <div className="card mb-5 rounded-md border border-slate-200 bg-white p-4 text-sm text-slate-600">
      <p className="font-semibold text-slate-800">Loading</p>
      <p className="mt-1">{message}</p>
    </div>
  )
}

function RetryButton({ onRetry }) {
  if (!onRetry) return null
  return <button className="button compact secondary" onClick={onRetry}>Retry</button>
}

function ErrorState({ title = "Could not load data", message, status, onRetry }) {
  return (
    <div className="error-state mb-5 rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-semibold">{title}</p>
          <p className="mt-1">{message || "Check whether the backend is running and try again."}</p>
          {status && <p className="mt-1 text-xs text-red-600">Status: {status}</p>}
          <p className="mt-2 text-xs text-red-600">Troubleshooting: refresh this section or verify the backend process is available.</p>
        </div>
        <RetryButton onRetry={onRetry} />
      </div>
    </div>
  )
}

function EmptyState({ title = "Nothing here yet", message, action }) {
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
      <p className="font-semibold">Check the form</p>
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
            <p className="text-xs text-slate-500">{field}</p>
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

function Notes({ title = "Notes", notes }) {
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
      <p className="font-semibold">Competitor context: {context.available ? "available" : "none"}</p>
      <p>count: {context.reference_price_count}</p>
      <p>avg: {formatMoney(context.average_reference_price)}</p>
    </div>
  )
}

export default App
