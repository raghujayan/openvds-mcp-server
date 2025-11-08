/**
 * CollapsibleImage - Expandable/collapsible component for seismic images
 */

import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Maximize2, Minimize2 } from 'lucide-react';

interface CollapsibleImageProps {
  src: string;
  alt: string;
  title?: string;
}

export const CollapsibleImage: React.FC<CollapsibleImageProps> = ({ src, alt, title }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="border rounded-lg my-2 overflow-hidden" style={{ backgroundColor: '#3a4149', borderColor: 'rgba(255, 255, 255, 0.1)' }}>
      {/* Header */}
      <div
        className="flex items-center justify-between p-2 cursor-pointer transition-opacity border-b"
        style={{ borderBottomColor: 'rgba(255, 255, 255, 0.1)' }}
        onClick={() => setIsExpanded(!isExpanded)}
        onMouseEnter={(e) => e.currentTarget.style.opacity = '0.8'}
        onMouseLeave={(e) => e.currentTarget.style.opacity = '1'}
      >
        <div className="flex items-center gap-2">
          {isExpanded ? (
            <Minimize2 className="w-4 h-4" style={{ color: '#9ca3af' }} />
          ) : (
            <Maximize2 className="w-4 h-4" style={{ color: '#9ca3af' }} />
          )}
          <span className="text-sm font-medium" style={{ color: '#cedfe7' }}>
            {title || 'Seismic Visualization'}
          </span>
        </div>
        {isExpanded ? (
          <ChevronDown className="w-4 h-4" style={{ color: '#9ca3af' }} />
        ) : (
          <ChevronRight className="w-4 h-4" style={{ color: '#9ca3af' }} />
        )}
      </div>

      {/* Image Content */}
      {isExpanded && (
        <div className="p-2">
          <img
            src={src}
            alt={alt}
            className="w-full rounded"
            style={{ maxWidth: '100%', height: 'auto' }}
          />
        </div>
      )}
    </div>
  );
};
