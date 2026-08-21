export default function Footer() {
  return (
    <footer style={styles.footer}>
      <span>Profit Max Trading Systems © {new Date().getFullYear()}</span>
      <span style={styles.status}>
        <span style={styles.indicator}></span> System Operational
      </span>
    </footer>
  );
}

const styles = {
  footer: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '0.75rem 2rem',
    backgroundColor: '#0f172a',
    borderTop: '1px solid #1e293b',
    color: '#64748b',
    fontSize: '0.85rem',
  },
  status: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.4rem',
  },
  indicator: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    backgroundColor: '#22c55e',
  },
};