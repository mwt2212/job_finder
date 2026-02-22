export const DEFAULT_PREFS = {
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

export const DEFAULT_RULES = {
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

export const SHORTLIST_REASONS = [
  { label: "Wrong field", value: "wrong field" },
  { label: "Not qualified", value: "not qualified" },
  { label: "Salesy/outbound", value: "salesy" },
  { label: "Healthcare", value: "healthcare" },
  { label: "Low pay", value: "low pay" },
  { label: "Onsite only", value: "onsite" }
];
