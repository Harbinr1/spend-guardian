import { Link } from 'react-router-dom';
import { theme } from '../styles/theme';

export default function LandingPage() {
  return (
    <div style={{
      minHeight: '100vh',
      backgroundColor: theme.colors.background,
      color: theme.colors.onBackground,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '0 24px',
      position: 'relative',
      overflow: 'hidden'
    }}>
      {/* Background Glows for Cinematic Feel */}
      <div style={{
        position: 'absolute',
        top: '-10%',
        left: '-10%',
        width: '40%',
        height: '40%',
        background: 'radial-gradient(circle, rgba(94, 107, 255, 0.05) 0%, rgba(7, 7, 8, 0) 70%)',
        filter: 'blur(60px)',
        zIndex: 0
      }} />
      <div style={{
        position: 'absolute',
        bottom: '-10%',
        right: '-10%',
        width: '40%',
        height: '40%',
        background: 'radial-gradient(circle, rgba(80, 216, 233, 0.03) 0%, rgba(7, 7, 8, 0) 70%)',
        filter: 'blur(60px)',
        zIndex: 0
      }} />

      <div style={{ zIndex: 1, maxWidth: '800px', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <h1 className="hero-text" style={{
          ...theme.typography.h1,
          marginBottom: theme.spacing.lg,
          background: `linear-gradient(180deg, ${theme.colors.onBackground} 0%, rgba(229, 226, 227, 0.6) 100%)`,
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
        }}>
          Spend Guardian
        </h1>
        
        <h2 style={{
          ...theme.typography.h3,
          color: theme.colors.outline,
          maxWidth: '600px',
          marginBottom: '64px',
          fontWeight: 400
        }}>
          Automated precision for high-stakes business operations. 
          Detect overlap, eliminate duplicate waste, and regain control.
        </h2>

        <Link to="/dashboard" className="touch-target" style={{
          textDecoration: 'none',
          backgroundColor: theme.colors.buttonPrimaryBg,
          color: theme.colors.buttonPrimaryText,
          padding: '16px 32px',
          width: '100%',
          maxWidth: '300px',
          borderRadius: theme.rounded.default,
          ...theme.typography.bodyLg,
          fontWeight: 500,
          border: `1px solid ${theme.colors.buttonPrimaryBg}`,
          boxShadow: '0 0 20px rgba(94, 107, 255, 0.2)',
          transition: 'all 0.2s ease-in-out',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.transform = 'translateY(-2px)';
          e.currentTarget.style.boxShadow = '0 0 30px rgba(94, 107, 255, 0.4)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = 'translateY(0)';
          e.currentTarget.style.boxShadow = '0 0 20px rgba(94, 107, 255, 0.2)';
        }}
        >
          Enter Workspace
        </Link>
      </div>

      <div style={{
        position: 'absolute',
        bottom: theme.spacing.xl,
        color: theme.colors.outlineVariant,
        ...theme.typography.labelSm,
        textTransform: 'uppercase',
        letterSpacing: '0.1em'
      }}>
        System Status: Online
      </div>
    </div>
  );
}
