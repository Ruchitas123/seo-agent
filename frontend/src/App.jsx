import { useState } from "react";
import "./App.css";

const API = "";

const STEP_LABELS = {
  1: "Fetching live Google SERP...",
  2: "Fetching Google Autocomplete...",
  3: "Detecting search intent...",
  4: "Scraping competitor pages...",
  5: "Computing keyword gaps...",
  6: "Done!",
};

const PRIORITY_COLOR = {
  critical: { bg: "#fff5f5", border: "#fc8181", text: "#c53030", badge: "#fed7d7" },
  high:     { bg: "#fffaf0", border: "#f6ad55", text: "#c05621", badge: "#feebc8" },
  medium:   { bg: "#fffff0", border: "#f6e05e", text: "#975a16", badge: "#fefcbf" },
};

function Badge({ children, color = "#e2e8f0", textColor = "#4a5568" }) {
  return (
    <span style={{ background: color, color: textColor, borderRadius: 4, padding: "2px 8px", fontSize: 11, fontWeight: 700 }}>
      {children}
    </span>
  );
}

function GapCard({ gap }) {
  const c = PRIORITY_COLOR[gap.priority] || PRIORITY_COLOR.medium;
  const sources = [...new Set(gap.sources.map(s => s.split(" #")[0].replace("(phrase)", "").trim()))];
  return (
    <div style={{ border: `1px solid ${c.border}`, borderLeft: `4px solid ${c.border}`, borderRadius: 6, padding: "10px 14px", marginBottom: 8, background: c.bg }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
        <span style={{ fontWeight: 700, fontSize: 15, color: "#1a202c" }}>{gap.keyword}</span>
        <Badge color={c.badge} textColor={c.text}>{gap.priority.toUpperCase()}</Badge>
        <Badge color={gap.track === "product_specific" ? "#ebf8ff" : "#f0fff4"} textColor={gap.track === "product_specific" ? "#2b6cb0" : "#276749"}>
          {gap.track === "product_specific" ? "product" : "general"}
        </Badge>
      </div>
      <div style={{ fontSize: 12, color: "#718096" }}>
        Sources: {sources.join(" · ")} <span style={{ marginLeft: 12 }}>Signal: {gap.signal_count}</span>
      </div>
    </div>
  );
}

function TabBtn({ label, active, onClick }) {
  return (
    <button onClick={onClick} style={{ padding: "10px 20px", border: "none", cursor: "pointer", fontWeight: 600, borderBottom: active ? "3px solid #4299e1" : "3px solid transparent", color: active ? "#2b6cb0" : "#718096", background: "transparent", fontSize: 14 }}>
      {label}
    </button>
  );
}

function PipelineProgress({ steps, currentStep }) {
  return (
    <div style={{ margin: "20px 0" }}>
      {[1, 2, 3, 4, 5].map(n => {
        const done = steps.some(s => s.step > n) || currentStep > n;
        const active = currentStep === n;
        return (
          <div key={n} style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 10 }}>
            <div style={{ width: 28, height: 28, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700, fontSize: 13, background: done ? "#48bb78" : active ? "#4299e1" : "#e2e8f0", color: done || active ? "white" : "#a0aec0", flexShrink: 0 }}>
              {done ? "✓" : n}
            </div>
            <span style={{ color: !done && !active ? "#a0aec0" : "#1a202c", fontSize: 13 }}>
              {steps.find(s => s.step === n)?.desc || STEP_LABELS[n]}
            </span>
            {active && <span style={{ color: "#4299e1" }}>●●●</span>}
          </div>
        );
      })}
    </div>
  );
}

function OverviewTab({ result, onKeyword }) {
  const { intent, competitor_pages, your_page, gaps } = result;
  const critical = gaps.filter(g => g.priority === "critical").length;
  const high = gaps.filter(g => g.priority === "high").length;
  const medium = gaps.filter(g => g.priority === "medium").length;
  const matchedRanks = new Set(intent.intent_matched_competitor_ranks || []);
  return (
    <div>
      {!intent.match ? (
        <div style={{ background: "#fff5f5", border: "1px solid #fc8181", borderLeft: "5px solid #e53e3e", borderRadius: 6, padding: "14px 18px", marginBottom: 20 }}>
          <div style={{ fontWeight: 700, color: "#c53030", marginBottom: 6 }}>⚠️ Not Yet Ranking</div>
          <div style={{ color: "#742a2a", fontSize: 14, marginBottom: intent.suggested_keywords?.length ? 12 : 0 }}>{intent.warning}</div>
          {intent.suggested_keywords?.length > 0 && (
            <div>
              <div style={{ fontSize: 13, fontWeight: 600, color: "#c53030", marginBottom: 6 }}>
                Try these intent-matched keyword variants (click to use):
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {intent.suggested_keywords.map((kw, i) => (
                  <button key={i} onClick={() => onKeyword(kw)}
                    style={{ padding: "4px 10px", borderRadius: 4, border: "1px solid #fc8181", background: "white", color: "#c53030", fontSize: 12, fontWeight: 600, cursor: "pointer" }}>
                    {kw}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        <div style={{ background: "#f0fff4", border: "1px solid #9ae6b4", borderLeft: "5px solid #38a169", borderRadius: 6, padding: "14px 18px", marginBottom: 20 }}>
          <span style={{ fontWeight: 700, color: "#276749" }}>✅ Intent Match — Your domain appears in the top 10.</span>
        </div>
      )}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 12, marginBottom: 24 }}>
        {[
          { label: "Your Rank", value: intent.your_rank, color: "#4299e1" },
          { label: "🔴 Critical", value: critical, color: "#e53e3e" },
          { label: "🟠 High", value: high, color: "#dd6b20" },
          { label: "🟡 Medium", value: medium, color: "#d69e2e" },
          { label: "Total Gaps", value: gaps.length, color: "#4a5568" },
        ].map(m => (
          <div key={m.label} style={{ background: "white", borderRadius: 8, padding: "16px 18px", border: "1px solid #e2e8f0", textAlign: "center" }}>
            <div style={{ fontSize: 26, fontWeight: 800, color: m.color }}>{m.value}</div>
            <div style={{ fontSize: 12, color: "#718096", marginTop: 4 }}>{m.label}</div>
          </div>
        ))}
      </div>
      <h3 style={{ marginBottom: 12 }}>Top 5 SERP Results</h3>
      {competitor_pages.map(comp => {
        const matched = matchedRanks.has(comp.rank);
        const yourKws = new Set(your_page.keywords);
        const missing = comp.keywords.filter(k => !yourKws.has(k));
        const present = comp.keywords.filter(k => yourKws.has(k));
        return (
          <div key={comp.url} style={{ background: "white", border: `1px solid ${matched ? "#9ae6b4" : "#e2e8f0"}`, borderLeft: `4px solid ${matched ? "#38a169" : "#cbd5e0"}`, borderRadius: 8, padding: "14px 18px", marginBottom: 10 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div style={{ flex: 1 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                  <span style={{ fontWeight: 700 }}>#{comp.rank}</span>
                  <span style={{ fontWeight: 600 }}>{comp.title}</span>
                  {matched
                    ? <Badge color="#f0fff4" textColor="#276749">intent-matched</Badge>
                    : <Badge color="#f7fafc" textColor="#a0aec0">off-topic</Badge>}
                </div>
                <div style={{ fontSize: 12, color: "#4299e1", marginBottom: 4 }}>{comp.url}</div>
                {comp.h2?.length > 0 && <div style={{ fontSize: 12, color: "#718096", marginBottom: 6 }}>H2: {comp.h2.slice(0, 4).join(" · ")}</div>}
                <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                  {missing.slice(0, 12).map((k, j) => <span key={j} style={{ background: "#fff5f5", border: "1px solid #fc8181", borderRadius: 4, padding: "1px 7px", fontSize: 11, color: "#c53030" }}>{k}</span>)}
                  {present.slice(0, 8).map((k, j) => <span key={j} style={{ background: "#f0fff4", border: "1px solid #9ae6b4", borderRadius: 4, padding: "1px 7px", fontSize: 11, color: "#276749" }}>{k}</span>)}
                </div>
              </div>
              <div style={{ textAlign: "right", flexShrink: 0, marginLeft: 16 }}>
                <div style={{ fontSize: 12, color: "#718096", marginBottom: 4 }}>{comp.word_count} words</div>
                <Badge color={comp.scraped ? "#f0fff4" : "#fff5f5"} textColor={comp.scraped ? "#276749" : "#c53030"}>{comp.scraped ? "✓ scraped" : "✗ JS-blocked"}</Badge>
                <div style={{ fontSize: 11, color: "#a0aec0", marginTop: 4 }}>{missing.length} missing · {present.length} present</div>
              </div>
            </div>
          </div>
        );
      })}
      <h3 style={{ marginTop: 20, marginBottom: 12 }}>Your Article</h3>
      <div style={{ background: "#ebf8ff", border: "1px solid #90cdf4", borderRadius: 8, padding: "14px 18px" }}>
        <div style={{ fontWeight: 600, marginBottom: 6, fontSize: 13, wordBreak: "break-all" }}>{your_page.url}</div>
        <div style={{ display: "flex", gap: 20, fontSize: 14 }}>
          <span>📝 {your_page.word_count} words</span>
          <span>🔑 {your_page.keywords.length} keywords</span>
        </div>
        {your_page.h1?.length > 0 && <div style={{ fontSize: 13, color: "#2b6cb0", marginTop: 6 }}>H1: {your_page.h1[0]}</div>}
      </div>
    </div>
  );
}

function GapsTab({ gaps }) {
  const [priorityFilter, setPriorityFilter] = useState(["critical", "high"]);
  const [trackFilter, setTrackFilter] = useState("all");
  const [search, setSearch] = useState("");
  const toggle = (p) => setPriorityFilter(prev => prev.includes(p) ? prev.filter(x => x !== p) : [...prev, p]);
  const filtered = gaps.filter(g => {
    if (priorityFilter.length && !priorityFilter.includes(g.priority)) return false;
    if (trackFilter === "product" && g.track !== "product_specific") return false;
    if (trackFilter === "general" && g.track !== "general") return false;
    if (search && !g.keyword.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });
  return (
    <div>
      <div style={{ display: "flex", gap: 12, marginBottom: 20, flexWrap: "wrap", alignItems: "center" }}>
        <div style={{ display: "flex", gap: 8 }}>
          {["critical", "high", "medium"].map(p => (
            <button key={p} onClick={() => toggle(p)} style={{ padding: "6px 14px", borderRadius: 20, border: `2px solid ${PRIORITY_COLOR[p].border}`, cursor: "pointer", fontWeight: 600, fontSize: 13, background: priorityFilter.includes(p) ? PRIORITY_COLOR[p].badge : "white", color: priorityFilter.includes(p) ? PRIORITY_COLOR[p].text : "#718096" }}>
              {p === "critical" ? "🔴" : p === "high" ? "🟠" : "🟡"} {p}
            </button>
          ))}
        </div>
        <select value={trackFilter} onChange={e => setTrackFilter(e.target.value)} style={{ padding: "6px 12px", borderRadius: 6, border: "1px solid #e2e8f0", fontSize: 13 }}>
          <option value="all">All tracks</option>
          <option value="product">Product specific</option>
          <option value="general">General</option>
        </select>
        <input placeholder="Search keywords..." value={search} onChange={e => setSearch(e.target.value)} style={{ padding: "6px 12px", borderRadius: 6, border: "1px solid #e2e8f0", fontSize: 13, width: 200 }} />
        <span style={{ color: "#718096", fontSize: 13 }}>{filtered.length} gaps</span>
      </div>
      {filtered.map((g, i) => <GapCard key={i} gap={g} />)}
      {filtered.length === 0 && <div style={{ color: "#a0aec0", textAlign: "center", padding: 40 }}>No gaps match your filters.</div>}
    </div>
  );
}

function SearchIntentTab({ result }) {
  const { keyword, serp, autocomplete } = result;
  const kwTokens = keyword.toLowerCase().split(/\s+/).filter(w => w.length >= 3);
  const isRelevant = (text) => kwTokens.every(t => text.toLowerCase().includes(t));

  const isEnglish = (text) => /^[\x00-\x7F]+$/.test(text);

  const items = [
    ...serp.paa.filter(q => isRelevant(q) && isEnglish(q)).map(q => ({ text: q, source: "People Also Ask" })),
    ...serp.related_searches.filter(s => isRelevant(s) && isEnglish(s)).map(s => ({ text: s, source: "Related Search" })),
    ...autocomplete.suggestions.filter(s => isRelevant(s) && isEnglish(s)).map(s => ({ text: s, source: "Autocomplete" })),
  ];

  const sourceColor = {
    "People Also Ask": { bg: "#ebf8ff", text: "#2b6cb0" },
    "Related Search":  { bg: "#f0fff4", text: "#276749" },
    "Autocomplete":    { bg: "#fffff0", text: "#975a16" },
  };

  return (
    <div>
      <div style={{ color: "#718096", fontSize: 13, marginBottom: 16 }}>
        {items.length} search intent signals related to <strong>"{keyword}"</strong>
      </div>
      {items.length === 0 && <div style={{ color: "#a0aec0", padding: 40, textAlign: "center" }}>No intent signals found for this keyword.</div>}
      {items.map((item, i) => {
        const c = sourceColor[item.source];
        return (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 12, padding: "10px 14px", borderRadius: 6, marginBottom: 6, border: "1px solid #e2e8f0", background: "white" }}>
            <span style={{ background: c.bg, color: c.text, borderRadius: 4, padding: "2px 8px", fontSize: 11, fontWeight: 700, flexShrink: 0 }}>{item.source}</span>
            <span style={{ fontSize: 14, color: "#1a202c" }}>{item.text}</span>
          </div>
        );
      })}
    </div>
  );
}


export default function App() {
  const [keyword, setKeyword] = useState("");
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [steps, setSteps] = useState([]);
  const [currentStep, setCurrentStep] = useState(0);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState("overview");

  const runAnalysis = async () => {
    if (!keyword.trim() || !url.trim()) { setError("Both keyword and URL are required."); return; }
    setLoading(true); setResult(null); setError(null); setSteps([]); setCurrentStep(1);
    try {
      const res = await fetch(`${API}/api/analyze`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ keyword, url }) });
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop();
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const msg = JSON.parse(line.slice(6));
          if (msg.type === "progress") { setCurrentStep(msg.step); setSteps(prev => [...prev, { step: msg.step, desc: msg.desc }]); }
          else if (msg.type === "result") { setResult(msg.data); setActiveTab("overview"); }
          else if (msg.type === "error") { setError(msg.message); }
        }
      }
    } catch (e) {
      setError(`Connection error: ${e.message}. Make sure the API is running: python3 api.py`);
    } finally { setLoading(false); }
  };

  const TABS = [
    { id: "overview", label: "Overview" },
    { id: "gaps", label: "Keyword Gaps" },
    { id: "serp", label: "Search Intent" },
  ];

  return (
    <div style={{ minHeight: "100vh", background: "#f7fafc", fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" }}>
      <div style={{ background: "white", borderBottom: "1px solid #e2e8f0", padding: "16px 32px", display: "flex", alignItems: "center", gap: 12 }}>
        <span style={{ fontSize: 24 }}>🔍</span>
        <div>
          <h1 style={{ margin: 0, fontSize: 20, fontWeight: 800, color: "#1a202c" }}>SEO Keyword Gap Analyzer</h1>
        </div>
      </div>
      <div style={{ display: "flex", height: "calc(100vh - 65px)" }}>
        <div style={{ width: 300, background: "white", borderRight: "1px solid #e2e8f0", padding: 24, flexShrink: 0, overflowY: "auto" }}>
          <h3 style={{ margin: "0 0 16px", color: "#2d3748" }}>Run Analysis</h3>

          <label style={{ display: "block", marginBottom: 14 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: "#4a5568", marginBottom: 6 }}>Target Keyword *</div>
            <input value={keyword} onChange={e => setKeyword(e.target.value)}
              placeholder="Enter target keyword"
              style={{ width: "100%", padding: "9px 12px", borderRadius: 6, border: "1px solid #e2e8f0", fontSize: 14, boxSizing: "border-box" }} />
          </label>

          <label style={{ display: "block", marginBottom: 14 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: "#4a5568", marginBottom: 6 }}>Your Article URL</div>
            <input value={url} onChange={e => setUrl(e.target.value)} placeholder="https://..."
              style={{ width: "100%", padding: "9px 12px", borderRadius: 6, border: "1px solid #e2e8f0", fontSize: 14, boxSizing: "border-box" }} />
          </label>
          <button onClick={runAnalysis} disabled={loading} style={{ width: "100%", padding: 11, borderRadius: 6, border: "none", background: loading ? "#a0aec0" : "#4299e1", color: "white", fontWeight: 700, fontSize: 15, cursor: loading ? "not-allowed" : "pointer", marginBottom: 8 }}>
            {loading ? "Running..." : "▶  Run Analysis"}
          </button>
          {error && <div style={{ marginTop: 10, background: "#fff5f5", border: "1px solid #fc8181", borderRadius: 6, padding: "10px 12px", fontSize: 13, color: "#c53030" }}>{error}</div>}
          {loading && <PipelineProgress steps={steps} currentStep={currentStep} />}
          {!loading && !result && (
            <div style={{ marginTop: 24 }}>
              <div style={{ fontSize: 12, color: "#a0aec0", fontWeight: 600, marginBottom: 8 }}>DATA SOURCES</div>
              {["Google SERP (SerpAPI)", "People Also Ask", "Related Searches", "Google Autocomplete", "Competitor page scraping"].map(s => (
                <div key={s} style={{ fontSize: 12, color: "#718096", marginBottom: 4 }}>· {s}</div>
              ))}
            </div>
          )}
        </div>
        <div style={{ flex: 1, overflowY: "auto", padding: 24 }}>
          {result ? (
            <>
              <div style={{ borderBottom: "2px solid #e2e8f0", marginBottom: 24, display: "flex" }}>
                {TABS.map(t => <TabBtn key={t.id} label={t.label} active={activeTab === t.id} onClick={() => setActiveTab(t.id)} />)}
              </div>
              {activeTab === "overview" && <OverviewTab result={result} onKeyword={setKeyword} />}
              {activeTab === "gaps" && <GapsTab gaps={result.gaps} />}
              {activeTab === "serp" && <SearchIntentTab result={result} />}
            </>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "70%", color: "#a0aec0" }}>
              <div style={{ fontSize: 64, marginBottom: 16 }}>🔍</div>
              <h2 style={{ color: "#4a5568", margin: 0 }}>SEO Keyword Gap Analyzer</h2>
              <p style={{ textAlign: "center", maxWidth: 420, lineHeight: 1.7, color: "#718096" }}>Enter a keyword and your article URL in the sidebar, then click Run Analysis.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
