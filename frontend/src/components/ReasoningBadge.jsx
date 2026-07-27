import React from 'react';
import { Cpu, Zap, Database, AlertTriangle, CheckCircle2, ShieldAlert } from 'lucide-react';

export const ReasoningBadge = ({ message }) => {
  if (!message || message.role !== 'assistant') return null;

  const {
    intent = 'general',
    intent_confidence = 0,
    rag_grounded = false,
    retrieval_score = null,
    escalated = false,
    escalation_reason = null,
    response_time_ms = 0
  } = message;

  // Format intent colors
  const getIntentBadgeStyle = (intentName) => {
    switch (intentName?.toLowerCase()) {
      case 'billing':
        return { bg: 'rgba(6, 182, 212, 0.15)', color: '#38bdf8', border: 'rgba(6, 182, 212, 0.3)' };
      case 'technical':
        return { bg: 'rgba(99, 102, 241, 0.15)', color: '#818cf8', border: 'rgba(99, 102, 241, 0.3)' };
      case 'account':
        return { bg: 'rgba(16, 185, 129, 0.15)', color: '#34d399', border: 'rgba(16, 185, 129, 0.3)' };
      case 'complaint':
        return { bg: 'rgba(244, 63, 94, 0.15)', color: '#fb7185', border: 'rgba(244, 63, 94, 0.3)' };
      case 'urgent':
        return { bg: 'rgba(245, 158, 11, 0.15)', color: '#fbbf24', border: 'rgba(245, 158, 11, 0.3)' };
      default:
        return { bg: 'rgba(148, 163, 184, 0.15)', color: '#cbd5e1', border: 'rgba(148, 163, 184, 0.3)' };
    }
  };

  const intentStyle = getIntentBadgeStyle(intent);
  const confPct = Math.round((intent_confidence || 0) * 100);

  return (
    <div style={{
      marginTop: '10px',
      marginBottom: '6px',
      padding: '10px 14px',
      background: 'rgba(15, 23, 42, 0.7)',
      borderRadius: '8px',
      border: '1px solid rgba(255, 255, 255, 0.06)',
      fontSize: '0.75rem'
    }}>
      {/* Header bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
        <span style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          fontWeight: 700,
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
          color: '#94a3b8',
          fontSize: '0.7rem'
        }}>
          <Cpu size={14} color="#6366f1" /> Autonomous Routing Reasoning
        </span>
        <span style={{
          display: 'flex',
          alignItems: 'center',
          gap: '4px',
          color: '#64748b',
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: '0.7rem'
        }}>
          <Zap size={12} color="#f59e0b" /> {response_time_ms}ms
        </span>
      </div>

      {/* Reasoning Chips Grid */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', alignItems: 'center' }}>
        {/* Intent Chip */}
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '6px',
          padding: '3px 8px',
          borderRadius: '6px',
          background: intentStyle.bg,
          color: intentStyle.color,
          border: `1px solid ${intentStyle.border}`,
          fontWeight: 600
        }}>
          <span>Intent: <strong>{intent}</strong></span>
          <span style={{
            fontSize: '0.65rem',
            opacity: 0.85,
            paddingLeft: '4px',
            borderLeft: '1px solid rgba(255,255,255,0.2)'
          }}>
            {confPct}% conf
          </span>
        </div>

        {/* RAG Grounding Chip */}
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '6px',
          padding: '3px 8px',
          borderRadius: '6px',
          background: rag_grounded ? 'rgba(16, 185, 129, 0.12)' : 'rgba(255, 255, 255, 0.05)',
          color: rag_grounded ? '#34d399' : '#94a3b8',
          border: rag_grounded ? '1px solid rgba(16, 185, 129, 0.25)' : '1px solid rgba(255, 255, 255, 0.08)',
          fontWeight: 600
        }}>
          <Database size={12} />
          <span>{rag_grounded ? 'RAG Grounded' : 'General LLM'}</span>
          {retrieval_score !== null && (
            <span style={{ fontSize: '0.65rem', opacity: 0.85, paddingLeft: '4px', borderLeft: '1px solid rgba(255,255,255,0.2)' }}>
              score: {retrieval_score}
            </span>
          )}
        </div>

        {/* Escalation Chip */}
        {escalated && (
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            padding: '3px 8px',
            borderRadius: '6px',
            background: 'rgba(244, 63, 94, 0.18)',
            color: '#fda4af',
            border: '1px solid rgba(244, 63, 94, 0.4)',
            fontWeight: 700
          }}>
            <ShieldAlert size={13} color="#f43f5e" />
            <span>Escalated to Human Agent</span>
          </div>
        )}
      </div>

      {/* Escalation Details Alert Box */}
      {escalated && escalation_reason && (
        <div style={{
          marginTop: '8px',
          padding: '6px 10px',
          background: 'rgba(244, 63, 94, 0.08)',
          borderLeft: '3px solid #f43f5e',
          borderRadius: '0 6px 6px 0',
          color: '#fecdd3',
          fontSize: '0.72rem',
          display: 'flex',
          alignItems: 'center',
          gap: '6px'
        }}>
          <AlertTriangle size={13} style={{ shrink: 0, color: '#fb7185' }} />
          <span><strong>Escalation Trigger:</strong> {escalation_reason}</span>
        </div>
      )}
    </div>
  );
};
