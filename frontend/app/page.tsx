"use client";

import { useState, useCallback, useRef } from "react";
import { Rocket, RotateCcw, Rabbit } from "lucide-react";
import { toast } from "sonner";
import confetti from "canvas-confetti";

import DropZone from "@/components/drop-zone";
import EmailInput from "@/components/email-input";
import SubjectEditor from "@/components/subject-editor";
import FilePreview from "@/components/file-preview";
import ProgressTracker, {
  type PipelineStage,
} from "@/components/progress-tracker";
import SummaryPreview from "@/components/summary-preview";
import ThemeToggle from "@/components/theme-toggle";
import HistorySidebar, { addHistoryEntry } from "@/components/history-sidebar";
import {
  uploadAndAnalyze,
  sendSummaryEmail,
  streamPipeline,
  type SSEEvent,
} from "@/lib/api";
import { validateEmail } from "@/lib/validators";
import { cn } from "@/lib/utils";

export default function HomePage() {
  const [file, setFile] = useState<File | null>(null);
  const [email, setEmail] = useState("");
  const [subject, setSubject] = useState(
    "Q1 2026 Sales Insight Brief — Rabbitt AI",
  );
  const [stage, setStage] = useState<PipelineStage>("idle");
  const [errorMsg, setErrorMsg] = useState("");
  const [summary, setSummary] = useState("");
  const [stats, setStats] = useState<Record<string, unknown> | null>(null);
  const [useStreaming, setUseStreaming] = useState(true);
  const [historyTrigger, setHistoryTrigger] = useState<object | null>(null);
  const abortRef = useRef<(() => void) | null>(null);

  const isProcessing =
    stage !== "idle" && stage !== "done" && stage !== "error";

  const fireConfetti = () => {
    confetti({
      particleCount: 120,
      spread: 80,
      origin: { y: 0.6 },
      colors: ["#6366f1", "#8b5cf6", "#a78bfa", "#22c55e", "#facc15"],
    });
  };

  const handleReset = () => {
    if (abortRef.current) abortRef.current();
    setFile(null);
    setEmail("");
    setSubject("Q1 2026 Sales Insight Brief — Rabbitt AI");
    setStage("idle");
    setErrorMsg("");
    setSummary("");
    setStats(null);
  };

  const handleSubmitStream = useCallback(() => {
    if (!file) return toast.error("Please upload a file first.");
    const emailErr = validateEmail(email);
    if (emailErr) return toast.error(emailErr);

    setStage("parsing");
    setSummary("");
    setStats(null);
    setErrorMsg("");

    const cancel = streamPipeline(
      file,
      email,
      subject,
      (event: SSEEvent) => {
        if (event.status === "in-progress") {
          setStage(event.stage as PipelineStage);
        }
        if (event.status === "complete") {
          if (event.data?.summary) setSummary(event.data.summary as string);
          if (event.data?.stats)
            setStats(event.data.stats as Record<string, unknown>);
        }
        if (event.status === "error") {
          setStage("error");
          setErrorMsg((event.data?.detail as string) || "An error occurred");
          toast.error((event.data?.detail as string) || "Pipeline failed");
        }
      },
      (error) => {
        setStage("error");
        setErrorMsg(error);
        toast.error(error);
      },
      () => {
        setStage("done");
        toast.success("Executive brief generated and sent!");
        fireConfetti();
        addHistoryEntry({
          filename: file.name,
          email,
          rowsProcessed:
            ((stats as Record<string, unknown>)?.total_rows as number) || 0,
        });
        setHistoryTrigger({});
      },
    );

    abortRef.current = cancel;
  }, [file, email, subject, stats]);

  const handleSubmitClassic = useCallback(async () => {
    if (!file) return toast.error("Please upload a file first.");
    const emailErr = validateEmail(email);
    if (emailErr) return toast.error(emailErr);

    setStage("parsing");
    setSummary("");
    setStats(null);
    setErrorMsg("");

    try {
      // Step 1: Upload & Analyze
      setStage("analyzing");
      const result = await uploadAndAnalyze(file);
      setSummary(result.summary);
      setStats({ ...result.stats, rows_processed: result.rows_processed });

      // Step 2: Send Email
      setStage("sending");
      await sendSummaryEmail(email, result.summary, subject);

      setStage("done");
      toast.success("Executive brief generated and sent!");
      fireConfetti();
      addHistoryEntry({
        filename: file.name,
        email,
        rowsProcessed: result.rows_processed,
      });
      setHistoryTrigger({});
    } catch (err: unknown) {
      setStage("error");
      const msg =
        err instanceof Error ? err.message : "An unknown error occurred";
      setErrorMsg(msg);
      toast.error(msg);
    }
  }, [file, email, subject]);

  const handleSubmit = useStreaming ? handleSubmitStream : handleSubmitClassic;

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="sticky top-0 z-20 backdrop-blur-md bg-white/80 dark:bg-gray-900/80 border-b border-gray-200 dark:border-gray-800">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand-500 to-purple-600 flex items-center justify-center">
              <Rabbit className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold bg-gradient-to-r from-brand-600 to-purple-600 bg-clip-text text-transparent">
                Sales Insight Automator
              </h1>
              <p className="text-[10px] text-gray-400 -mt-0.5 tracking-wide uppercase">
                by Rabbitt AI
              </p>
            </div>
          </div>
          <ThemeToggle />
        </div>
      </header>

      {/* Main */}
      <main className="max-w-4xl mx-auto px-4 py-8 space-y-6">
        {/* Hero card */}
        <div className="text-center space-y-2 pb-2">
          <h2 className="text-2xl sm:text-3xl font-bold">
            Turn Raw Data into{" "}
            <span className="bg-gradient-to-r from-brand-500 to-purple-500 bg-clip-text text-transparent">
              Executive Insights
            </span>
          </h2>
          <p className="text-gray-500 dark:text-gray-400 max-w-lg mx-auto text-sm">
            Upload your sales data file, and our AI engine will generate a
            professional narrative summary and deliver it straight to any inbox.
          </p>
        </div>

        {/* Upload Section */}
        <div className="rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-sm p-6 space-y-5">
          <DropZone onFileAccepted={setFile} disabled={isProcessing} />
          <FilePreview file={file} />

          <div className="grid sm:grid-cols-2 gap-4">
            <EmailInput
              value={email}
              onChange={setEmail}
              disabled={isProcessing}
            />
            <SubjectEditor
              value={subject}
              onChange={setSubject}
              disabled={isProcessing}
            />
          </div>

          {/* Mode toggle */}
          <div className="flex items-center gap-2 text-xs text-gray-400">
            <label className="flex items-center gap-1.5 cursor-pointer">
              <input
                type="checkbox"
                checked={useStreaming}
                onChange={(e) => setUseStreaming(e.target.checked)}
                disabled={isProcessing}
                className="rounded border-gray-300 text-brand-500 focus:ring-brand-500"
              />
              Real-time progress (SSE stream)
            </label>
          </div>

          {/* Actions */}
          <div className="flex gap-3">
            <button
              onClick={handleSubmit}
              disabled={isProcessing || !file}
              className={cn(
                "flex-1 flex items-center justify-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold transition-all",
                "bg-gradient-to-r from-brand-500 to-purple-600 text-white",
                "hover:from-brand-600 hover:to-purple-700 hover:shadow-lg hover:shadow-brand-500/25",
                "disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-none",
                "active:scale-[0.98]",
              )}
            >
              <Rocket className="w-4 h-4" />
              {isProcessing ? "Processing..." : "Generate & Send Brief"}
            </button>

            {(stage === "done" || stage === "error") && (
              <button
                onClick={handleReset}
                className="flex items-center gap-2 px-4 py-3 rounded-xl text-sm font-medium border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
              >
                <RotateCcw className="w-4 h-4" />
                Reset
              </button>
            )}
          </div>
        </div>

        {/* Progress */}
        {stage !== "idle" && (
          <div className="rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-sm p-6">
            <ProgressTracker currentStage={stage} errorMessage={errorMsg} />
          </div>
        )}

        {/* Summary Preview */}
        {summary && (
          <SummaryPreview summary={summary} stats={stats || undefined} />
        )}
      </main>

      {/* History Sidebar */}
      <HistorySidebar onNewEntry={historyTrigger as never} />

      {/* Footer */}
      <footer className="text-center py-6 text-xs text-gray-400 border-t border-gray-100 dark:border-gray-800">
        <p>&copy; 2026 Rabbitt AI — Sales Insight Automator v1.0.0</p>
      </footer>
    </div>
  );
}
