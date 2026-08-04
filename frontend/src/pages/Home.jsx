import React, { useEffect, useMemo, useState } from "react";
import ChatBox from "../components/ChatBox";
import { getChatHistory, getDocuments, saveChatHistory, uploadFile } from "../utils/api";
import "../styles/globals.css";

const BG_VIDEO = "https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260511_230229_7c9bc431-46cf-489a-948d-e8144d8eb5d4.mp4";

const Home = () => {
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [isSidebarUploading, setIsSidebarUploading] = useState(false);
  const [sidebarError, setSidebarError] = useState("");

  useEffect(() => {
    let mounted = true;
    getChatHistory()
      .then(({ conversations: savedConversations }) => {
        if (mounted) setConversations(savedConversations);
      })
      .catch(() => {
        // The chat screen remains usable if the backend is temporarily unavailable.
      });
    return () => { mounted = false; };
  }, []);

  useEffect(() => {
    let mounted = true;
    const refreshDocuments = async () => {
      try {
        const response = await getDocuments();
        if (mounted) setDocuments(response.documents);
      } catch {
        // The upload and chat flow will show a direct error when the API is unavailable.
      }
    };
    refreshDocuments();
    const timer = window.setInterval(refreshDocuments, 3000);
    return () => { mounted = false; window.clearInterval(timer); };
  }, []);

  const activeConversation = useMemo(
    () => conversations.find((conversation) => conversation.id === activeConversationId),
    [activeConversationId, conversations],
  );
  const visibleConversations = conversations.filter((conversation) => conversation.messages.length > 0);

  const readyDocuments = documents.filter((document) => document.status === "ready");

  const createKnowledgeBaseChat = () => {
    const conversation = {
      id: crypto.randomUUID(),
      title: "New knowledge-base chat",
      documentName: `${readyDocuments.length} knowledge-base document${readyDocuments.length === 1 ? "" : "s"}`,
      provider: "gemini",
      messages: [],
      updatedAt: new Date().toISOString(),
    };
    setConversations((current) => [conversation, ...current]);
    setActiveConversationId(conversation.id);
  };

  const startNewChat = () => {
    if (readyDocuments.length === 0) {
      setActiveConversationId(null);
      return;
    }
    createKnowledgeBaseChat();
  };

  useEffect(() => {
    if (activeConversationId || readyDocuments.length === 0) return;
    const conversation = {
      id: crypto.randomUUID(),
      title: "New knowledge-base chat",
      documentName: `${readyDocuments.length} knowledge-base document${readyDocuments.length === 1 ? "" : "s"}`,
      provider: "gemini",
      messages: [],
      updatedAt: new Date().toISOString(),
    };
    setConversations((current) => [conversation, ...current]);
    setActiveConversationId(conversation.id);
  }, [activeConversationId, readyDocuments.length]); // Open the shared knowledge-base chat when documents become ready.

  const handleFileSelect = (file) => {
    if (!file) return;
    const conversation = {
      id: crypto.randomUUID(),
      title: file.name,
      documentName: file.name,
      fileId: file.fileId,
      provider: "gemini",
      messages: [],
      updatedAt: new Date().toISOString(),
    };
    setConversations((current) => [conversation, ...current]);
    setActiveConversationId(conversation.id);
  };

  const handleSidebarUpload = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    if (file.type !== "application/pdf") {
      setSidebarError("Please choose a PDF file.");
      return;
    }
    setSidebarError("");
    setIsSidebarUploading(true);
    try {
      const result = await uploadFile(file);
      handleFileSelect({ name: file.name, size: file.size, type: file.type, fileId: result.fileId });
    } catch (error) {
      setSidebarError(error.message);
    } finally {
      setIsSidebarUploading(false);
    }
  };

  const updateConversation = (messages, provider) => {
    const currentConversation = conversations.find((conversation) => conversation.id === activeConversationId);
    if (!currentConversation) return;
    const firstQuestion = messages.find((message) => message.role === "user")?.content;
    const changedConversation = {
      ...currentConversation,
      messages,
      provider,
      title: firstQuestion ? firstQuestion.slice(0, 38) : currentConversation.documentName,
      updatedAt: new Date().toISOString(),
    };
    setConversations((current) => current.map((conversation) => {
      if (conversation.id !== activeConversationId) return conversation;
      return changedConversation;
    }));
    if (changedConversation.messages.length > 0) {
      saveChatHistory(changedConversation).catch((error) => {
        console.error("Couldn't save chat history:", error);
      });
    }
  };

  return (
    <div className="workspace">
      <video className="workspace-video" autoPlay muted loop playsInline src={BG_VIDEO} />
      <div className="workspace-backdrop" />
      <aside className="sidebar">
        <a className="brand" href="/" aria-label="Equilibrium home"><span>∞</span> Equilibrium</a>
        <p className="brand-subtitle">Knowledge companion</p>
        <button className="new-chat-button" onClick={startNewChat}>＋ <span>New chat</span></button>

        <label className={`sidebar-upload ${isSidebarUploading ? "uploading" : ""}`}>
          <span>⇧</span> <span>{isSidebarUploading ? "Uploading…" : "Upload document"}</span>
          <input id="sidebar-upload-input" type="file" accept="application/pdf" onChange={handleSidebarUpload} disabled={isSidebarUploading} />
        </label>
        {sidebarError && <p className="sidebar-error">{sidebarError}</p>}

        <div className="sidebar-label">Knowledge base</div>
        <div className="document-list">
          {documents.length === 0 && <p className="no-conversations">Upload a document to start asking questions.</p>}
          {documents.slice(0, 6).map((document) => (
            <div className="document-item" key={document.file_id} title={document.name}>
              <span>📄</span><span>{document.name}</span><em className={document.status}>{document.status}</em>
            </div>
          ))}
        </div>

        <div className="sidebar-label">Recent chats</div>
        <nav className="conversation-list" aria-label="Conversation history">
          {visibleConversations.length === 0 && <p className="no-conversations">Completed conversations will appear here.</p>}
          {visibleConversations.map((conversation) => (
            <button
              className={`conversation-item ${conversation.id === activeConversationId ? "active" : ""}`}
              key={conversation.id}
              onClick={() => setActiveConversationId(conversation.id)}
              title={conversation.title}
            >
              <span>◻</span><span>{conversation.title}</span>
            </button>
          ))}
        </nav>
        <div className="sidebar-footer">ClaimIQ · Document intelligence</div>
      </aside>

      <main className="workspace-main">
        {activeConversation ? (
          <ChatBox
            key={activeConversation.id}
            file={{ name: activeConversation.documentName, fileId: activeConversation.fileId }}
            initialMessages={activeConversation.messages}
            initialProvider={activeConversation.provider}
            onConversationChange={updateConversation}
          />
        ) : (
          <section className="welcome-screen">
            <div className="welcome-copy">
              <div className="welcome-mark">✦</div>
              <h1>Your knowledge base is empty</h1>
              <p>Click <strong>Upload document</strong> in the left sidebar to add a PDF before starting a chat.</p>
            </div>
            <p className="welcome-note">Questions unlock only after at least one document has finished indexing.</p>
          </section>
        )}
      </main>
    </div>
  );
};

export default Home;
