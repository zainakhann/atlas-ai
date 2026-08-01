"use client";

import { useEffect, useRef } from "react";
import { ChatEmptyState } from "@/components/chat/chat-empty-state";
import { ChatMessageBubble, ThinkingIndicator, type Message } from "@/components/chat/chat-message-bubble";

export function ChatMessages({
  messages,
  isThinking,
  onExampleClick,
  onAnalyzeClick,
}: {
  messages: Message[];
  isThinking: boolean;
  onExampleClick: (text: string) => void;
  onAnalyzeClick: (mode: string) => void;
}) {
  const hasMessages = messages.length > 0;
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isThinking]);

  return (
    <div className="flex-1 overflow-y-auto bg-background">
      {!hasMessages && !isThinking ? (
        <ChatEmptyState documentCount={4} onExampleClick={onExampleClick} onAnalyzeClick={onAnalyzeClick} />
      ) : (
        <div className="mx-auto flex max-w-2xl flex-col gap-5 px-5 py-6">
          {messages.map((m) => (
            <ChatMessageBubble key={m.id} message={m} onFollowUpClick={onExampleClick} />
          ))}
          {isThinking && <ThinkingIndicator />}
          <div ref={bottomRef} />
        </div>
      )}
    </div>
  );
}