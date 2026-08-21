import { Link, useLocation } from 'react-router-dom';

export default function Navbar() {
  const location = useLocation();

  const isActive = (path: string) => location.pathname === path;

  return (
    <header style={styles.header}>
      <div style={styles.brand}>
        <span style={styles.logoText}>Profit Max</span>
        <span style={styles.badge}>PROD</span>
      </div>
      <nav style={styles.nav}>
        <Link
          to="/"
          style={{
            ...styles.link,
            ...(isActive('/') ? styles.activeLink : {}),
          }}
        >
          Dashboard
        </Link>
        <Link
          to="/trades"
          style={{
            ...styles.link,
            ...(isActive('/trades') ? styles.activeLink : {}),
          }}
        >
          Trade History
        </Link>
      </nav>
    </header>
  );
}

const styles = {
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '0.75rem 2rem',
    backgroundColor: '#0f172a',
    borderBottom: '1px solid #1e293b',
    color: '#f8fafc',
  },
  brand: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    fontWeight: 'bold',
    fontSize: '1.25rem',
  },
  logoText: {
    color: '#38bdf8',
  },
  badge: {
    fontSize: '0.65rem',
    padding: '0.1rem 0.4rem',
    backgroundColor: '#0369a1',
    borderRadius: '4px',
    color: '#e0f2fe',
  },
  nav: {
    display: 'flex',
    gap: '1.5rem',
  },
  link: {
    color: '#94a3b8',
    textDecoration: 'none',
    fontWeight: 500,
    fontSize: '0.95rem',
    transition: 'color 0.2s',
  },
  activeLink: {
    color: '#38bdf8',
    borderBottom: '2px solid #38bdf8',
    paddingBottom: '0.2rem',
  },
};