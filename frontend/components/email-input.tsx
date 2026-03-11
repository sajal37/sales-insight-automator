"use client";

import { useState } from "react";
import { Mail, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { validateEmail } from "@/lib/validators";

interface EmailInputProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}

export default function EmailInput({
  value,
  onChange,
  disabled,
}: EmailInputProps) {
  const [touched, setTouched] = useState(false);
  const error = touched ? validateEmail(value) : null;

  return (
    <div className="space-y-1.5">
      <label
        htmlFor="email"
        className="block text-sm font-medium text-gray-700 dark:text-gray-300"
      >
        Recipient Email
      </label>
      <div className="relative">
        <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          id="email"
          type="email"
          placeholder="executive@company.com"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onBlur={() => setTouched(true)}
          disabled={disabled}
          className={cn(
            "w-full pl-10 pr-4 py-2.5 rounded-lg border text-sm transition-colors",
            "bg-white dark:bg-gray-800 placeholder-gray-400",
            "focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent",
            error
              ? "border-red-400 dark:border-red-500"
              : "border-gray-300 dark:border-gray-600",
            disabled && "opacity-50 cursor-not-allowed",
          )}
        />
      </div>
      {error && (
        <p className="text-xs text-red-500 flex items-center gap-1 animate-fade-in">
          <AlertCircle className="w-3 h-3" />
          {error}
        </p>
      )}
    </div>
  );
}
