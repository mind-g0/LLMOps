export interface JobRequirement {
  id?: string;
  name: string;
  title: string;
  description: string;
  requirements: string[];
}

/** A single label used to slot a JobRequirement into one of the three
 * fixed panels on the setup page (Job 1 / Job 2 / Job 3). This is a
 * frontend-only concept; the backend only ever sees JobRequirement. */
export type JobSlot = 1 | 2 | 3;

export const EMPTY_JOB_REQUIREMENT: JobRequirement = {
  name: "",
  title: "",
  description: "",
  requirements: [],
};
