import { Routes, Route, Navigate, useLocation, Link } from 'react-router-dom';
import { theme } from './styles/theme';
import DashboardView from './components/DashboardView';
import FlagsView from './components/FlagsView';
import DraftsView from './components/DraftsView';
import LandingPage from './components/LandingPage';

function DashboardLayout() {
  const location = useLocation();
  const currentPath = location.pathname;

  const tabs = [
    { id: '/dashboard', label: 'Overview' },
    { id: '/dashboard/flags', label: 'Flags' },
    { id: '/dashboard/drafts', label: 'Drafts' },
  ];

  return (
    <div style={{ minHeight: '100vh', backgroundColor: theme.colors.background, color: theme.colors.onBackground }}>
      <main style={{ maxWidth: '1000px', margin: '0 auto', padding: '40px 24px 80px' }}>
        <header style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'baseline',
          marginBottom: '64px',
          position: 'relative'
        }}>
          <div className="nav-container">
            <Link to="/" style={{ 
              ...theme.typography.labelSm,
              color: theme.colors.onBackground,
              textDecoration: 'none',
              letterSpacing: '0.05em',
              textTransform: 'uppercase'
            }}>
              Spend Guardian
            </Link>
            <nav style={{ display: 'flex', gap: '24px' }}>
              {tabs.map(tab => {
                const isActive = currentPath === tab.id || (tab.id === '/dashboard' && currentPath === '/dashboard/');
                return (
                  <Link
                    key={tab.id}
                    to={tab.id}
                    style={{
                      textDecoration: 'none',
                      ...theme.typography.bodyMd,
                      fontWeight: isActive ? 600 : 400,
                      color: isActive ? theme.colors.onBackground : theme.colors.outline,
                      padding: 0,
                      transition: 'color 0.2s ease'
                    }}
                  >
                    {tab.label}
                  </Link>
                );
              })}
            </nav>
          </div>
        </header>

        <Routes>
          <Route path="/" element={<DashboardView />} />
          <Route path="/flags" element={<FlagsView />} />
          <Route path="/drafts" element={<DraftsView />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/dashboard/*" element={<DashboardLayout />} />
    </Routes>
  );
}
