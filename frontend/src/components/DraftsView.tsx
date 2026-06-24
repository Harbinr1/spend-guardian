import { useState, useEffect } from 'react';
import { fetchDrafts, approveDraft } from '../api/client';
import type { Draft } from '../api/client';
import { theme } from '../styles/theme';

export default function DraftsView() {
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [approving, setApproving] = useState<Record<string, boolean>>({});
  const [rowErrors, setRowErrors] = useState<Record<string, string>>({});

  const loadDrafts = () => {
    setLoading(true);
    fetchDrafts()
      .then(data => {
        setDrafts(data.drafts || []);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message || 'Failed to fetch drafts');
        setLoading(false);
      });
  };

  useEffect(() => { loadDrafts(); }, []);

  const handleApprove = async (draftId: string) => {
    setApproving(prev => ({ ...prev, [draftId]: true }));
    setRowErrors(prev => ({ ...prev, [draftId]: '' }));
    try {
      await approveDraft(draftId);
      // Only refresh AFTER the API confirms — no optimistic update
      loadDrafts();
    } catch (err: unknown) {
      setRowErrors(prev => ({ ...prev, [draftId]: 'Failed to send — try again' }));
    } finally {
      setApproving(prev => ({ ...prev, [draftId]: false }));
    }
  };

  const statusBadge = (draft: Draft) => {
    const status = draft.status;
    const colors: Record<string, { bg: string; text: string }> = {
      DRAFTED:  { bg: 'rgba(245, 158, 11, 0.1)', text: '#F59E0B' }, // Warning color
      APPROVED: { bg: 'rgba(94, 107, 255, 0.1)', text: theme.colors.primary },
      SENT:     { bg: 'rgba(16, 185, 129, 0.1)', text: '#10B981' }, // Success color
    };
    const c = colors[status] || { bg: 'rgba(229, 226, 227, 0.1)', text: theme.colors.outline };
    
    let timeStr = '';
    if (status === 'SENT' && draft.sent_at) {
      try {
        const date = new Date(draft.sent_at);
        timeStr = `${date.toLocaleDateString()} ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false })}`;
      } catch (e) {
        // ignore
      }
    }

    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}>
        <span style={{
          ...theme.typography.labelSm,
          padding: '4px 10px',
          borderRadius: '9999px',
          background: c.bg,
          color: c.text,
          textTransform: 'uppercase'
        }}>
          {status}
        </span>
        {timeStr && (
          <span style={{ ...theme.typography.monoData, color: theme.colors.outline, fontSize: '11px' }}>
            {timeStr}
          </span>
        )}
      </div>
    );
  };

  if (loading) return <div style={{ padding: '40px', color: theme.colors.outline, textAlign: 'center', ...theme.typography.bodyMd }}>Loading...</div>;
  if (error) return <div style={{ padding: '40px', color: theme.colors.error, textAlign: 'center', ...theme.typography.bodyMd }}>Error: {error}</div>;
  if (drafts.length === 0) return <div style={{ padding: '40px', color: theme.colors.outline, textAlign: 'center', ...theme.typography.bodyMd }}>No drafts found — create one via the CLI first.</div>;

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 340px), 1fr))', gap: theme.spacing.gutter }}>
      {drafts.map(draft => (
        <div key={draft.draft_id} style={{
          background: theme.colors.panelBg,
          border: `1px solid ${theme.colors.divider}`,
          borderRadius: theme.rounded.container,
          padding: '24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
          transition: 'transform 0.15s ease, background-color 0.2s ease',
        }}
          onMouseEnter={e => {
            e.currentTarget.style.transform = 'translateY(-2px)';
            e.currentTarget.style.backgroundColor = theme.colors.panelBgHover;
          }}
          onMouseLeave={e => {
            e.currentTarget.style.transform = 'translateY(0)';
            e.currentTarget.style.backgroundColor = theme.colors.panelBg;
          }}
        >
          {/* Header: draft_id + status */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ ...theme.typography.monoData, color: theme.colors.onBackground, wordBreak: 'break-all', fontSize: '14px' }}>
              {draft.draft_id.slice(0, 8)}...
            </span>
            {statusBadge(draft)}
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {/* Recipient */}
            <div style={{ ...theme.typography.bodyMd, color: theme.colors.outline }}>
              <span style={{ fontWeight: 500, color: theme.colors.onBackground }}>To:</span> {draft.recipient}
            </div>

            {/* Subject */}
            <div style={{ ...theme.typography.bodyMd, color: theme.colors.outline }}>
              <span style={{ fontWeight: 500, color: theme.colors.onBackground }}>Subject:</span> {draft.subject}
            </div>
          </div>

          {/* Body preview */}
          <div style={{
            ...theme.typography.bodyMd,
            color: theme.colors.onBackground,
            background: theme.colors.background,
            padding: '12px',
            borderRadius: theme.rounded.default,
            maxHeight: '120px',
            overflowY: 'auto',
            whiteSpace: 'pre-wrap',
            border: `1px solid ${theme.colors.structuralBorder}`,
          }}>
            {draft.body}
          </div>

          {/* Action / Error section */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '8px', marginTop: 'auto' }}>
            {rowErrors[draft.draft_id] && (
              <span style={{ ...theme.typography.labelSm, color: theme.colors.error }}>
                {rowErrors[draft.draft_id]}
              </span>
            )}
            {draft.status === 'DRAFTED' && (
              <button
                className="touch-target"
                onClick={() => handleApprove(draft.draft_id)}
                disabled={approving[draft.draft_id]}
                style={{
                  padding: '8px 24px',
                  borderRadius: theme.rounded.default,
                  border: 'none',
                  cursor: approving[draft.draft_id] ? 'not-allowed' : 'pointer',
                  ...theme.typography.bodyMd,
                  fontWeight: 500,
                  background: theme.colors.buttonPrimaryBg,
                  color: theme.colors.buttonPrimaryText,
                  opacity: approving[draft.draft_id] ? 0.6 : 1,
                  transition: 'all 0.15s ease',
                }}
              >
                {approving[draft.draft_id] ? 'Sending...' : 'Send to Slack'}
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
