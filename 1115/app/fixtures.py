"""Deterministic, fictional evidence used only by explicit fixture runs."""

from app.models import CompanyInput, LinkupResult, PageExtraction

FIXTURE_NOTICE = (
    "Fictional fixture data — no Linkup, Browser Use, Anthropic, Freepik, "
    "SmartBuckets, or other provider request was made."
)


def fixture_company() -> CompanyInput:
    return CompanyInput(
        name="Northstar Labs",
        domain="northstar-labs.invalid",
        persona="SDR researching an account",
        notes="Immutable checked-in fictional fixture northstar-v1",
        mode="fixture",
    )


def fixture_linkup_results() -> list[LinkupResult]:
    return [
        LinkupResult(
            title="Northstar Labs | Platform",
            url="https://northstar-labs.invalid/product",
            snippet="Fictional workflow automation platform for operations teams.",
            source="checked-in-fictional-fixture",
        ),
        LinkupResult(
            title="Northstar Labs | Solutions",
            url="https://northstar-labs.invalid/solutions",
            snippet="Fictional solution briefs for revenue and support operations.",
            source="checked-in-fictional-fixture",
        ),
        LinkupResult(
            title="Northstar Labs | Pricing",
            url="https://northstar-labs.invalid/pricing",
            snippet="Fictional team and scale plan packaging.",
            source="checked-in-fictional-fixture",
        ),
    ]


FIXTURE_PAGES = {
    "https://northstar-labs.invalid/product": PageExtraction(
        url="https://northstar-labs.invalid/product",
        page_type="product",
        icp="Operations teams coordinating repeatable customer workflows",
        product_lines=["Workflow Studio", "Signal Board"],
        pain_points=["Manual handoffs", "Fragmented account context"],
        signals=["workflow automation", "shared evidence", "operational visibility"],
        raw_text_excerpt="Fictional product page for the deterministic demo.",
        usefulness_score=0.91,
        notes=FIXTURE_NOTICE,
    ),
    "https://northstar-labs.invalid/solutions": PageExtraction(
        url="https://northstar-labs.invalid/solutions",
        page_type="solutions",
        icp="Revenue and support operations leaders",
        product_lines=["Revenue Operations", "Support Operations"],
        pain_points=["Slow research cycles", "Inconsistent process execution"],
        signals=["repeatable playbooks", "team collaboration", "audit trails"],
        raw_text_excerpt="Fictional solutions page for the deterministic demo.",
        usefulness_score=0.86,
        notes=FIXTURE_NOTICE,
    ),
    "https://northstar-labs.invalid/pricing": PageExtraction(
        url="https://northstar-labs.invalid/pricing",
        page_type="pricing",
        icp="Growing operations teams",
        product_lines=["Team", "Scale"],
        pain_points=["Unclear expansion costs"],
        signals=["seat-based plans", "annual option", "enterprise controls"],
        raw_text_excerpt="Fictional pricing page for the deterministic demo.",
        usefulness_score=0.79,
        notes=FIXTURE_NOTICE,
    ),
}
