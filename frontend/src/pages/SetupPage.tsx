import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { JobRequirementCard } from "@/components/JobRequirementCard";
import { CvUpload, type FileRejection } from "@/components/CvUpload";
import { LoadingState, ErrorState } from "@/components/LoadingState";
import { ToastStack } from "@/components/ToastStack";
import { useToast } from "@/hooks/useToast";
import { EMPTY_JOB_REQUIREMENT, type JobRequirement } from "@/types/jobRequirement";
import {
  createJobRequirement,
  listJobRequirements,
  updateJobRequirement,
} from "@/api/jobRequirements";
import { startAnalysis } from "@/api/cvReviews";
import { ApiError } from "@/api/client";

const SLOT_LABELS = ["Job 1", "Job 2", "Job 3"];

export function SetupPage() {
  const navigate = useNavigate();
  const { toasts, showToast, dismissToast } = useToast();

  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [slots, setSlots] = useState<JobRequirement[]>([
    EMPTY_JOB_REQUIREMENT,
    EMPTY_JOB_REQUIREMENT,
    EMPTY_JOB_REQUIREMENT,
  ]);
  const [savingSlot, setSavingSlot] = useState<number | null>(null);

  const [selectedJobId, setSelectedJobId] = useState<string>("");
  const [files, setFiles] = useState<File[]>([]);
  const [rejections, setRejections] = useState<FileRejection[]>([]);
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      setLoading(true);
      setLoadError(null);
      try {
        const existing = await listJobRequirements(controller.signal);
        setSlots((current) => {
          const next = [...current];
          existing.slice(0, 3).forEach((job, i) => {
            next[i] = job;
          });
          return next;
        });
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setLoadError(err instanceof ApiError ? err.message : "Couldn't load job requirements.");
      } finally {
        setLoading(false);
      }
    }
    load();
    return () => controller.abort();
  }, []);

  const savedJobs = slots.filter((s): s is JobRequirement & { id: string } => Boolean(s.id));

  async function handleSaveSlot(index: number, value: JobRequirement) {
    setSavingSlot(index);
    try {
      const saved = value.id
        ? await updateJobRequirement(value.id, value)
        : await createJobRequirement(value);
      setSlots((current) => {
        const next = [...current];
        next[index] = saved;
        return next;
      });
      showToast(`${SLOT_LABELS[index]} saved.`);
    } catch (err) {
      showToast(err instanceof ApiError ? err.message : "Couldn't save this job requirement.", "error");
    } finally {
      setSavingSlot(null);
    }
  }

  const canStart = files.length > 0 && Boolean(selectedJobId) && !starting;

  async function handleStartProcess() {
    if (!canStart) return;
    setStarting(true);
    setStartError(null);
    try {
      await startAnalysis({ files, jobRequirementId: selectedJobId });
      showToast("Processing started.");
      navigate("/review");
    } catch (err) {
      setStartError(err instanceof ApiError ? err.message : "Couldn't start processing. Please try again.");
    } finally {
      setStarting(false);
    }
  }

  function handleClear() {
    setFiles([]);
    setRejections([]);
    setStartError(null);
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#FDFBF7]">
        <LoadingState label="Loading job requirements" />
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="min-h-screen bg-[#FDFBF7] p-6 text-stone-800">
        <ErrorState description={loadError} onRetry={() => window.location.reload()} />
      </div>
    );
  }

  return (
    <div className="relative min-h-screen bg-[#FDFBF7] text-stone-800 px-4 py-10 sm:px-6">
      <div className="relative z-10 mx-auto max-w-5xl space-y-10">
        {/* Page Heading */}
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-stone-900">Set up a review</h1>
          <p className="mt-1 text-sm text-stone-600">
            Define up to three roles, then upload the CVs you want scored against one of them.
          </p>
        </div>

        {/* Job Requirements Section */}
        <section aria-labelledby="job-requirements-heading">
          <div className="flex items-center gap-3">
            <h2 id="job-requirements-heading" className="text-xs font-bold uppercase tracking-widest text-[#5A8052]">
              Job requirements
            </h2>
            <div className="h-[1px] flex-1 bg-stone-200" />
          </div>

          <div className="mt-4 grid gap-4 lg:grid-cols-3">
            {slots.map((slot, i) => (
              <JobRequirementCard
                key={slot.id ?? `slot-${i}`}
                slotLabel={SLOT_LABELS[i]}
                value={slot}
                saving={savingSlot === i}
                onSave={(value) => handleSaveSlot(i, value)}
              />
            ))}
          </div>
        </section>

        {/* Upload Section */}
        <section aria-labelledby="upload-heading">
          <div className="flex items-center gap-3">
            <h2 id="upload-heading" className="text-xs font-bold uppercase tracking-widest text-[#5A8052]">
              Upload CVs
            </h2>
            <div className="h-[1px] flex-1 bg-stone-200" />
          </div>

          <div className="mt-4 rounded-xl border border-stone-200 bg-white p-6 shadow-sm">
            <div className="mb-5">
              <label className="mb-1.5 block text-xs font-semibold text-stone-700" htmlFor="job-select">
                Score against
              </label>
              <select
                id="job-select"
                value={selectedJobId}
                onChange={(e) => setSelectedJobId(e.target.value)}
                className="w-full max-w-sm rounded-lg border border-stone-300 bg-white px-3 py-2 text-sm text-stone-800 focus:border-[#BCD9B4] focus:outline-none focus:ring-2 focus:ring-[#BCD9B4]/50"
              >
                <option value="">Select a saved job requirement&hellip;</option>
                {savedJobs.map((job) => (
                  <option key={job.id} value={job.id}>
                    {job.name}
                  </option>
                ))}
              </select>
              {savedJobs.length === 0 && (
                <p className="mt-2 text-xs text-amber-600 flex items-center gap-1">
                  <span>&#9888;</span> Save at least one job requirement above first.
                </p>
              )}
            </div>

            <CvUpload
              files={files}
              onChange={setFiles}
              onRejections={(next) => setRejections(next)}
              disabled={starting}
            />

            {rejections.length > 0 && (
              <ul className="mt-3 space-y-1 text-xs text-red-600">
                {rejections.map((r, i) => (
                  <li key={i}>
                    {r.file.name}: {r.reason}
                  </li>
                ))}
              </ul>
            )}

            {startError && (
              <p className="mt-3 text-sm text-red-600" role="alert">
                {startError}
              </p>
            )}

            <div className="mt-6 flex flex-wrap gap-3">
              <button
                type="button"
                onClick={handleStartProcess}
                disabled={!canStart}
                className="inline-flex items-center justify-center rounded-lg bg-[#BCD9B4] px-5 py-2.5 text-sm font-bold text-emerald-950 shadow-sm transition-all duration-200 hover:bg-[#a8cd9f] focus:outline-none focus:ring-2 focus:ring-[#BCD9B4] disabled:cursor-not-allowed disabled:opacity-40"
              >
                {starting ? "Starting process\u2026" : "Start process"}
              </button>
              <button
                type="button"
                onClick={handleClear}
                disabled={starting || files.length === 0}
                className="rounded-lg border border-stone-300 bg-white px-5 py-2.5 text-sm font-semibold text-stone-700 transition-colors hover:border-[#BCD9B4] hover:bg-stone-50 focus:outline-none focus:ring-2 focus:ring-[#BCD9B4] disabled:cursor-not-allowed disabled:opacity-40"
              >
                Clear
              </button>
            </div>
          </div>
        </section>

        <ToastStack toasts={toasts} onDismiss={dismissToast} />
      </div>
    </div>
  );
}