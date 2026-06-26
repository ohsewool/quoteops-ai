import { expect, test } from "@playwright/test"

const stickerOption = "50mm circle / standard paper / matte coating"

async function loginAsDemoOwner(page) {
  await page.goto("/")
  await expect(page.getByTestId("login-card")).toBeVisible()
  await expect(
    page.getByTestId("login-card").getByText("관리자 계정으로 로그인해야 가격표를 승인하거나 변경할 수 있습니다."),
  ).toBeVisible()
  await page.getByRole("button", { name: "로그인" }).click()
  await expect(page.getByTestId("workspace-overview")).toBeVisible()
}

test("landing page and workspace sections render", async ({ page }) => {
  await loginAsDemoOwner(page)

  await expect(page.getByTestId("quoteops-app")).toBeVisible()
  await expect(page.getByRole("heading", { name: /AI는 계산 결과를 설명하고/ })).toBeVisible()
  await expect(page.getByText("AI는 가격 숫자를 생성하지 않습니다.")).toBeVisible()
  await expect(page.getByText("가격은 백엔드 계산식으로 산출됩니다.")).toBeVisible()
  await expect(page.getByText("경쟁사 가격은 참고 데이터입니다.", { exact: true })).toBeVisible()
  await expect(page.getByText("최저가를 무조건 따라가지 않습니다.", { exact: true })).toBeVisible()
  await expect(page.locator("span", { hasText: "승인된 가격표만 실제 견적에 사용됩니다." })).toBeVisible()

  await expect(page.getByTestId("workspace-overview")).toBeVisible()
  await expect(page.getByTestId("system-status-panel")).toBeVisible()
  await expect(page.getByTestId("system-status-panel")).toContainText("System Status")
  await expect(page.getByTestId("product-count")).not.toHaveText("0")
  await expect(page.getByTestId("workspace-overview")).toContainText("A3 Flyer")
  await expect(page.getByTestId("workspace-overview")).toContainText("Product Sticker")
  await expect(page.getByTestId("market-reference-card")).toContainText("경쟁사 참고 데이터")
  await expect(page.getByTestId("cost-margin-card")).toContainText("원가·마진 설정")
  await expect(page.getByTestId("quote-preview-card")).toContainText("결정론적 견적")
  await expect(page.getByTestId("quote-preview-price")).not.toHaveText("-")
  await expect(page.getByRole("heading", { name: "후보 가격표 생성" })).toBeVisible()
  await expect(page.getByRole("heading", { name: "백엔드 실행 로그" })).toBeVisible()
  await expect(page.getByText("관리자 승인 패널")).toBeVisible()
})

test("UI workflow generates, validates, explains, and shows approval controls", async ({ page }) => {
  await loginAsDemoOwner(page)

  await page.getByRole("button", { name: "후보 생성" }).click()
  await expect(page.getByText("후보 가격표가 generated 상태로 저장되었습니다")).toBeVisible()
  await expect(page.getByRole("heading", { name: "후보 가격", exact: true })).toBeVisible()

  await page.getByRole("button", { name: "후보 검증" }).click()
  await expect(page.getByText("검증 결과", { exact: true })).toBeVisible()
  await expect(page.locator("span", { hasText: /pass|pass_with_warnings/ }).first()).toBeVisible()

  await page.getByRole("button", { name: "AI 설명 생성" }).click()
  await expect(page.getByText("AI 설명 패널", { exact: true })).toBeVisible()
  await expect(page.locator("span", { hasText: /fallback|openai/ }).first()).toBeVisible()
  await expect(page.getByText("OPENAI_API_KEY is not configured")).toBeVisible()

  await expect(page.getByLabel("검토 메모")).toBeVisible()
  await expect(page.getByRole("button", { name: "승인하고 활성화" })).toBeVisible()
  await expect(page.getByRole("button", { name: "거절" })).toBeVisible()
  await expect(page.getByText("승인 이력")).toBeVisible()
  await expect(page.getByText("백엔드 실행 로그")).toBeVisible()
})

test("backend workflow approves a candidate and quote preview uses it", async ({ request }) => {
  const login = await request.post("http://127.0.0.1:8000/api/auth/login", {
    data: {
      email: "admin@quoteops.local",
      password: "quoteops-demo-admin",
    },
  })
  expect(login.ok()).toBeTruthy()
  const token = (await login.json()).access_token

  const generated = await request.post("http://127.0.0.1:8000/api/candidate-prices/generate", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    data: {
      product_slug: "product-sticker",
      option_summary: stickerOption,
      quantities: [100, 500],
      strategy_name: "balanced_market",
    },
  })
  expect(generated.ok()).toBeTruthy()
  const generatedBody = await generated.json()
  const candidateId = generatedBody.candidate_table_id
  const expectedPrice = generatedBody.items.find((item) => item.quantity === 100).candidate_price

  const validation = await request.post(`http://127.0.0.1:8000/api/candidate-prices/${candidateId}/validate`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
  expect(validation.ok()).toBeTruthy()
  const validationBody = await validation.json()
  expect(["pass", "pass_with_warnings"]).toContain(validationBody.overall_status)

  const explanation = await request.post(`http://127.0.0.1:8000/api/candidate-prices/${candidateId}/explain`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
  expect(explanation.ok()).toBeTruthy()
  const explanationBody = await explanation.json()
  expect(explanationBody.source).toBe("fallback")

  const approval = await request.post(`http://127.0.0.1:8000/api/candidate-prices/${candidateId}/approve`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    data: {
      reviewer_note: "End-to-end workflow approval.",
    },
  })
  expect(approval.ok()).toBeTruthy()
  const approvalBody = await approval.json()
  expect(approvalBody.created_price_table_id).toBeGreaterThan(0)

  const quote = await request.post("http://127.0.0.1:8000/api/quotes/preview", {
    data: {
      product_slug: "product-sticker",
      quantity: 100,
      option_summary: stickerOption,
    },
  })
  expect(quote.ok()).toBeTruthy()
  const quoteBody = await quote.json()
  expect(quoteBody.calculation_source).toBe("active_price_table")
  expect(quoteBody.price_table_name).toContain("Approved candidate")
  expect(quoteBody.quote_price).toBe(expectedPrice)

  const logs = await request.get(`http://127.0.0.1:8000/api/agent-logs?candidate_table_id=${candidateId}`)
  expect(logs.ok()).toBeTruthy()
  const stepTypes = (await logs.json()).map((log) => log.step_type)
  expect(stepTypes).toContain("candidate_generated")
  expect(stepTypes).toContain("validation_run")
  expect(stepTypes).toContain("ai_explanation_generated")
  expect(stepTypes).toContain("candidate_approved")
  expect(stepTypes).toContain("price_table_activated")
})
