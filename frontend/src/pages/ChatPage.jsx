import React, { useState, useEffect, useRef } from 'react';
import client from '../api/client';
import { ReasoningBadge } from '../components/ReasoningBadge';
import { FeedbackButtons } from '../components/FeedbackButtons';
import {
  Plus,
  Send,
  MessageSquare,
  Trash2,
  CheckCircle,
  AlertTriangle,
  Bot,
  User,
  Clock,
  Sparkles,
  RefreshCw
} from 'lucide-react';

export const ChatPage = () => {
  const [conversations, setConversations] = useState([]);
  const [activeConvId, setActiveConvId] = useState(null);
  const [activeConv, setActiveConv] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputContent, setInputContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef(null);

  // Fetch conversation list
  const loadConversations = async (selectId = null) => {
    try {
      const res = await client.get('/chat/conversations');
      setConversations(res.data);
      if (selectId) {
        setActiveConvId(selectId);
      } else if (!activeConvId && res.data.length > 0) {
        setActiveConvId(res.data[0].id);
      }
    } catch (err) {
      console.error("Failed to load conversations:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadConversations();
  }, []);

  // Fetch active conversation detail
  useEffect(() => {
    if (!activeConvId) {
      setActiveConv(null);
      setMessages([]);
      return;
    }

    const fetchDetail = async () => {
      try {
        const res = await client.get(`/chat/conversations/${activeConvId}`);
        setActiveConv(res.data);
        setMessages(res.data.messages || []);
      } catch (err) {
        console.error("Failed to fetch conversation details:", err);
      }
    };

    fetchDetail();
  }, [activeConvId]);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, sending]);

  const handleStartNewChat = () => {
    setActiveConvId(null);
    setActiveConv(null);
    setMessages([]);
    setInputContent('');
  };

  const handleDeleteConversation = async (e, convId) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this conversation?")) return;

    try {
      await client.delete(`/chat/conversations/${convId}`);
      if (activeConvId === convId) {
        setActiveConvId(null);
        setActiveConv(null);
        setMessages([]);
      }
      loadConversations();
    } catch (err) {
      console.error("Failed to delete conversation:", err);
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!inputContent.trim() || sending) return;

    const userText = inputContent.trim();
    setInputContent('');
    setSending(true);

    // Optimistic user message preview
    const tempUserMsg = {
      id: Date.now(),
      role: 'user',
      content: userText,
      created_at: new Date().toISOString()
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      const res = await client.post('/chat/message', {
        conversation_id: activeConvId,
        content: userText
      });

      const { conversation_id, bot_message } = res.data;
      
      if (!activeConvId) {
        setActiveConvId(conversation_id);
        await loadConversations(conversation_id);
      } else {
        setMessages((prev) => {
          // Replace temp user message with real response set
          const filtered = prev.filter((m) => m.id !== tempUserMsg.id);
          return [...filtered, res.data.user_message, bot_message];
        });
        // Update status of active conversation
        const detailRes = await client.get(`/chat/conversations/${conversation_id}`);
        setActiveConv(detailRes.data);
      }
    } catch (err) {
      console.error("Failed to send message:", err);
      alert("Failed to send message. Please try again.");
    } finally {
      setSending(false);
    }
  };

  const handleResolve = async () => {
    if (!activeConvId) return;
    try {
      await client.post(`/chat/resolve/${activeConvId}`);
      setActiveConv((prev) => prev ? { ...prev, status: 'resolved' } : null);
      loadConversations(activeConvId);
    } catch (err) {
      console.error("Failed to resolve conversation:", err);
    }
  };

  const getStatusBadge = (statusStr) => {
    switch (statusStr) {
      case 'resolved':
        return (
          <span style={{ fontSize: '0.7rem', padding: '2px 8px', borderRadius: '12px', background: 'rgba(16, 185, 129, 0.15)', color: '#34d399', border: '1px solid rgba(16, 185, 129, 0.3)', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
            <CheckCircle size={10} /> Resolved
          </span>
        );
      case 'escalated':
        return (
          <span style={{ fontSize: '0.7rem', padding: '2px 8px', borderRadius: '12px', background: 'rgba(244, 63, 94, 0.15)', color: '#fb7185', border: '1px solid rgba(244, 63, 94, 0.3)', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
            <AlertTriangle size={10} /> Escalated
          </span>
        );
      default:
        return (
          <span style={{ fontSize: '0.7rem', padding: '2px 8px', borderRadius: '12px', background: 'rgba(99, 102, 241, 0.15)', color: '#818cf8', border: '1px solid rgba(99, 102, 241, 0.3)', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
            <Clock size={10} /> Open
          </span>
        );
    }
  };

  return (
    <div style={{ display: 'flex', height: 'calc(100vh - 61px)', overflow: 'hidden' }}>
      {/* SIDEBAR: Conversation History */}
      <div style={{
        width: '320px',
        background: 'rgba(15, 23, 42, 0.95)',
        borderRight: '1px solid rgba(255, 255, 255, 0.08)',
        display: 'flex',
        flexDirection: 'column',
        shrink: 0
      }}>
        {/* New Chat Button */}
        <div style={{ padding: '16px', borderBottom: '1px solid rgba(255, 255, 255, 0.08)' }}>
          <button
            onClick={handleStartNewChat}
            className="btn-primary"
            style={{ width: '100%', justifyContent: 'center' }}
          >
            <Plus size={18} /> New Conversation
          </button>
        </div>

        {/* Conversation List */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '12px 10px' }}>
          {loading ? (
            <div style={{ padding: '20px', textAlign: 'center', color: '#64748b', fontSize: '0.85rem' }}>
              Loading conversations...
            </div>
          ) : conversations.length === 0 ? (
            <div style={{ padding: '20px', textAlign: 'center', color: '#64748b', fontSize: '0.85rem' }}>
              No past conversations found. Start a new session above!
            </div>
          ) : (
            conversations.map((conv) => {
              const isSelected = conv.id === activeConvId;
              return (
                <div
                  key={conv.id}
                  onClick={() => setActiveConvId(conv.id)}
                  style={{
                    padding: '12px',
                    borderRadius: '8px',
                    marginBottom: '6px',
                    cursor: 'pointer',
                    background: isSelected ? 'rgba(99, 102, 241, 0.15)' : 'rgba(255, 255, 255, 0.02)',
                    border: isSelected ? '1px solid rgba(99, 102, 241, 0.4)' : '1px solid transparent',
                    transition: 'all 0.15s'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                    <span style={{ fontWeight: 600, fontSize: '0.875rem', color: isSelected ? '#ffffff' : '#cbd5e1', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '170px' }}>
                      {conv.title || `Chat #${conv.id}`}
                    </span>
                    <button
                      onClick={(e) => handleDeleteConversation(e, conv.id)}
                      style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', padding: '2px' }}
                      title="Delete chat"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '6px' }}>
                    {getStatusBadge(conv.status)}
                    <span style={{ fontSize: '0.7rem', color: '#64748b' }}>
                      {new Date(conv.updated_at).toLocaleDateString([], { month: 'short', day: 'numeric' })}
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* MAIN THREAD CONTAINER */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', background: 'rgba(9, 13, 22, 0.5)' }}>
        {/* Active Conversation Top Bar */}
        <div style={{
          padding: '14px 24px',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          background: 'rgba(17, 24, 39, 0.6)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <div>
            <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <MessageSquare size={18} color="#6366f1" />
              {activeConv ? activeConv.title : 'New Support Chat Session'}
            </h3>
            {activeConv && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
                {getStatusBadge(activeConv.status)}
                <span style={{ fontSize: '0.75rem', color: '#64748b' }}>ID: #{activeConv.id}</span>
              </div>
            )}
          </div>

          {activeConv && activeConv.status !== 'resolved' && (
            <button
              onClick={handleResolve}
              className="btn-secondary"
              style={{ fontSize: '0.8rem', borderColor: 'rgba(16, 185, 129, 0.3)', color: '#34d399' }}
            >
              <CheckCircle size={15} /> Mark Resolved
            </button>
          )}
        </div>

        {/* MESSAGES THREAD AREA */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '24px' }}>
          {messages.length === 0 ? (
            <div style={{
              height: '100%',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              textAlign: 'center',
              color: '#64748b'
            }}>
              <div style={{
                width: '64px',
                height: '64px',
                borderRadius: '20px',
                background: 'rgba(99, 102, 241, 0.1)',
                border: '1px solid rgba(99, 102, 241, 0.25)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: '16px'
              }}>
                <Sparkles size={32} color="#818cf8" />
              </div>
              <h3 style={{ color: '#f1f5f9', fontWeight: 700, marginBottom: '6px' }}>Autonomous Support Copilot Ready</h3>
              <p style={{ maxWidth: '420px', fontSize: '0.875rem' }}>
                Ask a question regarding product features, billing, account management, or technical troubleshooting.
              </p>
            </div>
          ) : (
            messages.map((msg) => {
              const isUser = msg.role === 'user';
              return (
                <div
                  key={msg.id}
                  className="animate-fade-in"
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: isUser ? 'flex-end' : 'flex-start',
                    marginBottom: '20px'
                  }}
                >
                  <div style={{
                    maxWidth: '80%',
                    display: 'flex',
                    flexDirection: isUser ? 'row-reverse' : 'row',
                    gap: '12px',
                    alignItems: 'flex-start'
                  }}>
                    {/* Avatar Icon */}
                    <div style={{
                      width: '32px',
                      height: '32px',
                      borderRadius: '50%',
                      background: isUser ? 'linear-gradient(135deg, #6366f1, #4f46e5)' : 'linear-gradient(135deg, #06b6d4, #0891b2)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      shrink: 0,
                      boxShadow: '0 2px 8px rgba(0,0,0,0.3)'
                    }}>
                      {isUser ? <User size={16} color="#fff" /> : <Bot size={16} color="#fff" />}
                    </div>

                    {/* Bubble Content */}
                    <div style={{ width: '100%' }}>
                      <div style={{
                        background: isUser ? 'rgba(99, 102, 241, 0.2)' : 'rgba(30, 41, 59, 0.8)',
                        border: isUser ? '1px solid rgba(99, 102, 241, 0.4)' : '1px solid rgba(255, 255, 255, 0.08)',
                        borderRadius: isUser ? '14px 14px 2px 14px' : '14px 14px 14px 2px',
                        padding: '12px 16px',
                        color: '#f8fafc',
                        fontSize: '0.925rem',
                        lineHeight: 1.5,
                        whiteSpace: 'pre-wrap',
                        boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
                      }}>
                        {msg.content}
                      </div>

                      {/* Signature Reasoning Widget (Only for Assistant messages) */}
                      {!isUser && (
                        <>
                          <ReasoningBadge message={msg} />
                          <FeedbackButtons messageId={msg.id} initialFeedback={msg.feedback} />
                        </>
                      )}
                    </div>
                  </div>
                </div>
              );
            })
          )}

          {sending && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#818cf8', fontSize: '0.85rem', marginTop: '12px' }}>
              <RefreshCw size={16} className="animate-spin" style={{ animation: 'spin 1s linear infinite' }} />
              <span>Autonomous Copilot evaluating intent & knowledge base...</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* INPUT FORM AREA */}
        <div style={{
          padding: '16px 24px',
          background: 'rgba(17, 24, 39, 0.8)',
          borderTop: '1px solid rgba(255, 255, 255, 0.08)'
        }}>
          <form onSubmit={handleSendMessage} style={{ display: 'flex', gap: '12px' }}>
            <input
              type="text"
              className="glass-input"
              style={{ flex: 1, padding: '14px 18px', fontSize: '0.925rem' }}
              placeholder="Type your question or support issue..."
              value={inputContent}
              onChange={(e) => setInputContent(e.target.value)}
              disabled={sending}
            />
            <button
              type="submit"
              disabled={sending || !inputContent.trim()}
              className="btn-primary"
              style={{ padding: '0 24px' }}
            >
              <Send size={18} /> Send
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};
