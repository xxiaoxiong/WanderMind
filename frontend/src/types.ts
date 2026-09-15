export type KnowledgeType =
  | "note"
  | "concept"
  | "fact"
  | "document"
  | "question"
  | "hypothesis"
  | "idea"
  | "insight"
  | "evidence";

export interface KnowledgeItem {
  id: string;
  title: string;
  content: string;
  summary: string;
  type: KnowledgeType;
  source: string;
  source_ref: string | null;
  topics: string[];
  entities: string[];
  importance: number;
  confidence: number;
  created_at: string;
}

export interface Seed {
  id: string;
  content: string;
  source: string;
  priority: number;
  status: string;
  created_at: string;
}

export interface WonderScores {
  novelty: number;
  coherence: number;
  usefulness: number;
  surprise: number;
  evidence_potential: number;
  redundancy: number;
  arbitrariness: number;
  hallucination_risk: number;
  total: number;
}

export interface WanderStep {
  id: string;
  index: number;
  state: string;
  action: string;
  reason: string;
  item_ids: string[];
  operator: string | null;
  novelty_gain: number | null;
  relevance: number | null;
  collision_score: number | null;
  created_at: string;
}

export interface WanderSession {
  id: string;
  seed_id: string;
  state: string;
  status: string;
  trace: {
    steps: WanderStep[];
    patches: string[];
    operators: string[];
    candidate_ids: string[];
    final_wonder_ids: string[];
    stop_reason: string | null;
  };
  created_at: string;
}

export interface Candidate {
  id: string;
  statement: string;
  explanation: string;
  operator: string;
  status: string;
  source_items: string[];
  scores: WonderScores | null;
}

export interface Wonder {
  id: string;
  candidate_id: string | null;
  type: string;
  statement: string;
  explanation: string;
  why_interesting: string;
  source_items: string[];
  connection_path: string[];
  supporting_evidence: string[];
  counter_evidence: string[];
  assumptions: string[];
  questions: string[];
  scores: WonderScores;
  confidence: number;
  status: string;
  parent_wonder_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface WanderRunResponse {
  session: WanderSession;
  candidates: Candidate[];
  wonders: Wonder[];
}

export interface DeepExploreResponse {
  wonder: Wonder;
  evaluation: {
    explorer: {
      expanded_idea: string;
      implications: string[];
      follow_up_questions: string[];
    } | null;
    evidence: {
      supporting_evidence: string[];
      counter_evidence: string[];
      source_refs: string[];
      uncertainty: number;
      status: string;
    };
    critic: {
      weakness: string[];
      obviousness: number;
      over_analogy: boolean;
      factual_risk: number;
      alternative_explanation: string[];
      verdict: string;
    };
  };
}

export interface ApiErrorEnvelope {
  error: {
    code: string;
    message: string;
    details: Record<string, unknown>;
    retryable: boolean;
  };
}
