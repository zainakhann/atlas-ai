"use client";

import { useState } from "react";
import { ArrowUp } from "lucide-react";

export function ChatInput({
  value,
  onChange,
  onSend,
  disabled,
}: {
  value: string;
  onChange: (v: string) => void;
  onSend: () => void;
  disabled?: boolean;
}) {
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (value.trim() && !disabled) onSend();
    }
  };

  return (
    <div className="border-t border-border bg-background px-5 py-3">
      <div className="mx-auto flex max-w-3xl items-center gap-2 rounded-3xl border border-border bg-card px-4 py-2">
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question about your documents"
          rows={1}
          className="flex-1 resize-none bg-transparent text-base text-foreground placeholder:text-muted-foreground focus:outline-none"
        />
        <button
          onClick={onSend}
          disabled={!value.trim() || disabled}
          className="flex h-6.5 w-6.5 shrink-0 items-center justify-center rounded-full bg-foreground text-background transition-opacity disabled:opacity-20"
        >
          <ArrowUp className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}