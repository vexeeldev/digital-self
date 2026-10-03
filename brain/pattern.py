"""
Digital Self — pattern.py
Version: V2.1 — Initial Pattern Formation

Identifies patterns (repeated associations) from historical evidence.
Does NOT modify database schema or records.
"""

import uuid
import yaml
from pydantic import BaseModel
from pathlib import Path
from psycopg2.extensions import connection
from models import AssociationType

PARAMS_PATH = Path(__file__).parent / "params.yaml"

def load_params():
    with open(PARAMS_PATH, 'r') as f:
        return yaml.safe_load(f)

PARAMS = load_params()
MINIMUM_EVIDENCE = int(PARAMS['pattern']['minimum_evidence'])

class Pattern(BaseModel):
    """
    Derived in-memory representation of a Pattern.
    A Pattern is defined as a repeated association that meets the minimum evidence threshold.
    """
    association_id: uuid.UUID
    source_node_id: uuid.UUID
    target_node_id: uuid.UUID
    relationship_type: AssociationType
    evidence_count: int
    negative_evidence: int
    association_strength: float
    confidence: float
    supporting_experiences: list[uuid.UUID]

def form_patterns(conn: connection, minimum_evidence: int = MINIMUM_EVIDENCE) -> list[Pattern]:
    """
    Scans associations and identifies those that meet the minimum evidence threshold.
    Returns derived Pattern objects. Does not modify the database.
    """
    patterns = []
    
    with conn.cursor() as cur:
        # Only consider associations where positive_evidence >= minimum_evidence
        cur.execute(
            """
            SELECT id, source_node_id, target_node_id, type, strength, positive_evidence, negative_evidence
            FROM associations
            WHERE positive_evidence >= %s
            """,
            (minimum_evidence,)
        )
        associations = cur.fetchall()
        
        for row in associations:
            assoc_id, src_id, tgt_id, rel_type, strength, pos_ev, neg_ev = row
            
            # Confidence Logic
            # Deterministic: positive / (positive + negative)
            pos_ev = int(pos_ev)
            neg_ev = int(neg_ev)
            denominator = pos_ev + neg_ev
            
            if denominator == 0:
                confidence = 0.0
            else:
                confidence = pos_ev / denominator
                
            confidence = max(0.0, min(1.0, confidence))
            
            # Provenance Logic
            cur.execute(
                """
                SELECT experience_id 
                FROM vw_active_experience_associations 
                WHERE association_id = %s
                """,
                (str(assoc_id),)
            )
            provenance = [uuid.UUID(r[0]) for r in cur.fetchall()]
            
            pat = Pattern(
                association_id=uuid.UUID(assoc_id),
                source_node_id=uuid.UUID(src_id),
                target_node_id=uuid.UUID(tgt_id),
                relationship_type=AssociationType(rel_type),
                evidence_count=pos_ev,
                negative_evidence=neg_ev,
                association_strength=float(strength),
                confidence=confidence,
                supporting_experiences=provenance
            )
            patterns.append(pat)
            
    return patterns

ASSEMBLY_WEIGHT_ROUNDING = int(PARAMS['pattern'].get('assembly_weight_rounding_decimals', 1))

class AssemblyMemberStruct(BaseModel):
    node_id: uuid.UUID
    role: str
    weight: float
    
    def __hash__(self):
        return hash((str(self.node_id), self.role, self.weight))
        
    def __eq__(self, other):
        return (self.node_id == other.node_id and 
                self.role == other.role and 
                self.weight == other.weight)

class AssemblyPattern(BaseModel):
    """
    Derived in-memory representation of an Assembly Pattern.
    Identified by a stable, repeated multi-node configuration.
    """
    configuration: list[AssemblyMemberStruct]
    evidence_count: int
    negative_evidence: int
    confidence: float
    supporting_experiences: list[uuid.UUID]

def form_assembly_patterns(conn: connection, minimum_evidence: int = MINIMUM_EVIDENCE) -> list[AssemblyPattern]:
    """
    Scans assemblies, extracts their member configurations, deduplicates by exact configuration,
    and forms patterns if the evidence threshold is met.
    """
    from psycopg2.extras import RealDictCursor
    from collections import defaultdict
    
    patterns = []
    
    # Map identity tuple -> set of experience_ids
    # This prevents double counting if the same experience somehow has identical assemblies.
    config_evidence = defaultdict(set)
    # Map identity tuple -> configuration list (to easily reconstruct)
    config_structs = {}
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # Fetch all assemblies and their members in one query
        cur.execute(
            """
            SELECT a.id as assembly_id, a.experience_id, am.node_id, am.role, am.weight
            FROM assemblies a
            JOIN vw_active_assembly_members am ON a.id = am.assembly_id
            """
        )
        rows = cur.fetchall()
        
    # Group by assembly_id
    assemblies_map = defaultdict(list)
    experience_map = {}
    for row in rows:
        asm_id = str(row['assembly_id'])
        assemblies_map[asm_id].append(row)
        experience_map[asm_id] = uuid.UUID(row['experience_id'])
        
    for asm_id, members in assemblies_map.items():
        # Build configuration list
        config = []
        for m in members:
            # Normalize weight
            w = round(float(m['weight']), ASSEMBLY_WEIGHT_ROUNDING)
            config.append(
                AssemblyMemberStruct(
                    node_id=uuid.UUID(m['node_id']),
                    role=m['role'],
                    weight=w
                )
            )
            
        # Sort canonically by node_id, then role, to ensure deterministic identity
        config.sort(key=lambda x: (str(x.node_id), x.role))
        
        # Tuple of immutable representations for hashing
        identity = tuple(config)
        
        exp_id = experience_map[asm_id]
        config_evidence[identity].add(exp_id)
        config_structs[identity] = config
        
    # Filter by minimum_evidence and create Pattern objects
    for identity, exp_set in config_evidence.items():
        if len(exp_set) >= minimum_evidence:
            pos_ev = len(exp_set)
            neg_ev = 0  # Assemblies do not have explicit negative evidence yet
            
            denominator = pos_ev + neg_ev
            confidence = float(pos_ev) / denominator if denominator > 0 else 0.0
            
            pat = AssemblyPattern(
                configuration=config_structs[identity],
                evidence_count=pos_ev,
                negative_evidence=neg_ev,
                confidence=confidence,
                supporting_experiences=sorted(list(exp_set)) # Sort for determinism
            )
            patterns.append(pat)
            
    # Return sorted to ensure determinism
    patterns.sort(key=lambda p: str(p.configuration))
    return patterns
