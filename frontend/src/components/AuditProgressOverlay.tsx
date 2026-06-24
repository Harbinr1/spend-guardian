import { useEffect, useState } from 'react';
import { theme } from '../styles/theme';

interface Props {
  isVisible: boolean;
  isComplete: boolean;
  runId?: number;   // kept for compatibility, not used for polling
}

const STAGES = [
  { id: 0, text: '🔍 Ingesting transactions…', tier: null },
  { id: 1, text: '🏷️ Classifying vendors (rule engine + lightweight AI fallback)', tier: 'LIGHTWEIGHT AI' },
  { id: 2, text: '⚠️ Detecting duplicate charges & overlaps', tier: 'MEDIUM AI' },
  { id: 3, text: '📊 Generating savings recommendations', tier: 'ADVANCED AI' },
  { id: 4, text: '📋 Finalizing report…', tier: null },
];

export default function AuditProgressOverlay({ isVisible, isComplete }: Props) {
  const [currentStage, setCurrentStage] = useState(0);

  useEffect(() => {
    if (!isVisible) {
      setCurrentStage(0);
      return;
    }
    if (isComplete) {
      setCurrentStage(4);
      return;
    }

    // Timed progression – works for both sample and CSV audits
    const timers: ReturnType<typeof setTimeout>[] = [];
    timers.push(setTimeout(() => setCurrentStage(1), 500));
    timers.push(setTimeout(() => setCurrentStage(2), 1000));
    timers.push(setTimeout(() => setCurrentStage(3), 1500));
    timers.push(setTimeout(() => setCurrentStage(4), 2000));

    return () => timers.forEach(clearTimeout);
  }, [isVisible, isComplete]);

  if (!isVisible) return null;

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(7, 7, 8, 0.8)',
        backdropFilter: 'blur(20px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 9999,
      }}
    >
      <div
        className="audit-modal"
        style={{
          background: '#191A1C',
          padding: '40px',
          borderRadius: theme.rounded.container,
          width: '600px',
          border: `1px solid ${theme.colors.divider}`,
          borderTop: `1px solid rgba(255,255,255,0.05)`,
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
        }}
      >
        <h2
          style={{
            ...theme.typography.h3,
            margin: '0 0 32px 0',
            color: theme.colors.onBackground,
          }}
        >
          Running Spend Audit
        </h2>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {STAGES.map((stage) => {
            const isActive = currentStage === stage.id;
            const isDone = currentStage > stage.id;
            const isVisibleItem = currentStage >= stage.id;

            return (
              <div
                key={stage.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '16px',
                  opacity: isVisibleItem ? 1 : 0.3,
                  transition: 'all 0.3s ease',
                }}
              >
                {/* Status icon */}
                <div
                  style={{
                    width: '24px',
                    height: '24px',
                    borderRadius: '50%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: isDone
                      ? 'transparent'
                      : isActive
                        ? theme.colors.buttonPrimaryBg
                        : theme.colors.surfaceBright,
                    border: isDone ? `1px solid ${theme.colors.outline}` : 'none',
                    color: isDone ? theme.colors.outline : '#FFFFFF',
                    ...theme.typography.labelSm,
                    flexShrink: 0,
                    transition: 'background 0.3s ease, border 0.3s ease',
                  }}
                >
                  {isDone ? '✅' : isActive ? '...' : ''}
                </div>

                {/* Label + AI badge */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    flexGrow: 1,
                  }}
                >
                  <span
                    style={{
                      ...theme.typography.bodyMd,
                      color: isActive
                        ? theme.colors.onBackground
                        : isDone
                          ? theme.colors.outline
                          : theme.colors.outlineVariant,
                      fontWeight: isActive ? 500 : 400,
                      transition: 'color 0.3s ease',
                    }}
                  >
                    {stage.text}
                  </span>

                  {stage.tier && (
                    <span
                      style={{
                        background: `${theme.colors.primary}15`,
                        color: theme.colors.primary,
                        padding: '2px 8px',
                        borderRadius: theme.rounded.sm,
                        ...theme.typography.labelSm,
                      }}
                    >
                      {stage.tier}
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}