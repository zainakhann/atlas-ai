"use client";

import Link from "next/link";
import { useEffect, useState, useCallback, useRef } from "react";
import { usePathname, useRouter } from "next/navigation";
import { ThemeToggle } from "@/components/theme-toggle";
import { Plus, LogOut, Home, FileText, MessageSquare, Sparkles } from "lucide-react";
import { apiFetch, clearToken } from "@/lib/api";

function TypewriterText({ text }: { text: string }) {
  const [displayed, setDisplayed] = useState("");
  useEffect(() => {
    setDisplayed("");
    let i = 0;
    const interval = setInterval(() => {
      i++;
      setDisplayed(text.slice(0, i));
      if (i >= text.length) clearInterval(interval);
    }, 20);
    return () => clearInterval(interval);
  }, [text]);
  return <>{displayed}</>;
}

interface ConversationSummary {
  id: string;
  title: string;
}

export function Sidebar() {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [newIds, setNewIds] = useState<Set<string>>(new Set());
  const seenIdsRef = useRef<Set<string> | null>(null);
  const pathname = usePathname();
  const router = useRouter();

  const loadConversations = useCallback(() => {
    apiFetch("/conversations")
      .then((res) => (res.ok ? res.json() : []))
      .then((data: ConversationSummary[]) => {
        if (seenIdsRef.current === null) {
          seenIdsRef.current = new Set(data.map((c) => c.id));
        } else {
          const freshlyNew = data.filter((c) => !seenIdsRef.current!.has(c.id));
          if (freshlyNew.length > 0) {
            setNewIds((prev) => new Set([...prev, ...freshlyNew.map((c) => c.id)]));
            freshlyNew.forEach((c) => seenIdsRef.current!.add(c.id));
          }
        }
        setConversations(data);
      })
      .catch(() => setConversations([]));
  }, []);

  useEffect(() => {
    loadConversations();
  }, [pathname, loadConversations]);

  useEffect(() => {
    window.addEventListener("atlas:conversations-changed", loadConversations);
    return () => window.removeEventListener("atlas:conversations-changed", loadConversations);
  }, [loadConversations]);

  const handleLogout = () => {
    clearToken();
    router.push("/login");
  };

  const navItems = [
    { href: "/dashboard", label: "Home", icon: Home },
    { href: "/dashboard/documents", label: "Documents", icon: FileText },
  ];

  return (
    <aside className="flex h-full w-64 shrink-0 flex-col border-r border-border bg-card p-4">
      <div className="mb-6 flex items-center gap-2">
        <svg viewBox="0 0 24 24" width="22" height="22" fill="none">
          <circle cx="12" cy="12" r="2.2" fill="#3B82F6" />
          <ellipse cx="12" cy="12" rx="9.2" ry="3.4" stroke="#3B82F6" strokeWidth="1.5" />
          <ellipse cx="12" cy="12" rx="9.2" ry="3.4" transform="rotate(60 12 12)" stroke="#3B82F6" strokeWidth="1.5" />
          <ellipse cx="12" cy="12" rx="9.2" ry="3.4" transform="rotate(120 12 12)" stroke="#3B82F6" strokeWidth="1.5" />
        </svg>
        <span className="text-lg font-semibold text-foreground">Atlas AI</span>
      </div>

      <nav className="flex flex-col gap-1">
        {navItems.map((item) => {
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors ${
                active
                  ? "border border-blue-500/30 bg-blue-500/10 text-foreground"
                  : "text-muted-foreground hover:bg-muted"
              }`}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <button
        onClick={() => router.push("/dashboard")}
        className="mt-4 flex items-center justify-center gap-2 rounded-lg border border-border px-3 py-2 text-sm text-foreground hover:bg-muted"
      >
        <Plus className="h-3.5 w-3.5" />
        New chat
      </button>

      <div className="mt-6 flex-1 overflow-y-auto">
        <p className="mb-2 px-3 text-xs text-muted-foreground">Recent</p>
        <div className="flex flex-col gap-1">
          {conversations.map((c) => (
            <Link
              key={c.id}
              href={`/dashboard/chat?conversation=${c.id}`}
              className="flex items-center gap-2 truncate rounded-lg px-3 py-1.5 text-sm text-muted-foreground hover:bg-muted"
            >
              <MessageSquare className="h-3.5 w-3.5 shrink-0 opacity-60" />
              <span className="truncate">
                {newIds.has(c.id) ? <TypewriterText text={c.title} /> : c.title}
              </span>
            </Link>
          ))}
        </div>
      </div>

      <div className="mt-4 rounded-xl border border-blue-500/20 bg-gradient-to-br from-blue-500/15 to-blue-500/5 p-3.5">
        <div className="mb-1.5 flex items-center gap-1.5">
          <Sparkles className="h-3.5 w-3.5 text-blue-400" />
          <span className="text-sm font-medium text-foreground">Atlas AI Pro</span>
        </div>
        <p className="mb-2.5 text-xs leading-relaxed text-muted-foreground">
          Unlock unlimited uploads, longer chats, and advanced features.
        </p>
        <button className="text-xs font-medium text-blue-400 hover:underline">Upgrade now →</button>
      </div>

      <button
        onClick={handleLogout}
        className="mt-3 flex items-center gap-2 rounded-md px-3 py-2 text-sm text-muted-foreground hover:bg-muted"
      >
        <LogOut className="h-3.5 w-3.5" />
        Log out
      </button>

      <ThemeToggle />
    </aside>
  );
}