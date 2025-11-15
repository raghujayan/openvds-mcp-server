/**
 * System Status Panel
 * Displays comprehensive system health and status information
 */

import React, { useState, useEffect } from 'react';

interface SystemStatus {
  services: {
    backend: {
      status: string;
      port: number;
      pid: number;
      health: string;
      memory_mb: number;
      cpu_percent: number;
    };
    mcp_server: {
      status: string;
      container_id: string | null;
      image: string;
      platform: string;
    };
    elasticsearch: {
      status: string;
      url: string;
      index: string;
      document_count: number | null;
    };
  };
  data_sources: {
    vds_mount: {
      path: string;
      status: string;
      health_check_time_ms: number | null;
      surveys_available: number;
    };
    license_server: {
      server: string;
      status: string;
    };
  };
  tools: {
    available: number;
    list: Array<{
      name: string;
      description: string;
    }>;
  };
}

interface SystemStatusPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SystemStatusPanel: React.FC<SystemStatusPanelProps> = ({ isOpen, onClose }) => {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showTools, setShowTools] = useState(false);

  const fetchStatus = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('http://localhost:8000/api/system/status');
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      const data = await response.json();
      setStatus(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch status');
    } finally {
      setLoading(false);
    };
  };

  useEffect(() => {
    if (isOpen) {
      fetchStatus();
      // Auto-refresh every 5 seconds when open
      const interval = setInterval(fetchStatus, 5000);
      return () => clearInterval(interval);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
    const colors: Record<string, { bg: string; text: string }> = {
      running: { bg: '#dcfce7', text: '#166534' },
      connected: { bg: '#dcfce7', text: '#166534' },
      healthy: { bg: '#dcfce7', text: '#166534' },
      disconnected: { bg: '#fee2e2', text: '#991b1b' },
      unknown: { bg: '#f3f4f6', text: '#374151' },
    };

    const color = colors[status] || colors.unknown;

    return (
      <span style={{
        padding: '4px 12px',
        fontSize: '12px',
        fontWeight: 500,
        borderRadius: '4px',
        backgroundColor: color.bg,
        color: color.text
      }}>
        {status}
      </span>
    );
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.7)',
      zIndex: 9999,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px'
    }}>
      <div style={{
        backgroundColor: 'white',
        borderRadius: '12px',
        width: '100%',
        maxWidth: '1200px',
        maxHeight: '90vh',
        overflowY: 'auto',
        boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.3)'
      }}>
        {/* Header */}
        <div style={{
          position: 'sticky',
          top: 0,
          background: 'linear-gradient(to right, #2563eb, #1d4ed8)',
          padding: '20px 24px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderTopLeftRadius: '12px',
          borderTopRightRadius: '12px'
        }}>
          <h2 style={{ fontSize: '24px', fontWeight: 'bold', color: 'white', margin: 0 }}>
            System Status
          </h2>
          <button
            onClick={onClose}
            style={{
              color: 'white',
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              padding: '4px'
            }}
          >
            <svg style={{ width: '24px', height: '24px' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div style={{ padding: '24px', backgroundColor: '#f9fafb' }}>
          {loading && !status && (
            <div style={{ textAlign: 'center', padding: '48px 0' }}>
              <div style={{
                display: 'inline-block',
                width: '48px',
                height: '48px',
                border: '4px solid #e5e7eb',
                borderTop: '4px solid #3b82f6',
                borderRadius: '50%',
                animation: 'spin 1s linear infinite'
              }}></div>
              <p style={{ marginTop: '16px', color: '#374151', fontWeight: 600, fontSize: '18px' }}>
                Loading system status...
              </p>
            </div>
          )}

          {error && (
            <div style={{
              backgroundColor: '#fee2e2',
              borderLeft: '4px solid #ef4444',
              borderRadius: '8px',
              padding: '16px',
              marginBottom: '16px'
            }}>
              <p style={{ color: '#991b1b', fontWeight: 600, margin: 0 }}>Error: {error}</p>
            </div>
          )}

          {status && (
            <>
              {/* Services Section */}
              <section style={{ marginBottom: '24px' }}>
                <h3 style={{
                  fontSize: '20px',
                  fontWeight: 'bold',
                  marginBottom: '16px',
                  color: '#1f2937',
                  borderBottom: '2px solid #3b82f6',
                  paddingBottom: '8px'
                }}>Services</h3>

                {/* Backend */}
                <div style={{
                  background: 'linear-gradient(to right, #dbeafe, #bfdbfe)',
                  borderLeft: '4px solid #3b82f6',
                  borderRadius: '8px',
                  padding: '16px',
                  marginBottom: '12px',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                    <h4 style={{ fontSize: '18px', fontWeight: 'bold', color: '#1f2937', margin: 0 }}>Backend (FastAPI)</h4>
                    <StatusBadge status={status.services.backend.status} />
                  </div>
                  <div style={{ fontSize: '14px', color: '#374151', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                    <p style={{ margin: 0 }}><strong>Port:</strong> {status.services.backend.port}</p>
                    <p style={{ margin: 0 }}><strong>PID:</strong> {status.services.backend.pid}</p>
                    <p style={{ margin: 0 }}><strong>Memory:</strong> {status.services.backend.memory_mb} MB</p>
                    <p style={{ margin: 0 }}><strong>CPU:</strong> {status.services.backend.cpu_percent}%</p>
                  </div>
                </div>

                {/* MCP Server */}
                <div style={{
                  background: 'linear-gradient(to right, #f3e8ff, #e9d5ff)',
                  borderLeft: '4px solid #a855f7',
                  borderRadius: '8px',
                  padding: '16px',
                  marginBottom: '12px',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                    <h4 style={{ fontSize: '18px', fontWeight: 'bold', color: '#1f2937', margin: 0 }}>MCP Server (Docker)</h4>
                    <StatusBadge status={status.services.mcp_server.status} />
                  </div>
                  <div style={{ fontSize: '14px', color: '#374151' }}>
                    <p style={{ margin: '4px 0' }}><strong>Image:</strong> {status.services.mcp_server.image}</p>
                    <p style={{ margin: '4px 0' }}><strong>Platform:</strong> {status.services.mcp_server.platform}</p>
                  </div>
                </div>

                {/* Elasticsearch */}
                <div style={{
                  background: 'linear-gradient(to right, #d1fae5, #a7f3d0)',
                  borderLeft: '4px solid #10b981',
                  borderRadius: '8px',
                  padding: '16px',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                    <h4 style={{ fontSize: '18px', fontWeight: 'bold', color: '#1f2937', margin: 0 }}>Elasticsearch</h4>
                    <StatusBadge status={status.services.elasticsearch.status} />
                  </div>
                  <div style={{ fontSize: '14px', color: '#374151' }}>
                    <p style={{ margin: '4px 0' }}><strong>Index:</strong> {status.services.elasticsearch.index}</p>
                    <p style={{ margin: '4px 0' }}><strong>Documents:</strong> {status.services.elasticsearch.document_count?.toLocaleString() || 'N/A'}</p>
                  </div>
                </div>
              </section>

              {/* Data Sources Section */}
              <section style={{ marginBottom: '24px' }}>
                <h3 style={{
                  fontSize: '20px',
                  fontWeight: 'bold',
                  marginBottom: '16px',
                  color: '#1f2937',
                  borderBottom: '2px solid #3b82f6',
                  paddingBottom: '8px'
                }}>Data Sources</h3>

                {/* VDS Mount */}
                <div style={{
                  background: 'linear-gradient(to right, #fed7aa, #fdba74)',
                  borderLeft: '4px solid #f97316',
                  borderRadius: '8px',
                  padding: '16px',
                  marginBottom: '12px',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                    <h4 style={{ fontSize: '18px', fontWeight: 'bold', color: '#1f2937', margin: 0 }}>VDS Mount</h4>
                    <StatusBadge status={status.data_sources.vds_mount.status} />
                  </div>
                  <div style={{ fontSize: '14px', color: '#374151' }}>
                    <p style={{ margin: '4px 0' }}><strong>Path:</strong> {status.data_sources.vds_mount.path}</p>
                    <p style={{ margin: '4px 0' }}><strong>Surveys:</strong> {status.data_sources.vds_mount.surveys_available.toLocaleString()}</p>
                  </div>
                </div>

                {/* License Server */}
                <div style={{
                  background: 'linear-gradient(to right, #e0e7ff, #c7d2fe)',
                  borderLeft: '4px solid #6366f1',
                  borderRadius: '8px',
                  padding: '16px',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                    <h4 style={{ fontSize: '18px', fontWeight: 'bold', color: '#1f2937', margin: 0 }}>License Server</h4>
                    <StatusBadge status={status.data_sources.license_server.status} />
                  </div>
                  <div style={{ fontSize: '14px', color: '#374151' }}>
                    <p style={{ margin: '4px 0' }}><strong>Server:</strong> {status.data_sources.license_server.server}</p>
                  </div>
                </div>
              </section>

              {/* Tools Section */}
              <section style={{ marginBottom: '24px' }}>
                <h3 style={{
                  fontSize: '20px',
                  fontWeight: 'bold',
                  marginBottom: '16px',
                  color: '#1f2937',
                  borderBottom: '2px solid #3b82f6',
                  paddingBottom: '8px'
                }}>MCP Tools</h3>
                <div style={{
                  background: 'linear-gradient(to right, #ccfbf1, #99f6e4)',
                  borderLeft: '4px solid #14b8a6',
                  borderRadius: '8px',
                  padding: '16px',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                    <p style={{ fontSize: '18px', fontWeight: 'bold', color: '#1f2937', margin: 0 }}>
                      {status.tools.available} tools available
                    </p>
                    <button
                      onClick={() => setShowTools(!showTools)}
                      style={{
                        padding: '6px 12px',
                        fontSize: '14px',
                        backgroundColor: '#3b82f6',
                        color: 'white',
                        borderRadius: '6px',
                        border: 'none',
                        cursor: 'pointer'
                      }}
                    >
                      {showTools ? 'Hide' : 'Show'} list
                    </button>
                  </div>

                  {showTools && (
                    <div style={{ marginTop: '12px', display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px' }}>
                      {status.tools.list.map((tool, idx) => (
                        <div key={idx} style={{
                          backgroundColor: 'white',
                          borderRadius: '4px',
                          padding: '12px',
                          border: '1px solid #5eead4',
                          boxShadow: '0 1px 2px rgba(0,0,0,0.05)'
                        }}>
                          <div style={{
                            fontSize: '13px',
                            fontWeight: 'bold',
                            fontFamily: 'monospace',
                            color: '#1f2937',
                            marginBottom: '4px'
                          }}>
                            {tool.name}
                          </div>
                          <div style={{
                            fontSize: '11px',
                            color: '#6b7280',
                            lineHeight: '1.4'
                          }}>
                            {tool.description}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </section>

              {/* Refresh Button */}
              <div style={{ textAlign: 'center', paddingTop: '16px', borderTop: '1px solid #e5e7eb', marginTop: '24px' }}>
                <button
                  onClick={fetchStatus}
                  disabled={loading}
                  style={{
                    padding: '12px 24px',
                    background: loading ? '#9ca3af' : 'linear-gradient(to right, #2563eb, #1d4ed8)',
                    color: 'white',
                    fontWeight: 600,
                    borderRadius: '8px',
                    border: 'none',
                    cursor: loading ? 'not-allowed' : 'pointer',
                    boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
                    fontSize: '14px'
                  }}
                >
                  {loading ? '🔄 Refreshing...' : '🔄 Refresh Now'}
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};
