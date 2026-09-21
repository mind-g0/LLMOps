import { apiClient } from "./client";
import type { JobRequirement } from "@/types/jobRequirement";

const BASE = "/api/v1/job-requirements";

export function listJobRequirements(signal?: AbortSignal): Promise<JobRequirement[]> {
  return apiClient.get<JobRequirement[]>(BASE, undefined, signal);
}

export function getJobRequirement(id: string, signal?: AbortSignal): Promise<JobRequirement> {
  return apiClient.get<JobRequirement>(`${BASE}/${id}`, undefined, signal);
}

export function createJobRequirement(
  payload: Omit<JobRequirement, "id">,
  signal?: AbortSignal
): Promise<JobRequirement> {
  return apiClient.post<JobRequirement>(BASE, payload, signal);
}

export function updateJobRequirement(
  id: string,
  payload: Partial<Omit<JobRequirement, "id">>,
  signal?: AbortSignal
): Promise<JobRequirement> {
  return apiClient.patch<JobRequirement>(`${BASE}/${id}`, payload, signal);
}

export function deleteJobRequirement(id: string, signal?: AbortSignal): Promise<void> {
  return apiClient.delete<void>(`${BASE}/${id}`);
}
