import axios from 'axios';
import { Experience, MemoryNode, ApiGraphData, ReasoningResponse } from './types';

const api = axios.create({
  baseURL: 'http://localhost:8000',
});

export async function createExperience(raw_text: string): Promise<Experience> {
  const res = await api.post<Experience>('/experiences', { raw_text });
  return res.data;
}

export async function getExperience(id: string): Promise<Experience> {
  const res = await api.get<Experience>(`/experiences/${id}`);
  return res.data;
}

export async function getExperiences(): Promise<Experience[]> {
  const res = await api.get<Experience[]>('/experiences');
  return res.data;
}

export async function getMemoryNode(id: string): Promise<MemoryNode> {
  const res = await api.get<MemoryNode>(`/memory/${id}`);
  return res.data;
}

/**
 * Get a contextual subgraph.
 * - With experienceId: returns nodes/edges linked to that experience
 * - With nodeId: returns node and its immediate neighbors
 * - With no params: returns empty (by API design — no global dump)
 */
export async function getGraph(experienceId?: string, nodeId?: string): Promise<ApiGraphData> {
  const params = new URLSearchParams();
  if (experienceId) params.append('experience_id', experienceId);
  if (nodeId) params.append('node_id', nodeId);

  const url = params.toString() ? `/memory/graph?${params}` : '/memory/graph';
  const res = await api.get<ApiGraphData>(url);
  return res.data;
}

export async function runReasoning(query: string): Promise<ReasoningResponse> {
  const res = await api.post<ReasoningResponse>('/reasoning', { query, context: {} });
  return res.data;
}
