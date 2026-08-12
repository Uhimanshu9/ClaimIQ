import React, { useEffect, useRef, useState } from "react";
import MessageBubble from "./MessageBubble";
import Loader from "./Loader";
import { cancelFileProcessing, getFileStatus, queryPDF } from "../utils/api";
import "../styles/chat.css";

const ChatBox = ({ file, initialMessages = [], initialProvider = "gemini", onConversationChange }) => {
  const [messages, setMessages] = useState(initialMessages);
  const [provider, setProvider] = useState(initialProvider);
  const [question, setQuestion] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isCancelling, setIsCancelling] = useState(false);
  const [indexing, setIndexing] = useState(file.fileId ? { status: "queued", progress: 5, stage: "queued" } : { status: "ready", progress: 100, stage: "indexed" });
  const endOfMessagesRef = useRef(null);

  useEffect(() => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  useEffect(() => {
    if (!file.fileId || indexing.status === "ready" || indexing.status === "error") return undefined;
    let cancelled = false;
    const checkStatus = async () => {
      try {
        const status = await getFileStatus(file.fileId);
        if (!cancelled) setIndexing(status);
      } catch (error) {
        if (!cancelled) setIndexing({ status: "error", error: error.message, stage: "status check failed" });
      }
    };
    checkStatus();
    const timer = window.setInterval(checkStatus, 2500);
    return () => { cancelled = true; window.clearInterval(timer); };
  }, [file.fileId, indexing.status]);

  const updateConversation = (nextMessages, nextProvider = provider) => {
    setMessages(nextMessages);
    onConversationChange?.(nextMessages, nextProvider);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion || isLoading || indexing.status !== "ready") return;

    const nextMessages = [...messages, { id: crypto.randomUUID(), role: "user", content: trimmedQuestion }];
    setQuestion("");
    updateConversation(nextMessages);
    setIsLoading(true);

    try {
      const result = await queryPDF(trimmedQuestion, provider);
      updateConversation([
        ...nextMessages,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: result.response,
          thinking: result.thinking,
        },
      ]);
    } catch (error) {
      updateConversation([
        ...nextMessages,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: "I couldn't complete that request.",
          thinking: error.message,
          isError: true,
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleProviderChange = (event) => {
    const nextProvider = event.target.value;
    setProvider(nextProvider);
    onConversationChange?.(messages, nextProvider);
  };

  const handleCancelIndexing = async () => {
    if (!file.fileId || isCancelling) return;
    setIsCancelling(true);
    try {
      const result = await cancelFileProcessing(file.fileId);
      setIndexing({ status: result.status, stage: "cancelled", progress: 0 });
    } catch (error) {
      setIndexing((current) => ({ ...current, cancelError: error.message }));
    } finally {
      setIsCancelling(false);
    }
  };

  const composer = (
    <form className="chat-input-container" onSubmit={handleSubmit}>
      <div className="chat-input">
        <textarea
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              handleSubmit(event);
            }
          }}
          placeholder="Ask anything about your knowledge base"
          rows="1"
          disabled={isLoading || indexing.status !== "ready"}
        />
        <div className="composer-actions">
          <label className="composer-provider">
            <select value={provider} onChange={handleProviderChange} disabled={isLoading || indexing.status !== "ready"}>
              <option value="gemini">Gemini via LiteLLM</option>
              <option value="openai">OpenAI via LiteLLM</option>
            </select>
          </label>
          <button className="send-button" type="submit" disabled={!question.trim() || isLoading || indexing.status !== "ready"} aria-label="Send message">↑</button>
        </div>
      </div>
      <p className="chat-disclaimer">{indexing.status === "ready" ? "Responses are based on the shared knowledge base. Verify important decisions against the source." : "To prevent incomplete or partial-document answers, querying unlocks only after indexing is complete."}</p>
    </form>
  );

  return (
    <section className={`chat-container ${messages.length === 0 ? "empty-chat" : ""}`}>
      <header className="chat-header">
        <div className="file-info">
          <span className="file-icon">📄</span>
          <div className="file-details-header">
            <strong>{file.name}</strong>
            <span className="file-status">{indexing.status === "ready" ? "Shared application knowledge base" : "Document is still indexing"}</span>
          </div>
        </div>
      </header>

      <div className="chat-messages">
        {indexing.status !== "ready" && (
          <div className={`indexing-banner ${indexing.status === "error" ? "error" : ""}`}>
            {indexing.status === "error" || indexing.status === "cancelled" ? (
              <><strong>{indexing.status === "cancelled" ? "Indexing cancelled." : "Indexing failed."}</strong><span>{indexing.error || "This document was not added to the knowledge base. Upload it again when you are ready."}</span></>
            ) : (
              <>
                <div className="indexing-banner-copy"><strong>Preparing your document</strong><span>{indexing.stage || "indexing"} — questions are disabled until this is complete.</span>{indexing.cancelError && <span className="cancel-error">{indexing.cancelError}</span>}</div>
                <div className="indexing-progress" role="progressbar" aria-label="Document indexing in progress"><span /></div>
                <button className="cancel-indexing-button" type="button" onClick={handleCancelIndexing} disabled={isCancelling}>{isCancelling ? "Cancelling…" : "Cancel upload"}</button>
              </>
            )}
          </div>
        )}
        {messages.length === 0 ? (
          <div className="chat-empty-state">
            <div className="chat-empty-icon">✦</div>
            <h2>What would you like to understand?</h2>
            <p>Ask a question across your uploaded knowledge base.</p>
            {composer}
          </div>
        ) : messages.map((message) => <MessageBubble key={message.id} msg={message} />)}
        {isLoading && (
          <div className="message-wrapper assistant">
            <div className="assistant-avatar">✦</div>
            <div className="message loading-message"><Loader /></div>
          </div>
        )}
        <div ref={endOfMessagesRef} />
      </div>

      {messages.length > 0 && composer}
    </section>
  );
};

export default ChatBox;
