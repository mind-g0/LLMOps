import { useRef } from "react";
import type { DragEvent } from "react";

const MAX_FILES = 10;
const MAX_FILE_SIZE_MB = 10;
const ACCEPTED_TYPES = [".pdf", ".docx"];
const ACCEPTED_MIME = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
];

export interface FileRejection {
  file: File;
  reason: string;
}

interface CvUploadProps {
  files: File[];
  onChange: (files: File[]) => void;
  onRejections?: (rejections: FileRejection[]) => void;
  disabled?: boolean;
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function hasAcceptedExtension(name: string): boolean {
  const lower = name.toLowerCase();
  return ACCEPTED_TYPES.some((ext) => lower.endsWith(ext));
}

export function CvUpload({ files, onChange, onRejections, disabled }: CvUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  function addFiles(incoming: FileList | File[]) {
    const rejections: FileRejection[] = [];
    const accepted: File[] = [];
    const existingKeys = new Set(files.map((f) => `${f.name}-${f.size}`));

    for (const file of Array.from(incoming)) {
      const key = `${file.name}-${file.size}`;
      if (existingKeys.has(key)) continue;

      if (!hasAcceptedExtension(file.name) && !ACCEPTED_MIME.includes(file.type)) {
        rejections.push({ file, reason: "Only .pdf and .docx files are supported." });
        continue;
      }
      if (file.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
        rejections.push({ file, reason: `File exceeds the ${MAX_FILE_SIZE_MB} MB limit.` });
        continue;
      }
      accepted.push(file);
      existingKeys.add(key);
    }

    const combined = [...files, ...accepted];
    const overflow = combined.length - MAX_FILES;
    const finalFiles = overflow > 0 ? combined.slice(0, MAX_FILES) : combined;

    if (overflow > 0) {
      const dropped = combined.slice(MAX_FILES);
      dropped.forEach((file) => rejections.push({ file, reason: `Only ${MAX_FILES} CVs can be processed at once.` }));
    }

    onChange(finalFiles);
    if (rejections.length > 0) {
      onRejections?.(rejections);
    }
  }

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    if (disabled) return;
    if (e.dataTransfer.files?.length) {
      addFiles(e.dataTransfer.files);
    }
  }

  function removeFile(index: number) {
    onChange(files.filter((_, i) => i !== index));
  }

  return (
    <div>
      <div
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
        className={`flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed px-6 py-8 text-center transition-colors ${
          disabled ? "border-ink-100 bg-ink-50" : "border-ink-200 hover:border-signal hover:bg-signal-light/40"
        }`}
      >
        <p className="text-sm text-ink-600">
          Drag CVs here, or{" "}
          <button
            type="button"
            disabled={disabled}
            onClick={() => inputRef.current?.click()}
            className="focus-ring font-medium text-signal underline underline-offset-2 disabled:no-underline disabled:text-ink-400"
          >
            add CVs
          </button>
        </p>
        <p className="text-xs text-ink-400">
          .pdf or .docx &middot; up to {MAX_FILES} files &middot; {MAX_FILE_SIZE_MB} MB each
        </p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={[...ACCEPTED_TYPES, ...ACCEPTED_MIME].join(",")}
          disabled={disabled}
          className="hidden"
          onChange={(e) => {
            if (e.target.files) addFiles(e.target.files);
            e.target.value = "";
          }}
        />
      </div>

      {files.length > 0 && (
        <ul className="mt-3 divide-y divide-ink-100 rounded-lg border border-ink-100">
          {files.map((file, i) => (
            <li key={`${file.name}-${file.size}-${i}`} className="flex items-center justify-between gap-3 px-3 py-2">
              <div className="min-w-0">
                <p className="truncate text-sm text-ink-800">{file.name}</p>
                <p className="text-xs text-ink-400">{formatSize(file.size)}</p>
              </div>
              <button
                type="button"
                disabled={disabled}
                onClick={() => removeFile(i)}
                aria-label={`Remove ${file.name}`}
                className="focus-ring shrink-0 rounded-md p-1.5 text-ink-400 hover:bg-rejected-bg hover:text-rejected disabled:opacity-40"
              >
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                  <path d="M2 2l10 10M12 2 2 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
              </button>
            </li>
          ))}
        </ul>
      )}

      <p className="mt-2 text-xs text-ink-400">
        {files.length} of {MAX_FILES} CVs selected
      </p>
    </div>
  );
}
