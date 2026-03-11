"use client";

import { useState } from "react";
import { Eye, EyeOff, Copy, Check, FileText } from "lucide-react";
import { cn } from "@/lib/utils";
import ReactMarkdown from "react-markdown";

interface SummaryPreviewProps {
  summary: string;
  stats?: Record<string, unknown>;
}

export default function SummaryPreview({
  summary,
  stats,
}: SummaryPreviewProps) {
  const [showRaw, setShowRaw] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(summary);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!summary) return null;

  return (
    <div className="animate-slide-up rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-gray-50 dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-brand-500" />
          <span className="text-sm font-semibold">
            AI-Generated Executive Brief
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setShowRaw(!showRaw)}
            className="p-1.5 rounded-md hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
            title={showRaw ? "Show rendered" : "Show raw markdown"}
          >
            {showRaw ? (
              <Eye className="w-4 h-4" />
            ) : (
              <EyeOff className="w-4 h-4" />
            )}
          </button>
          <button
            onClick={handleCopy}
            className="p-1.5 rounded-md hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
            title="Copy to clipboard"
          >
            {copied ? (
              <Check className="w-4 h-4 text-green-500" />
            ) : (
              <Copy className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="p-5 max-h-[500px] overflow-y-auto">
        {showRaw ? (
          <pre className="text-sm whitespace-pre-wrap font-mono text-gray-600 dark:text-gray-400">
            {summary}
          </pre>
        ) : (
          <div className="prose prose-sm dark:prose-invert max-w-none prose-headings:text-brand-600 dark:prose-headings:text-brand-400 prose-strong:text-brand-700 dark:prose-strong:text-brand-300">
            <ReactMarkdown>{summary}</ReactMarkdown>
          </div>
        )}
      </div>

      {/* Stats footer */}
      {stats && (
        <div className="px-4 py-3 bg-gray-50 dark:bg-gray-800/50 border-t border-gray-200 dark:border-gray-700">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {stats.total_revenue != null && (
              <Stat
                label="Total Revenue"
                value={`$${Number(stats.total_revenue).toLocaleString()}`}
              />
            )}
            {stats.total_units_sold != null && (
              <Stat
                label="Units Sold"
                value={Number(stats.total_units_sold).toLocaleString()}
              />
            )}
            {stats.rows_processed != null && (
              <Stat
                label="Rows Processed"
                value={Number(stats.rows_processed).toLocaleString()}
              />
            )}
            {stats.cancellation_rate_pct != null && (
              <Stat
                label="Cancellation Rate"
                value={`${stats.cancellation_rate_pct}%`}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="text-center">
      <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
      <p className="text-sm font-bold text-brand-600 dark:text-brand-400">
        {value}
      </p>
    </div>
  );
}
