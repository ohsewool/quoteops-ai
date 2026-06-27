import axios from "axios"

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
})

export function setAccessToken(token) {
  if (token) {
    api.defaults.headers.common.Authorization = `Bearer ${token}`
  } else {
    delete api.defaults.headers.common.Authorization
  }
}

export async function login(payload) {
  const { data } = await api.post("/api/auth/login", payload)
  return data
}

export async function getCurrentUser() {
  const { data } = await api.get("/api/auth/me")
  return data
}

export async function getDemoUsers() {
  const { data } = await api.get("/api/auth/demo-users")
  return data
}

export async function getAuditLogs(params = {}) {
  const { data } = await api.get("/api/audit-logs", { params })
  return data
}

export async function importCsv(entity, file) {
  const formData = new FormData()
  formData.append("file", file)
  const { data } = await api.post(`/api/import/${entity}`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  })
  return data
}

export async function downloadCsv(entity, filename) {
  const { data } = await api.get(`/api/export/${entity}.csv`, { responseType: "blob" })
  const url = window.URL.createObjectURL(data)
  const link = document.createElement("a")
  link.href = url
  link.download = filename
  link.click()
  window.URL.revokeObjectURL(url)
}

export async function getHealth() {
  const { data } = await api.get("/api/health")
  return data
}

export async function getSystemStatus() {
  const { data } = await api.get("/api/system/status")
  return data
}

export async function getProducts() {
  const { data } = await api.get("/api/products")
  return data
}

export async function getPriceTables() {
  const { data } = await api.get("/api/price-tables")
  return data
}

export async function getPriceTableSummary(id) {
  const { data } = await api.get(`/api/price-tables/${id}/summary`)
  return data
}

export async function createPriceTableSnapshot(id, payload) {
  const { data } = await api.post(`/api/price-tables/${id}/snapshots`, payload)
  return data
}

export async function getPriceTableSnapshots(id) {
  const { data } = await api.get(`/api/price-tables/${id}/snapshots`)
  return data
}

export async function comparePriceTables(payload) {
  const { data } = await api.post("/api/price-tables/compare", payload)
  return data
}

export async function comparePriceTableSnapshots(payload) {
  const { data } = await api.post("/api/price-table-snapshots/compare", payload)
  return data
}

export async function createWorkflowJob(payload) {
  const { data } = await api.post("/api/workflow-jobs", payload)
  return data
}

export async function getWorkflowJobs(params = {}) {
  const { data } = await api.get("/api/workflow-jobs", { params })
  return data
}

export async function runWorkflowJob(id) {
  const { data } = await api.post(`/api/workflow-jobs/${id}/run`)
  return data
}

export async function cancelWorkflowJob(id) {
  const { data } = await api.post(`/api/workflow-jobs/${id}/cancel`)
  return data
}

export async function createQuotePreview(payload) {
  const { data } = await api.post("/api/quote-preview", payload)
  return data
}

export async function createCandidatePrices(payload) {
  const { data } = await api.post("/api/candidate-prices", payload)
  return data
}

export async function validatePrice(payload) {
  const { data } = await api.post("/api/price-validation", payload)
  return data
}

export async function createPricingSimulation(payload) {
  const { data } = await api.post("/api/pricing-simulations", payload)
  return data
}

export async function getPricingSimulations() {
  const { data } = await api.get("/api/pricing-simulations")
  return data
}

export async function createCustomerQuoteRequest(payload) {
  const { data } = await api.post("/api/customer-quote-requests", payload)
  return data
}

export async function getCustomerQuoteRequests() {
  const { data } = await api.get("/api/customer-quote-requests")
  return data
}

export async function updateCustomerQuoteRequestStatus(id, payload) {
  const { data } = await api.post(`/api/customer-quote-requests/${id}/status`, payload)
  return data
}

export async function createCustomerQuotePreview(id) {
  const { data } = await api.post(`/api/customer-quote-requests/${id}/quote-preview`)
  return data
}

export async function createCustomerQuoteCandidates(id, payload) {
  const { data } = await api.post(`/api/customer-quote-requests/${id}/candidate-prices`, payload)
  return data
}

export async function createApprovalRequest(payload) {
  const { data } = await api.post("/api/approval-requests", payload)
  return data
}

export async function getApprovalRequests() {
  const { data } = await api.get("/api/approval-requests")
  return data
}

export async function approveApprovalRequest(id, payload) {
  const { data } = await api.post(`/api/approval-requests/${id}/approve`, payload)
  return data
}

export async function rejectApprovalRequest(id, payload) {
  const { data } = await api.post(`/api/approval-requests/${id}/reject`, payload)
  return data
}

export async function createQuoteExplanation(payload) {
  const { data } = await api.post("/api/explanations/quote", payload)
  return data
}
