"use client";

import { useState, useEffect } from "react";
import {
  History,
  Clock,
  Trash2,
  ChevronRight,
  ChevronLeft,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface HistoryEntry {
  id: string;
  filename: string;
  email: string;
  timestamp: string;
  rowsProcessed: number;
}

interface HistorySidebarProps {
  onNewEntry?: HistoryEntry | null;
}

const STORAGE_KEY = "sales-insight-history";

export function addHistoryEntry(entry: Omit<HistoryEntry, "id" | "timestamp">) {
  const stored = localStorage.getItem(STORAGE_KEY);
  const history: HistoryEntry[] = stored ? JSON.parse(stored) : [];
  const newEntry: HistoryEntry = {
    ...entry,
    id: crypto.randomUUID(),
    timestamp: new Date().toISOString(),
  };
  history.unshift(newEntry);
  // Keep last 20 entries
  localStorage.setItem(STORAGE_KEY, JSON.stringify(history.slice(0, 20)));
}

export default function HistorySidebar({ onNewEntry }: HistorySidebarProps) {
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [isOpen, setIsOpen] = useState(false);

  const loadHistory = () => {
    const stored = localStorage.getItem(STORAGE_KEY);
    setHistory(stored ? JSON.parse(stored) : []);
  };

  useEffect(() => {
    loadHistory();
  }, [onNewEntry]);

  const clearHistory = () => {
    localStorage.removeItem(STORAGE_KEY);
    setHistory([]);
  };

  const formatTime = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <>
      {/* Toggle button */}
      <button
        onClick={() => {
          setIsOpen(!isOpen);
          loadHistory();
        }}
        className={cn(
          "fixed right-0 top-1/2 -translate-y-1/2 z-40 p-2 rounded-l-lg shadow-lg transition-all",
          "bg-brand-500 text-white hover:bg-brand-600",
          isOpen && "translate-x-72",
        )}
        aria-label="Toggle history"
      >
        {isOpen ? (
          <ChevronRight className="w-4 h-4" />
        ) : (
          <ChevronLeft className="w-4 h-4" />
        )}
      </button>

      {/* Sidebar */}
      <div
        className={cn(
          "fixed right-0 top-0 h-full w-72 bg-white dark:bg-gray-900 shadow-xl z-30 transition-transform duration-300 border-l border-gray-200 dark:border-gray-700",
          isOpen ? "translate-x-0" : "translate-x-full",
        )}
      >
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2">
            <History className="w-4 h-4 text-brand-500" />
            <span className="font-semibold text-sm">Recent Uploads</span>
          </div>
          {history.length > 0 && (
            <button
              onClick={clearHistory}
              className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400"
              title="Clear history"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        <div className="overflow-y-auto h-[calc(100%-56px)] p-3 space-y-2">
          {history.length === 0 ? (
            <p className="text-xs text-gray-400 text-center mt-8">
              No uploads yet. Your history will appear here.
            </p>
          ) : (
            history.map((entry) => (
              <div
                key={entry.id}
                className="p-3 rounded-lg bg-gray-50 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700"
              >
                <p className="text-sm font-medium truncate">{entry.filename}</p>
                <p className="text-xs text-gray-500 truncate mt-0.5">
                  {entry.email}
                </p>
                <div className="flex items-center justify-between mt-2">
                  <span className="text-xs text-gray-400 flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {formatTime(entry.timestamp)}
                  </span>
                  <span className="text-xs text-brand-500 font-medium">
                    {entry.rowsProcessed} rows
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </>
  );
}
