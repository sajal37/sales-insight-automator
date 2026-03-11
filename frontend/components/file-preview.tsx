"use client";

import { useEffect, useState } from "react";
import { Table } from "lucide-react";
import Papa from "papaparse";

interface FilePreviewProps {
  file: File | null;
}

export default function FilePreview({ file }: FilePreviewProps) {
  const [headers, setHeaders] = useState<string[]>([]);
  const [rows, setRows] = useState<string[][]>([]);
  const [totalRows, setTotalRows] = useState(0);

  useEffect(() => {
    if (!file) {
      setHeaders([]);
      setRows([]);
      setTotalRows(0);
      return;
    }

    const ext = file.name.split(".").pop()?.toLowerCase();

    if (ext === "csv") {
      const reader = new FileReader();
      reader.onload = (e) => {
        const text = e.target?.result as string;
        const parsed = Papa.parse(text, { header: false, preview: 6 });
        const allRows = parsed.data as string[][];
        if (allRows.length > 0) {
          setHeaders(allRows[0]);
          setRows(allRows.slice(1, 6));

          // Count total rows
          const full = Papa.parse(text, { header: false });
          setTotalRows((full.data as string[][]).length - 1); // minus header
        }
      };
      reader.readAsText(file);
    } else {
      // For XLSX, we won't preview client-side to keep it simple
      setHeaders([]);
      setRows([]);
      setTotalRows(0);
    }
  }, [file]);

  if (!file || headers.length === 0) return null;

  return (
    <div className="animate-fade-in rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-2.5 bg-gray-50 dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-700">
        <Table className="w-4 h-4 text-brand-500" />
        <span className="text-sm font-medium">
          Data Preview — {totalRows.toLocaleString()} row
          {totalRows !== 1 ? "s" : ""}
        </span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-gray-50 dark:bg-gray-800/30">
              {headers.map((h, i) => (
                <th
                  key={i}
                  className="px-3 py-2 text-left font-semibold text-gray-600 dark:text-gray-400 whitespace-nowrap"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, ri) => (
              <tr
                key={ri}
                className="border-t border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/20"
              >
                {row.map((cell, ci) => (
                  <td
                    key={ci}
                    className="px-3 py-1.5 text-gray-700 dark:text-gray-300 whitespace-nowrap"
                  >
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {totalRows > 5 && (
        <div className="px-4 py-2 text-xs text-gray-400 bg-gray-50 dark:bg-gray-800/50 border-t border-gray-100 dark:border-gray-800">
          Showing 5 of {totalRows.toLocaleString()} rows
        </div>
      )}
    </div>
  );
}
