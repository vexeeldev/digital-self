export interface Experience {
  id: string;
  raw_text: string;
  occurred_at: string | null;
  created_at: string;
}

// Actual API node from GET /memory/{id} and GET /memory/graph
export interface MemoryNode {
  id: string;
  name: string;
  type: string;
  associations_count?: number;
}

// API graph node (from /memory/graph — no activation field returned)
export interface ApiGraphNode {
  id: string;
  name: string;
  type: string;
}

export interface ApiGraphEdge {
  id: string;
  source: string;
  target: string;
  type: string;
}

export interface ApiGraphData {
  nodes: ApiGraphNode[];
  edges: ApiGraphEdge[];
}

// Reasoning types
export interface Evidence {
  source_type: string;
  source_id: string;
  relevance: number;
  confidence: number;
  supporting_experiences: string[];
}

export interface Inference {
  statement: string;
  supporting_evidence: Evidence[];
  contradicting_evidence: Evidence[];
  confidence: number;
  provenance: string[];
}

export interface Conflict {
  id: string;
  belief_a_id: string;
  belief_b_id: string;
  subject_id: string;
  object_id: string;
}

export interface ReasoningResponse {
  inferences: Inference[];
  evidence: Evidence[];
  conflicts: Conflict[];
  confidence: number;
  provenance: string[];
}
