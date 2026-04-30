import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "@/lib/auth.jsx";
import { PortfolioProvider } from "@/lib/portfolio.jsx";
import AppLayout from "@/components/AppLayout.jsx";
import LoginPage from "@/pages/LoginPage.jsx";
import OverviewPage from "@/pages/OverviewPage.jsx";
import PortfolioPage from "@/pages/PortfolioPage.jsx";
import FundDetailPage from "@/pages/FundDetailPage.jsx";
import AlertsPage from "@/pages/AlertsPage.jsx";
import NewsPage from "@/pages/NewsPage.jsx";
import SipPlannerPage from "@/pages/SipPlannerPage.jsx";
import TaxReportPage from "@/pages/TaxReportPage.jsx";

function App() {
  return (
    <div className="App">
      <AuthProvider>
        <PortfolioProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/login" element={<LoginPage mode="login" />} />
              <Route path="/register" element={<LoginPage mode="register" />} />
              <Route element={<AppLayout />}>
                <Route path="/" element={<OverviewPage />} />
                <Route path="/portfolio" element={<PortfolioPage />} />
                <Route path="/fund/:id" element={<FundDetailPage />} />
                <Route path="/alerts" element={<AlertsPage />} />
                <Route path="/news" element={<NewsPage />} />
                <Route path="/sip" element={<SipPlannerPage />} />
                <Route path="/tax" element={<TaxReportPage />} />
              </Route>
            </Routes>
          </BrowserRouter>
        </PortfolioProvider>
      </AuthProvider>
    </div>
  );
}

export default App;
