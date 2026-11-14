import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import type { ReactNode } from "react";

import { cancelEvaluationJob, getEvaluationJob } from "../api/openings";
import type { TrackedEvaluationJob } from "../types/evaluation";

interface EvaluationJobsContextValue {
  jobs: Record<string, TrackedEvaluationJob>;
  trackJob: (
    opening: { id: number; name: string },
    jobId: string,
    total: number,
  ) => void;
  cancelJob: (jobId: string) => Promise<void>;
  lastFinished: TrackedEvaluationJob | null;
}

const EvaluationJobsContext =
  createContext<EvaluationJobsContextValue | null>(null);

export function EvaluationJobsProvider({ children }: { children: ReactNode }) {
  const [jobs, setJobs] = useState<Record<string, TrackedEvaluationJob>>({});
  const [lastFinished, setLastFinished] =
    useState<TrackedEvaluationJob | null>(null);
  const jobsRef = useRef(jobs);

  useEffect(() => {
    jobsRef.current = jobs;
  }, [jobs]);

  const trackJob = useCallback(
    (
      opening: { id: number; name: string },
      jobId: string,
      total: number,
    ) => {
      setJobs((current) => ({
        ...current,
        [jobId]: {
          jobId,
          openingId: opening.id,
          openingName: opening.name,
          state: "running",
          done: 0,
          total,
          errors: 0,
          message: null,
        },
      }));
    },
    [],
  );

  const cancelJob = useCallback(async (jobId: string) => {
    const status = await cancelEvaluationJob(jobId);
    setJobs((current) =>
      current[jobId]
        ? { ...current, [jobId]: { ...current[jobId], ...status } }
        : current,
    );
  }, []);

  const runningKey = useMemo(
    () =>
      Object.values(jobs)
        .filter((job) => job.state === "running")
        .map((job) => job.jobId)
        .sort()
        .join("|"),
    [jobs],
  );

  useEffect(() => {
    if (!runningKey) {
      return;
    }

    const ids = runningKey.split("|");
    let stopped = false;

    const poll = async () => {
      const results = await Promise.all(
        ids.map(async (id) => {
          try {
            return [id, await getEvaluationJob(id)] as const;
          } catch {
            return null;
          }
        }),
      );
      if (stopped) {
        return;
      }

      const currentJobs = jobsRef.current;
      const finished: TrackedEvaluationJob[] = [];
      const updates: Array<[string, TrackedEvaluationJob]> = [];

      for (const result of results) {
        if (!result) {
          continue;
        }
        const [id, status] = result;
        const current = currentJobs[id];
        if (!current) {
          continue;
        }
        const next = { ...current, ...status };
        updates.push([id, next]);
        if (current.state === "running" && status.state !== "running") {
          finished.push(next);
        }
      }

      if (updates.length > 0) {
        setJobs((current) => {
          const next = { ...current };
          for (const [id, job] of updates) {
            if (next[id]) {
              next[id] = job;
            }
          }
          return next;
        });
      }

      for (const job of finished) {
        setLastFinished(job);
      }
    };

    void poll();
    const timer = window.setInterval(() => {
      void poll();
    }, 1000);

    return () => {
      stopped = true;
      window.clearInterval(timer);
    };
  }, [runningKey]);

  const value = useMemo(
    () => ({ jobs, trackJob, cancelJob, lastFinished }),
    [cancelJob, jobs, lastFinished, trackJob],
  );

  return (
    <EvaluationJobsContext.Provider value={value}>
      {children}
    </EvaluationJobsContext.Provider>
  );
}

export function useEvaluationJobs(): EvaluationJobsContextValue {
  const context = useContext(EvaluationJobsContext);
  if (!context) {
    throw new Error("useEvaluationJobs must be used inside its provider");
  }
  return context;
}
