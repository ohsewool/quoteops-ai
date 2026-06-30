from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from backend.models import (
    Competitor,
    CompetitorPrice,
    CostProfile,
    CustomerQuoteRequest,
    HtmlReport,
    PriceApprovalRequest,
    PriceTable,
    PriceTableItem,
    PricingSimulation,
    PricingSimulationScenario,
    PricingStrategyTemplate,
    Product,
    ScenarioComparison,
    ScenarioComparisonItem,
    WorkflowJob,
)
from backend.schemas import (
    ApprovalRequestCreate,
    CandidatePriceRequest,
    CustomerQuoteRequestCreate,
    DemoFullScenarioResponse,
    DemoGuideResponse,
    DemoResetResponse,
    DemoScenarioStep,
    DemoSeedResponse,
    DemoStatusResponse,
    HtmlReportCreate,
    PriceValidationRequest,
    PricingSimulationCreate,
    QuotePreviewRequest,
    ScenarioComparisonCreate,
    ScenarioComparisonScenarioInput,
    WorkflowJobCreate,
)
from backend.services.approval_service import create_approval_request
from backend.services.candidate_price_service import generate_candidate_prices
from backend.services.customer_quote_request_service import create_customer_quote_request
from backend.services.dashboard_service import get_dashboard_metrics
from backend.services.html_report_service import create_html_report
from backend.services.pricing_simulation_service import create_pricing_simulation
from backend.services.quote_preview_service import calculate_quote_preview
from backend.services.scenario_comparison_service import create_scenario_comparison
from backend.services.validation_service import validate_price
from backend.services.workflow_job_service import create_workflow_job


DEMO_PRODUCT_DATA = [
    {
        "sku": "DEMO-BANNER-001",
        "name": "QuoteOps Demo Banner",
        "category": "Large Format Print",
        "description": "QuoteOps Demo product for local presentation only.",
        "cost": (4200.0, 1800.0, 900.0, 0.35),
    },
    {
        "sku": "DEMO-STICKER-001",
        "name": "QuoteOps Demo Sticker",
        "category": "Product / Brand Sticker",
        "description": "QuoteOps Demo sticker product for deterministic pricing demos.",
        "cost": (420.0, 230.0, 120.0, 0.35),
    },
    {
        "sku": "DEMO-TUMBLER-001",
        "name": "QuoteOps Demo Tumbler",
        "category": "Custom Goods",
        "description": "QuoteOps Demo tumbler product for portfolio walkthroughs.",
        "cost": (5200.0, 2100.0, 800.0, 0.4),
    },
    {
        "sku": "DEMO-HOODIE-001",
        "name": "QuoteOps Demo Hoodie",
        "category": "Apparel",
        "description": "QuoteOps Demo hoodie product for safe scenario testing.",
        "cost": (14500.0, 4200.0, 1800.0, 0.42),
    },
    {
        "sku": "DEMO-PACKAGE-001",
        "name": "QuoteOps Demo Package Box",
        "category": "Packaging",
        "description": "QuoteOps Demo packaging product for deterministic comparisons.",
        "cost": (1900.0, 900.0, 350.0, 0.36),
    },
]
DEMO_PRODUCT_SKUS = [item["sku"] for item in DEMO_PRODUCT_DATA]
DEMO_COMPETITORS = [
    ("QuoteOps Demo Local Print Shop", "local_shop"),
    ("QuoteOps Demo Similar Studio", "similar_size"),
    ("QuoteOps Demo Premium Studio", "premium_shop"),
]
DEMO_PRICE_TABLE_NAME = "QuoteOps Demo Presentation Price Table"
DEMO_APPROVAL_NOTE = "QuoteOps Demo approval request. Human review required."
DEMO_SIMULATION_NAME = "QuoteOps Demo Pricing Simulation"
DEMO_COMPARISON_NAME = "QuoteOps Demo Scenario Comparison"
DEMO_REPORT_TITLE = "QuoteOps Demo Scenario Comparison Report"
DEMO_WORKFLOW_TITLE = "QuoteOps Demo Workflow Job"
DEMO_CUSTOMER_EMAIL = "quoteops-demo-customer@example.com"
DEMO_STRATEGY_CODES = {"standard_margin", "premium_margin", "conservative_bulk"}


def get_demo_status(db: Session) -> DemoStatusResponse:
    counts = _demo_counts(db)
    return DemoStatusResponse(
        demo_ready=counts["products"] >= len(DEMO_PRODUCT_SKUS)
        and counts["cost_profiles"] >= len(DEMO_PRODUCT_SKUS)
        and counts["competitors"] >= 3,
        counts=counts,
        demo_notes=[
            "Demo status is calculated from current database records.",
            "Demo tools are intended for local development and presentation scenarios.",
            "Competitor prices are manually entered demo references, not real market data.",
        ],
    )


def seed_demo_data_tools(db: Session, username: str) -> DemoSeedResponse:
    products = _ensure_demo_products(db)
    competitors = _ensure_demo_competitors(db)
    _ensure_demo_competitor_prices(db, products, competitors)
    price_table = _ensure_demo_price_table(db, products)
    customer_request = _ensure_customer_quote_request(db, products["DEMO-BANNER-001"])
    approval_request = _ensure_approval_request(db, products["DEMO-BANNER-001"])
    workflow_job = _ensure_workflow_job(db, products["DEMO-BANNER-001"], username)
    simulation = _ensure_pricing_simulation(db, products["DEMO-BANNER-001"], username)
    comparison = _ensure_scenario_comparison(db, products["DEMO-BANNER-001"], username)
    report = _ensure_html_report(db, comparison.id, username)
    db.commit()

    counts = _demo_counts(db)
    return DemoSeedResponse(
        seed_completed=True,
        created_or_verified={
            **counts,
            "presentation_price_table_id": price_table.id,
            "customer_quote_request_id": customer_request.id,
            "approval_request_id": approval_request.id,
            "workflow_job_id": workflow_job.id,
            "pricing_simulation_id": simulation.id,
            "scenario_comparison_id": comparison.id,
            "html_report_id": report.id,
        },
        demo_notes=[
            "Seed is idempotent and uses stable DEMO-/QuoteOps Demo identifiers.",
            "Demo prices are deterministic reference data only.",
            "No AI-generated price, approval, email, scraping, or activation was performed.",
        ],
    )


def reset_demo_data(db: Session) -> DemoResetResponse:
    deleted_or_disabled: dict[str, int] = {}

    deleted_or_disabled["html_reports"] = _delete_query(
        db, db.query(HtmlReport).filter(HtmlReport.title == DEMO_REPORT_TITLE)
    )
    demo_comparisons = db.query(ScenarioComparison).filter(
        ScenarioComparison.name == DEMO_COMPARISON_NAME
    )
    comparison_ids = [row.id for row in demo_comparisons.all()]
    if comparison_ids:
        _delete_query(
            db,
            db.query(ScenarioComparisonItem).filter(
                ScenarioComparisonItem.comparison_id.in_(comparison_ids)
            ),
        )
    deleted_or_disabled["scenario_comparisons"] = _delete_query(
        db, db.query(ScenarioComparison).filter(ScenarioComparison.id.in_(comparison_ids))
    )

    demo_simulations = db.query(PricingSimulation).filter(
        PricingSimulation.name == DEMO_SIMULATION_NAME
    )
    simulation_ids = [row.id for row in demo_simulations.all()]
    if simulation_ids:
        _delete_query(
            db,
            db.query(PricingSimulationScenario).filter(
                PricingSimulationScenario.simulation_id.in_(simulation_ids)
            ),
        )
    deleted_or_disabled["pricing_simulations"] = _delete_query(
        db, db.query(PricingSimulation).filter(PricingSimulation.id.in_(simulation_ids))
    )
    deleted_or_disabled["workflow_jobs"] = _delete_query(
        db, db.query(WorkflowJob).filter(WorkflowJob.title == DEMO_WORKFLOW_TITLE)
    )
    deleted_or_disabled["customer_quote_requests"] = _delete_query(
        db,
        db.query(CustomerQuoteRequest).filter(
            CustomerQuoteRequest.customer_email == DEMO_CUSTOMER_EMAIL
        ),
    )
    deleted_or_disabled["approval_requests"] = _delete_query(
        db,
        db.query(PriceApprovalRequest).filter(
            PriceApprovalRequest.submitted_note == DEMO_APPROVAL_NOTE
        ),
    )

    demo_table_ids = [
        row.id
        for row in db.query(PriceTable)
        .filter(PriceTable.name == DEMO_PRICE_TABLE_NAME)
        .all()
    ]
    if demo_table_ids:
        deleted_or_disabled["price_table_items"] = _delete_query(
            db,
            db.query(PriceTableItem).filter(PriceTableItem.price_table_id.in_(demo_table_ids)),
        )
    else:
        deleted_or_disabled["price_table_items"] = 0
    deleted_or_disabled["price_tables"] = _soft_disable_price_tables(db)
    deleted_or_disabled["competitor_prices"] = _delete_query(
        db,
        db.query(CompetitorPrice).filter(
            CompetitorPrice.source_note.like("QuoteOps Demo%")
        ),
    )
    deleted_or_disabled["cost_profiles"] = _soft_disable_cost_profiles(db)
    deleted_or_disabled["competitors"] = _soft_disable_competitors(db)
    deleted_or_disabled["products"] = _soft_disable_products(db)
    deleted_or_disabled["strategy_templates"] = _soft_disable_strategy_templates(db)
    db.commit()

    return DemoResetResponse(
        reset_completed=True,
        deleted_or_disabled=deleted_or_disabled,
        safety_notes=[
            "Only known deterministic demo records were deleted or soft-disabled.",
            "Unknown customer data, unknown users, audit logs, and environment values were not deleted.",
            "Demo products, competitors, price tables, cost profiles, and templates are soft-disabled when direct deletion could affect related records.",
        ],
    )


def create_full_demo_scenario(db: Session, username: str) -> DemoFullScenarioResponse:
    seed_demo_data_tools(db, username)
    product = _get_demo_product(db, "DEMO-BANNER-001")

    quote_preview = calculate_quote_preview(
        db, QuotePreviewRequest(product_id=product.id, quantity=50)
    )
    candidates = generate_candidate_prices(
        db,
        CandidatePriceRequest(
            product_id=product.id,
            quantity=50,
            margin_rates=[0.25, 0.35, 0.45],
            include_competitor_context=True,
        ),
    )
    validation = validate_price(
        db,
        PriceValidationRequest(
            product_id=product.id,
            quantity=50,
            candidate_unit_price=candidates.candidates[1].unit_price,
            include_competitor_context=True,
        ),
    )
    approval = _ensure_approval_request(db, product)
    customer_request = _ensure_customer_quote_request(db, product)
    workflow_job = _ensure_workflow_job(db, product, username)
    simulation = _ensure_pricing_simulation(db, product, username)
    comparison = _ensure_scenario_comparison(db, product, username)
    report = _ensure_html_report(db, comparison.id, username)
    get_dashboard_metrics(db)

    return DemoFullScenarioResponse(
        scenario_name="QuoteOps AI End-to-End Demo",
        ready=True,
        demo_product_sku=product.sku,
        generated_ids={
            "product_id": product.id,
            "approval_request_id": approval.id,
            "customer_quote_request_id": customer_request.id,
            "workflow_job_id": workflow_job.id,
            "pricing_simulation_id": simulation.id,
            "scenario_comparison_id": comparison.id,
            "html_report_id": report.id,
        },
        steps=_presentation_steps(),
        decision_boundaries=[
            "No AI-generated price was used.",
            "No AI approval decision was used.",
            "No price table was automatically activated.",
            "No websites were scraped and no emails were sent.",
        ],
        demo_notes=[
            f"Quote preview suggested unit price: {quote_preview.suggested_unit_price}",
            f"Candidate count: {len(candidates.candidates)}",
            f"Validation status: {validation.validation_status}",
            "Dashboard metrics are available from existing deterministic records.",
        ],
    )


def get_demo_guide() -> DemoGuideResponse:
    return DemoGuideResponse(
        demo_login_users=[
            {
                "username": "admin",
                "role": "admin",
                "password_hint": "local demo credential: admin-demo-password",
            },
            {
                "username": "manager",
                "role": "manager",
                "password_hint": "local demo credential: manager-demo-password",
            },
            {
                "username": "viewer",
                "role": "viewer",
                "password_hint": "local demo credential: viewer-demo-password",
            },
        ],
        recommended_demo_flow=_presentation_steps(),
        important_api_endpoints=[
            "GET /api/demo/status",
            "POST /api/demo/seed",
            "POST /api/demo/scenario/full",
            "POST /api/quote-preview",
            "POST /api/candidate-prices",
            "POST /api/price-validation",
            "POST /api/scenario-comparisons",
            "POST /api/html-reports",
        ],
        business_safety_boundaries=[
            "Demo tools are for local development and presentations.",
            "Demo competitor prices are manually entered references, not real market prices.",
            "Demo tools do not approve, reject, or activate production prices.",
            "Demo tools do not scrape websites, call external AI, or send emails.",
        ],
        frontend_show=[
            "Demo status counts",
            "Seed demo data action",
            "Full scenario presentation steps",
            "Scenario comparison summary",
            "HTML report availability",
            "Cautious admin-only reset action",
        ],
        what_not_to_claim=[
            "Do not claim demo competitor prices are real market data.",
            "Do not claim AI generated the numeric prices.",
            "Do not claim demo approvals are production approval decisions.",
            "Do not claim demo reset deletes arbitrary production data.",
        ],
        guide_notes=[
            "This guide intentionally shows only local demo credential hints.",
            "Password hashes, tokens, auth secrets, and environment values are never returned.",
        ],
    )


def _ensure_demo_products(db: Session) -> dict[str, Product]:
    products: dict[str, Product] = {}
    for item in DEMO_PRODUCT_DATA:
        product = db.query(Product).filter(Product.sku == item["sku"]).first()
        if product is None:
            product = Product(
                name=item["name"],
                sku=item["sku"],
                category=item["category"],
                description=item["description"],
                active=True,
            )
            db.add(product)
            db.flush()
        else:
            product.name = item["name"]
            product.category = item["category"]
            product.description = item["description"]
            product.active = True
        products[item["sku"]] = product
        _ensure_cost_profile(db, product, item["cost"])
    return products


def _ensure_cost_profile(
    db: Session, product: Product, cost: tuple[float, float, float, float]
) -> CostProfile:
    profile = (
        db.query(CostProfile)
        .filter(CostProfile.product_id == product.id)
        .order_by(CostProfile.id)
        .first()
    )
    material_cost, labor_cost, overhead_cost, target_margin_rate = cost
    if profile is None:
        profile = CostProfile(
            product_id=product.id,
            material_cost=material_cost,
            labor_cost=labor_cost,
            overhead_cost=overhead_cost,
            target_margin_rate=target_margin_rate,
            active=True,
        )
        db.add(profile)
        db.flush()
    else:
        profile.material_cost = material_cost
        profile.labor_cost = labor_cost
        profile.overhead_cost = overhead_cost
        profile.target_margin_rate = target_margin_rate
        profile.active = True
    return profile


def _ensure_demo_competitors(db: Session) -> dict[str, Competitor]:
    competitors: dict[str, Competitor] = {}
    for name, channel in DEMO_COMPETITORS:
        competitor = db.query(Competitor).filter(Competitor.name == name).first()
        if competitor is None:
            competitor = Competitor(
                name=name,
                channel=channel,
                notes="QuoteOps Demo reference only. Not real market data.",
                active=True,
            )
            db.add(competitor)
            db.flush()
        else:
            competitor.channel = channel
            competitor.notes = "QuoteOps Demo reference only. Not real market data."
            competitor.active = True
        competitors[name] = competitor
    return competitors


def _ensure_demo_competitor_prices(
    db: Session, products: dict[str, Product], competitors: dict[str, Competitor]
) -> None:
    for product_index, product in enumerate(products.values(), start=1):
        for competitor_index, competitor in enumerate(competitors.values(), start=1):
            reference_price = 9000.0 + product_index * 2750.0 + competitor_index * 950.0
            exists = (
                db.query(CompetitorPrice)
                .filter(
                    CompetitorPrice.product_id == product.id,
                    CompetitorPrice.competitor_id == competitor.id,
                    CompetitorPrice.source_note.like("QuoteOps Demo%"),
                )
                .first()
            )
            if exists is None:
                db.add(
                    CompetitorPrice(
                        product_id=product.id,
                        competitor_id=competitor.id,
                        reference_price=reference_price,
                        source_note="QuoteOps Demo manual reference only. Not real market data.",
                        observed_at=datetime(2026, 1, 1),
                    )
                )


def _ensure_demo_price_table(db: Session, products: dict[str, Product]) -> PriceTable:
    price_table = db.query(PriceTable).filter(PriceTable.name == DEMO_PRICE_TABLE_NAME).first()
    if price_table is None:
        price_table = PriceTable(
            name=DEMO_PRICE_TABLE_NAME,
            status="draft",
            description="QuoteOps Demo draft table. It is not automatically activated.",
        )
        db.add(price_table)
        db.flush()
    else:
        price_table.status = "draft"
        price_table.description = "QuoteOps Demo draft table. It is not automatically activated."
    for index, product in enumerate(products.values(), start=1):
        exists = (
            db.query(PriceTableItem)
            .filter(
                PriceTableItem.price_table_id == price_table.id,
                PriceTableItem.product_id == product.id,
            )
            .first()
        )
        if exists is None:
            db.add(
                PriceTableItem(
                    price_table_id=price_table.id,
                    product_id=product.id,
                    price=12000.0 + index * 3100.0,
                    margin_rate=0.34 + index * 0.01,
                )
            )
    return price_table


def _ensure_customer_quote_request(db: Session, product: Product) -> CustomerQuoteRequest:
    request = (
        db.query(CustomerQuoteRequest)
        .filter(
            CustomerQuoteRequest.customer_email == DEMO_CUSTOMER_EMAIL,
            CustomerQuoteRequest.product_id == product.id,
        )
        .first()
    )
    if request is not None:
        return request
    response = create_customer_quote_request(
        db,
        CustomerQuoteRequestCreate(
            customer_name="QuoteOps Demo Customer",
            customer_email=DEMO_CUSTOMER_EMAIL,
            customer_company="QuoteOps Demo Studio",
            product_id=product.id,
            quantity=50,
            request_note="QuoteOps Demo customer quote request for presentation testing.",
        ),
    )
    return db.get(CustomerQuoteRequest, response.id)


def _ensure_approval_request(db: Session, product: Product) -> PriceApprovalRequest:
    approval = (
        db.query(PriceApprovalRequest)
        .filter(
            PriceApprovalRequest.product_id == product.id,
            PriceApprovalRequest.submitted_note == DEMO_APPROVAL_NOTE,
        )
        .first()
    )
    if approval is not None:
        return approval
    response = create_approval_request(
        db,
        ApprovalRequestCreate(
            product_id=product.id,
            quantity=50,
            proposed_unit_price=11200.0,
            minimum_margin_rate=0.3,
            submitted_note=DEMO_APPROVAL_NOTE,
        ),
    )
    return db.get(PriceApprovalRequest, response.id)


def _ensure_workflow_job(db: Session, product: Product, username: str) -> WorkflowJob:
    job = db.query(WorkflowJob).filter(WorkflowJob.title == DEMO_WORKFLOW_TITLE).first()
    if job is not None:
        return job
    response = create_workflow_job(
        db,
        WorkflowJobCreate(
            job_type="pricing_simulation",
            title=DEMO_WORKFLOW_TITLE,
            description="QuoteOps Demo workflow job for deterministic simulation.",
            input={
                "product_id": product.id,
                "quantities": [10, 50, 100],
                "margin_rates": [0.25, 0.35, 0.45],
                "include_competitor_context": True,
            },
        ),
        username,
    )
    return db.get(WorkflowJob, response.id)


def _ensure_pricing_simulation(db: Session, product: Product, username: str) -> PricingSimulation:
    simulation = db.query(PricingSimulation).filter(PricingSimulation.name == DEMO_SIMULATION_NAME).first()
    if simulation is not None:
        return simulation
    response = create_pricing_simulation(
        db,
        PricingSimulationCreate(
            name=DEMO_SIMULATION_NAME,
            product_id=product.id,
            quantities=[10, 50, 100],
            margin_rates=[0.25, 0.35, 0.45],
            include_competitor_context=True,
            notes="QuoteOps Demo deterministic pricing simulation.",
        ),
        username,
    )
    return db.get(PricingSimulation, response.id)


def _ensure_scenario_comparison(db: Session, product: Product, username: str) -> ScenarioComparison:
    comparison = (
        db.query(ScenarioComparison)
        .filter(ScenarioComparison.name == DEMO_COMPARISON_NAME)
        .first()
    )
    if comparison is not None:
        return comparison
    response = create_scenario_comparison(
        db,
        ScenarioComparisonCreate(
            name=DEMO_COMPARISON_NAME,
            description="QuoteOps Demo direct scenario comparison for presentation.",
            product_id=product.id,
            scenarios=[
                ScenarioComparisonScenarioInput(
                    label="Conservative", quantity=50, margin_rate=0.25
                ),
                ScenarioComparisonScenarioInput(
                    label="Standard", quantity=50, margin_rate=0.35
                ),
                ScenarioComparisonScenarioInput(
                    label="Premium", quantity=50, margin_rate=0.45
                ),
            ],
            include_competitor_context=True,
        ),
        username,
    )
    return db.get(ScenarioComparison, response.id)


def _ensure_html_report(db: Session, comparison_id: int, username: str) -> HtmlReport:
    report = db.query(HtmlReport).filter(HtmlReport.title == DEMO_REPORT_TITLE).first()
    if report is not None:
        return report
    response = create_html_report(
        db,
        HtmlReportCreate(
            report_type="scenario_comparison",
            title=DEMO_REPORT_TITLE,
            source_id=comparison_id,
        ),
        username,
    )
    return db.get(HtmlReport, response.id)


def _get_demo_product(db: Session, sku: str) -> Product:
    product = db.query(Product).filter(Product.sku == sku).first()
    if product is None:
        raise RuntimeError(f"Demo product {sku} was not seeded")
    return product


def _demo_counts(db: Session) -> dict[str, int]:
    demo_product_ids = [
        row.id
        for row in db.query(Product.id)
        .filter(Product.sku.in_(DEMO_PRODUCT_SKUS))
        .all()
    ]
    demo_competitor_ids = [
        row.id
        for row in db.query(Competitor.id)
        .filter(Competitor.name.in_(_demo_competitor_names()))
        .all()
    ]
    demo_table_ids = [
        row.id
        for row in db.query(PriceTable.id)
        .filter(PriceTable.name == DEMO_PRICE_TABLE_NAME)
        .all()
    ]
    return {
        "products": len(demo_product_ids),
        "competitors": len(demo_competitor_ids),
        "cost_profiles": _count_for_ids(db, CostProfile, CostProfile.product_id, demo_product_ids),
        "competitor_prices": _count_demo_competitor_prices(db, demo_product_ids, demo_competitor_ids),
        "price_tables": len(demo_table_ids),
        "price_table_items": _count_for_ids(db, PriceTableItem, PriceTableItem.price_table_id, demo_table_ids),
        "approval_requests": _count_for_ids(db, PriceApprovalRequest, PriceApprovalRequest.product_id, demo_product_ids),
        "customer_quote_requests": _count_for_ids(db, CustomerQuoteRequest, CustomerQuoteRequest.product_id, demo_product_ids),
        "pricing_simulations": _count_named(db, PricingSimulation, PricingSimulation.name),
        "scenario_comparisons": _count_named(db, ScenarioComparison, ScenarioComparison.name),
        "html_reports": _count_named(db, HtmlReport, HtmlReport.title),
        "workflow_jobs": _count_named(db, WorkflowJob, WorkflowJob.title),
        "strategy_templates": db.query(PricingStrategyTemplate)
        .filter(PricingStrategyTemplate.strategy_code.in_(DEMO_STRATEGY_CODES))
        .count(),
    }


def _count_for_ids(db: Session, model: Any, column: Any, ids: list[int]) -> int:
    if not ids:
        return 0
    return db.query(model).filter(column.in_(ids)).count()


def _count_named(db: Session, model: Any, column: Any) -> int:
    known_names = {
        PricingSimulation: DEMO_SIMULATION_NAME,
        ScenarioComparison: DEMO_COMPARISON_NAME,
        HtmlReport: DEMO_REPORT_TITLE,
        WorkflowJob: DEMO_WORKFLOW_TITLE,
    }
    known_name = known_names.get(model)
    if known_name is None:
        return 0
    return db.query(model).filter(column == known_name).count()


def _count_demo_competitor_prices(
    db: Session, demo_product_ids: list[int], demo_competitor_ids: list[int]
) -> int:
    query = db.query(CompetitorPrice).filter(
        CompetitorPrice.source_note.like("QuoteOps Demo%")
    )
    if demo_product_ids:
        query = query.filter(CompetitorPrice.product_id.in_(demo_product_ids))
    if demo_competitor_ids:
        query = query.filter(CompetitorPrice.competitor_id.in_(demo_competitor_ids))
    return query.count()


def _delete_query(db: Session, query: Any) -> int:
    rows = query.all()
    for row in rows:
        db.delete(row)
    return len(rows)


def _soft_disable_products(db: Session) -> int:
    rows = db.query(Product).filter(Product.sku.in_(DEMO_PRODUCT_SKUS)).all()
    for row in rows:
        row.active = False
    return len(rows)


def _soft_disable_competitors(db: Session) -> int:
    rows = db.query(Competitor).filter(Competitor.name.in_(_demo_competitor_names())).all()
    for row in rows:
        row.active = False
    return len(rows)


def _soft_disable_cost_profiles(db: Session) -> int:
    product_ids = [row.id for row in db.query(Product).filter(Product.sku.in_(DEMO_PRODUCT_SKUS)).all()]
    if not product_ids:
        return 0
    rows = db.query(CostProfile).filter(CostProfile.product_id.in_(product_ids)).all()
    for row in rows:
        row.active = False
    return len(rows)


def _soft_disable_price_tables(db: Session) -> int:
    rows = db.query(PriceTable).filter(PriceTable.name == DEMO_PRICE_TABLE_NAME).all()
    for row in rows:
        row.status = "disabled"
    return len(rows)


def _demo_competitor_names() -> list[str]:
    return [name for name, _channel in DEMO_COMPETITORS]


def _soft_disable_strategy_templates(db: Session) -> int:
    rows = (
        db.query(PricingStrategyTemplate)
        .filter(PricingStrategyTemplate.strategy_code.in_(DEMO_STRATEGY_CODES))
        .all()
    )
    for row in rows:
        row.active = False
    return len(rows)


def _presentation_steps() -> list[DemoScenarioStep]:
    return [
        DemoScenarioStep(step=1, title="Review demo data status", api="GET /api/demo/status"),
        DemoScenarioStep(step=2, title="Seed deterministic demo data", api="POST /api/demo/seed"),
        DemoScenarioStep(step=3, title="Generate quote preview", api="POST /api/quote-preview"),
        DemoScenarioStep(step=4, title="Generate candidate prices", api="POST /api/candidate-prices"),
        DemoScenarioStep(step=5, title="Validate proposed price", api="POST /api/price-validation"),
        DemoScenarioStep(step=6, title="Submit human approval request", api="POST /api/approval-requests"),
        DemoScenarioStep(step=7, title="Compare scenarios", api="POST /api/scenario-comparisons"),
        DemoScenarioStep(step=8, title="Generate deterministic HTML report", api="POST /api/html-reports"),
    ]
