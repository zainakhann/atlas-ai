"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { FileText, ListFilter, HelpCircle, Sparkles, Clock, ShieldCheck, ArrowUp, ArrowRight, MessageSquare, LogOut, User } from "lucide-react";
import { apiFetch, isDemoAccount } from "@/lib/api";
import { DocumentPickerModal } from "@/components/chat/document-picker-modal";

interface DocumentItem {
  id: string;
  filename: string;
  status: string;
}

interface ConversationSummary {
  id: string;
  title: string;
}

const TRY_ASKING = [
  { icon: FileText, title: "Summarize", subtitle: "Summarize this document", mode: "summarize", iconBg: "bg-blue-500" },
  { icon: ListFilter, title: "Key points", subtitle: "What are the key points?", mode: "key_points", iconBg: "bg-teal-500" },
  { icon: HelpCircle, title: "Questions", subtitle: "What questions does this document answer?", mode: "questions", iconBg: "bg-violet-500" },
  { icon: Sparkles, title: "Explain simply", subtitle: "Explain this in simple terms", mode: "simplify", iconBg: "bg-amber-500" },
];

export default function HomePage() {
  const router = useRouter();
  const [question, setQuestion] = useState("");
  const [documentCount, setDocumentCount] = useState(0);
  const [recent, setRecent] = useState<ConversationSummary[]>([]);
  const [showDocPicker, setShowDocPicker] = useState(false);
  const [pendingMode, setPendingMode] = useState<string | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    apiFetch("/documents")
      .then((res) => (res.ok ? res.json() : []))
      .then((docs: DocumentItem[]) => setDocumentCount(docs.filter((d) => d.status === "ready").length))
      .catch(() => setDocumentCount(0));

    if (!isDemoAccount()) {
      apiFetch("/conversations")
        .then((res) => (res.ok ? res.json() : []))
        .then((data: ConversationSummary[]) => setRecent(data.slice(0, 4)))
        .catch(() => setRecent([]));
    }
  }, []);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("atlas_token");
    router.push("/login");
  };

  const handleAsk = () => {
    if (!question.trim()) return;
    router.push(`/dashboard/chat?new=${Date.now()}&prefill=${encodeURIComponent(question)}`);
  };

  const handleTryAsking = async (mode: string) => {
    try {
      const res = await apiFetch("/documents");
      const docs = await res.json();
      const ready = docs.filter((d: DocumentItem) => d.status === "ready");
      if (ready.length === 1) {
        router.push(`/dashboard/chat?new=${Date.now()}&analyze=${mode}&doc=${ready[0].id}`);
      } else {
        setPendingMode(mode);
        setShowDocPicker(true);
      }
    } catch {
      setPendingMode(mode);
      setShowDocPicker(true);
    }
  };

  return (
    <div className="relative -m-8 flex h-full flex-col overflow-y-auto p-8">
      {/* space background with real globe image */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <img
          src="/globe.png"
          alt=""
          className="absolute -right-20 top-[-40px] w-[720px] max-w-none"
          style={{
            maskImage:
              "radial-gradient(circle at 75% 35%, black 40%, transparent 72%)",
            WebkitMaskImage:
              "radial-gradient(circle at 75% 35%, black 40%, transparent 72%)",
          }}
        />
      </div>

      {/* top bar */}
      <div className="relative z-10 mb-2 flex items-center justify-end">
        <div ref={menuRef} className="relative">
          <button
            onClick={() => setMenuOpen((v) => !v)}
            className="flex h-9 w-9 items-center justify-center rounded-full border-2 border-blue-500 text-foreground hover:bg-accent"
          >
            <User className="h-4 w-4" />
          </button>

          {menuOpen && (
            <div className="absolute right-0 top-11 w-40 overflow-hidden rounded-xl border border-border bg-card shadow-lg">
              <button
                onClick={handleLogout}
                className="flex w-full items-center gap-2.5 px-4 py-2.5 text-left text-sm text-red-400 hover:bg-accent"
              >
                <LogOut className="h-4 w-4" />
                Log out
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="relative z-10 mx-auto flex w-full max-w-4xl flex-1 flex-col px-6 pb-12 pt-6">
        <div className="mb-4 flex items-center justify-center">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-blue-500/30 bg-blue-500/10 px-3 py-1 text-xs font-medium text-blue-400">
            <span className="h-1.5 w-1.5 rounded-full bg-blue-400" />
            Atlas AI v1.0
          </span>
        </div>

        <div className="mb-8 text-center">
          <p className="mb-2 text-sm text-muted-foreground">Welcome back 👋</p>
          <h1 className="mb-2 text-4xl font-semibold tracking-tight text-foreground">
            Ask your documents <span className="text-blue-400">anything</span>
          </h1>
          <p className="text-sm text-muted-foreground">
            {documentCount} document{documentCount === 1 ? "" : "s"} indexed, answers grounded with citations
          </p>
        </div>

        <div className="mb-10 rounded-2xl border border-border bg-card p-4">
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleAsk();
              }
            }}
            placeholder="Ask a question about your documents..."
            rows={2}
            className="mb-3 w-full resize-none bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
          />
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-xs text-muted-foreground">
              <FileText className="h-3.5 w-3.5" />
              All documents
            </span>
            <button
              onClick={handleAsk}
              className="flex h-9 w-9 items-center justify-center rounded-full bg-blue-500 text-white transition-colors hover:bg-blue-600"
            >
              <ArrowUp className="h-4 w-4" />
            </button>
          </div>
        </div>

        <div className="mb-10">
          <p className="mb-3 flex items-center gap-1.5 text-sm font-medium text-foreground">
            <Sparkles className="h-4 w-4 text-blue-400" />
            Try asking
          </p>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {TRY_ASKING.map((item) => (
              <button
                key={item.mode}
                onClick={() => handleTryAsking(item.mode)}
                className="group relative overflow-hidden rounded-2xl border border-border bg-card p-4 text-left transition-colors hover:border-muted-foreground"
              >
                <div className={`mb-6 flex h-9 w-9 items-center justify-center rounded-xl ${item.iconBg}`}>
                  <item.icon className="h-4.5 w-4.5 text-white" />
                </div>
                <p className="text-sm font-medium text-foreground">{item.title}</p>
                <p className="text-xs text-muted-foreground">{item.subtitle}</p>
                <div className="absolute bottom-3 right-3 flex h-6 w-6 items-center justify-center rounded-full bg-muted opacity-0 transition-opacity group-hover:opacity-100">
                  <ArrowRight className="h-3 w-3 text-foreground" />
                </div>
              </button>
            ))}
          </div>
        </div>

        {recent.length > 0 && (
          <div className="mb-8 rounded-2xl border border-border bg-card p-4">
            <div className="mb-2 flex items-center justify-between">
              <p className="flex items-center gap-1.5 text-sm font-medium text-foreground">
                <Clock className="h-4 w-4 text-muted-foreground" />
                Recent activity
              </p>
              <button
                onClick={() => router.push("/dashboard/chat")}
                className="text-xs font-medium text-blue-400 hover:underline"
              >
                View all
              </button>
            </div>
            <div className="flex flex-col">
              {recent.map((c) => (
                <div
                  key={c.id}
                  className="flex items-center gap-2.5 border-t border-border py-3 first:border-t-0"
                >
                  <button
                    onClick={() => router.push(`/dashboard/chat?conversation=${c.id}`)}
                    className="flex flex-1 items-center gap-2.5 text-left hover:opacity-80"
                  >
                    <MessageSquare className="h-4 w-4 shrink-0 text-muted-foreground" />
                    <span className="truncate text-sm text-foreground">{c.title}</span>
                  </button>
                  
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="mt-auto flex justify-center">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-border px-3 py-1.5 text-xs text-muted-foreground">
            <ShieldCheck className="h-3.5 w-3.5" />
            Your data is private and secure
          </span>
        </div>
      </div>

      {showDocPicker && (
        <DocumentPickerModal
          onSelect={(doc) => {
            setShowDocPicker(false);
            router.push(`/dashboard/chat?new=${Date.now()}&analyze=${pendingMode}&doc=${doc.id}`);
          }}
          onClose={() => setShowDocPicker(false)}
        />
      )}
    </div>
  );
}