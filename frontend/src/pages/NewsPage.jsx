import { useEffect, useState } from "react";
import { api } from "../lib/api";

export default function NewsPage() {
  const [holdings, setHoldings] = useState([]);
  const [active, setActive] = useState(null);
  const [news, setNews] = useState(null);

  useEffect(() => {
    api.get("/portfolio").then((r) => {
      setHoldings(r.data.holdings);
      if (r.data.holdings.length) setActive(r.data.holdings[0].fund_id);
    });
  }, []);

  useEffect(() => {
    if (!active) return;
    setNews(null);
    api.get(`/funds/${active}/news`).then((r) => setNews(r.data));
  }, [active]);

  return (
    <div className="space-y-6" data-testid="news-page">
      <div>
        <div className="label-uppercase">// News Wire</div>
        <h1 className="text-3xl font-black tracking-tighter">Per-Fund News Feed</h1>
      </div>

      {holdings.length === 0 && (
        <div className="border border-border p-8 text-center text-muted-foreground text-sm">
          Add funds to your portfolio to see fund-specific news.
        </div>
      )}

      {holdings.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-px bg-border">
          <div className="bg-card lg:col-span-1">
            <div className="label-uppercase p-4 border-b border-border">Schemes</div>
            <div>
              {holdings.map((h) => (
                <button
                  key={h.id}
                  onClick={() => setActive(h.fund_id)}
                  data-testid={`news-tab-${h.fund_id}`}
                  className={"w-full text-left px-4 py-3 border-l-2 border-b border-border " +
                    (active === h.fund_id ? "border-l-primary bg-secondary" : "border-l-transparent hover:bg-secondary/40")}
                >
                  <div className="text-xs font-medium leading-tight">{h.fund.name}</div>
                  <div className="text-[10px] uppercase tracking-widest text-muted-foreground mt-1">{h.fund.amc}</div>
                </button>
              ))}
            </div>
          </div>

          <div className="bg-card lg:col-span-3 p-5 min-h-[400px]">
            {!news ? <div className="text-xs text-muted-foreground">Fetching wire...</div> :
              news.items.length === 0 ? <div className="text-xs text-muted-foreground">No news items found.</div> :
                <div className="space-y-3">
                  <div className="label-uppercase mono mb-3">query: "{news.query}"</div>
                  {news.items.map((n, i) => (
                    <a key={i} href={n.link} target="_blank" rel="noreferrer"
                       data-testid={`news-item-${i}`}
                       className="block border border-border p-4 hover:border-primary transition-colors">
                      <div className="text-sm font-medium leading-snug"
                           dangerouslySetInnerHTML={{ __html: n.title }} />
                      <div className="text-[10px] uppercase tracking-widest text-muted-foreground mt-2 mono">
                        {n.published}
                      </div>
                    </a>
                  ))}
                </div>}
          </div>
        </div>
      )}
    </div>
  );
}
