"use client";

import { useEffect, useState, useCallback } from "react";
import { Upload, FileText, CheckCircle2, Loader2, XCircle, Trash2 } from "lucide-react";
import { apiFetch } from "@/lib/api";

interface DocumentItem {
  id: string;
  filename: string;
  status: string;
  chunk_count: number;
  deletable: boolean;
}

export default function DashboardPage() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  const loadDocuments = useCallback(() => {
    apiFetch("/documents")
      .then((res) => (res.ok ? res.json() : []))
      .then(setDocuments)
      .catch(() => setDocuments([]));
  }, []);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  const deleteDocument = async (id: string) => {
    if (!confirm("Delete this document? This can't be undone.")) return;
    try {
      await apiFetch(`/documents/${id}`, { method: "DELETE" });
      loadDocuments();
    } catch {
      // silently fail for now, could add a toast later
    }
  };

  const uploadFile = async (file: File) => {
    setIsUploading(true);
    const formData = new FormData();
    formData.append("file", file);
    try {
      await apiFetch("/upload", {
        method: "POST",
        body: formData,
      });
      loadDocuments();
    } catch {
      // silently fail for now, could add a toast later
    } finally {
      setIsUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) uploadFile(file);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) uploadFile(file);
  };

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="mb-1 text-2xl font-semibold text-foreground">Documents</h1>
      <p className="mb-6 text-sm text-muted-foreground">
        Upload PDFs, Word docs, or text files to ask questions about them.
      </p>

      <label
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        className={`mb-8 flex flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors cursor-pointer ${
          isDragging
            ? "border-cyan-500 bg-cyan-500/5"
            : "border-border hover:border-muted-foreground"
        }`}
      >
        <input
          type="file"
          accept=".pdf,.docx,.txt,.md"
          className="hidden"
          onChange={handleFileSelect}
        />
        {isUploading ? (
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        ) : (
          <Upload className="h-6 w-6 text-muted-foreground" />
        )}
        <p className="text-sm text-muted-foreground">
          {isUploading ? "Uploading..." : "Drop a file here, or click to browse"}
        </p>
        <p className="text-xs text-muted-foreground">PDF, DOCX, TXT, or MD</p>
      </label>

      <div className="flex flex-col gap-2">
        {documents.length === 0 && (
          <p className="text-sm text-muted-foreground">No documents uploaded yet.</p>
        )}
        {documents.map((doc) => (
          <div
            key={doc.id}
            className="flex items-center gap-3 rounded-lg border border-border px-4 py-3"
          >
            <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
            <span className="flex-1 truncate text-sm text-foreground">{doc.filename}</span>
            <span className="text-xs text-muted-foreground">
              {doc.chunk_count} {doc.chunk_count === 1 ? "chunk" : "chunks"}
            </span>
            {doc.status === "ready" && (
              <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-500" />
            )}
            {doc.status === "processing" && (
              <Loader2 className="h-4 w-4 shrink-0 animate-spin text-muted-foreground" />
            )}
            {doc.status === "failed" && (
              <XCircle className="h-4 w-4 shrink-0 text-red-500" />
            )}
            {doc.deletable && (
              <button
                onClick={() => deleteDocument(doc.id)}
                className="text-muted-foreground transition-colors hover:text-red-500"
                title="Delete document"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}