/**
 * CollapsibleValidationReport - Collapsible container for validation reports
 */

import React, { useState } from 'react';

interface CollapsibleValidationReportProps {
  content: string;
  verdict: 'APPROVED' | 'WARNING' | 'REJECTED';
}

export function CollapsibleValidationReport({ content, verdict }: CollapsibleValidationReportProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const getStatusColor = (verdict: string) => {
    switch (verdict) {
      case 'APPROVED':
        return { bg: '#1e3a1e', border: '#4caf50', text: '#66bb6a' };
      case 'WARNING':
        return { bg: '#3a2e1e', border: '#ff9800', text: '#ffb74d' };
      case 'REJECTED':
        return { bg: '#3a1e1e', border: '#f44336', text: '#ef5350' };
      default:
        return { bg: '#3a4149', border: '#cedfe7', text: '#cedfe7' };
    }
  };

  const colors = getStatusColor(verdict);

  return (
    <div style={{
      backgroundColor: '#3a4149',
      border: `1px solid ${colors.border}`,
      borderRadius: '8px',
      margin: '12px 0',
      overflow: 'hidden'
    }}>
      {/* Header - Always visible */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        style={{
          width: '100%',
          padding: '12px 16px',
          backgroundColor: colors.bg,
          border: 'none',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          cursor: 'pointer',
          transition: 'all 0.2s',
          outline: 'none'
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.backgroundColor = colors.bg.replace('1e', '2e');
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.backgroundColor = colors.bg;
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            backgroundColor: colors.text,
            animation: 'pulse 2s ease-in-out infinite'
          }}></div>
          <span style={{
            fontSize: '14px',
            fontWeight: 600,
            color: colors.text
          }}>
            Seismic Cop Validation Report - {verdict}
          </span>
        </div>
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke={colors.text}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{
            transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
            transition: 'transform 0.2s'
          }}
        >
          <polyline points="6 9 12 15 18 9"></polyline>
        </svg>
      </button>

      {/* Expandable content */}
      {isExpanded && (
        <div style={{
          padding: '16px',
          backgroundColor: '#3a4149',
          borderTop: `1px solid ${colors.border}`
        }}>
          <pre style={{
            fontSize: '12px',
            color: '#cedfe7',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            margin: 0,
            fontFamily: 'monospace',
            lineHeight: '1.6'
          }}>
            {content}
          </pre>
        </div>
      )}
    </div>
  );
}
