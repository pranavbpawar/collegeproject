import React, { useState, useEffect, useCallback, useRef } from "react";
import { useEmployeeAuth } from "../../hooks/useEmployeeAuth";
import EmployeeLayout from "./EmployeeLayout";
import "./EmployeePortal.css";

function formatTime(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
}

export default function EmployeeChat() {
  const { employee, isLoading: authLoading, logout, authFetch } = useEmployeeAuth();
  const [conversations, setConversations] = useState([]);
  const [activeConv,    setActiveConv]    = useState(null);
  const [messages,      setMessages]      = useState([]);
  const [text,          setText]          = useState("");
  const [loading,       setLoading]       = useState(true);
  const [sending,       setSending]       = useState(false);
  const [error,         setError]         = useState(null);
  const [uploading,     setUploading]     = useState(false);
  const fileRef = useRef();
  const bottomRef = useRef();

  useEffect(() => {
    if (!authLoading && !employee) window.location.href = "/employee";
  }, [authLoading, employee]);

  // Load conversations
  useEffect(() => {
    if (!employee) return;
    authFetch("/api/v1/chat/conversations")
      .then(setConversations)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [employee, authFetch]);

  // Load messages for active conversation
  const loadMessages = useCallback(async (convId) => {
    try {
      const msgs = await authFetch(`/api/v1/chat/${convId}/messages?limit=50`);
      setMessages(msgs);
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
    } catch (e) {
      setError(e.message);
    }
  }, [authFetch]);

  const selectConv = (conv) => {
    setActiveConv(conv);
    loadMessages(conv.id);
  };

  // Poll messages every 10s when conversation is open
  useEffect(() => {
    if (!activeConv) return;
    const id = setInterval(() => loadMessages(activeConv.id), 10_000);
    return () => clearInterval(id);
  }, [activeConv, loadMessages]);

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!text.trim() || !activeConv || sending) return;
    setSending(true);
    try {
      await authFetch(`/api/v1/chat/${activeConv.id}/messages`, {
        method: "POST",
        body: JSON.stringify({ content: text.trim() }),
      });
      setText("");
      await loadMessages(activeConv.id);
    } catch (err) {
      setError(err.message);
    } finally {
      setSending(false);
    }
  };

  const uploadFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file || !activeConv) return;
    setUploading(true);
    try {
      const form = new FormData();
      form.append("conversation_id", activeConv.id);
      form.append("file", file);
      const token = localStorage.getItem("employee_token");
      const res = await fetch(`${import.meta.env.VITE_BACKEND_URL || ""}/api/v1/chat/upload`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      });
      if (!res.ok) throw new Error("Upload failed");
      await loadMessages(activeConv.id);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  if (authLoading || loading) return (
    <div style={{ minHeight: "100vh", background: "var(--ep-bg)", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div className="ep-spinner" />
    </div>
  );
  if (!employee) return null;

  return (
    <EmployeeLayout employee={employee} logout={logout}>
      <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 20 }}>Chat</h1>
      {error && <div className="ep-error-msg" style={{ marginBottom: 12 }}>⚠ {error}</div>}

      <div style={{ display: "flex", gap: 16, height: "calc(100vh - 180px)", minHeight: 400 }}>
        {/* Conversation list */}
        <div className="ep-card" style={{ width: 240, flexShrink: 0, padding: 0, overflow: "hidden", display: "flex", flexDirection: "column" }}>
          <div style={{ padding: "14px 16px", borderBottom: "1px solid var(--ep-border)", fontWeight: 600, fontSize: 13 }}>
            Conversations
          </div>
          <div style={{ flex: 1, overflowY: "auto" }}>
            {conversations.length === 0 ? (
              <p style={{ padding: 16, color: "var(--ep-muted)", fontSize: 12 }}>
                No conversations yet. Your manager or HR will initiate contact.
              </p>
            ) : (
              conversations.map((conv) => (
                <button
                  key={conv.id}
                  onClick={() => selectConv(conv)}
                  style={{
                    width: "100%", textAlign: "left", padding: "12px 16px", border: "none",
                    background: activeConv?.id === conv.id ? "rgba(88,166,255,0.1)" : "transparent",
                    borderLeft: activeConv?.id === conv.id ? "2px solid var(--ep-accent)" : "2px solid transparent",
                    cursor: "pointer", color: "var(--ep-text)",
                    borderBottom: "1px solid var(--ep-border)",
                  }}
                >
                  <div style={{ fontWeight: 600, fontSize: 13 }}>{conv.staff_name || "Manager"}</div>
                  <div style={{ color: "var(--ep-muted)", fontSize: 11, textTransform: "capitalize" }}>{conv.staff_role}</div>
                  {conv.last_message_at && (
                    <div style={{ color: "var(--ep-muted)", fontSize: 11, marginTop: 2 }}>
                      {formatTime(conv.last_message_at)}
                    </div>
                  )}
                </button>
              ))
            )}
          </div>
        </div>

        {/* Message thread */}
        <div className="ep-card" style={{ flex: 1, padding: 0, display: "flex", flexDirection: "column", overflow: "hidden" }}>
          {!activeConv ? (
            <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--ep-muted)" }}>
              Select a conversation to start messaging
            </div>
          ) : (
            <>
              {/* Thread header */}
              <div style={{ padding: "14px 16px", borderBottom: "1px solid var(--ep-border)", display: "flex", alignItems: "center", gap: 10 }}>
                <div className="ep-avatar" style={{ width: 28, height: 28, fontSize: 11 }}>
                  {(activeConv.staff_name || "M")[0].toUpperCase()}
                </div>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 13 }}>{activeConv.staff_name || "Manager"}</div>
                  <div style={{ color: "var(--ep-muted)", fontSize: 11, textTransform: "capitalize" }}>{activeConv.staff_role}</div>
                </div>
              </div>

              {/* Messages */}
              <div style={{ flex: 1, overflowY: "auto", padding: 16, display: "flex", flexDirection: "column", gap: 8 }}>
                {messages.map((msg) => {
                  const isMine = msg.sender_id === employee.id;
                  return (
                    <div key={msg.id} style={{ display: "flex", justifyContent: isMine ? "flex-end" : "flex-start" }}>
                      <div style={{
                        maxWidth: "70%", padding: "8px 12px", borderRadius: isMine ? "12px 12px 2px 12px" : "12px 12px 12px 2px",
                        background: isMine ? "var(--ep-accent)" : "var(--ep-border)",
                        color: isMine ? "#0d1117" : "var(--ep-text)",
                        fontSize: 13,
                      }}>
                        {msg.message_type === "file" ? (
                          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                            <span>📎</span>
                            <span>{msg.file_name || "Attachment"}</span>
                            {msg.file_size_human && <span style={{ opacity: 0.7, fontSize: 11 }}>({msg.file_size_human})</span>}
                          </div>
                        ) : (
                          msg.content
                        )}
                        <div style={{ fontSize: 10, opacity: 0.6, marginTop: 3, textAlign: isMine ? "right" : "left" }}>
                          {formatTime(msg.created_at)}
                        </div>
                      </div>
                    </div>
                  );
                })}
                <div ref={bottomRef} />
              </div>

              {/* Input */}
              <form onSubmit={sendMessage} style={{ padding: 12, borderTop: "1px solid var(--ep-border)", display: "flex", gap: 8 }}>
                <input
                  type="file"
                  ref={fileRef}
                  onChange={uploadFile}
                  style={{ display: "none" }}
                />
                <button
                  type="button"
                  className="ep-btn ep-btn--ghost"
                  style={{ padding: "8px 12px", flexShrink: 0 }}
                  onClick={() => fileRef.current?.click()}
                  disabled={uploading}
                  title="Attach file"
                >
                  {uploading ? "⏳" : "📎"}
                </button>
                <input
                  className="ep-input"
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  placeholder="Type a message…"
                  disabled={sending}
                />
                <button
                  type="submit"
                  className="ep-btn ep-btn--primary"
                  disabled={sending || !text.trim()}
                  style={{ flexShrink: 0 }}
                >
                  {sending ? "…" : "Send"}
                </button>
              </form>
            </>
          )}
        </div>
      </div>
    </EmployeeLayout>
  );
}
