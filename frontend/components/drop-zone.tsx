"use client";

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, FileSpreadsheet, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { validateFile, formatFileSize } from "@/lib/validators";

interface DropZoneProps {
  onFileAccepted: (file: File) => void;
  disabled?: boolean;
}

export default function DropZone({ onFileAccepted, disabled }: DropZoneProps) {
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      setError(null);
      if (acceptedFiles.length === 0) return;

      const file = acceptedFiles[0];
      const validationError = validateFile(file);
      if (validationError) {
        setError(validationError);
        return;
      }

      setSelectedFile(file);
      onFileAccepted(file);
    },
    [onFileAccepted],
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "text/csv": [".csv"],
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [
        ".xlsx",
      ],
      "application/vnd.ms-excel": [".xls"],
    },
    maxFiles: 1,
    disabled,
  });

  const clearFile = (e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedFile(null);
    setError(null);
  };

  return (
    <div className="space-y-2">
      <div
        {...getRootProps()}
        className={cn(
          "relative border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-300",
          isDragActive &&
            "dropzone-active border-brand-500 bg-brand-50 dark:bg-brand-950/30",
          !isDragActive &&
            !error &&
            "border-gray-300 dark:border-gray-600 hover:border-brand-400 hover:bg-brand-50/50 dark:hover:bg-brand-950/20",
          error && "border-red-400 bg-red-50 dark:bg-red-950/20",
          disabled && "opacity-50 cursor-not-allowed",
          selectedFile &&
            !error &&
            "border-green-400 bg-green-50 dark:bg-green-950/20",
        )}
      >
        <input {...getInputProps()} />

        {selectedFile && !error ? (
          <div className="flex items-center justify-center gap-3 animate-fade-in">
            <FileSpreadsheet className="w-10 h-10 text-green-500" />
            <div className="text-left">
              <p className="font-semibold text-green-700 dark:text-green-400">
                {selectedFile.name}
              </p>
              <p className="text-sm text-gray-500">
                {formatFileSize(selectedFile.size)}
              </p>
            </div>
            {!disabled && (
              <button
                onClick={clearFile}
                className="ml-2 p-1 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                aria-label="Remove file"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            <Upload
              className={cn(
                "w-12 h-12 mx-auto transition-transform",
                isDragActive ? "text-brand-500 scale-110" : "text-gray-400",
              )}
            />
            <div>
              <p className="font-medium">
                {isDragActive
                  ? "Drop your file here..."
                  : "Drag & drop your sales data file"}
              </p>
              <p className="text-sm text-gray-500 mt-1">
                or click to browse — .csv, .xlsx (max 50 MB)
              </p>
            </div>
          </div>
        )}
      </div>

      {error && (
        <p className="text-sm text-red-500 animate-fade-in flex items-center gap-1">
          <X className="w-3 h-3" />
          {error}
        </p>
      )}
    </div>
  );
}
