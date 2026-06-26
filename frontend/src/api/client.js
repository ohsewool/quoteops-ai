import axios from "axios"

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
})

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
