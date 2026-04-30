import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api } from "./api";

const PortfolioCtx = createContext(null);

export function PortfolioProvider({ children }) {
  const [portfolios, setPortfolios] = useState([]);
  const [activeId, setActiveId] = useState(
    () => localStorage.getItem("active_portfolio_id") || null
  );

  const load = useCallback(async () => {
    try {
      const { data } = await api.get("/portfolios");
      setPortfolios(data);
      if (!activeId || !data.find((p) => p.id === activeId)) {
        const def = data.find((p) => p.is_default) || data[0];
        if (def) {
          setActiveId(def.id);
          localStorage.setItem("active_portfolio_id", def.id);
        }
      }
    } catch { /* not authed */ }
  }, [activeId]);

  useEffect(() => { load(); }, [load]);

  const setActive = (id) => {
    setActiveId(id);
    localStorage.setItem("active_portfolio_id", id);
  };

  const create = async (name) => {
    const { data } = await api.post("/portfolios", { name });
    await load();
    setActive(data.id);
    return data;
  };

  const remove = async (id) => {
    await api.delete(`/portfolios/${id}`);
    await load();
  };

  return (
    <PortfolioCtx.Provider value={{ portfolios, activeId, setActive, create, remove, reload: load }}>
      {children}
    </PortfolioCtx.Provider>
  );
}

export const usePortfolio = () => useContext(PortfolioCtx);
