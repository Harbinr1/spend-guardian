import { useState, useEffect } from 'react';
import { fetchFlags, fetchDrafts, approveDraft, createDraft, runSampleAudit, uploadCsvAudit } from '../api/client';
import type { WasteFlag, Draft } from '../api/client';
import AuditProgressOverlay from './AuditProgressOverlay';
import { theme } from '../styles/theme';

const CATEGORY_COLORS: Record<string, string> = {
  'exact_duplicate': '#FF6B4A',
  'category_overlap': '#7C5CFC',
  'named_seat_ownership_unclear': '#2EA8E0',
};

const CATEGORY_LABELS: Record<string, string> = {
  'exact_duplicate': 'exact dup',
  'category_overlap': 'overlap category',
  'named_seat_ownership_unclear': 'named seat',
};

export default function DashboardView() {
  const [flags, setFlags] = useState<WasteFlag[]>([]);
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);
  const [approving, setApproving] = useState<Record<string, boolean>>({});
  const [creating, setCreating] = useState<Record<string, boolean>>({});
  const [draftForms, setDraftForms] = useState<Record<string, string>>({});
  const [draftErrors, setDraftErrors] = useState<Record<string, string>>({});
  const [runningAudit, setRunningAudit] = useState(false);
  const [auditComplete, setAuditComplete] = useState(false);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [warningsExpanded, setWarningsExpanded] = useState(false);
  const [auditRunId, setAuditRunId] = useState(0);

  // Load data on mount
  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [flagsData, draftsData] = await Promise.all([fetchFlags(), fetchDrafts()]);
      const drafts = draftsData.drafts || [];
      const resolvedFlagIds = new Set(
        drafts.filter((d: Draft) => d.status === 'SENT').map((d: Draft) => d.flag_id)
      );
      const activeFlags = (flagsData.waste_flags || []).filter(
        (f: WasteFlag) => !resolvedFlagIds.has(f.flag_id)
      );
      setFlags(activeFlags);
      setDrafts(drafts);
      setWarnings(flagsData.warnings || []);
      setLastRefreshed(new Date());
      setLoading(false);
      return activeFlags.length;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard data');
      setLoading(false);
      throw err;
    }
  };

  const handleApprove = async (draftId: string) => {
    setApproving(prev => ({ ...prev, [draftId]: true }));
    try {
      await approveDraft(draftId);
      await loadData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      alert(`Failed to approve draft: ${msg}`);
    } finally {
      setApproving(prev => ({ ...prev, [draftId]: false }));
    }
  };

  const handleCreateDraft = async (flagId: string) => {
    const recipient = draftForms[flagId];
    if (!recipient?.trim()) {
      setDraftErrors(prev => ({ ...prev, [flagId]: 'Recipient is required' }));
      return;
    }

    setCreating(prev => ({ ...prev, [flagId]: true }));
    setDraftErrors(prev => ({ ...prev, [flagId]: '' }));
    try {
      await createDraft(flagId, recipient);
      setDraftForms(prev => ({ ...prev, [flagId]: '' }));
      await loadData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to create draft';
      setDraftErrors(prev => ({ ...prev, [flagId]: msg }));
    } finally {
      setCreating(prev => ({ ...prev, [flagId]: false }));
    }
  };

  const handleRunAudit = async () => {
    setAuditRunId(prev => prev + 1);
    setRunningAudit(true);
    setAuditComplete(false);
    try {
      await runSampleAudit();
      await loadData();
      setAuditComplete(true);
      setTimeout(() => {
        setRunningAudit(false);
      }, 500);
    } catch (err) {
      setAuditComplete(false);
      setRunningAudit(false);
      const msg = err instanceof Error ? err.message : 'Unknown error';
      alert(`Audit failed: ${msg}`);
    }
  };

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.csv')) {
      alert('Error: Please select a valid .csv file.');
      return;
    }
    if (file.size === 0) {
      alert('Error: The selected file is empty.');
      return;
    }

    setAuditRunId(prev => prev + 1);
    setRunningAudit(true);
    setAuditComplete(false);
    try {
      await uploadCsvAudit(file);
      await loadData();
      setAuditComplete(true);
      setTimeout(() => {
        setRunningAudit(false);
      }, 500);
    } catch (err) {
      setAuditComplete(false);
      setRunningAudit(false);
      const msg = err instanceof Error ? err.message : 'Unknown error';
      alert(`Audit failed: ${msg}`);
    } finally {
      event.target.value = '';
    }
  };

  if (loading) return <div style={{ ...theme.typography.bodyMd, color: theme.colors.outline, marginTop: '40px' }}>Loading...</div>;
  if (error) return <div style={{ ...theme.typography.bodyMd, color: theme.colors.error, marginTop: '40px' }}>Error: {error}</div>;

  const totalSavings = flags.reduce((sum, f) => sum + (f.monthly_cost || 0), 0);
  const pendingDraftsList = drafts.filter(d => d.status === 'DRAFTED');
  const pendingDrafts = pendingDraftsList.length;

  const categoryCounts = flags.reduce((acc, f) => {
    acc[f.overlap_category] = (acc[f.overlap_category] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return (
    <>
      <AuditProgressOverlay isVisible={runningAudit} isComplete={auditComplete} runId={auditRunId} />
      <div>

        {/* Header Controls */}
        <div className="header-controls">
          <input
            type="file"
            id="csv-file-input"
            accept=".csv"
            onChange={handleFileChange}
            style={{ display: 'none' }}
          />
          <button
            className="touch-target"
            onClick={() => document.getElementById('csv-file-input')?.click()}
            disabled={runningAudit}
            style={{
              background: 'transparent',
              color: theme.colors.buttonPrimaryText,
              border: `1px solid ${theme.colors.structuralBorder}`,
              padding: '10px 20px',
              borderRadius: theme.rounded.default,
              ...theme.typography.bodyMd,
              fontWeight: 500,
              cursor: runningAudit ? 'not-allowed' : 'pointer',
              transition: 'all 0.15s ease',
              opacity: runningAudit ? 0.5 : 1
            }}
            onMouseEnter={e => !runningAudit && (e.currentTarget.style.backgroundColor = theme.colors.panelBg)}
            onMouseLeave={e => !runningAudit && (e.currentTarget.style.backgroundColor = 'transparent')}
          >
            Upload CSV
          </button>
          <button
            className="touch-target"
            onClick={handleRunAudit}
            disabled={runningAudit}
            style={{
              background: runningAudit ? theme.colors.surfaceBright : theme.colors.buttonPrimaryBg,
              color: theme.colors.buttonPrimaryText,
              border: 'none',
              padding: '10px 20px',
              borderRadius: theme.rounded.default,
              ...theme.typography.bodyMd,
              fontWeight: 500,
              cursor: runningAudit ? 'not-allowed' : 'pointer',
              transition: 'all 0.15s ease',
              opacity: runningAudit ? 0.8 : 1
            }}
          >
            {runningAudit ? 'Running Audit...' : 'Run Sample Audit'}
          </button>
          <div style={{ textAlign: 'right' }}>
            <div style={{ ...theme.typography.labelSm, color: theme.colors.outline, marginBottom: '4px' }}>
              Last refreshed
            </div>
            <div style={{ ...theme.typography.monoData, color: theme.colors.onSurface }}>
              {lastRefreshed ? lastRefreshed.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false }) : '—'}
            </div>
          </div>
        </div>

        {/* Warnings Banner */}
        {warnings.length > 0 && (
          <div style={{
            background: theme.colors.panelBg,
            border: `1px solid ${theme.colors.errorContainer}`,
            borderRadius: theme.rounded.container,
            padding: theme.spacing.md,
            marginBottom: theme.spacing.lg,
            color: theme.colors.error
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ ...theme.typography.bodyMd, fontWeight: 500 }}>
                <span style={{ display: 'inline-block', width: '6px', height: '6px', borderRadius: '50%', background: theme.colors.error, marginRight: '8px', verticalAlign: 'middle' }}></span>
                {warnings.length} warning{warnings.length !== 1 ? 's' : ''} detected during ingestion.
              </div>
              <button
                onClick={() => setWarningsExpanded(!warningsExpanded)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: theme.colors.error,
                  textDecoration: 'underline',
                  cursor: 'pointer',
                  ...theme.typography.bodyMd,
                  fontWeight: 400
                }}
              >
                {warningsExpanded ? 'Hide Details' : 'Show Details'}
              </button>
            </div>
            {warningsExpanded && (
              <ul style={{ marginTop: theme.spacing.sm, marginBottom: 0, paddingLeft: theme.spacing.gutter, ...theme.typography.monoData }}>
                {warnings.map((w, idx) => (
                  <li key={idx} style={{ marginBottom: theme.spacing.xs }}>{w}</li>
                ))}
              </ul>
            )}
          </div>
        )}

        {/* Bento Grid Layout */}
        <div className="bento-grid">

          {/* Hero Statement - spans all 12 columns */}
          <div className="bento-item-full" style={{
            background: theme.colors.panelBg,
            borderRadius: theme.rounded.container,
            padding: '40px',
            border: `1px solid ${theme.colors.divider}`,
            borderTop: `1px solid rgba(255,255,255,0.1)`,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
          }}>
            <div className="hero-text-dashboard" style={{
              ...theme.typography.h1,
              marginBottom: theme.spacing.md
            }}>
              We found <br />
              <span style={{ ...theme.typography.monoData, fontSize: 'inherit', fontWeight: 500, letterSpacing: '-1.5px', color: theme.colors.primary }}>
                ${totalSavings.toFixed(2)}/mo
              </span><br />
              leaking out.
            </div>
            <div style={{ ...theme.typography.h4, color: theme.colors.outline, fontWeight: 400 }}>
              Across {flags.length} flag{flags.length !== 1 ? 's' : ''} · {pendingDrafts} pending approval{pendingDrafts !== 1 ? 's' : ''}
            </div>
          </div>

          {/* Category Counts */}
          {Object.entries(categoryCounts).map(([cat, count]) => {
            const isExact = cat === 'exact_duplicate';
            const countLabel = isExact ? 'exact' : cat === 'named_seat_ownership_unclear' ? 'named' : 'overlap';

            return (
              <div key={cat} className="bento-item-third" style={{
                background: theme.colors.panelBg,
                borderRadius: theme.rounded.container,
                padding: theme.spacing.lg,
                border: `1px solid ${theme.colors.divider}`,
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center',
                alignItems: 'center',
                textAlign: 'center',
                aspectRatio: '1',
              }}>
                <div style={{
                  width: '6px',
                  height: '6px',
                  borderRadius: '50%',
                  backgroundColor: CATEGORY_COLORS[cat] || theme.colors.primary,
                  marginBottom: theme.spacing.md,
                  boxShadow: `0 0 8px ${CATEGORY_COLORS[cat] || theme.colors.primary}`
                }}></div>
                <div style={{ ...theme.typography.h2, marginBottom: theme.spacing.xs }}>
                  {count} {countLabel}
                </div>
                <div style={{ ...theme.typography.bodyMd, color: theme.colors.outline }}>
                  {CATEGORY_LABELS[cat] || cat}
                </div>
              </div>
            );
          })}

          {/* Pending Approvals List */}
          {pendingDraftsList.length > 0 && (
            <div className="bento-item-full" style={{
              background: theme.colors.panelBg,
              borderRadius: theme.rounded.container,
              padding: theme.spacing.lg,
              border: `1px solid ${theme.colors.divider}`,
              marginTop: theme.spacing.lg
            }}>
              <div style={{ ...theme.typography.h3, marginBottom: theme.spacing.lg, paddingBottom: theme.spacing.md, borderBottom: `1px solid ${theme.colors.divider}` }}>
                Pending Approvals
              </div>
              <div style={{ maxHeight: '400px', overflowY: 'auto', paddingRight: theme.spacing.sm }}>
                {pendingDraftsList.map(d => {
                  const parentFlag = flags.find(f => f.flag_id === d.flag_id);
                  const rowColor = parentFlag ? CATEGORY_COLORS[parentFlag.overlap_category] : theme.colors.outline;

                  return (
                    <div key={d.draft_id} style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      padding: '16px 0',
                      borderBottom: `1px solid ${theme.colors.divider}`,
                    }}>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: rowColor }}></span>
                          <span style={{ ...theme.typography.bodyLg, fontWeight: 500 }}>{d.recipient}</span>
                        </div>
                        <div style={{ ...theme.typography.bodyMd, color: theme.colors.outline }}>{d.subject}</div>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
                        <span style={{ ...theme.typography.monoData, color: theme.colors.outline, textTransform: 'uppercase' }}>
                          {d.status}
                        </span>
                        <button
                          className="touch-target"
                          onClick={() => handleApprove(d.draft_id)}
                          disabled={approving[d.draft_id]}
                          style={{
                            background: theme.colors.buttonPrimaryBg,
                            color: theme.colors.buttonPrimaryText,
                            border: 'none',
                            padding: '8px 20px',
                            borderRadius: theme.rounded.default,
                            ...theme.typography.bodyMd,
                            fontWeight: 500,
                            cursor: approving[d.draft_id] ? 'not-allowed' : 'pointer',
                            opacity: approving[d.draft_id] ? 0.7 : 1,
                            transition: 'all 0.15s ease',
                          }}
                        >
                          {approving[d.draft_id] ? 'Approving...' : 'Approve'}
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Active Flags List */}
          <div className="bento-item-full" style={{
            background: theme.colors.panelBg,
            borderRadius: theme.rounded.container,
            padding: theme.spacing.lg,
            border: `1px solid ${theme.colors.divider}`,
            marginTop: pendingDraftsList.length > 0 ? 0 : theme.spacing.lg
          }}>
            <div style={{ ...theme.typography.h3, marginBottom: theme.spacing.lg, paddingBottom: theme.spacing.md, borderBottom: `1px solid ${theme.colors.divider}` }}>
              Detected Flags
            </div>

            {flags.length === 0 ? (
              <div style={{ ...theme.typography.bodyMd, color: theme.colors.outline }}>No flags detected.</div>
            ) : (
              <div style={{ maxHeight: '500px', overflowY: 'auto', paddingRight: theme.spacing.sm }}>
                {flags.map(f => (
                  <div key={f.flag_id} style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '16px 0',
                    borderBottom: `1px solid ${theme.colors.divider}`,
                    transition: 'background-color 0.2s ease',
                  }}
                    onMouseEnter={e => (e.currentTarget.style.backgroundColor = theme.colors.panelBgHover)}
                    onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
                  >
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: '12px', paddingLeft: '8px' }}>
                      <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: CATEGORY_COLORS[f.overlap_category] || theme.colors.outline }}></span>
                      <span style={{ ...theme.typography.bodyLg, fontWeight: 500 }}>{f.vendor_name}</span>
                      <span style={{ ...theme.typography.bodyMd, color: theme.colors.outline }}>— {f.overlap_category.replace(/_/g, ' ')}</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '24px', paddingRight: '8px' }}>
                      <div style={{ ...theme.typography.monoData, fontSize: '16px', color: theme.colors.primary }}>
                        ${f.monthly_cost.toFixed(2)}
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
                          <div style={{ display: 'flex', gap: '8px' }}>
                            <input
                              className="touch-target"
                              type="text"
                              placeholder="@user or #channel"
                              value={draftForms[f.flag_id] || ''}
                              onChange={e => {
                                setDraftForms(prev => ({ ...prev, [f.flag_id]: e.target.value }));
                                setDraftErrors(prev => ({ ...prev, [f.flag_id]: '' }));
                              }}
                              style={{
                                padding: '6px 12px',
                                borderRadius: theme.rounded.default,
                                border: `1px solid ${theme.colors.divider}`,
                                background: theme.colors.background,
                                color: theme.colors.onBackground,
                                ...theme.typography.bodyMd,
                                fontSize: '13px',
                                width: '160px',
                                outline: 'none',
                                transition: 'all 0.2s ease',
                              }}
                              onFocus={(e) => {
                                e.currentTarget.style.borderColor = theme.colors.buttonPrimaryBg;
                                e.currentTarget.style.boxShadow = `0 0 0 2px rgba(94, 107, 255, 0.2)`;
                              }}
                              onBlur={(e) => {
                                e.currentTarget.style.borderColor = theme.colors.divider;
                                e.currentTarget.style.boxShadow = 'none';
                              }}
                            />
                            <button
                              className="touch-target"
                              onClick={() => handleCreateDraft(f.flag_id)}
                              disabled={creating[f.flag_id]}
                              style={{
                                background: creating[f.flag_id] ? theme.colors.surfaceBright : 'transparent',
                                color: theme.colors.onBackground,
                                border: `1px solid ${theme.colors.structuralBorder}`,
                                padding: '6px 16px',
                                borderRadius: theme.rounded.default,
                                ...theme.typography.bodyMd,
                                fontSize: '13px',
                                fontWeight: 500,
                                cursor: creating[f.flag_id] ? 'not-allowed' : 'pointer',
                                opacity: creating[f.flag_id] ? 0.7 : 1,
                                transition: 'all 0.2s ease',
                              }}
                              onMouseEnter={e => !creating[f.flag_id] && (e.currentTarget.style.backgroundColor = theme.colors.panelBg)}
                              onMouseLeave={e => !creating[f.flag_id] && (e.currentTarget.style.backgroundColor = 'transparent')}
                            >
                              {creating[f.flag_id] ? '...' : 'Draft'}
                            </button>
                          </div>
                          {draftErrors[f.flag_id] && (
                            <div style={{ ...theme.typography.labelSm, color: theme.colors.error, marginTop: '4px' }}>
                              {draftErrors[f.flag_id]}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

        </div>
      </div>
    </>
  );
}