"use client";

import {
  Upload,
  BarChart3,
  Sparkles,
  Send,
  CheckCircle2,
  Loader2,
  XCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";

export type PipelineStage =
  | "idle"
  | "parsing"
  | "analyzing"
  | "generating"
  | "sending"
  | "done"
  | "error";

interface ProgressTrackerProps {
  currentStage: PipelineStage;
  errorMessage?: string;
}

const STAGES = [
  { key: "parsing", label: "Parsing File", icon: Upload },
  { key: "analyzing", label: "Analyzing Data", icon: BarChart3 },
  { key: "generating", label: "Generating Brief", icon: Sparkles },
  { key: "sending", label: "Sending Email", icon: Send },
] as const;

const stageOrder: Record<string, number> = {
  idle: -1,
  parsing: 0,
  analyzing: 1,
  generating: 2,
  sending: 3,
  done: 4,
  error: -2,
};

export default function ProgressTracker({
  currentStage,
  errorMessage,
}: ProgressTrackerProps) {
  const currentIdx = stageOrder[currentStage] ?? -1;

  if (currentStage === "idle") return null;

  return (
    <div className="animate-slide-up">
      <div className="flex items-center justify-between">
        {STAGES.map((stage, idx) => {
          const isComplete = currentIdx > idx || currentStage === "done";
          const isActive =
            currentIdx === idx &&
            currentStage !== "done" &&
            currentStage !== "error";
          const isPending = currentIdx < idx;
          const isErrorStage = currentStage === "error" && currentIdx === -2;

          const Icon = stage.icon;

          return (
            <div
              key={stage.key}
              className="flex-1 flex flex-col items-center relative"
            >
              {/* Connector line */}
              {idx > 0 && (
                <div
                  className={cn(
                    "absolute top-5 -left-1/2 w-full h-0.5 transition-colors duration-500",
                    isComplete
                      ? "bg-green-500"
                      : "bg-gray-200 dark:bg-gray-700",
                  )}
                />
              )}

              {/* Circle */}
              <div
                className={cn(
                  "relative z-10 w-10 h-10 rounded-full flex items-center justify-center transition-all duration-500",
                  isComplete && "bg-green-500 text-white",
                  isActive && "bg-brand-500 text-white animate-pulse-slow",
                  isPending && "bg-gray-200 dark:bg-gray-700 text-gray-400",
                  isErrorStage && "bg-red-500 text-white",
                )}
              >
                {isComplete ? (
                  <CheckCircle2 className="w-5 h-5" />
                ) : isActive ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Icon className="w-5 h-5" />
                )}
              </div>

              {/* Label */}
              <span
                className={cn(
                  "text-xs mt-2 font-medium transition-colors",
                  isComplete && "text-green-600 dark:text-green-400",
                  isActive && "text-brand-600 dark:text-brand-400",
                  isPending && "text-gray-400",
                )}
              >
                {stage.label}
              </span>
            </div>
          );
        })}
      </div>

      {currentStage === "error" && errorMessage && (
        <div className="mt-4 p-3 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 rounded-lg flex items-start gap-2 animate-fade-in">
          <XCircle className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" />
          <p className="text-sm text-red-600 dark:text-red-400">
            {errorMessage}
          </p>
        </div>
      )}

      {currentStage === "done" && (
        <div className="mt-4 p-3 bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-800 rounded-lg flex items-center gap-2 animate-fade-in">
          <CheckCircle2 className="w-4 h-4 text-green-500" />
          <p className="text-sm text-green-600 dark:text-green-400 font-medium">
            Pipeline complete — summary generated and email sent!
          </p>
        </div>
      )}
    </div>
  );
}
