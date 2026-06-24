import { useState, useEffect } from 'react';
import { fetchFlags, fetchDrafts, createDraft } from '../api/client';
import type { WasteFlag, Draft } from '../api/client';
import { theme } from '../styles/theme';

const CATEGORY_COLORS: Record<string, string> = {
  'exact_duplicate': '#FF6B4A',
  'category_overlap': '#7C5CFC',
  'named_seat_ownership_unclear': '#2EA8E0',
};

export default function FlagsView() {
  const [flags, setFlags] = useState<WasteFlag[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [creating, setCreating] = useState<Record<string, boolean>>({});
  const [draftForms, setDraftForms] = useState<Record<string, string>>({});
  const [draftErrors, setDraftErrors] = useState<Record<string, string>>({});

  const loadFlags = () => {
    Promise.all([fetchFlags(), fetchDrafts()])
      .then(([flagsData, draftsData]) => {
        const drafts = draftsData.drafts || [];
        const resolvedFlagIds = new Set(
          drafts.filter((d: Draft) => d.status === 'SENT').map((d: Draft) => d.flag_id)
        );
        const activeFlags = (flagsData.waste_flags || []).filter(
          (f: WasteFlag) => !resolvedFlagIds.has(f.flag_id)
        );
        
        setFlags(activeFlags);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message || 'Failed to fetch flags');
        setLoading(false);
      });
  };

  useEffect(() => {
    loadFlags();
  }, []);

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
      alert('Draft created successfully. View it in Pending Approvals.');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to create draft';
      setDraftErrors(prev => ({ ...prev, [flagId]: msg }));
    } finally {
      setCreating(prev => ({ ...prev, [flagId]: false }));
    }
  };

  if (loading) return <div style={{ padding: '40px', color: theme.colors.outline, textAlign: 'center', ...theme.typography.bodyMd }}>Loading...</div>;
  if (error) return <div style={{ padding: '40px', color: theme.colors.error, textAlign: 'center', ...theme.typography.bodyMd }}>Error: {error}</div>;
  if (flags.length === 0) return <div style={{ padding: '40px', color: theme.colors.outline, textAlign: 'center', ...theme.typography.bodyMd }}>No flags found — run an audit first via the CLI.</div>;

  const confidenceBadge = (score: string) => {
    const colors: Record<string, { bg: string; text: string }> = {
      high:   { bg: 'rgba(255, 107, 74, 0.1)', text: '#FF6B4A' },
      medium: { bg: 'rgba(245, 158, 11, 0.1)', text: '#F59E0B' },
      low:    { bg: 'rgba(229, 226, 227, 0.1)', text: theme.colors.outline },
    };
    const c = colors[score.toLowerCase()] || colors.low;
    return (
      <span style={{
        ...theme.typography.labelSm,
        padding: '4px 10px',
        borderRadius: '9999px',
        background: c.bg,
        color: c.text,
        textTransform: 'uppercase'
      }}>
        {score}
      </span>
    );
  };

  return (
    <div className="table-container" style={{ overflowX: 'auto', background: theme.colors.panelBg, borderRadius: theme.rounded.container, border: `1px solid ${theme.colors.divider}`, padding: theme.spacing.md }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
        <thead>
          <tr style={{ borderBottom: `1px solid ${theme.colors.structuralBorder}` }}>
            {['Flag ID', 'Vendor', 'Category', 'Confidence', 'Monthly Cost', 'Review', 'Reason', 'Action'].map(h => (
              <th key={h} style={{
                padding: '16px 16px',
                ...theme.typography.labelSm,
                color: theme.colors.outline,
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
              }}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {flags.map(flag => (
            <tr key={flag.flag_id} style={{ borderBottom: `1px solid ${theme.colors.divider}`, transition: 'background-color 0.2s ease' }}
              onMouseEnter={e => (e.currentTarget.style.backgroundColor = theme.colors.panelBgHover)}
              onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
            >
              <td style={{ padding: '16px 16px', ...theme.typography.monoData, color: theme.colors.onBackground }}>
                {flag.flag_id.slice(0, 8)}...
              </td>
              <td style={{ padding: '16px 16px', ...theme.typography.bodyMd, color: theme.colors.onBackground, fontWeight: 500 }}>
                {flag.vendor_name}
              </td>
              <td style={{ padding: '16px 16px', ...theme.typography.bodyMd, color: theme.colors.outline }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: CATEGORY_COLORS[flag.overlap_category] || theme.colors.outline }}></span>
                  {flag.overlap_category.replace(/_/g, ' ')}
                </div>
              </td>
              <td style={{ padding: '16px 16px' }}>{confidenceBadge(flag.confidence_score)}</td>
              <td style={{ padding: '16px 16px', ...theme.typography.monoData, color: theme.colors.primary }}>
                ${flag.monthly_cost.toFixed(2)}
              </td>
              <td style={{ padding: '16px 16px', ...theme.typography.bodyMd, color: theme.colors.outline }}>
                {flag.requires_human_review ? 'Yes' : 'No'}
              </td>
              <td style={{ padding: '16px 16px', ...theme.typography.bodyMd, color: theme.colors.outline, maxWidth: '250px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {flag.reason}
              </td>
              <td style={{ padding: '16px 16px' }}>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start' }}>
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <input
                      className="touch-target"
                      type="text"
                      placeholder="@user or #channel"
                      value={draftForms[flag.flag_id] || ''}
                      onChange={e => {
                        setDraftForms(prev => ({ ...prev, [flag.flag_id]: e.target.value }));
                        setDraftErrors(prev => ({ ...prev, [flag.flag_id]: '' }));
                      }}
                      style={{
                        padding: '6px 10px',
                        borderRadius: theme.rounded.default,
                        border: `1px solid ${theme.colors.divider}`,
                        background: theme.colors.background,
                        color: theme.colors.onBackground,
                        ...theme.typography.bodyMd,
                        fontSize: '13px',
                        width: '120px',
                        outline: 'none',
                        transition: 'all 0.2s ease',
                      }}
                      onFocus={(e) => {
                        e.currentTarget.style.borderColor = theme.colors.buttonPrimaryBg;
                      }}
                      onBlur={(e) => {
                        e.currentTarget.style.borderColor = theme.colors.divider;
                      }}
                    />
                    <button
                      className="touch-target"
                      onClick={() => handleCreateDraft(flag.flag_id)}
                      disabled={creating[flag.flag_id]}
                      style={{
                        background: creating[flag.flag_id] ? theme.colors.surfaceBright : 'transparent',
                        color: theme.colors.onBackground,
                        border: `1px solid ${theme.colors.structuralBorder}`,
                        padding: '6px 12px',
                        borderRadius: theme.rounded.default,
                        ...theme.typography.bodyMd,
                        fontSize: '13px',
                        fontWeight: 500,
                        cursor: creating[flag.flag_id] ? 'not-allowed' : 'pointer',
                        transition: 'all 0.2s ease',
                      }}
                      onMouseEnter={e => !creating[flag.flag_id] && (e.currentTarget.style.backgroundColor = theme.colors.panelBgHover)}
                      onMouseLeave={e => !creating[flag.flag_id] && (e.currentTarget.style.backgroundColor = 'transparent')}
                    >
                      {creating[flag.flag_id] ? '...' : 'Draft'}
                    </button>
                  </div>
                  {draftErrors[flag.flag_id] && (
                    <div style={{ ...theme.typography.labelSm, color: theme.colors.error, marginTop: '4px' }}>
                      {draftErrors[flag.flag_id]}
                    </div>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
