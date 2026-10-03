import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple
from psycopg2.extensions import connection
from psycopg2.extras import RealDictCursor

from models import AssociationType
from pattern import form_patterns
from belief import Belief, form_beliefs
from conflict import BeliefConflict, detect_conflicts
from activation import spread_activation

@dataclass(frozen=True)
class ReasoningQuery:
    text: str
    context: dict = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.text or not self.text.strip():
            raise ValueError("Query text cannot be empty.")

@dataclass(frozen=True)
class Evidence:
    source_type: str  # "EXPERIENCE", "PATTERN", "BELIEF", "ASSEMBLY"
    source_id: str
    relevance: float
    confidence: float
    supporting_experiences: tuple

@dataclass(frozen=True)
class Inference:
    statement: str
    supporting_evidence: tuple
    contradicting_evidence: tuple
    confidence: float
    provenance: tuple

@dataclass(frozen=True)
class ReasoningContext:
    query: ReasoningQuery
    activated_nodes: tuple
    activated_assemblies: tuple
    relevant_experiences: tuple
    relevant_patterns: tuple
    relevant_beliefs: tuple
    conflicts: tuple

class ReasoningEngine:
    def __init__(self, db_connection: connection):
        self.conn = db_connection

    def _extract_seeds(self, query: ReasoningQuery) -> Dict[uuid.UUID, float]:
        """
        Extracts seeds from the query using basic deterministic string matching.
        Limitation: Without semantic embeddings/NLP, this relies on exact word matches.
        """
        words = set(query.text.lower().replace('?', '').replace('.', '').replace(',', '').split())
        seeds = {}
        with self.conn.cursor() as cur:
            # Match words against node names or aliases
            cur.execute("SELECT id, name FROM nodes WHERE lower(name) = ANY(%s)", (list(words),))
            for row in cur.fetchall():
                seeds[uuid.UUID(str(row[0]))] = 1.0
                
            cur.execute("SELECT node_id FROM node_aliases WHERE lower(alias_name) = ANY(%s)", (list(words),))
            for row in cur.fetchall():
                seeds[uuid.UUID(str(row[0]))] = 1.0
        return seeds

    def build_context(self, query: ReasoningQuery) -> ReasoningContext:
        """
        Retrieves relevant memory using the existing activation architecture.
        """
        seeds = self._extract_seeds(query)
        if not seeds:
            # Fallback to context if provided
            if 'seed_nodes' in query.context:
                seeds = {uuid.UUID(n): 1.0 for n in query.context['seed_nodes']}
                
        # Spreading activation
        activations = spread_activation(self.conn, seeds, max_depth=2)
        activated_nodes = tuple(activations.keys())
        
        # Retrieve assemblies involving these nodes
        assemblies = set()
        if activated_nodes:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT DISTINCT assembly_id FROM vw_active_assembly_members 
                    WHERE node_id = ANY(%s::uuid[])
                    """,
                    (list(map(str, activated_nodes)),)
                )
                assemblies = {uuid.UUID(row[0]) for row in cur.fetchall()}
                
        # Retrieve patterns and beliefs involving highly activated nodes (score > 0.0)
        relevant_beliefs = []
        relevant_patterns = []
        conflicts = []
        relevant_experiences = set()
        
        if activated_nodes:
            # For Stage 20, we retrieve all patterns and filter to those connecting activated nodes.
            # In a larger graph, we would query the database directly.
            all_patterns = form_patterns(self.conn, minimum_evidence=1)
            all_beliefs = form_beliefs(all_patterns)
            
            # Filter beliefs that have both subject and object activated (strong relevance)
            # Or at least one activated if we want broader recall. Let's require both for precision.
            act_set = set(activated_nodes)
            for b in all_beliefs:
                if b.subject in act_set and b.object in act_set:
                    relevant_beliefs.append(b)
                    relevant_patterns.append(b.source_pattern)
                    for exp in b.supporting_experiences:
                        relevant_experiences.add(exp)
                        
            # Detect conflicts among relevant beliefs
            conflicts = detect_conflicts(relevant_beliefs)

        return ReasoningContext(
            query=query,
            activated_nodes=tuple(activated_nodes),
            activated_assemblies=tuple(assemblies),
            relevant_experiences=tuple(relevant_experiences),
            relevant_patterns=tuple(relevant_patterns),
            relevant_beliefs=tuple(relevant_beliefs),
            conflicts=tuple(conflicts)
        )

    def _calculate_confidence(self, supporting_evidence: List[Evidence], contradicting_evidence: List[Evidence]) -> float:
        """
        Deterministic confidence calculation.
        support_score = sum of evidence confidences (unique experiences)
        """
        # Ensure we don't double count experiences
        supp_exps = set()
        supp_score = 0.0
        for ev in supporting_evidence:
            for exp in ev.supporting_experiences:
                if exp not in supp_exps:
                    supp_exps.add(exp)
                    supp_score += ev.confidence # simplified: each unique piece of evidence adds its source confidence
                    
        con_exps = set()
        con_score = 0.0
        for ev in contradicting_evidence:
            for exp in ev.supporting_experiences:
                if exp not in con_exps:
                    con_exps.add(exp)
                    con_score += ev.confidence
                    
        denominator = supp_score + con_score
        if denominator == 0:
            return 0.0
        return max(0.0, min(1.0, supp_score / denominator))

    def _get_node_name(self, node_id: uuid.UUID) -> str:
        with self.conn.cursor() as cur:
            cur.execute("SELECT name FROM nodes WHERE id = %s", (str(node_id),))
            row = cur.fetchone()
            if row:
                return row[0]
        return str(node_id)

    def reason(self, query: ReasoningQuery) -> List[Inference]:
        """
        Constructs traceable inferences based on memory.
        """
        ctx = self.build_context(query)
        inferences = []
        
        if not ctx.relevant_beliefs:
            return [Inference(
                statement="NO_SUFFICIENT_EVIDENCE",
                supporting_evidence=(),
                contradicting_evidence=(),
                confidence=0.0,
                provenance=()
            )]
            
        # Process conflicts first
        conflict_beliefs = set()
        for c in ctx.conflicts:
            conflict_beliefs.add(f"{c.belief_a.subject}_{c.belief_a.relationship_type.value}_{c.belief_a.object}")
            conflict_beliefs.add(f"{c.belief_b.subject}_{c.belief_b.relationship_type.value}_{c.belief_b.object}")
            
            ev_a = Evidence("BELIEF", f"{c.belief_a.subject}_{c.belief_a.relationship_type.value}_{c.belief_a.object}", 1.0, c.belief_a.confidence, tuple(c.belief_a.supporting_experiences))
            ev_b = Evidence("BELIEF", f"{c.belief_b.subject}_{c.belief_b.relationship_type.value}_{c.belief_b.object}", 1.0, c.belief_b.confidence, tuple(c.belief_b.supporting_experiences))
            
            sub_name = self._get_node_name(c.subject)
            obj_name = self._get_node_name(c.object)
            
            statement = f"Conflicting evidence found regarding {sub_name} and {obj_name} ({c.belief_a.relationship_type.value} vs {c.belief_b.relationship_type.value})"
            
            # For a conflict statement, BOTH are supporting the fact that there is a conflict.
            # But in terms of the underlying claim, they contradict each other.
            # We'll expose the conflict explicitly.
            confidence = self._calculate_confidence([ev_a], [ev_b])
            prov = tuple(set(ev_a.supporting_experiences + ev_b.supporting_experiences))
            
            inf = Inference(
                statement=statement,
                supporting_evidence=(ev_a,),
                contradicting_evidence=(ev_b,),
                confidence=confidence,
                provenance=prov
            )
            inferences.append(inf)
            
        # Process multi-evidence / direct beliefs
        # Group by subject and object to aggregate evidence
        grouped_beliefs = {}
        for b in ctx.relevant_beliefs:
            b_id = f"{b.subject}_{b.relationship_type.value}_{b.object}"
            if b_id in conflict_beliefs:
                continue # Already handled in conflicts
            key = (b.subject, b.object, b.relationship_type)
            if key not in grouped_beliefs:
                grouped_beliefs[key] = []
            grouped_beliefs[key].append(b)
            
        for (sub, obj, rel), group in grouped_beliefs.items():
            evs = []
            for b in group:
                evs.append(Evidence("BELIEF", f"{b.subject}_{b.relationship_type.value}_{b.object}", 1.0, b.confidence, tuple(b.supporting_experiences)))
                
            sub_name = self._get_node_name(sub)
            obj_name = self._get_node_name(obj)
            
            if len(group) == 1:
                statement = f"Direct belief: {sub_name} {rel.value} {obj_name}"
            else:
                statement = f"Multiple evidence support: {sub_name} {rel.value} {obj_name}"
                
            confidence = self._calculate_confidence(evs, [])
            prov = set()
            for e in evs:
                prov.update(e.supporting_experiences)
                
            inf = Inference(
                statement=statement,
                supporting_evidence=tuple(evs),
                contradicting_evidence=(),
                confidence=confidence,
                provenance=tuple(prov)
            )
            inferences.append(inf)
            
        # Sort inferences deterministically
        inferences.sort(key=lambda i: (i.statement, i.confidence))
        return inferences
