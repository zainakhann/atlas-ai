"use client";

import { useEffect, useState } from "react";
import { FileText, Loader2, X } from "lucide-react";
import { apiFetch } from "@/lib/api";

interface DocumentItem {
  id: string;
  filename: string;
  status: string;
  chunk_count: number;
}

export function DocumentPickerModal({
  onSelect,
  onClose,
}: {
  onSelect: (doc: DocumentItem) => void;
  onClose: () => void;
}) {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    apiFetch("/documents")
      .then((res) => (res.ok ? res.json() : []))
      .then((data) => setDocuments(data.filter((d: DocumentItem) => d.status === "ready")))
      .catch(() => setDocuments([]))
      .finally(() => setIsLoading(false));
  }, []);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div
        className="w-full max-w-sm rounded-2xl border border-border bg-card p-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-medium text-foreground">Choose a document to summarize</h2>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
            <X className="h-4 w-4" />
          </button>
        </div>

        {isLoading && (
          <div className="flex items-center justify-center py-6">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        )}

        {!isLoading && documents.length === 0 && (
          <p className="py-4 text-center text-sm text-muted-foreground">No documents ready yet.</p>
        )}

        <div className="flex flex-col gap-1.5">
          {documents.map((doc) => (
            <button
              key={doc.id}
              onClick={() => onSelect(doc)}
              className="flex items-center gap-2.5 rounded-lg border border-border px-3 py-2.5 text-left transition-colors hover:bg-accent"
            >
              <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
              <span className="truncate text-sm text-foreground">{doc.filename}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}