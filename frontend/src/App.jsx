import { useEffect, useMemo, useState } from "react"
import {
  approveApprovalRequest,
  comparePriceTableSnapshots,
  comparePriceTables,
  cancelWorkflowJob,
  createApprovalRequest,
  createCandidatePrices,
  createCustomerQuoteCandidates,
  createCustomerQuotePreview,
  createCustomerQuoteRequest,
  createPricingSimulation,
  createQuoteExplanation,
  createQuotePreview,
  createPriceTableSnapshot,
  createWorkflowJob,
  createStrategyTemplate,
  createStrategyTemplateCandidates,
  createStrategyTemplateSimulation,
  disableStrategyTemplate,
  downloadCsv,
  getAuditLogs,
  getApprovalRequests,
  getCurrentUser,
  getCustomerQuoteRequests,
  getDemoUsers,
  getHealth,
  getProducts,
  getPriceTables,
  getPriceTableSnapshots,
  getPriceTableSummary,
  getPricingSimulations,
  getStrategyTemplates,
  getSystemStatus,
  getWorkflowJobs,
  importCsv,
  login,
  rejectApprovalRequest,
  runWorkflowJob,
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

function App() {
  const [health, setHealth] = useState(null)
  const [systemStatus, setSystemStatus] = useState(null)
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
  const [demoUsers, setDemoUsers] = useState([])
  const [auditLogs, setAuditLogs] = useState([])
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
          getPricingSimulations().then(setPricingSimulations).catch(() => {})
          getStrategyTemplates().then((templates) => {
            setStrategyTemplates(templates)
            if (templates.length > 0) setSelectedStrategyTemplateId(String(templates[0].id))
          }).catch(() => {})
          getCustomerQuoteRequests().then(setCustomerQuoteRequests).catch(() => {})
          getWorkflowJobs().then(setWorkflowJobs).catch(() => {})
        })
        .catch(() => handleLogout())
    }
    loadInitialData()
  }, [])

  async function runAction(label, action) {
    setLoading(label)
    setError("")
    try {
      await action()
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "API request failed")
    } finally {
      setLoading("")
    }
  }

  async function loadInitialData() {
    await runAction("Loading initial data", async () => {
      const [healthData, statusData, productData, approvalData, demoUserData, priceTableData] = await Promise.all([
        getHealth(),
        getSystemStatus(),
        getProducts(),
        getApprovalRequests(),
        getDemoUsers(),
        getPriceTables(),
      ])
      setHealth(healthData)
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
      setPricingSimulations(await getPricingSimulations())
      const templates = await getStrategyTemplates()
      setStrategyTemplates(templates)
      if (templates.length > 0) setSelectedStrategyTemplateId(String(templates[0].id))
      setCustomerQuoteRequests(await getCustomerQuoteRequests())
      setWorkflowJobs(await getWorkflowJobs())
    })
  }

  function handleLogout() {
    localStorage.removeItem("quoteops_token")
    setAccessToken("")
    setCurrentUser(null)
    setAuditLogs([])
    setPricingSimulations([])
    setActiveSimulation(null)
    setStrategyTemplates([])
    setSelectedStrategyTemplateId("")
    setStrategyTemplateCandidates(null)
    setStrategyTemplateSimulation(null)
    setCustomerQuoteRequests([])
    setWorkflowJobs([])
    setActiveWorkflowJob(null)
  }

  async function refreshAuditLogs(user = currentUser) {
    if (!user || !["admin", "manager"].includes(user.role)) {
      setAuditLogs([])
      return
    }
    setAuditLogs(await getAuditLogs({ limit: 10 }))
  }

  async function handleCsvImport(entity) {
    if (!csvFiles[entity]) {
      setError("Choose a CSV file first.")
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
    await runAction("Creating strategy template", async () => {
      const template = await createStrategyTemplate(strategyTemplatePayload())
      await refreshStrategyTemplates()
      setSelectedStrategyTemplateId(String(template.id))
      await refreshAuditLogs()
    })
  }

  async function handleUpdateStrategyTemplate() {
    await runAction("Updating strategy template", async () => {
      const template = await updateStrategyTemplate(selectedStrategyTemplateId, strategyTemplatePayload())
      await refreshStrategyTemplates()
      setSelectedStrategyTemplateId(String(template.id))
      await refreshAuditLogs()
    })
  }

  async function handleDisableStrategyTemplate() {
    await runAction("Disabling strategy template", async () => {
      await disableStrategyTemplate(selectedStrategyTemplateId)
      await refreshStrategyTemplates()
      await refreshAuditLogs()
    })
  }

  async function handleStrategyTemplateCandidates() {
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

  async function refreshCustomerQuoteRequests() {
    if (!currentUser) return
    setCustomerQuoteRequests(await getCustomerQuoteRequests())
  }

  async function handleCreateCustomerQuoteRequest() {
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
    await runAction("Loading price table summary", async () => {
      const summary = await getPriceTableSummary(selectedPriceTableId)
      setPriceTableSummary(summary)
      setPriceTableSnapshots(await getPriceTableSnapshots(selectedPriceTableId))
      await refreshAuditLogs()
    })
  }

  async function handleCreateSnapshot() {
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

  return (
    <main className="min-h-screen bg-slate-100 text-slate-950">
      <div className="mx-auto max-w-7xl px-5 py-6">
        <header className="mb-6 flex flex-col gap-3 border-b border-slate-200 pb-5 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-sm font-semibold text-slate-500">QuoteOps AI</p>
            <h1 className="text-3xl font-semibold tracking-tight">Admin API workspace</h1>
          </div>
          <button className="button secondary" onClick={loadInitialData} disabled={!!loading}>
            Refresh
          </button>
        </header>

        {error && <div className="mb-5 rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>}
        {loading && <div className="mb-5 rounded-md border border-slate-200 bg-white p-4 text-sm text-slate-600">{loading}...</div>}

        <section className="mb-5 grid gap-4 lg:grid-cols-[1fr_1.4fr]">
          <Panel title="Admin login">
            {currentUser ? (
              <div className="space-y-3">
                <div className="flex flex-wrap gap-2">
                  <Badge>{currentUser.display_name}</Badge>
                  <Badge>role: {currentUser.role}</Badge>
                </div>
                <button className="button secondary" onClick={handleLogout}>Log out</button>
              </div>
            ) : (
              <form className="grid gap-3 md:grid-cols-[1fr_1fr_auto]" onSubmit={handleLogin}>
                <label className="field">
                  <span>Username</span>
                  <input value={loginForm.username} onChange={(event) => setLoginForm((current) => ({ ...current, username: event.target.value }))} />
                </label>
                <label className="field">
                  <span>Password</span>
                  <input type="password" value={loginForm.password} onChange={(event) => setLoginForm((current) => ({ ...current, password: event.target.value }))} />
                </label>
                <button className="button" type="submit">Log in</button>
              </form>
            )}
            <div className="flex flex-wrap gap-2">
              {demoUsers.map((user) => (
                <button className="button compact secondary" key={user.username} onClick={() => useDemoUser(user.username)}>
                  Use {user.username}
                </button>
              ))}
            </div>
            <p className="text-sm text-slate-500">Demo credentials are for local MVP testing only.</p>
          </Panel>

          <section className="grid gap-4 lg:grid-cols-4">
            <StatusCard label="Health" value={health?.status || "-"} />
            <StatusCard label="Database" value={systemStatus?.database_configured ? "configured" : "-"} />
            <StatusCard label="DB type" value={systemStatus?.database_type || "-"} />
            <StatusCard label="OpenAI" value={systemStatus?.openai_configured ? "configured" : "not configured"} />
          </section>
        </section>

        <section className="grid gap-5 lg:grid-cols-[360px_1fr]">
          <Panel title="Product and inputs">
            <label className="field">
              <span>Product</span>
              <select value={selectedProductId} onChange={(event) => setSelectedProductId(event.target.value)}>
                {products.map((product) => (
                  <option key={product.id} value={product.id}>{product.name}</option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Quantity</span>
              <input type="number" min="1" value={quantity} onChange={(event) => setQuantity(event.target.value)} />
            </label>
            <label className="field">
              <span>Proposed unit price</span>
              <input type="number" min="1" value={proposedUnitPrice} onChange={(event) => setProposedUnitPrice(event.target.value)} />
            </label>
            <div className="grid gap-3 sm:grid-cols-2">
              {Object.keys(optionalCosts).map((key) => (
                <label className="field" key={key}>
                  <span>{key}</span>
                  <input value={optionalCosts[key]} onChange={(event) => setOptionalCosts((current) => ({ ...current, [key]: event.target.value }))} />
                </label>
              ))}
            </div>
            <label className="field">
              <span>Candidate margin rates</span>
              <input value={marginRates} onChange={(event) => setMarginRates(event.target.value)} />
            </label>
            <label className="checkbox">
              <input type="checkbox" checked={includeCompetitors} onChange={(event) => setIncludeCompetitors(event.target.checked)} />
              Include competitor context
            </label>
            <p className="text-sm text-slate-500">Selected: {selectedProduct?.name || "No product"}</p>
          </Panel>

          <div className="grid gap-5">
            <Panel title="Quote preview">
              <ActionButton onClick={handleQuotePreview}>Create quote preview</ActionButton>
              <MetricGrid data={results.quotePreview} fields={["unit_cost", "total_cost", "suggested_unit_price", "suggested_total_price", "estimated_gross_profit", "estimated_margin_rate"]} />
              <Notes notes={results.quotePreview?.calculation_notes} />
            </Panel>

            <Panel title="Candidate prices">
              <ActionButton onClick={handleCandidates}>Generate candidate prices</ActionButton>
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

            <Panel title="Price validation">
              <ActionButton onClick={handleValidation}>Validate proposed price</ActionButton>
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

            {currentUser && (
              <Panel title="Pricing simulation">
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
                  <ActionButton onClick={handlePricingSimulation}>Run simulation</ActionButton>
                )}
                {activeSimulation && (
                  <div className="space-y-3">
                    <div className="flex flex-wrap gap-2">
                      <Badge>{activeSimulation.name}</Badge>
                      <Badge>scenarios: {activeSimulation.scenario_count}</Badge>
                      <Badge>unit cost: {formatMoney(activeSimulation.unit_cost)}</Badge>
                    </div>
                    <div className="overflow-x-auto">
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

            {currentUser && (
              <Panel title="Strategy templates">
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
                        <tr><td colSpan="7">No strategy templates.</td></tr>
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

            {currentUser && (
              <Panel title="Price table history and comparison">
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

            <Panel title="Approval workflow">
              <div className="grid gap-3 md:grid-cols-[1fr_1fr_auto]">
                <label className="field">
                  <span>Reviewer</span>
                  <input value={reviewerName} onChange={(event) => setReviewerName(event.target.value)} />
                </label>
                <label className="field">
                  <span>Review note</span>
                  <input value={reviewNote} onChange={(event) => setReviewNote(event.target.value)} />
                </label>
                <ActionButton onClick={handleCreateApproval}>Create approval request</ActionButton>
              </div>
              <div className="overflow-x-auto">
                <table>
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Product</th>
                      <th>Unit price</th>
                      <th>Validation</th>
                      <th>Risk</th>
                      <th>Status</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {approvalRequests.length === 0 && (
                      <tr><td colSpan="7">No approval requests.</td></tr>
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
                              <button className="button compact" onClick={() => handleReviewApproval(request.id, "approve")}>Approve</button>
                              <button className="button compact secondary" onClick={() => handleReviewApproval(request.id, "reject")}>Reject</button>
                            </div>
                          ) : request.review_note || "-"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Panel>

            <Panel title="Explanation">
              <ActionButton onClick={handleExplanation}>Generate explanation</ActionButton>
              {results.explanation && (
                <div className="space-y-3">
                  <p className="rounded-md bg-slate-950 p-4 text-white">{results.explanation.explanation_summary}</p>
                  <Notes notes={results.explanation.explanation_bullets} />
                  <Notes title="Decision boundaries" notes={results.explanation.decision_boundaries} />
                  <Badge>source: {results.explanation.explanation_source}</Badge>
                </div>
              )}
            </Panel>

            {currentUser && (
              <Panel title="Customer quote requests">
                <div className="grid gap-3 md:grid-cols-2">
                  {["customer_name", "customer_email", "customer_company", "quantity", "request_note"].map((field) => (
                    <label className="field" key={field}>
                      <span>{field}</span>
                      <input value={customerQuoteForm[field]} onChange={(event) => setCustomerQuoteForm((current) => ({ ...current, [field]: event.target.value }))} />
                    </label>
                  ))}
                </div>
                <ActionButton onClick={handleCreateCustomerQuoteRequest}>Submit quote request</ActionButton>
                <div className="grid gap-3 md:grid-cols-[1fr_auto]">
                  <label className="field">
                    <span>Status update</span>
                    <select value={quoteRequestStatus} onChange={(event) => setQuoteRequestStatus(event.target.value)}>
                      {["new", "reviewing", "quoted", "closed"].map((status) => (
                        <option key={status} value={status}>{status}</option>
                      ))}
                    </select>
                  </label>
                  <ActionButton onClick={refreshCustomerQuoteRequests}>Refresh requests</ActionButton>
                </div>
                <div className="overflow-x-auto">
                  <table>
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>Customer</th>
                        <th>Product</th>
                        <th>Qty</th>
                        <th>Status</th>
                        <th>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {customerQuoteRequests.length === 0 && (
                        <tr><td colSpan="6">No customer quote requests.</td></tr>
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
                                  <button className="button compact" onClick={() => handleCustomerQuoteStatus(request.id)}>Set status</button>
                                  <button className="button compact secondary" onClick={() => handleCustomerQuotePreview(request.id)}>Preview</button>
                                  <button className="button compact secondary" onClick={() => handleCustomerQuoteCandidates(request.id)}>Candidates</button>
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

            {currentUser && (
              <Panel title="CSV import and export">
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
                          <button className="button compact" onClick={() => handleCsvImport(entity)}>Import</button>
                        )}
                        <button className="button compact secondary" onClick={() => handleCsvExport(entity, `${entity}.csv`)}>Export</button>
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

            {currentUser && (
              <Panel title="Workflow jobs">
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
                    <button className="button compact" onClick={handleCreateWorkflowJob}>Create job</button>
                  )}
                  <button className="button compact secondary" onClick={refreshWorkflowJobs}>Refresh jobs</button>
                </div>
                <div className="overflow-x-auto">
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
                        <tr><td colSpan="5">No workflow jobs.</td></tr>
                      )}
                      {workflowJobs.map((job) => (
                        <tr key={job.id}>
                          <td>{job.id}</td>
                          <td>{job.job_type}</td>
                          <td>{job.title}</td>
                          <td>{job.status}</td>
                          <td>
                            <div className="flex flex-wrap gap-2">
                              <button className="button compact secondary" onClick={() => setActiveWorkflowJob(job)}>View</button>
                              {job.status === "pending" && ["admin", "manager"].includes(currentUser.role) && (
                                <>
                                  <button className="button compact" onClick={() => handleRunWorkflowJob(job.id)}>Run</button>
                                  <button className="button compact secondary" onClick={() => handleCancelWorkflowJob(job.id)}>Cancel</button>
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

            {currentUser && ["admin", "manager"].includes(currentUser.role) && (
              <Panel title="Audit logs">
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
                        <tr><td colSpan="5">No audit logs loaded.</td></tr>
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
        </section>
      </div>
    </main>
  )
}

function StatusCard({ label, value }) {
  return (
    <div className="rounded-md border border-slate-200 bg-white p-4">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-1 font-semibold">{value}</p>
    </div>
  )
}

function Panel({ title, children }) {
  return (
    <section className="rounded-md border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="mb-4 text-lg font-semibold">{title}</h2>
      <div className="space-y-4">{children}</div>
    </section>
  )
}

function ActionButton({ children, onClick }) {
  return <button className="button" onClick={onClick}>{children}</button>
}

function Badge({ children }) {
  return <span className="rounded-full bg-slate-100 px-3 py-1 text-sm text-slate-700">{children}</span>
}

function MetricGrid({ data, fields }) {
  if (!data) return <p className="empty">No result yet.</p>
  return (
    <div className="grid gap-3 md:grid-cols-3">
      {fields.map((field) => (
        <div className="rounded-md bg-slate-50 p-3" key={field}>
          <p className="text-xs text-slate-500">{field}</p>
          <p className="font-semibold">{formatMoney(data[field])}</p>
        </div>
      ))}
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
