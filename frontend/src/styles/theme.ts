export const theme = {
  colors: {
    surface: '#131314',
    surfaceDim: '#131314',
    surfaceBright: '#3a393a',
    surfaceContainerLowest: '#0e0e0f',
    surfaceContainerLow: '#1c1b1d',
    surfaceContainer: '#201f21',
    surfaceContainerHigh: '#2a2a2b',
    surfaceContainerHighest: '#353436',
    onSurface: '#e5e2e3',
    onSurfaceVariant: '#c6c5d8',
    inverseSurface: '#e5e2e3',
    inverseOnSurface: '#313031',
    outline: '#8f8fa1',
    outlineVariant: '#454655',
    surfaceTint: '#bec2ff',
    primary: '#bec2ff',
    onPrimary: '#000ba6',
    primaryContainer: '#7a85ff',
    onPrimaryContainer: '#000992',
    inversePrimary: '#3d4ae0',
    secondary: '#50d8e9',
    onSecondary: '#00363c',
    secondaryContainer: '#00b1c2',
    onSecondaryContainer: '#003e44',
    tertiary: '#ffb689',
    onTertiary: '#512300',
    tertiaryContainer: '#e0731d',
    onTertiaryContainer: '#471e00',
    error: '#ffb4ab',
    onError: '#690005',
    errorContainer: '#93000a',
    onErrorContainer: '#ffdad6',
    background: '#070708', // Primary Canvas
    panelBg: '#101112', // Layering
    panelBgHover: '#151617', // Hover state layer
    onBackground: '#e5e2e3',
    divider: '#1b1c1e',
    structuralBorder: '#232426',
    buttonPrimaryBg: '#5e6bff',
    buttonPrimaryText: '#f0f1f2',
    buttonGhostText: '#9a9da3'
  },
  typography: {
    h1: {
      fontFamily: "'Manrope', sans-serif",
      fontSize: '48px',
      fontWeight: 520,
      lineHeight: 1.1,
      letterSpacing: '-0.05em'
    },
    h2: {
      fontFamily: "'Manrope', sans-serif",
      fontSize: '32px',
      fontWeight: 520,
      lineHeight: 1.2,
      letterSpacing: '-0.05em'
    },
    h3: {
      fontFamily: "'Manrope', sans-serif",
      fontSize: '24px',
      fontWeight: 520,
      lineHeight: 1.2,
      letterSpacing: '-0.04em'
    },
    h4: {
      fontFamily: "'Manrope', sans-serif",
      fontSize: '18px',
      fontWeight: 520,
      lineHeight: 1.4,
      letterSpacing: '-0.02em'
    },
    bodyLg: {
      fontFamily: "'Inter', sans-serif",
      fontSize: '16px',
      fontWeight: 400,
      lineHeight: 1.6,
      letterSpacing: '0em'
    },
    bodyMd: {
      fontFamily: "'Inter', sans-serif",
      fontSize: '14px',
      fontWeight: 400,
      lineHeight: 1.5,
      letterSpacing: '0em'
    },
    labelSm: {
      fontFamily: "'Inter', sans-serif",
      fontSize: '12px',
      fontWeight: 500,
      lineHeight: 1,
      letterSpacing: '0.02em'
    },
    monoData: {
      fontFamily: "'Inter', monospace", // We'll use Inter tabular numbers instead of actual monospace if we can, but fallback to Inter for simplicity per DESIGN.md: "mono-data (Inter with tabular lining figures)"
      fontSize: '13px',
      fontWeight: 400,
      lineHeight: 1,
      letterSpacing: '-0.01em',
      fontFeatureSettings: "'tnum' on, 'lnum' on"
    }
  },
  rounded: {
    sm: '0.125rem',
    default: '0.25rem', // 4px
    md: '0.375rem',
    container: '8px',
    lg: '0.5rem',
    xl: '0.75rem',
    full: '9999px'
  },
  spacing: {
    base: '4px',
    xs: '4px',
    sm: '8px',
    md: '16px',
    lg: '24px',
    xl: '40px',
    gutter: '20px',
    marginSafe: '32px'
  }
};
