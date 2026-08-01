"use client";

import { FileText, ListFilter, HelpCircle, Sparkles } from "lucide-react";

const EXAMPLES = [
  { icon: FileText, text: "Summarize this document", mode: "summarize" },
  { icon: ListFilter, text: "What are the key points?", mode: "key_points" },
  { icon: HelpCircle, text: "What questions does this document answer?", mode: "questions" },
  { icon: Sparkles, text: "Explain this in simple terms", mode: "simplify" },
];

export function ChatEmptyState({
  documentCount,
  onExampleClick,
  onAnalyzeClick,
}: {
  documentCount: number;
  onExampleClick: (text: string) => void;
  onAnalyzeClick: (mode: string) => void;
}) {
  return (
    <div className="mx-auto flex w-full max-w-lg flex-col items-center px-6 pt-20">
      <div className="mb-6">
        <svg viewBox="0 0 24 24" width="48" height="48" fill="none">
          <circle cx="12" cy="12" r="2.2" fill="#3B82F6" />
          <ellipse cx="12" cy="12" rx="9.2" ry="3.4" stroke="#3B82F6" strokeWidth="1.1" />
          <ellipse cx="12" cy="12" rx="9.2" ry="3.4" transform="rotate(60 12 12)" stroke="#3B82F6" strokeWidth="1.1" />
          <ellipse cx="12" cy="12" rx="9.2" ry="3.4" transform="rotate(120 12 12)" stroke="#3B82F6" strokeWidth="1.1" />
        </svg>
      </div>

      <h1 className="mb-1 text-center text-2xl font-medium text-foreground">
        Ask your documents
      </h1>
      <p className="mb-8 text-center text-[15px] text-muted-foreground">
        {documentCount} document{documentCount === 1 ? "" : "s"} indexed, answers grounded with citations
      </p>

      <div className="mb-6 w-full">
        <p className="mb-2.5 text-[11px] tracking-wide text-muted-foreground">TRY ASKING</p>
        <div className="grid grid-cols-2 gap-2">
          {EXAMPLES.map((ex) => (
            <button
              key={ex.text}
              onClick={() => onAnalyzeClick(ex.mode)}
              className="rounded-2xl border border-border bg-card p-3 text-left transition-colors hover:bg-accent"
            >
              <ex.icon className="mb-2 h-4 w-4" style={{ color: "#3B82F6" }} />
              <p className="text-[13px] text-foreground">{ex.text}</p>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}