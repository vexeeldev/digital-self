import { buildFlowNodes, buildFlowEdges } from '@/components/brain/BrainGraph';
import { ApiGraphNode, ApiGraphEdge } from '@/lib/types';
import { Position } from 'reactflow';

describe('BrainGraph logic', () => {
  it('buildFlowEdges creates correct ReactFlow edges from API associations', () => {
    const apiEdges: ApiGraphEdge[] = [
      { id: 'assoc1', source: 'A', target: 'B', type: 'related', created_at: '' }
    ];

    const edges = buildFlowEdges(apiEdges);
    expect(edges).toHaveLength(1);
    expect(edges[0].id).toBe('assoc1');
    expect(edges[0].source).toBe('A');
    expect(edges[0].target).toBe('B');
    expect(edges[0].label).toBe('related');
    // Ensure it has arrow heads
    expect(edges[0].markerEnd).toBeDefined();
  });

  it('buildFlowEdges handles zero edges gracefully without inventing fake ones', () => {
    const edges = buildFlowEdges([]);
    expect(edges).toHaveLength(0);
  });

  it('buildFlowNodes positions nodes properly and assigns handles', () => {
    const apiNodes: ApiGraphNode[] = [
      { id: 'A', name: 'node A', type: 'PERSON', confidence: 1 },
      { id: 'B', name: 'node B', type: 'ACTION', confidence: 1 },
      { id: 'C', name: 'node C', type: 'OBJECT', confidence: 1 }
    ];
    
    // A -> B -> C
    const apiEdges: ApiGraphEdge[] = [
      { id: 'e1', source: 'A', target: 'B', type: 'x', created_at: '' },
      { id: 'e2', source: 'B', target: 'C', type: 'y', created_at: '' }
    ];

    const nodes = buildFlowNodes(apiNodes, apiEdges);
    expect(nodes).toHaveLength(3);

    // Verify all nodes have target/source positions set to Top/Bottom for TB rankdir
    nodes.forEach(n => {
      expect(n.targetPosition).toBe(Position.Top);
      expect(n.sourcePosition).toBe(Position.Bottom);
    });

    // B should have a greater Y than A (because of TB layout)
    const nodeA = nodes.find(n => n.id === 'A')!;
    const nodeB = nodes.find(n => n.id === 'B')!;
    const nodeC = nodes.find(n => n.id === 'C')!;

    expect(nodeB.position.y).toBeGreaterThan(nodeA.position.y);
    expect(nodeC.position.y).toBeGreaterThan(nodeB.position.y);
  });

  it('buildFlowNodes gives nodes unique coordinates when there are branches', () => {
    const apiNodes: ApiGraphNode[] = [
      { id: 'A', name: 'node A', type: 'PERSON', confidence: 1 },
      { id: 'B', name: 'node B', type: 'ACTION', confidence: 1 },
      { id: 'C', name: 'node C', type: 'OBJECT', confidence: 1 }
    ];
    
    // A -> B
    // A -> C
    const apiEdges: ApiGraphEdge[] = [
      { id: 'e1', source: 'A', target: 'B', type: 'x', created_at: '' },
      { id: 'e2', source: 'A', target: 'C', type: 'y', created_at: '' }
    ];

    const nodes = buildFlowNodes(apiNodes, apiEdges);
    
    const nodeB = nodes.find(n => n.id === 'B')!;
    const nodeC = nodes.find(n => n.id === 'C')!;

    // B and C should be on the same rank (Y level) roughly, but different X
    expect(nodeB.position.x).not.toBe(nodeC.position.x);
  });
});
