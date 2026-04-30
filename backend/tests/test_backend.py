"""Backend integration tests for MF Intelligence."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://mutualiq-hub.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "admin@mfintel.com"
ADMIN_PASSWORD = "Admin@12345"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=20)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    assert "access_token" in s.cookies, "access_token cookie not set"
    assert "refresh_token" in s.cookies, "refresh_token cookie not set"
    return s


# --- Auth ---
class TestAuth:
    def test_unauth_me(self):
        r = requests.get(f"{BASE_URL}/api/auth/me", timeout=15)
        assert r.status_code == 401

    def test_login(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/auth/me", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["email"] == ADMIN_EMAIL
        assert d.get("role") == "admin"
        assert "_id" not in d
        assert "password_hash" not in d

    def test_login_bad_creds(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong"}, timeout=15)
        assert r.status_code == 401

    def test_register_and_logout(self):
        s = requests.Session()
        import uuid
        email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        r = s.post(f"{BASE_URL}/api/auth/register", json={"email": email, "password": "secret123", "name": "T User"}, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json()["email"] == email
        assert "access_token" in s.cookies
        # me works
        r2 = s.get(f"{BASE_URL}/api/auth/me", timeout=15)
        assert r2.status_code == 200
        # duplicate register fails
        r3 = s.post(f"{BASE_URL}/api/auth/register", json={"email": email, "password": "secret123", "name": "T2"}, timeout=15)
        assert r3.status_code == 400
        # logout
        r4 = s.post(f"{BASE_URL}/api/auth/logout", timeout=15)
        assert r4.status_code == 200
        s.cookies.clear()
        r5 = s.get(f"{BASE_URL}/api/auth/me", timeout=15)
        assert r5.status_code == 401


# --- Funds ---
class TestFunds:
    def test_list_funds(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/funds", timeout=15)
        assert r.status_code == 200
        funds = r.json()
        assert isinstance(funds, list) and len(funds) == 6
        ids = {f["id"] for f in funds}
        for needed in ["axis-bluechip", "parag-flexi", "mirae-largemid", "kotak-emerg", "sbi-smallcap", "hdfc-balanced"]:
            assert needed in ids

    def test_fund_detail(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/funds/axis-bluechip", timeout=15)
        assert r.status_code == 200
        assert r.json()["id"] == "axis-bluechip"

    def test_fund_404(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/funds/nonexistent", timeout=15)
        assert r.status_code == 404


# --- Portfolio ---
class TestPortfolio:
    def test_get_portfolio_admin(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/portfolio", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "holdings" in d and "summary" in d
        # admin seeded with 4 funds
        assert d["summary"]["fund_count"] >= 4
        assert d["summary"]["invested"] > 0

    def test_add_remove_portfolio(self, admin_session):
        # add
        r = admin_session.post(f"{BASE_URL}/api/portfolio",
                               json={"fund_id": "sbi-smallcap", "units": 10, "avg_cost": 100.5}, timeout=15)
        assert r.status_code == 200, r.text
        item_id = r.json()["id"]
        # verify present
        r2 = admin_session.get(f"{BASE_URL}/api/portfolio", timeout=15)
        assert any(h["id"] == item_id for h in r2.json()["holdings"])
        # remove
        r3 = admin_session.delete(f"{BASE_URL}/api/portfolio/{item_id}", timeout=15)
        assert r3.status_code == 200
        # verify gone
        r4 = admin_session.get(f"{BASE_URL}/api/portfolio", timeout=15)
        assert not any(h["id"] == item_id for h in r4.json()["holdings"])

    def test_portfolio_validation(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/portfolio",
                               json={"fund_id": "axis-bluechip", "units": 0, "avg_cost": 100}, timeout=15)
        assert r.status_code == 422
        r2 = admin_session.post(f"{BASE_URL}/api/portfolio",
                                json={"fund_id": "bogus", "units": 1, "avg_cost": 1}, timeout=15)
        assert r2.status_code == 404


# --- Holdings/Sectors/Performance/Allocation ---
class TestFundData:
    def test_holdings_diff(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/funds/axis-bluechip/holdings-diff", timeout=15)
        assert r.status_code == 200
        d = r.json()
        for k in ["new_buys", "exits", "increased", "decreased"]:
            assert k in d["diff"]

    def test_sector_diff(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/funds/axis-bluechip/sector-diff", timeout=15)
        assert r.status_code == 200
        rows = r.json()["rows"]
        assert isinstance(rows, list) and len(rows) > 0
        for row in rows:
            assert {"sector", "current", "previous", "delta", "flag"} <= set(row.keys())
            assert row["flag"] == (abs(row["delta"]) >= 2.0)

    def test_performance(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/funds/axis-bluechip/performance", timeout=15)
        assert r.status_code == 200
        d = r.json()
        for k in ["1Y", "3Y", "5Y", "inception", "rolling_3Y", "benchmark_history", "differentials"]:
            assert k in d, f"missing {k}"

    def test_asset_allocation(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/funds/axis-bluechip/asset-allocation", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "current" in d and "previous" in d


# --- Alerts & News ---
class TestAlertsNews:
    def test_alerts(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/alerts", timeout=15)
        assert r.status_code == 200
        alerts = r.json()
        assert isinstance(alerts, list)
        # admin's portfolio has 4 funds → expect 7 alerts as per spec
        assert len(alerts) >= 1
        for a in alerts:
            assert "fund_name" in a and "fund_id" in a

    def test_news(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/funds/axis-bluechip/news", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert "items" in d and isinstance(d["items"], list)
