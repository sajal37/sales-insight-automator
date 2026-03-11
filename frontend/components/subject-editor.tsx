"use client";

import { useState } from "react";
import { Edit3 } from "lucide-react";
import { cn } from "@/lib/utils";

interface SubjectEditorProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}

export default function SubjectEditor({
  value,
  onChange,
  disabled,
}: SubjectEditorProps) {
  const [editing, setEditing] = useState(false);

  return (
    <div className="space-y-1.5">
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
        Email Subject
      </label>
      <div className="relative">
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => setEditing(true)}
          onBlur={() => setEditing(false)}
          disabled={disabled}
          className={cn(
            "w-full pl-3 pr-10 py-2.5 rounded-lg border text-sm transition-colors",
            "bg-white dark:bg-gray-800 placeholder-gray-400",
            "focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent",
            "border-gray-300 dark:border-gray-600",
            disabled && "opacity-50 cursor-not-allowed",
          )}
        />
        <Edit3
          className={cn(
            "absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 transition-colors",
            editing ? "text-brand-500" : "text-gray-400",
          )}
        />
      </div>
    </div>
  );
}
