"""Phase 2 backend tests: portfolios, XIRR, tax-report, SIP planner."""
import os
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://mutualiq-hub.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "admin@mfintel.com"
ADMIN_PASSWORD = "Admin@12345"


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=20)
    assert r.status_code == 200, r.text
    return s


# Portfolios CRUD
class TestPortfolios:
    def test_list_default(self, admin):
        r = admin.get(f"{BASE_URL}/api/portfolios", timeout=15)
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list) and len(items) >= 1
        default = [p for p in items if p.get("is_default")]
        assert len(default) == 1
        assert default[0]["name"] == "Main Portfolio"
        assert "fund_count" in default[0]
        assert default[0]["fund_count"] >= 4

    def test_create_and_delete(self, admin):
        r = admin.post(f"{BASE_URL}/api/portfolios", json={"name": "TEST_Retirement"}, timeout=15)
        assert r.status_code == 200, r.text
        pid = r.json()["id"]
        assert r.json()["name"] == "TEST_Retirement"
        assert r.json()["is_default"] is False
        # list contains it
        items = admin.get(f"{BASE_URL}/api/portfolios", timeout=15).json()
        assert any(p["id"] == pid for p in items)
        # delete works
        r2 = admin.delete(f"{BASE_URL}/api/portfolios/{pid}", timeout=15)
        assert r2.status_code == 200
        # not found after
        items2 = admin.get(f"{BASE_URL}/api/portfolios", timeout=15).json()
        assert not any(p["id"] == pid for p in items2)

    def test_cannot_delete_default(self, admin):
        items = admin.get(f"{BASE_URL}/api/portfolios", timeout=15).json()
        default = [p for p in items if p.get("is_default")][0]
        r = admin.delete(f"{BASE_URL}/api/portfolios/{default['id']}", timeout=15)
        assert r.status_code == 400

    def test_filter_holdings_by_portfolio(self, admin):
        items = admin.get(f"{BASE_URL}/api/portfolios", timeout=15).json()
        default_id = [p for p in items if p.get("is_default")][0]["id"]
        # create new pf and add holding to it with backdated date
        cr = admin.post(f"{BASE_URL}/api/portfolios", json={"name": "TEST_Filter"}, timeout=15)
        new_pid = cr.json()["id"]
        try:
            ar = admin.post(f"{BASE_URL}/api/portfolio",
                            json={"fund_id": "sbi-smallcap", "units": 5, "avg_cost": 80.0,
                                  "portfolio_id": new_pid,
                                  "purchase_date": "2024-01-01T00:00:00+00:00"}, timeout=15)
            assert ar.status_code == 200, ar.text
            # filter by new
            r1 = admin.get(f"{BASE_URL}/api/portfolio?portfolio_id={new_pid}", timeout=15).json()
            assert r1["summary"]["fund_count"] == 1
            assert r1["holdings"][0]["fund_id"] == "sbi-smallcap"
            # filter by default — should NOT include this new holding
            r2 = admin.get(f"{BASE_URL}/api/portfolio?portfolio_id={default_id}", timeout=15).json()
            assert all(h["portfolio_id"] != new_pid for h in r2["holdings"])
        finally:
            admin.delete(f"{BASE_URL}/api/portfolios/{new_pid}", timeout=15)


# XIRR
class TestXirr:
    def test_xirr_admin(self, admin):
        items = admin.get(f"{BASE_URL}/api/portfolios", timeout=15).json()
        default_id = [p for p in items if p.get("is_default")][0]["id"]
        r = admin.get(f"{BASE_URL}/api/portfolios/{default_id}/xirr", timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert "xirr_pct" in d and d["xirr_pct"] is not None
        assert d["cashflow_count"] >= 5  # 4 buys + current
        # Seeded backdated holdings should produce a meaningful positive XIRR
        assert -100 < d["xirr_pct"] < 200
        assert d["current_value"] > 0


# Tax Report
class TestTax:
    def test_tax_report(self, admin):
        items = admin.get(f"{BASE_URL}/api/portfolios", timeout=15).json()
        default_id = [p for p in items if p.get("is_default")][0]["id"]
        r = admin.get(f"{BASE_URL}/api/portfolios/{default_id}/tax-report", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "rows" in d and "summary" in d
        assert len(d["rows"]) >= 4
        terms = {row["term"] for row in d["rows"]}
        assert terms <= {"STCG", "LTCG"}
        # admin seed has both <365d (90/200) and >=365d (540/720) holdings
        assert "STCG" in terms and "LTCG" in terms
        s = d["summary"]
        for k in ["stcg_gain", "ltcg_gain", "ltcg_exemption", "ltcg_taxable",
                  "stcg_tax", "ltcg_tax", "total_estimated_tax"]:
            assert k in s
        assert s["ltcg_exemption"] == 100000.0


# SIP Planner
class TestSip:
    def test_sip_basic(self, admin):
        r = admin.post(f"{BASE_URL}/api/sip-planner",
                       json={"monthly": 10000, "years": 10, "expected_return": 12, "step_up": 0}, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "summary" in d and "schedule" in d
        assert len(d["schedule"]) == 10
        s = d["summary"]
        assert s["total_invested"] == 1200000.0
        # FV for 10k SIP, 10y, 12% ≈ ~23.23L
        assert 2_200_000 < s["future_value"] < 2_500_000
        assert s["wealth_gain"] == round(s["future_value"] - s["total_invested"], 2)

    def test_sip_stepup(self, admin):
        r = admin.post(f"{BASE_URL}/api/sip-planner",
                       json={"monthly": 10000, "years": 5, "expected_return": 12, "step_up": 10}, timeout=15)
        assert r.status_code == 200
        d = r.json()
        # With 10% step-up, invested should exceed the flat case
        assert d["summary"]["total_invested"] > 600000

    def test_sip_validation(self, admin):
        r = admin.post(f"{BASE_URL}/api/sip-planner",
                       json={"monthly": 0, "years": 10, "expected_return": 12}, timeout=15)
        assert r.status_code == 422
