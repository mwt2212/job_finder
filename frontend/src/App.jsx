import { useEffect, useRef, useState } from "react";

const API = "http://127.0.0.1:8001";

const DEFAULT_PREFS = {
  industry_preferences: { soft_penalize: ["healthcare"] },
  role_preferences: {
    soft_penalize_sales_adjacent: true,
    hard_block_outbound_cold_calling: true,
    allow_minimal_outbound: true,
    inbound_ok: true
  },
  qualification: {
    signals: ["skills", "degree", "years"],
    safe_vs_stretch_ratio: 0.7,
    min_match_score: 0.55
  },
  employment: { hard_block_non_full_time: true },
  travel: { penalty: 0 }
};

const DEFAULT_RULES = {
  hard_reject_patterns: [],
  not_entry_level_patterns: [],
  optional_reject_patterns: [],
  title_boosts: {},
  company_penalties: {},
  workplace_score: { remote: -6, hybrid: 12, onsite: 8, unknown: 2 },
  recency_scoring: {
    just_now: 25,
    minutes_max: 22,
    minutes_step: 5,
    hours_start: 20,
    days_start: 8
  }
};

const SHORTLIST_REASONS = [
  { label: "Wrong field", value: "wrong field" },
  { label: "Not qualified", value: "not qualified" },
  { label: "Salesy/outbound", value: "salesy" },
  { label: "Healthcare", value: "healthcare" },
  { label: "Low pay", value: "low pay" },
  { label: "Onsite only", value: "onsite" }
];

function classNames(...items) {
  return items.filter(Boolean).join(" ");
}

const MONTHS = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December"
];
const DATE_REGEX = /^(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}$/i;
const GREETING_REGEX = /^dear\b/i;
const SIGNATURE_REGEX = /^(sincerely|best|regards|respectfully|yours)\b/i;

function formatDate(date) {
  const month = MONTHS[date.getMonth()];
  return `${month} ${date.getDate()}, ${date.getFullYear()}`;
}

function currentDateString() {
  return formatDate(new Date());
}

function splitBlocks(text) {
  if (!text) return [];
  return text
    .split(/\n\s*\n+/)
    .map((t) => t.trim())
    .filter(Boolean);
}

function splitCoverSections(text) {
  const blocks = splitBlocks(text);
  let greetingIdx = null;
  let signatureIdx = null;
  blocks.forEach((block, idx) => {
    const firstLine = (block.split("\n")[0] || "").trim();
    if (greetingIdx === null && GREETING_REGEX.test(firstLine)) greetingIdx = idx;
    if (signatureIdx === null && SIGNATURE_REGEX.test(firstLine)) signatureIdx = idx;
  });
  if (greetingIdx !== null && signatureIdx !== null && signatureIdx < greetingIdx) {
    signatureIdx = null;
  }
  const header = greetingIdx !== null ? blocks.slice(0, greetingIdx) : [];
  const greeting = greetingIdx !== null ? blocks[greetingIdx] : "";
  const bodyStart = greetingIdx !== null ? greetingIdx + 1 : 0;
  const bodyEnd = signatureIdx !== null ? signatureIdx : blocks.length;
  const body = blocks.slice(bodyStart, bodyEnd);
  const signature = signatureIdx !== null ? blocks.slice(signatureIdx) : [];
  return { header, greeting, body, signature };
}

function applyDateToHeader(blocks, ensureDate, company) {
  if (!blocks.length && !ensureDate) return [];
  let replaced = false;
  const updated = blocks
    .map((block) => {
      const lines = block.split("\n").map((line) => {
        if (DATE_REGEX.test(line.trim())) {
          replaced = true;
          return currentDateString();
        }
        if (company && line.trim().toLowerCase() === "ruan") {
          return company;
        }
        return line;
      });
      return lines.join("\n").trim();
    })
    .filter(Boolean);
  if (ensureDate && !replaced) {
    return [currentDateString(), ...updated].filter(Boolean);
  }
  return updated;
}

function applyDateToTemplate(text, company) {
  if (!text) return text;
  const sections = splitCoverSections(text);
  const header = applyDateToHeader(sections.header, true, company);
  const parts = [
    ...header,
    sections.greeting,
    ...sections.body,
    ...sections.signature
  ].filter(Boolean);
  return parts.join("\n\n");
}

function labelForParagraph(index, total) {
  if (total === 0) return "";
  if (index === 0) return "Opening";
  if (index === total - 1) return "Closing";
  return `Body ${index}`;
}

function formatTokens(value) {
  if (value == null) return "n/a";
  if (value >= 1000000) return `${(value / 1000000).toFixed(2)}M`;
  if (value >= 1000) return `${(value / 1000).toFixed(1)}k`;
  return String(value);
}

function formatCost(value) {
  if (value == null) return "n/a";
  if (value < 0.01) return `$${value.toFixed(4)}`;
  return `$${value.toFixed(3)}`;
}

function parseProgressLine(line) {
  if (!line) return null;
  const capMatch = line.match(/Cap:\s*(\d+)\s*jobs/i);
  if (capMatch) {
    const total = Number(capMatch[1]);
    return { current: 0, total, pct: 0, label: "scout" };
  }
  const totalMatch = line.match(/Total:\s*(\d+)/i);
  if (totalMatch) {
    const current = Number(totalMatch[1]);
    return { current, total: null, pct: null };
  }
  const bracketMatch = line.match(/\[(\d+)\s*\/\s*(\d+)\]/);
  if (bracketMatch) {
    const current = Number(bracketMatch[1]);
    const total = Number(bracketMatch[2]);
    const pct = total ? (current / total) * 100 : 0;
    return { current, total, pct };
  }
  const capReached = line.match(/Reached cap of\s*(\d+)/i);
  if (capReached) {
    const total = Number(capReached[1]);
    return { current: total, total, pct: 100 };
  }
  return null;
}

function displayRegex(lines) {
  return (lines || [])
    .map((l) => {
      const unescaped = l.replace(/\\\\b/g, "\\b");
      const m = unescaped.match(/^\\b(.+)\\b$/);
      return m ? m[1] : unescaped;
    })
    .join("\n");
}

function parseRegexLines(text) {
  const hasRegexMeta = (s) => /[\\\[\]\(\)\?\+\*\.\|\^\$]/.test(s);
  return text
    .split("\n")
    .map((t) => t.trim())
    .filter(Boolean)
    .map((l) => {
      if (l.includes("\\b")) {
        return l.replace(/\\b/g, "\\\\b");
      }
      if (hasRegexMeta(l)) {
        return l;
      }
      return `\\\\b${l}\\\\b`;
    });
}

function displayPatternWeights(obj) {
  return Object.entries(obj || {})
    .map(([k, v]) => `${displayRegex([k])}:${v}`)
    .join("\n");
}

function parsePatternWeights(text) {
  const obj = {};
  text.split("\n").forEach((line) => {
    const trimmed = line.trim();
    if (!trimmed) return;
    const idx = trimmed.lastIndexOf(":");
    if (idx <= 0) return;
    const key = trimmed.slice(0, idx).trim();
    const val = Number(trimmed.slice(idx + 1).trim());
    if (Number.isNaN(val)) return;
    const parsed = parseRegexLines(key).join("");
    obj[parsed] = val;
  });
  return obj;
}

function parsePostedMinutes(posted) {
  if (!posted) return null;
  const firstLine = posted.split("\n")[0].toLowerCase().trim();
  if (!firstLine) return null;
  if (firstLine.includes("just now")) return 0;
  const min = firstLine.match(/(\d+)\s*min/);
  if (min) return Number(min[1]);
  const hour = firstLine.match(/(\d+)\s*hour/);
  if (hour) return Number(hour[1]) * 60;
  const day = firstLine.match(/(\d+)\s*day/);
  if (day) return Number(day[1]) * 60 * 24;
  return null;
}

function formatMinutesAgo(totalMinutes) {
  if (totalMinutes == null) return "";
  const mins = Math.max(0, Math.round(totalMinutes));
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  const rem = mins % 60;
  if (hours < 24) return rem ? `${hours}h ${rem}m ago` : `${hours}h ago`;
  const days = Math.floor(hours / 24);
  const hr = hours % 24;
  return hr ? `${days}d ${hr}h ago` : `${days}d ago`;
}

function computeLivePosted(posted, scrapedAt) {
  const base = parsePostedMinutes(posted);
  if (base == null) return posted || "";
  if (!scrapedAt) return formatMinutesAgo(base);
  const scrapedMs = Date.parse(scrapedAt);
  if (Number.isNaN(scrapedMs)) return formatMinutesAgo(base);
  const nowMs = Date.now();
  const extra = Math.max(0, (nowMs - scrapedMs) / 60000);
  return formatMinutesAgo(base + extra);
}

function badgeClass(group, value) {
  const v = (value || "").toLowerCase();
  if (!v) return "badge neutral";
  if (group === "qualified") {
    if (v === "yes") return "badge good";
    if (v === "maybe") return "badge warn";
    if (v === "no") return "badge bad";
  }
  if (group === "next_action") {
    if (v === "apply") return "badge good";
    if (v === "review_manually" || v === "review") return "badge warn";
    if (v === "skip") return "badge bad";
  }
  if (group === "cold_call_risk") {
    if (v === "low") return "badge good";
    if (v === "medium") return "badge warn";
    if (v === "high") return "badge bad";
  }
  if (group === "workplace_match") {
    if (v === "good") return "badge good";
    if (v === "ok") return "badge warn";
    if (v === "bad") return "badge bad";
  }
  if (group === "mobility_signal") {
    if (v === "high") return "badge good";
    if (v === "medium") return "badge warn";
    if (v === "low") return "badge bad";
  }
  if (group === "salary_verdict") {
    if (v === "meets") return "badge good";
    if (v === "below") return "badge bad";
  }
  return "badge neutral";
}

export default function App() {
  const [tab, setTab] = useState("jobs");
  const [jobs, setJobs] = useState([]);
  const [coverJobs, setCoverJobs] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [selected, setSelected] = useState(null);
  const [detailDraft, setDetailDraft] = useState({
    rating: "",
    notes: "",
    tags: "",
    status: "",
    shortlist_verdict: "",
    shortlist_reason: "",
    correct_bucket: "",
    reasoning_quality: ""
  });
  const [filters, setFilters] = useState({ search: "", workplace: "", status: "", rating: "", min_score: "", date_filter: "", source: "" });
  const [settings, setSettings] = useState({ preferences: DEFAULT_PREFS, rules: DEFAULT_RULES });
  const [settingsLoaded, setSettingsLoaded] = useState(false);
  const [saveState, setSaveState] = useState("");
  const [runLog, setRunLog] = useState("");
  const [running, setRunning] = useState(false);
  const [activeStep, setActiveStep] = useState("");
  const [streamOk, setStreamOk] = useState(false);
  const [progress, setProgress] = useState({ current: 0, total: 0, pct: 0, label: "" });
  const [suggestions, setSuggestions] = useState([]);
  const [searches, setSearches] = useState([]);
  const [selectedSearch, setSelectedSearch] = useState("");
  const [sizePreset, setSizePreset] = useState("Large");
  const [searchQuery, setSearchQuery] = useState("");
  const logSourceRef = useRef(null);
  const logCursorRef = useRef(0);
  const logRef = useRef(null);
  const coverEstimateTimer = useRef(null);
  const [detailSaved, setDetailSaved] = useState("");
  const [coverJobId, setCoverJobId] = useState(null);
  const [coverJob, setCoverJob] = useState(null);
  const [coverLetters, setCoverLetters] = useState([]);
  const [coverSelectedId, setCoverSelectedId] = useState(null);
  const [coverDraft, setCoverDraft] = useState({ content: "", feedback: "" });
  const [coverTemplates, setCoverTemplates] = useState([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState("");
  const [templateModalOpen, setTemplateModalOpen] = useState(false);
  const [templateModalMode, setTemplateModalMode] = useState("new");
  const [templateDraftText, setTemplateDraftText] = useState("");
  const [lockStates, setLockStates] = useState([]);
  const [lockStatesByVersion, setLockStatesByVersion] = useState({});
  const [coverEstimate, setCoverEstimate] = useState(null);
  const [pipelineEstimate, setPipelineEstimate] = useState(null);
  const [coverStatus, setCoverStatus] = useState("");
  const [coverModel, setCoverModel] = useState("gpt-4.1");
  const [coverSearch, setCoverSearch] = useState("");
  const [evalModel, setEvalModel] = useState("gpt-4.1-mini");
  const COVER_MODELS = ["gpt-5.1", "gpt-5", "gpt-4.1"];
  const EVAL_MODELS = ["gpt-5-mini", "gpt-4.1-mini", "gpt-4.1", "gpt-5.1", "gpt-5"];
  const selectedTemplate = coverTemplates.find((t) => t.id === selectedTemplateId) || null;
  const bodyParagraphs = splitCoverSections(coverDraft.content || "").body;
  const selectedTemplateBodyCount = selectedTemplate
    ? splitCoverSections(selectedTemplate.text || "").body.length
    : 0;
  const templateWarning =
    selectedTemplate && (selectedTemplateBodyCount < 3 || selectedTemplateBodyCount > 5)
      ? `Template has ${selectedTemplateBodyCount} body paragraphs (recommended 3-5).`
      : "";

  useEffect(() => {
    fetchJobs();
    fetchCoverJobs();
    fetchSettings();
    fetchSearches();
    fetchCoverTemplates();
  }, []);

  useEffect(() => {
    const id = setTimeout(() => {
      fetchJobs();
    }, 250);
    return () => clearTimeout(id);
  }, [filters]);

  useEffect(() => {
    if (!running || streamOk) return;
    const id = setInterval(() => {
      fetchJobs();
      fetchRunState();
    }, 5000);
    return () => clearInterval(id);
  }, [running, streamOk]);

  useEffect(() => {
    if (!running || !streamOk) return;
    const id = setInterval(() => {
      fetchRunState(true);
    }, 3000);
    return () => clearInterval(id);
  }, [running, streamOk]);

  useEffect(() => {
    const el = logRef.current;
    if (!el) return;
    const nearBottom = el.scrollTop + el.clientHeight >= el.scrollHeight - 24;
    if (nearBottom) {
      el.scrollTop = el.scrollHeight;
    }
  }, [runLog]);

  useEffect(() => {
    if (selectedId) {
      fetch(`${API}/jobs/${selectedId}`)
        .then((r) => r.json())
        .then((data) => {
          setSelected(data);
          setDetailDraft({
            rating: data.rating ?? "",
            notes: "",
            tags: (data.tags || []).join(", "),
            status: data.status ?? "",
            shortlist_verdict: data.shortlist_verdict ?? "",
            shortlist_reason: data.shortlist_reason ?? "",
            correct_bucket: data.correct_bucket ?? "",
            reasoning_quality: data.reasoning_quality ?? ""
          });
        });
    }
  }, [selectedId]);

  useEffect(() => {
    if (!coverJobId) {
      setCoverJob(null);
      setCoverLetters([]);
      setCoverSelectedId(null);
      setCoverDraft({ content: "", feedback: "" });
      setSelectedTemplateId("");
      setLockStatesByVersion({});
      return;
    }
    fetch(`${API}/jobs/${coverJobId}`)
      .then((r) => r.json())
      .then((data) => setCoverJob(data));
    fetchCoverLetters(coverJobId);
  }, [coverJobId]);

  useEffect(() => {
    if (!coverSelectedId) return;
    const found = coverLetters.find((c) => c.id === coverSelectedId);
    if (found) {
      setCoverDraft({ content: found.content || "", feedback: found.feedback || "" });
    }
  }, [coverSelectedId, coverLetters]);

  useEffect(() => {
    if (!coverSelectedId) {
      setLockStates([]);
      return;
    }
    const saved = lockStatesByVersion[coverSelectedId] || [];
    if (!bodyParagraphs.length) {
      setLockStates([]);
      return;
    }
    setLockStates(bodyParagraphs.map((_, idx) => !!saved[idx]));
  }, [bodyParagraphs.length, coverSelectedId, lockStatesByVersion]);

  const fetchJobs = () => {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([k, v]) => {
      if (v !== "" && v !== null && v !== undefined) params.set(k, v);
    });
    fetch(`${API}/jobs?${params.toString()}`)
      .then((r) => r.json())
      .then(setJobs);
  };

  const fetchCoverJobs = () => {
    fetch(`${API}/jobs`)
      .then((r) => r.json())
      .then(setCoverJobs)
      .catch(() => {});
  };

  const fetchCoverLetters = (jobId) => {
    fetch(`${API}/cover-letters/${jobId}`)
      .then((r) => r.json())
      .then((data) => {
        const items = data.items || [];
        setCoverLetters(items);
        if (items.length && !coverSelectedId) {
          setCoverSelectedId(items[0].id);
        }
        if (items.length === 0) {
          setCoverSelectedId(null);
          setCoverDraft({ content: "", feedback: "" });
          setLockStates([]);
        }
      })
      .catch(() => {});
  };

  useEffect(() => {
    if (tab !== "cover") return;
    setSelectedTemplateId("");
    setCoverSelectedId(null);
    setCoverDraft({ content: "", feedback: "" });
    setLockStates([]);
    setLockStatesByVersion({});
  }, [tab]);

  useEffect(() => {
    if (tab !== "cover") return;
    if (coverEstimateTimer.current) {
      clearTimeout(coverEstimateTimer.current);
    }
    coverEstimateTimer.current = setTimeout(() => {
      fetchCoverEstimate();
    }, 400);
    return () => {
      if (coverEstimateTimer.current) clearTimeout(coverEstimateTimer.current);
    };
  }, [
    tab,
    coverJobId,
    coverDraft.content,
    coverDraft.feedback,
    coverModel,
    selectedTemplateId,
    lockStates
  ]);

  useEffect(() => {
    if (tab !== "pipeline") return;
    fetchPipelineEstimate(sizePreset, evalModel);
  }, [tab, sizePreset, evalModel]);

  const fetchCoverTemplates = () => {
    fetch(`${API}/cover-letter-templates`)
      .then((r) => r.json())
      .then((data) => {
        const items = data.items || [];
        setCoverTemplates(items);
        if (selectedTemplateId && !items.find((t) => t.id === selectedTemplateId)) {
          setSelectedTemplateId("");
        }
      })
      .catch(() => {});
  };

  const fetchCoverEstimate = () => {
    if (!coverJobId) {
      setCoverEstimate(null);
      return;
    }
    const locked_indices = lockStates
      .map((locked, idx) => (locked ? idx : null))
      .filter((v) => v !== null);
    fetch(`${API}/ai/estimate/cover-letter`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        job_id: coverJobId,
        feedback: coverDraft.feedback,
        model: coverModel,
        template_id: selectedTemplateId || null,
        draft: coverDraft.content,
        locked_indices
      })
    })
      .then((r) => r.json())
      .then((data) => setCoverEstimate(data))
      .catch(() => setCoverEstimate(null));
  };

  const fetchPipelineEstimate = (size, model) => {
    if (!size) return;
    fetch(`${API}/ai/estimate/pipeline`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ size, model })
    })
      .then((r) => r.json())
      .then((data) => setPipelineEstimate(data))
      .catch(() => setPipelineEstimate(null));
  };


  const fetchSettings = () => {
    fetch(`${API}/settings`)
      .then((r) => r.json())
      .then((data) => {
        setSettings({
          preferences: data.preferences || DEFAULT_PREFS,
          rules: data.rules || DEFAULT_RULES
        });
        setSettingsLoaded(true);
      })
      .catch(() => setSettingsLoaded(true));
  };

  const fetchSearches = () => {
    fetch(`${API}/searches`)
      .then((r) => r.json())
      .then((data) => {
        const items = data.searches || [];
        setSearches(items);
        if (!selectedSearch && items.length) {
          setSelectedSearch(items[0].label);
        }
      })
      .catch(() => {});
  };

  const saveSettings = () => {
    setSaveState("saving");
    fetch(`${API}/settings`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(settings)
    })
      .then(() => setSaveState("saved"))
      .catch(() => setSaveState("error"));
  };

  const importExisting = () => {
    fetch(`${API}/import`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({})
    }).then(fetchJobs);
  };

  const runStep = (step) => {
    if (running) return;
    setRunLog(`Starting ${step}...\n`);
    setActiveStep(step);
    setRunning(true);
    setStreamOk(false);
    logCursorRef.current = 0;
    setProgress({ current: 0, total: 0, pct: 0, label: step });

    const params = new URLSearchParams();
    if (step === "scout" && selectedSearch) params.set("search", selectedSearch);
    if (step === "scout" && searchQuery) params.set("query", searchQuery);
    if (step === "eval" && evalModel) params.set("model", evalModel);
    const searchParam = params.toString() ? `?${params.toString()}` : "";
    fetch(`${API}/run/${step}${searchParam}`, { method: "POST" })
      .then((r) => r.json())
      .then(() => {
        if (logSourceRef.current) {
          logSourceRef.current.close();
        }
        const source = new EventSource(`${API}/runs/stream`);
        logSourceRef.current = source;

        source.onopen = () => {
          setStreamOk(true);
        };

        source.onmessage = (event) => {
          setRunLog((prev) => prev + event.data + "\n");
          logCursorRef.current += 1;
          const next = parseProgressLine(event.data);
          if (next) {
            setProgress((prev) => {
              const total = next.total ?? prev.total;
              const current = next.current ?? prev.current;
              const pct = next.pct ?? (total ? (current / total) * 100 : prev.pct);
              const label = next.label ?? prev.label;
              return { current, total, pct, label };
            });
          }
        };

        source.addEventListener("done", (event) => {
          setRunLog((prev) => prev + `\nFinished (${event.data}).\n`);
          setRunning(false);
          setActiveStep("");
          setStreamOk(false);
          source.close();
          fetchJobs();
          fetchRunState(true);
        });

        source.onerror = () => {
          setRunLog((prev) => prev + "\nLive stream unavailable; switching to polling.\n");
          syncRunCursor();
          setStreamOk(false);
          source.close();
        };
      });
  };

  const runPipeline = () => {
    if (running) return;
    const ok = window.confirm("Start a new run? This will fetch fresh jobs and update today’s data.");
    if (!ok) return;
    if (!selectedSearch) {
      setRunLog("Please select a search before starting.\n");
      return;
    }
    setRunLog("Starting pipeline...\n");
    setActiveStep("pipeline");
    setRunning(true);
    setStreamOk(false);
    logCursorRef.current = 0;
    setProgress({ current: 0, total: 0, pct: 0, label: "pipeline" });

    fetch(`${API}/run/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ search: selectedSearch, size: sizePreset, query: searchQuery, eval_model: evalModel })
    })
      .then(async (r) => {
        const data = await r.json().catch(() => ({}));
        if (!r.ok || data.ok === false) {
          const msg = data.detail || data.error || "Start failed.";
          setRunLog(`Start failed: ${msg}\n`);
          setRunning(false);
          setActiveStep("");
          return;
        }

        if (logSourceRef.current) {
          logSourceRef.current.close();
        }
        const source = new EventSource(`${API}/runs/stream`);
        logSourceRef.current = source;

        source.onopen = () => {
          setStreamOk(true);
        };

        source.onmessage = (event) => {
          setRunLog((prev) => prev + event.data + "\n");
          logCursorRef.current += 1;
          const next = parseProgressLine(event.data);
          if (next) {
            setProgress((prev) => {
              const total = next.total ?? prev.total;
              const current = next.current ?? prev.current;
              const pct = next.pct ?? (total ? (current / total) * 100 : prev.pct);
              const label = next.label ?? prev.label;
              return { current, total, pct, label };
            });
          }
        };

        source.addEventListener("done", (event) => {
          setRunLog((prev) => prev + `\nFinished (${event.data}).\n`);
          setRunning(false);
          setActiveStep("");
          setStreamOk(false);
          source.close();
          fetchJobs();
          fetchRunState(true);
        });

        source.onerror = () => {
          setRunLog((prev) => prev + "\nLive stream unavailable; switching to polling.\n");
          syncRunCursor();
          setStreamOk(false);
          source.close();
        };
      });
  };

  const syncRunCursor = () => {
    fetch(`${API}/runs/state`)
      .then((r) => r.json())
      .then((state) => {
        if (!state || !state.lines) return;
        logCursorRef.current = state.lines.length;
      })
      .catch(() => {});
  };

  const fetchRunState = (onlyProgress = false) => {
    fetch(`${API}/runs/state`)
      .then((r) => r.json())
      .then((state) => {
        if (!state || !state.lines) return;
        if (!onlyProgress && !streamOk) {
          const cursor = logCursorRef.current;
          const newLines = state.lines.slice(cursor);
          if (newLines.length) {
            setRunLog((prev) => prev + newLines.join("\n") + "\n");
            logCursorRef.current = state.lines.length;
          }
        }
        if (state.progress) {
          setProgress(state.progress);
        }
        if (!state.running && running) {
          setRunning(false);
          setActiveStep("");
        }
      })
      .catch(() => {});
  };

  const saveRating = (payload) => {
    fetch(`${API}/ratings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }).then(() => {
      setDetailSaved("Saved");
      setTimeout(() => setDetailSaved(""), 1500);
      fetchJobs();
    });
  };

  const saveStatus = (payload) => {
    fetch(`${API}/status`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }).then(() => {
      setDetailSaved("Saved");
      setTimeout(() => setDetailSaved(""), 1500);
      fetchJobs();
    });
  };

  const generateSuggestions = () => {
    fetch(`${API}/suggestions/generate`, { method: "POST" })
      .then((r) => r.json())
      .then((data) => setSuggestions(data.suggestions || []));
  };

  const applySuggestions = () => {
    fetch(`${API}/suggestions/apply`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ operations: suggestions })
    }).then(() => {
      setSuggestions([]);
      fetchSettings();
    });
  };

  const openTemplateModal = (mode) => {
    setTemplateModalMode(mode);
    if (mode === "edit" && selectedTemplate) {
      setTemplateDraftText(selectedTemplate.text || "");
    } else if (mode === "duplicate" && selectedTemplate) {
      setTemplateDraftText(selectedTemplate.text || "");
    } else {
      setTemplateDraftText("");
    }
    setTemplateModalOpen(true);
  };

  const saveTemplateDraft = () => {
    const text = templateDraftText || "";
    if (templateModalMode === "edit" && selectedTemplate) {
      fetch(`${API}/cover-letter-templates/${selectedTemplate.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text })
      })
        .then((r) => r.json())
        .then((data) => {
          if (data?.item?.id) {
            setSelectedTemplateId(data.item.id);
          }
          setTemplateModalOpen(false);
          fetchCoverTemplates();
        })
        .catch(() => {});
      return;
    }
    fetch(`${API}/cover-letter-templates`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text })
    })
      .then((r) => r.json())
      .then((data) => {
        if (data?.item?.id) {
          setSelectedTemplateId(data.item.id);
        }
        setTemplateModalOpen(false);
        fetchCoverTemplates();
      })
      .catch(() => {});
  };

  const deleteTemplate = () => {
    if (!selectedTemplate) return;
    const ok = window.confirm("Delete this template? This cannot be undone.");
    if (!ok) return;
    fetch(`${API}/cover-letter-templates/${selectedTemplate.id}`, { method: "DELETE" })
      .then(() => {
        setSelectedTemplateId("");
        fetchCoverTemplates();
      })
      .catch(() => {});
  };

  const applyTemplateToDraft = (templateId) => {
    const template = coverTemplates.find((t) => t.id === templateId);
    if (!template) return;
    const updated = applyDateToTemplate(template.text || "", coverJob?.company || "");
    setCoverDraft((prev) => ({ ...prev, content: updated }));
    setCoverSelectedId(null);
  };

  const generateCoverLetter = () => {
    if (!coverJobId) return;
    setCoverStatus("Generating...");
    const locked_indices = lockStates
      .map((locked, idx) => (locked ? idx : null))
      .filter((v) => v !== null);
    fetch(`${API}/cover-letters/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        job_id: coverJobId,
        feedback: coverDraft.feedback,
        model: coverModel,
        template_id: selectedTemplateId || null,
        draft: coverDraft.content,
        locked_indices
      })
    })
      .then(async (r) => {
        const data = await r.json().catch(() => ({}));
        if (!r.ok || data.ok === false) {
          throw new Error(data.detail || "Failed");
        }
        setCoverStatus("Saved");
        setTimeout(() => setCoverStatus(""), 1500);
        fetchCoverLetters(coverJobId);
        if (data.id) {
          setLockStatesByVersion((map) => ({
            ...map,
            [data.id]: [...lockStates]
          }));
          setCoverSelectedId(data.id);
        }
      })
      .catch((err) => {
        setCoverStatus(`Error: ${err.message || "Failed"}`);
      });
  };

  const saveCoverLetter = () => {
    if (!coverSelectedId) return;
    setCoverStatus("Saving...");
    fetch(`${API}/cover-letters/save`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: coverSelectedId, content: coverDraft.content, feedback: coverDraft.feedback })
    })
      .then(() => {
        setCoverStatus("Saved");
        setTimeout(() => setCoverStatus(""), 1500);
        fetchCoverLetters(coverJobId);
      })
      .catch(() => setCoverStatus("Error"));
  };

  const exportCoverLetter = (format) => {
    if (!coverSelectedId) return;
    setCoverStatus("Exporting...");
    fetch(`${API}/cover-letters/export/${coverSelectedId}?format=${format}`)
      .then((r) => r.json())
      .then((data) => {
        if (!data || data.ok !== true) throw new Error("Export failed");
        setCoverStatus(`Saved to ${data.path}`);
        setTimeout(() => setCoverStatus(""), 2500);
      })
      .catch(() => setCoverStatus("Export failed"));
  };

  return (
    <div className="app">
      <header className="topbar">
        <div>
          <h1>Job Finder Dashboard</h1>
          <p>Shortlist + rating loop tuned to your preferences</p>
        </div>
        <div className="tabs">
          <button className={classNames(tab === "jobs" && "active")} onClick={() => setTab("jobs")}>Jobs</button>
          <button className={classNames(tab === "settings" && "active")} onClick={() => setTab("settings")}>Settings</button>
          <button className={classNames(tab === "pipeline" && "active")} onClick={() => setTab("pipeline")}>Pipeline</button>
          <button className={classNames(tab === "cover" && "active")} onClick={() => setTab("cover")}>Cover Letters</button>
        </div>
      </header>

      {tab === "jobs" && (
        <section className="jobs">
          <div className="filters">
            <input
              placeholder="Search title/company"
              value={filters.search}
              onChange={(e) => setFilters({ ...filters, search: e.target.value })}
            />
            <select value={filters.workplace} onChange={(e) => setFilters({ ...filters, workplace: e.target.value })}>
              <option value="">Workplace</option>
              <option value="remote">Remote</option>
              <option value="hybrid">Hybrid</option>
              <option value="onsite">Onsite</option>
            </select>
            <select value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })}>
              <option value="">Status</option>
              <option value="applied">Applied</option>
              <option value="interview">Interview</option>
              <option value="offer">Offer</option>
              <option value="rejected">Rejected</option>
            </select>
            <select value={filters.rating} onChange={(e) => setFilters({ ...filters, rating: e.target.value })}>
              <option value="">Rating</option>
              {[1, 2, 3, 4, 5].map((n) => (
                <option key={n} value={n}>{n}★</option>
              ))}
            </select>
            <input
              type="number"
              placeholder="Min score"
              value={filters.min_score}
              onChange={(e) => setFilters({ ...filters, min_score: e.target.value })}
            />
            <select value={filters.source || ""} onChange={(e) => setFilters({ ...filters, source: e.target.value })}>
              <option value="">All searches</option>
              {searches.map((s) => (
                <option key={s.label} value={s.label}>{s.label}</option>
              ))}
            </select>
            <button
              className={classNames(filters.date_filter === "today" && "active")}
              onClick={() => setFilters({ ...filters, date_filter: "today" })}
            >
              Today
            </button>
            <button
              className={classNames(filters.date_filter === "last24" && "active")}
              onClick={() => setFilters({ ...filters, date_filter: "last24" })}
            >
              Last 24h
            </button>
            <button
              className={classNames(filters.date_filter === "" && "active")}
              onClick={() => setFilters({ ...filters, date_filter: "" })}
            >
              All
            </button>
          </div>

          <div className="content">
            <div className="table">
              <div className="row header">
                <div>#</div>
                <div>Score</div>
                <div>Title</div>
                <div>Company</div>
                <div>Workplace</div>
                <div>Posted</div>
                <div>Salary</div>
                <div>Status</div>
                <div>Rating</div>
              </div>
              {jobs.map((job, idx) => (
                <div
                  key={job.id}
                  className={classNames("row", selectedId === job.id && "selected")}
                  onClick={() => setSelectedId(job.id)}
                >
                  <div>{idx + 1}</div>
                  <div>{Math.round(job.score || 0)}</div>
                  <div>{job.title}</div>
                  <div>{job.company}</div>
                  <div>{job.workplace || "unknown"}</div>
                  <div>{computeLivePosted(job.posted, job.scraped_at)}</div>
                  <div>{job.salary_hint || ""}</div>
                  <div>{job.status || ""}</div>
                  <div>{job.rating ? `${job.rating}★` : ""}</div>
                </div>
              ))}
            </div>

            <aside className="detail">
              {selected ? (
                <div>
                  <h2>{selected.title}</h2>
                  <div className="meta">
                    <span>{selected.company}</span>
                    <span>{selected.location}</span>
                    <span>{selected.workplace}</span>
                    <span>{selected.posted ? computeLivePosted(selected.posted, selected.scraped_at) : ""}</span>
                  </div>
                  <div className="meta meta-row">
                    <span>Score: {selected.fit_score ?? selected.shortlist_score ?? "n/a"}</span>
                    <span>Bucket: {selected.bucket || ""}</span>
                    <a href={selected.url} target="_blank" rel="noreferrer">Open listing</a>
                    <button
                      className="ghost"
                      onClick={() => {
                        setCoverJobId(selected.id);
                        setCoverSelectedId(null);
                        setTab("cover");
                      }}
                    >
                      Cover letter
                    </button>
                  </div>

                  <div className="panel">
                    <h3>Rate this job</h3>
                    {detailSaved && <div className="saved">{detailSaved}</div>}
                    <div className="field">
                      <label>Stars (1–5)</label>
                      <input
                        type="number"
                        min="1"
                        max="5"
                        value={detailDraft.rating}
                        onChange={(e) => setDetailDraft({ ...detailDraft, rating: e.target.value })}
                        onBlur={(e) => {
                          const value = Number(e.target.value || 0);
                          if (value < 1 || value > 5) return;
                          saveRating({
                            job_id: selected.id,
                            stars: value,
                            notes: "",
                            tags: detailDraft.tags.split(",").map((t) => t.trim()).filter(Boolean)
                          });
                        }}
                      />
                    </div>
                    <div className="field">
                      <label>Tags (comma separated)</label>
                      <input
                        value={detailDraft.tags}
                        onChange={(e) => setDetailDraft({ ...detailDraft, tags: e.target.value })}
                        onBlur={(e) => saveRating({
                          job_id: selected.id,
                          stars: Number(detailDraft.rating || 0) || 1,
                          notes: "",
                          tags: e.target.value.split(",").map((t) => t.trim()).filter(Boolean)
                        })}
                      />
                    </div>
                    <div className="field">
                      <label>Status</label>
                      <select
                        value={detailDraft.status}
                        onChange={(e) => {
                          setDetailDraft({ ...detailDraft, status: e.target.value });
                          saveStatus({ job_id: selected.id, status: e.target.value });
                        }}
                      >
                        <option value="">None</option>
                        <option value="applied">Applied</option>
                        <option value="interview">Interview</option>
                        <option value="offer">Offer</option>
                        <option value="rejected">Rejected</option>
                      </select>
                    </div>
                  </div>

                  <div className="panel">
                    <h3>Shortlist feedback</h3>
                    <div className="field">
                      <label>Keep or remove?</label>
                      <select
                        value={detailDraft.shortlist_verdict}
                        onChange={(e) => {
                          if (!e.target.value) return;
                          setDetailDraft({ ...detailDraft, shortlist_verdict: e.target.value });
                          fetch(`${API}/feedback/shortlist`, {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({
                              job_id: selected.id,
                              verdict: e.target.value,
                              reason: detailDraft.shortlist_reason || ""
                            })
                          }).then(() => {
                            setDetailSaved("Saved");
                            setTimeout(() => setDetailSaved(""), 1500);
                          });
                        }}
                      >
                        <option value="">No feedback</option>
                        <option value="keep">Keep</option>
                        <option value="remove">Remove</option>
                      </select>
                    </div>
                    <div className="field">
                      <label>Quick remove reasons</label>
                      <div className="pill-row">
                        {SHORTLIST_REASONS.map((r) => (
                          <button
                            key={r.value}
                            className={classNames("pill", detailDraft.shortlist_reason === r.value && "active")}
                            onClick={() => {
                              setDetailDraft({
                                ...detailDraft,
                                shortlist_verdict: "remove",
                                shortlist_reason: r.value
                              });
                              fetch(`${API}/feedback/shortlist`, {
                                method: "POST",
                                headers: { "Content-Type": "application/json" },
                                body: JSON.stringify({
                                  job_id: selected.id,
                                  verdict: "remove",
                                  reason: r.value
                                })
                              }).then(() => {
                                setDetailSaved("Saved");
                                setTimeout(() => setDetailSaved(""), 1500);
                              });
                            }}
                          >
                            {r.label}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div className="panel">
                    <h3>AI eval feedback</h3>
                    <div className="field">
                      <label>Correct bucket?</label>
                      <select
                        value={detailDraft.correct_bucket}
                        onChange={(e) => {
                          if (!e.target.value) return;
                          setDetailDraft({ ...detailDraft, correct_bucket: e.target.value });
                          fetch(`${API}/feedback/ai`, {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({
                              job_id: selected.id,
                              correct_bucket: e.target.value,
                              reasoning_quality: Number(detailDraft.reasoning_quality || 3)
                            })
                          }).then(() => {
                            setDetailSaved("Saved");
                            setTimeout(() => setDetailSaved(""), 1500);
                          });
                        }}
                      >
                        <option value="">No feedback</option>
                        <option value="apply">Apply</option>
                        <option value="review">Review</option>
                        <option value="skip">Skip</option>
                      </select>
                    </div>
                    <div className="field">
                      <label>Reasoning quality (1–5)</label>
                      <input
                        type="number"
                        min="1"
                        max="5"
                        value={detailDraft.reasoning_quality}
                        onChange={(e) => setDetailDraft({ ...detailDraft, reasoning_quality: e.target.value })}
                        onBlur={(e) => {
                          const value = Number(e.target.value || 0);
                          if (value < 1 || value > 5) return;
                          if (!detailDraft.correct_bucket) return;
                          fetch(`${API}/feedback/ai`, {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({
                              job_id: selected.id,
                              correct_bucket: detailDraft.correct_bucket || "review",
                              reasoning_quality: value
                            })
                          }).then(() => {
                            setDetailSaved("Saved");
                            setTimeout(() => setDetailSaved(""), 1500);
                          });
                        }}
                      />
                    </div>
                  </div>

                  <div className="panel">
                    <h3>AI Evaluation</h3>
                    {selected.eval_json ? (
                      <div className="ai-eval">
                        <div className="ai-summary">
                          <div className="ai-summary-label">Job summary</div>
                          <p>{selected.eval_json.job_summary || "No summary available."}</p>
                        </div>
                        <div className="ai-score">
                          <div className="ai-score-value">{selected.eval_json.fit_score ?? "–"}</div>
                          <div className="ai-score-label">Fit Score</div>
                        </div>
                        <div className="ai-meta">
                          <div>
                            <span>Qualified</span>
                            <span className={badgeClass("qualified", selected.eval_json.qualified)}>
                              {selected.eval_json.qualified || "unknown"}
                            </span>
                          </div>
                          <div>
                            <span>Next Action</span>
                            <span className={badgeClass("next_action", selected.eval_json.next_action)}>
                              {selected.eval_json.next_action || "review"}
                            </span>
                          </div>
                          <div>
                            <span>Cold Call Risk</span>
                            <span className={badgeClass("cold_call_risk", selected.eval_json.cold_call_risk)}>
                              {selected.eval_json.cold_call_risk || "unknown"}
                            </span>
                          </div>
                          <div>
                            <span>Employment OK</span>
                            <span className={selected.eval_json.employment_type_ok ? "badge good" : "badge bad"}>
                              {String(selected.eval_json.employment_type_ok ?? false)}
                            </span>
                          </div>
                          <div>
                            <span>Workplace Match</span>
                            <span className={badgeClass("workplace_match", selected.eval_json.workplace_match)}>
                              {selected.eval_json.workplace_match || "unknown"}
                            </span>
                          </div>
                          <div>
                            <span>Mobility Signal</span>
                            <span className={badgeClass("mobility_signal", selected.eval_json.mobility_signal)}>
                              {selected.eval_json.mobility_signal || "unknown"}
                            </span>
                          </div>
                          <div>
                            <span>Salary Verdict</span>
                            <span className={badgeClass("salary_verdict", selected.eval_json.salary_verdict)}>
                              {selected.eval_json.salary_verdict || "unknown"}
                            </span>
                          </div>
                        </div>
                        <div className="ai-grid">
                          <div>
                            <h4>Top Reasons</h4>
                            <ul>
                              {(selected.eval_json.top_reasons || []).map((r, i) => (
                                <li key={`tr-${i}`}>{r}</li>
                              ))}
                            </ul>
                          </div>
                          <div>
                            <h4>Red Flags</h4>
                            <ul>
                              {(selected.eval_json.red_flags || []).map((r, i) => (
                                <li key={`rf-${i}`}>{r}</li>
                              ))}
                            </ul>
                          </div>
                          <div>
                            <h4>Resume Angles</h4>
                            <ul>
                              {(selected.eval_json.resume_angles || []).map((r, i) => (
                                <li key={`ra-${i}`}>{r}</li>
                              ))}
                            </ul>
                          </div>
                          <div>
                            <h4>Missing Gaps</h4>
                            <ul>
                              {(selected.eval_json.missing_gaps || []).map((r, i) => (
                                <li key={`mg-${i}`}>{r}</li>
                              ))}
                            </ul>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="empty">No AI evaluation yet.</div>
                    )}
                  </div>

                  <div className="panel">
                    <h3>Description</h3>
                    <div className="description">
                      {(selected.description || "No description loaded yet.")
                        .split("\n")
                        .map((line, idx) => (
                          <p key={idx}>{line}</p>
                        ))}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="empty">Select a job to see details.</div>
              )}
            </aside>
          </div>
        </section>
      )}

      {tab === "settings" && settingsLoaded && (
        <section className="settings">
          <div className="settings-grid">
            <div className="panel">
              <h2>Preferences</h2>
              <div className="field">
                <label>Soft‑penalize industries (comma list)</label>
                <input
                  value={settings.preferences.industry_preferences?.soft_penalize?.join(", ") || ""}
                  onChange={(e) => {
                    const list = e.target.value.split(",").map((t) => t.trim()).filter(Boolean);
                    setSettings({
                      ...settings,
                      preferences: {
                        ...settings.preferences,
                        industry_preferences: { ...settings.preferences.industry_preferences, soft_penalize: list }
                      }
                    });
                  }}
                />
              </div>
              <div className="field checkbox">
                <label>
                  <input
                    type="checkbox"
                    checked={!!settings.preferences.role_preferences?.soft_penalize_sales_adjacent}
                    onChange={(e) => setSettings({
                      ...settings,
                      preferences: {
                        ...settings.preferences,
                        role_preferences: {
                          ...settings.preferences.role_preferences,
                          soft_penalize_sales_adjacent: e.target.checked
                        }
                      }
                    })}
                  />
                  Soft‑penalize sales‑adjacent roles
                </label>
              </div>
              <div className="field checkbox">
                <label>
                  <input
                    type="checkbox"
                    checked={!!settings.preferences.role_preferences?.hard_block_outbound_cold_calling}
                    onChange={(e) => setSettings({
                      ...settings,
                      preferences: {
                        ...settings.preferences,
                        role_preferences: {
                          ...settings.preferences.role_preferences,
                          hard_block_outbound_cold_calling: e.target.checked
                        }
                      }
                    })}
                  />
                  Hard‑block outbound cold calling
                </label>
              </div>
              <div className="field checkbox">
                <label>
                  <input
                    type="checkbox"
                    checked={!!settings.preferences.role_preferences?.allow_minimal_outbound}
                    onChange={(e) => setSettings({
                      ...settings,
                      preferences: {
                        ...settings.preferences,
                        role_preferences: {
                          ...settings.preferences.role_preferences,
                          allow_minimal_outbound: e.target.checked
                        }
                      }
                    })}
                  />
                  Allow minimal outbound
                </label>
              </div>
              <div className="field checkbox">
                <label>
                  <input
                    type="checkbox"
                    checked={!!settings.preferences.role_preferences?.inbound_ok}
                    onChange={(e) => setSettings({
                      ...settings,
                      preferences: {
                        ...settings.preferences,
                        role_preferences: {
                          ...settings.preferences.role_preferences,
                          inbound_ok: e.target.checked
                        }
                      }
                    })}
                  />
                  Inbound customer contact OK
                </label>
              </div>
              <div className="field">
                <label>Min qualification score</label>
                <input
                  type="number"
                  step="0.05"
                  value={settings.preferences.qualification?.min_match_score ?? 0.55}
                  onChange={(e) => setSettings({
                    ...settings,
                    preferences: {
                      ...settings.preferences,
                      qualification: {
                        ...settings.preferences.qualification,
                        min_match_score: Number(e.target.value)
                      }
                    }
                  })}
                />
              </div>
              <div className="field">
                <label>Safe vs stretch ratio (0–1)</label>
                <input
                  type="number"
                  step="0.05"
                  value={settings.preferences.qualification?.safe_vs_stretch_ratio ?? 0.7}
                  onChange={(e) => setSettings({
                    ...settings,
                    preferences: {
                      ...settings.preferences,
                      qualification: {
                        ...settings.preferences.qualification,
                        safe_vs_stretch_ratio: Number(e.target.value)
                      }
                    }
                  })}
                />
              </div>
              <div className="field checkbox">
                <label>
                  <input
                    type="checkbox"
                    checked={!!settings.preferences.employment?.hard_block_non_full_time}
                    onChange={(e) => setSettings({
                      ...settings,
                      preferences: {
                        ...settings.preferences,
                        employment: { hard_block_non_full_time: e.target.checked }
                      }
                    })}
                  />
                  Hard‑block non‑full‑time roles
                </label>
              </div>
            </div>

            <div className="panel">
              <h2>Shortlist Rules</h2>
              <div className="field">
                <label>Hard reject patterns (one per line)</label>
                <textarea
                  value={displayRegex(settings.rules.hard_reject_patterns)}
                  onChange={(e) => setSettings({
                    ...settings,
                    rules: { ...settings.rules, hard_reject_patterns: parseRegexLines(e.target.value) }
                  })}
                />
              </div>
              <div className="field">
                <label>Not entry‑level patterns (one per line)</label>
                <textarea
                  value={displayRegex(settings.rules.not_entry_level_patterns)}
                  onChange={(e) => setSettings({
                    ...settings,
                    rules: { ...settings.rules, not_entry_level_patterns: parseRegexLines(e.target.value) }
                  })}
                />
              </div>
              <div className="field">
                <label>Title boosts (pattern:weight per line)</label>
                <textarea
                  value={displayPatternWeights(settings.rules.title_boosts)}
                  onChange={(e) => {
                    const obj = parsePatternWeights(e.target.value);
                    setSettings({ ...settings, rules: { ...settings.rules, title_boosts: obj } });
                  }}
                />
              </div>
              <div className="field">
                <label>Company penalties (pattern:weight per line)</label>
                <textarea
                  value={displayPatternWeights(settings.rules.company_penalties)}
                  onChange={(e) => {
                    const obj = parsePatternWeights(e.target.value);
                    setSettings({ ...settings, rules: { ...settings.rules, company_penalties: obj } });
                  }}
                />
              </div>
              <div className="field workplace-grid">
                <label>Workplace score (higher = better)</label>
                {"remote,hybrid,onsite,unknown".split(",").map((key) => (
                  <div className="workplace-row" key={key}>
                    <span className="workplace-label">{key}</span>
                    <input
                      type="number"
                      value={settings.rules.workplace_score?.[key] ?? 0}
                      onChange={(e) => setSettings({
                        ...settings,
                        rules: { ...settings.rules, workplace_score: { ...settings.rules.workplace_score, [key]: Number(e.target.value) } }
                      })}
                      placeholder={key}
                    />
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="actions">
            <button onClick={saveSettings}>Save settings</button>
            <button onClick={importExisting}>Import current files</button>
            <button onClick={generateSuggestions}>Generate suggestions</button>
            {saveState && <span className="status">{saveState}</span>}
          </div>

          {suggestions.length > 0 && (
            <div className="panel">
              <h3>Suggested changes</h3>
              <ul>
                {suggestions.map((s, idx) => (
                  <li key={idx}>{s.reason} ({s.path} → {String(s.value)})</li>
                ))}
              </ul>
              <button onClick={applySuggestions}>Apply suggestions</button>
            </div>
          )}
        </section>
      )}

      {tab === "cover" && (
        <section className="cover">
          <div className="cover-layout">
            <div className="cover-list">
              <div className="panel">
                <h2>Cover Letters</h2>
                <div className="field">
                  <label>Search jobs</label>
                  <input
                    value={coverSearch}
                    onChange={(e) => setCoverSearch(e.target.value)}
                    placeholder="Title or company"
                  />
                </div>
                <div className="mini-list">
                  {coverJobs
                    .filter((job) => {
                      if (!coverSearch) return true;
                      const q = coverSearch.toLowerCase();
                      return (
                        (job.title || "").toLowerCase().includes(q) ||
                        (job.company || "").toLowerCase().includes(q)
                      );
                    })
                    .map((job) => (
                    <button
                      key={job.id}
                      className={classNames("mini-row", coverJobId === job.id && "active")}
                      onClick={() => {
                        setCoverJobId(job.id);
                        setCoverSelectedId(null);
                        setSelectedTemplateId("");
                      }}
                    >
                      <span className="mini-title">{job.title}</span>
                      <span className="mini-company">{job.company}</span>
                    </button>
                  ))}
                </div>
                {coverJob && (
                  <div className="cover-meta">
                    <div className="cover-title">{coverJob.title}</div>
                    <div className="cover-sub">
                      {coverJob.company} · {coverJob.location} · {coverJob.workplace || "unknown"}
                    </div>
                  </div>
                )}
                <div className="cover-versions">
                  <div className="cover-versions-label">Versions</div>
                  {coverLetters.length === 0 && <div className="empty">No cover letters yet.</div>}
                  {coverLetters.map((c) => (
                    <button
                      key={c.id}
                      className={classNames("cover-version", coverSelectedId === c.id && "active")}
                      onClick={() => {
                        setCoverSelectedId(c.id);
                        setSelectedTemplateId("");
                      }}
                    >
                      {new Date(c.created_at).toLocaleString()} · {c.model || "model"}
                    </button>
                  ))}
                </div>
              </div>
            </div>
            <div className="cover-editor">
              <div className="panel">
                <div className="cover-actions">
                  <button className="primary" onClick={generateCoverLetter} disabled={!coverJobId}>
                    Generate new
                  </button>
                  {COVER_MODELS.length > 1 && (
                    <select
                      className="cover-model"
                      value={coverModel}
                      onChange={(e) => setCoverModel(e.target.value)}
                    >
                      {COVER_MODELS.map((m) => (
                        <option key={m} value={m}>{m}</option>
                      ))}
                    </select>
                  )}
                  <button onClick={saveCoverLetter} disabled={!coverSelectedId}>
                    Save edits
                  </button>
                  <button onClick={() => exportCoverLetter("docx")} disabled={!coverSelectedId}>Export DOCX</button>
                  <button onClick={() => exportCoverLetter("pdf")} disabled={!coverSelectedId}>Export PDF</button>
                  <button onClick={() => exportCoverLetter("txt")} disabled={!coverSelectedId}>Export TXT</button>
                  <button
                    onClick={() => navigator.clipboard.writeText(coverDraft.content || "")}
                    disabled={!coverSelectedId}
                  >
                    Copy
                  </button>
                </div>
                {coverEstimate && (
                  <div className="ai-estimate">
                    Est. {formatTokens(coverEstimate.input_tokens_est)} in / {formatTokens(coverEstimate.output_tokens_est)} out
                    {coverEstimate.model ? ` · ${coverEstimate.model}` : ""}
                    {" · "}
                    {formatCost(coverEstimate.cost_est)}
                    {coverEstimate.cost_est_range
                      ? ` (${formatCost(coverEstimate.cost_est_range.low)}–${formatCost(coverEstimate.cost_est_range.high)})`
                      : ""}
                  </div>
                )}
                <div className="template-bar">
                  <div className="field">
                    <label>Template</label>
                    <select
                      value={selectedTemplateId}
                      onChange={(e) => {
                        const id = e.target.value;
                        setSelectedTemplateId(id);
                        if (id) applyTemplateToDraft(id);
                      }}
                    >
                      <option value="">No template</option>
                      {coverTemplates.map((t, idx) => (
                        <option key={t.id} value={t.id}>{`Template ${idx + 1}`}</option>
                      ))}
                    </select>
                  </div>
                  <div className="template-actions">
                    <button onClick={() => openTemplateModal("new")}>New template</button>
                    <button onClick={() => openTemplateModal("edit")} disabled={!selectedTemplateId}>Edit template</button>
                    <button onClick={() => openTemplateModal("duplicate")} disabled={!selectedTemplateId}>Duplicate</button>
                    <button onClick={deleteTemplate} disabled={!selectedTemplateId}>Delete</button>
                  </div>
                </div>
                {templateWarning && <div className="warning">{templateWarning}</div>}
                <div className="lock-panel">
                  <div className="lock-header">Lock paragraphs (per generation)</div>
                  {bodyParagraphs.length === 0 && (
                    <div className="empty">No paragraphs available. Select a template or add draft text.</div>
                  )}
                  {bodyParagraphs.map((para, idx) => (
                    <div key={`lock-${idx}`} className={classNames("lock-row", lockStates[idx] && "locked")}>
                      <div className="lock-meta">
                        <div className="lock-label">{labelForParagraph(idx, bodyParagraphs.length)}</div>
                        <label className="lock-toggle">
                          <input
                            type="checkbox"
                            checked={!!lockStates[idx]}
                            onChange={(e) => {
                              const checked = e.target.checked;
                              setLockStates((prev) => {
                                const next = [...prev];
                                next[idx] = checked;
                                if (coverSelectedId) {
                                  setLockStatesByVersion((map) => ({
                                    ...map,
                                    [coverSelectedId]: next
                                  }));
                                }
                                return next;
                              });
                            }}
                          />
                          Lock
                        </label>
                      </div>
                      <div className="lock-preview">{para.slice(0, 180)}{para.length > 180 ? "…" : ""}</div>
                    </div>
                  ))}
                </div>
                {coverStatus && <div className="saved">{coverStatus}</div>}
                <div className="field">
                  <label>Feedback to adjust the next version</label>
                  <textarea
                    rows="3"
                    value={coverDraft.feedback}
                    onChange={(e) => setCoverDraft({ ...coverDraft, feedback: e.target.value })}
                    placeholder="e.g., emphasize analytics more, soften sales background, mention FastAPI project"
                  />
                </div>
                <div className="field">
                  <label>Cover letter</label>
                  <textarea
                    rows="16"
                    value={coverDraft.content}
                    onChange={(e) => setCoverDraft({ ...coverDraft, content: e.target.value })}
                    placeholder="Generate a cover letter to get started."
                  />
                </div>
              </div>
            </div>
          </div>
        </section>
      )}

      {tab === "pipeline" && (
        <section className="pipeline">
          <div className="panel">
            <h2>Run Pipeline</h2>
            <div className="field">
              <label>Search</label>
              <select value={selectedSearch} onChange={(e) => setSelectedSearch(e.target.value)}>
                {searches.map((s) => (
                  <option key={s.label} value={s.label}>{s.label}</option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>Search term (optional)</label>
              <input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder='e.g. "operations analyst" OR "project coordinator"'
              />
            </div>
            <div className="field">
              <label>Size</label>
              <select value={sizePreset} onChange={(e) => setSizePreset(e.target.value)}>
                <option value="Large">Large (1000 / 120 / 50)</option>
                <option value="Medium">Medium (500 / 60 / 20)</option>
                <option value="Small">Small (100 / 30 / 10)</option>
              </select>
            </div>
            <div className="field">
              <label>AI eval model</label>
              <select value={evalModel} onChange={(e) => setEvalModel(e.target.value)}>
                {EVAL_MODELS.map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </div>
            <button className="primary" onClick={runPipeline} disabled={running}>
              Start
            </button>
            {pipelineEstimate && (
              <div className="ai-estimate">
                Pipeline AI eval est. {formatTokens(pipelineEstimate.input_tokens_est)} in / {formatTokens(pipelineEstimate.output_tokens_est)} out
                {pipelineEstimate.model ? ` · ${pipelineEstimate.model}` : ""}
                {" · "}
                {formatCost(pipelineEstimate.cost_est)}
                {pipelineEstimate.cost_est_range
                  ? ` (${formatCost(pipelineEstimate.cost_est_range.low)}–${formatCost(pipelineEstimate.cost_est_range.high)})`
                  : ""}
                {pipelineEstimate.jobs_est != null ? ` · jobs ${pipelineEstimate.jobs_est}` : ""}
              </div>
            )}
            <div className="pipeline-buttons">
              {["scout", "shortlist", "scrape", "eval"].map((step) => (
                <button key={step} onClick={() => runStep(step)} disabled={running}>
                  {running && activeStep === step ? `${step}…` : step}
                </button>
              ))}
            </div>
            <div className="progress">
              <div className="progress-label">
                {running ? `Running ${activeStep}` : "Idle"}
                {progress.total ? ` · ${progress.current}/${progress.total}` : ""}
              </div>
              <div className="progress-track">
                <div
                  className={progress.pct ? "progress-bar" : "progress-bar indeterminate"}
                  style={progress.pct ? { width: `${Math.min(100, progress.pct)}%` } : {}}
                />
              </div>
            </div>
            <pre className="log" ref={logRef}>{runLog}</pre>
          </div>
        </section>
      )}

      {templateModalOpen && (
        <div className="modal-backdrop" onClick={() => setTemplateModalOpen(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>
              {templateModalMode === "edit"
                ? "Edit Template"
                : templateModalMode === "duplicate"
                ? "Duplicate Template"
                : "New Template"}
            </h3>
            <div className="field">
              <label>Template text (use blank lines to separate paragraphs)</label>
              <textarea
                rows="12"
                value={templateDraftText}
                onChange={(e) => setTemplateDraftText(e.target.value)}
                placeholder="Paste or write your template here."
              />
            </div>
            {(() => {
              const count = splitCoverSections(templateDraftText || "").body.length;
              if (count && (count < 3 || count > 5)) {
                return <div className="warning">Template has {count} body paragraphs (recommended 3-5).</div>;
              }
              return null;
            })()}
            <div className="modal-actions">
              <button className="ghost" onClick={() => setTemplateModalOpen(false)}>Cancel</button>
              <button className="primary" onClick={saveTemplateDraft}>Save template</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
