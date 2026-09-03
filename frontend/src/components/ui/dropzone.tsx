"use client";

import * as React from "react";
import { motion, useReducedMotion } from "motion/react";
import { FileText, UploadCloud, X } from "lucide-react";

import { cn, formatBytes } from "@/lib/utils";
import { Button } from "./button";

export interface DroppedFile {
  id: string;
  name: string;
  size: number;
  /** The file itself, so the caller can upload it rather than re-prompt. */
  file: File;
}

export function Dropzone({
  files,
  onFilesChange,
  accept = ".pdf,.docx,.doc",
  className,
}: {
  files: DroppedFile[];
  onFilesChange: (files: DroppedFile[]) => void;
  accept?: string;
  className?: string;
}) {
  const [dragging, setDragging] = React.useState(false);
  const inputRef = React.useRef<HTMLInputElement>(null);
  const reduce = useReducedMotion();

  function ingest(list: FileList | null) {
    if (!list?.length) return;
    const next = Array.from(list).map((file) => ({
      id: `${file.name}-${file.size}-${file.lastModified}`,
      name: file.name,
      size: file.size,
      file,
    }));
    const merged = [...files];
    for (const file of next) if (!merged.some((f) => f.id === file.id)) merged.push(file);
    onFilesChange(merged);
  }

  return (
    <div className={cn("space-y-3", className)}>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          ingest(e.dataTransfer.files);
        }}
        className={cn(
          "relative rounded-lg border border-dashed px-6 py-10 text-center",
          "transition-[border-color,background-color] duration-200 ease-[cubic-bezier(0.32,0.72,0,1)]",
          dragging
            ? "border-patina bg-patina-tint"
            : "border-line-strong bg-paper-sunk hover:border-[var(--ink-faint)]",
        )}
      >
        <motion.div
          animate={reduce ? undefined : { y: dragging ? -3 : 0 }}
          transition={{ type: "spring", stiffness: 420, damping: 36 }}
          className="flex flex-col items-center gap-3"
        >
          <UploadCloud
            className={cn("size-7 transition-colors duration-200", dragging ? "text-patina" : "text-ink-faint")}
            aria-hidden
          />
          <div className="space-y-1">
            <p className="text-sm font-medium text-ink">
              Drop a solicitation here, or{" "}
              <button
                type="button"
                onClick={() => inputRef.current?.click()}
                className="text-patina underline decoration-[var(--line-strong)] underline-offset-4 transition-colors hover:decoration-current"
              >
                choose a file
              </button>
            </p>
            <p className="text-xs text-ink-faint">
              PDF or Word, up to 250 MB. Amendments can be added after the first read.
            </p>
          </div>
        </motion.div>
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          multiple
          className="sr-only"
          onChange={(e) => ingest(e.target.files)}
        />
      </div>

      {files.length > 0 ? (
        <ul className="space-y-1.5">
          {files.map((file) => (
            <motion.li
              key={file.id}
              initial={reduce ? false : { opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.24, ease: [0.32, 0.72, 0, 1] }}
              className="flex items-center gap-3 rounded-md border border-line bg-paper-raised px-3 py-2.5"
            >
              <FileText className="size-4 shrink-0 text-ink-faint" aria-hidden />
              <span className="min-w-0 flex-1 truncate text-sm text-ink">{file.name}</span>
              <span className="shrink-0 font-mono text-2xs text-ink-faint">{formatBytes(file.size)}</span>
              <Button
                variant="quiet"
                size="iconSm"
                aria-label={`Remove ${file.name}`}
                onClick={() => onFilesChange(files.filter((f) => f.id !== file.id))}
              >
                <X />
              </Button>
            </motion.li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
