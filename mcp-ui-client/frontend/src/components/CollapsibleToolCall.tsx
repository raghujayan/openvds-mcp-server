/**
 * CollapsibleToolCall - Expandable/collapsible component for tool execution details
 */

import React, { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';

interface CollapsibleToolCallProps {
  name: string;
  input: any;
  status?: 'executing' | 'completed' | 'error';
}

export const CollapsibleToolCall: React.FC<CollapsibleToolCallProps> = ({ name, input, status = 'completed' }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const getStatusIcon = () => {
    switch (status) {
      case 'executing':
        return '⏳';
      case 'completed':
        return '✓';
      case 'error':
        return '❌';
      default:
        return '🔧';
    }
  };

  const getStatusColor = () => {
    switch (status) {
      case 'executing':
        return { backgroundColor: '#3a4149', borderColor: 'rgba(220, 180, 38, 0.5)' };
      case 'completed':
        return { backgroundColor: '#3a4149', borderColor: 'rgba(206, 223, 231, 0.3)' };
      case 'error':
        return { backgroundColor: '#3a4149', borderColor: 'rgba(255, 182, 193, 0.5)' };
      default:
        return { backgroundColor: '#3a4149', borderColor: 'rgba(255, 255, 255, 0.1)' };
    }
  };

  const getTextColor = () => {
    switch (status) {
      case 'executing':
        return '#dcb426';
      case 'completed':
        return '#cedfe7';
      case 'error':
        return '#ffb6c1';
      default:
        return '#f4f4f4';
    }
  };

  return (
    <div className="border rounded-lg my-2 overflow-hidden transition-all" style={getStatusColor()}>
      {/* Header - Always visible */}
      <div
        className="flex items-center justify-between p-3 cursor-pointer hover:opacity-80 transition-opacity"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-2 flex-1">
          <span className="text-base">{getStatusIcon()}</span>
          <span className="text-sm font-medium" style={{ color: getTextColor() }}>
            {name}
          </span>
          {status === 'executing' && (
            <span className="text-xs animate-pulse" style={{ color: '#dcb426' }}>Running...</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {isExpanded ? (
            <ChevronDown className="w-4 h-4" style={{ color: '#9ca3af' }} />
          ) : (
            <ChevronRight className="w-4 h-4" style={{ color: '#9ca3af' }} />
          )}
        </div>
      </div>

      {/* Expandable Content */}
      {isExpanded && (
        <div className="px-3 pb-3" style={{ borderTop: '1px solid rgba(255, 255, 255, 0.1)' }}>
          <div className="text-xs font-medium mb-1 mt-2" style={{ color: '#9ca3af' }}>Input Parameters:</div>
          <pre className="text-xs overflow-x-auto p-2 rounded" style={{ backgroundColor: 'rgba(0, 0, 0, 0.3)', color: getTextColor() }}>
            {JSON.stringify(input, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
};
