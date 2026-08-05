"use client";

import { useState, useEffect, useRef } from "react";
import { useSearchParams } from "next/navigation";
import { ChatMessages } from "@/components/chat/chat-messages";
import { ChatInput } from "@/components/chat/chat-input";
import { DocumentPickerModal } from "@/components/chat/document-picker-modal";
import type { Message, Source } from "@/components/chat/chat-message-bubble";
import { apiFetch, notifyConversationsChanged } from "@/lib/api";

function ChatPageInner({ urlConversationId }: { urlConversationId: string | null }) {
  const searchParams = useSearchParams();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isThinking, setIsThinking] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(urlConversationId);
  const [showDocPicker, setShowDocPicker] = useState(false);
  const [pendingMode, setPendingMode] = useState<string | null>(null);

  const MODE_LABELS: Record<string, string> = {
    summarize: "Summarize",
    key_points: "Key points for",
    questions: "Questions answered by",
    simplify: "Simple explanation of",
  };

  const handleAnalyze = async (doc: { id: string; filename: string }, modeOverride?: string) => {
    const mode = modeOverride ?? pendingMode ?? "summarize";
    setShowDocPicker(false);
    setPendingMode(null);

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: `${MODE_LABELS[mode]} ${doc.filename}`,
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsThinking(true);

    try {
      const params = new URLSearchParams();
      if (conversationId) params.set("conversation_id", conversationId);
      if (mode !== "summarize") params.set("mode", mode);

      const endpoint =
        mode === "summarize"
          ? `/documents/${doc.id}/summarize?${params.toString()}`
          : `/documents/${doc.id}/analyze?${params.toString()}`;

      const response = await apiFetch(endpoint, { method: "POST" });
      const data = await response.json();
      const content = mode === "summarize" ? data.summary : data.result;

      if (data.conversation_id && !conversationId) {
        setConversationId(data.conversation_id);
        notifyConversationsChanged();
      }

      setIsThinking(false);
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: "assistant", content },
      ]);
    } catch {
      setIsThinking(false);
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: "Something went wrong reaching the server. Check that the backend is running.",
        },
      ]);
    }
  };

  useEffect(() => {
    if (!urlConversationId) return;
    apiFetch(`/conversations/${urlConversationId}/messages`)
      .then((res) => (res.ok ? res.json() : []))
      .then((data) => setMessages(data))
      .catch(() => setMessages([]));
  }, [urlConversationId]);

  const hasAutoTriggeredRef = useRef(false);

  const fetchDocsWithRetry = async (attempts = 4, delayMs = 3000): Promise<any[]> => {
    for (let i = 0; i < attempts; i++) {
      try {
        const res = await apiFetch("/documents");
        if (res.ok) return await res.json();
      } catch {
        // fall through to retry
      }
      if (i < attempts - 1) await new Promise((r) => setTimeout(r, delayMs));
    }
    return [];
  };

  useEffect(() => {
    if (hasAutoTriggeredRef.current) return;
    hasAutoTriggeredRef.current = true;

    const prefill = searchParams.get("prefill");
    const analyze = searchParams.get("analyze");
    const docId = searchParams.get("doc");

    if (prefill) {
      handleSend(decodeURIComponent(prefill));
    } else if (analyze && docId) {
      fetchDocsWithRetry().then((docs) => {
        const doc = docs.find((d: { id: string }) => d.id === docId);
        if (doc) {
          handleAnalyze(doc, analyze);
        } else {
          setMessages((prev) => [
            ...prev,
            {
              id: crypto.randomUUID(),
              role: "assistant",
              content: "The server took too long to respond (it may have been waking up). Please try again.",
            },
          ]);
        }
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSend = async (text?: string) => {
    const question = text ?? input;
    if (!question.trim()) return;

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: question,
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsThinking(true);

    const assistantId = crypto.randomUUID();
    let assistantContent = "";
    let assistantSources: Source[] = [];

    try {
      const response = await apiFetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question,
          top_k: 5,
          conversation_id: conversationId,
        }),
      });

      const returnedConversationId = response.headers.get("X-Conversation-Id");
      const isNewConversation = returnedConversationId && !conversationId;
      if (isNewConversation) {
        setConversationId(returnedConversationId);
      }

      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let firstTokenReceived = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const event = JSON.parse(line.slice(6));

          if (event.type === "token") {
            if (!firstTokenReceived) {
              firstTokenReceived = true;
              setIsThinking(false);
              setMessages((prev) => [
                ...prev,
                { id: assistantId, role: "assistant", content: "" },
              ]);
            }
            assistantContent += event.content;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId ? { ...m, content: assistantContent } : m
              )
            );
          } else if (event.type === "sources") {
            assistantSources = event.sources;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId ? { ...m, sources: assistantSources } : m
              )
            );
          }
        }
      }

      if (isNewConversation) {
        notifyConversationsChanged();
      }
      } catch (err) {
      setIsThinking(false);
      setMessages((prev) => [
        ...prev,
        {
          id: assistantId,
          role: "assistant",
          content: "Something went wrong reaching the server. Check that the backend is running.",
        },
      ]);
    }
  };

  return (
    <div className="flex h-full flex-col">
      <ChatMessages
        messages={messages}
        isThinking={isThinking}
        onExampleClick={(text) => handleSend(text)}
        onAnalyzeClick={async (mode) => {
          try {
            const res = await apiFetch("/documents");
            const docs = await res.json();
            const ready = docs.filter((d: { status: string }) => d.status === "ready");

            if (ready.length === 1) {
              handleAnalyze(ready[0], mode);
            } else {
              setPendingMode(mode);
              setShowDocPicker(true);
            }
          } catch {
            setPendingMode(mode);
            setShowDocPicker(true);
          }
        }}
      />
      <ChatInput value={input} onChange={setInput} onSend={() => handleSend()} disabled={isThinking} />
      {showDocPicker && (
        <DocumentPickerModal onSelect={(doc) => handleAnalyze(doc)} onClose={() => setShowDocPicker(false)} />
      )}
    </div>
  );
}

export default function ChatPage() {
  const searchParams = useSearchParams();
  const urlConversationId = searchParams.get("conversation");
  const key = searchParams.toString();

  return <ChatPageInner key={key} urlConversationId={urlConversationId} />;
}