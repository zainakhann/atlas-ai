"use client";

export interface Source {
  source_number: number;
  document_id: string;
  chunk_id: string;
  page_number: number | null;
  filename: string;
  snippet: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  followUps?: string[];
}

function AtlasLogo({ active }: { active?: boolean }) {
  return (
    <div
      className={`flex h-6.5 w-6.5 shrink-0 items-center justify-center rounded-full ${
        active ? "atlas-avatar-active" : ""
      }`}
    >
      <svg viewBox="0 0 24 24" width="18" height="18" fill="none">
        <circle cx="12" cy="12" r="2.2" fill="#3B82F6" />
        <ellipse cx="12" cy="12" rx="9.2" ry="3.4" stroke="#3B82F6" strokeWidth="1.5" />
        <ellipse cx="12" cy="12" rx="9.2" ry="3.4" transform="rotate(60 12 12)" stroke="#3B82F6" strokeWidth="1.5" />
        <ellipse cx="12" cy="12" rx="9.2" ry="3.4" transform="rotate(120 12 12)" stroke="#3B82F6" strokeWidth="1.5" />
      </svg>
    </div>
  );
}

export function ChatMessageBubble({
  message,
  onFollowUpClick,
  isStreaming,
}: {
  message: Message;
  onFollowUpClick?: (text: string) => void;
  isStreaming?: boolean;
}) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[78%] rounded-3xl bg-secondary px-4 py-2.5 text-base leading-relaxed text-secondary-foreground">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-2.5">
      <AtlasLogo active={isStreaming} />

      <div className="max-w-[82%]">
        <p className="whitespace-pre-line text-base leading-relaxed text-foreground">
          {message.content}
        </p>

        {message.sources && message.sources.length > 0 && (
          <div className="mt-2.5 flex flex-wrap gap-1.5">
            {message.sources.map((s) => (
              <button
                key={s.chunk_id}
                className="flex items-center gap-1.5 rounded-full border border-border bg-card px-3 py-1.5 text-[13px] text-muted-foreground transition-colors hover:bg-accent"
              >
                <span
                  className="flex h-4 w-4 items-center justify-center rounded-full text-[10px] font-medium text-white"
                  style={{ backgroundColor: "#3B82F6" }}
                >
                  {s.source_number}
                </span>
                {s.page_number
                  ? `${s.filename}, p.${s.page_number}`
                  : s.filename}
              </button>
            ))}
          </div>
        )}

        
      </div>
    </div>
  );
}

export function ThinkingIndicator() {
  return (
    <div className="flex items-center gap-2.5">
      <AtlasLogo active />
      <div className="flex items-center gap-1 py-1">
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.3s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.15s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground" />
      </div>
    </div>
  );
}