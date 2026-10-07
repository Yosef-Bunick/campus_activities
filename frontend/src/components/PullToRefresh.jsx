import Box from '@mui/material/Box';
import CircularProgress from '@mui/material/CircularProgress';
import { PULL_THRESHOLD, usePullToRefresh } from '../hooks/usePullToRefresh';

const SIZE = 36;
const REST = 16; // where the spinner sits while refreshing

// Wraps a page: pull down from the top to refresh. The indicator floats over
// the content (absolute, zero height), so the layout never shifts and fixed
// things like the tab bar and the New event button stay put.
export default function PullToRefresh({ onRefresh, children }) {
  const { ref, pull, refreshing } = usePullToRefresh(onRefresh);
  const shown = refreshing || pull > 0;
  const y = refreshing ? REST : Math.min(pull, PULL_THRESHOLD * 1.3) - SIZE;

  return (
    <Box ref={ref} sx={{ position: 'relative' }}>
      <Box
        role="status"
        aria-label={refreshing ? 'Refreshing' : 'Pull to refresh'}
        aria-hidden={!shown}
        style={{ transform: `translate(-50%, ${y}px)`, opacity: shown ? 1 : 0 }}
        sx={{
          position: 'absolute', top: 0, left: '50%', zIndex: 1, pointerEvents: 'none',
          width: SIZE, height: SIZE, borderRadius: '50%', bgcolor: 'background.paper', boxShadow: 2,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          // Follow the finger exactly; animate only the snap back / settle.
          transition: pull > 0 ? 'none' : 'transform 200ms ease, opacity 200ms ease',
          '@media (prefers-reduced-motion: reduce)': {
            transform: `translate(-50%, ${REST}px) !important`, transition: 'none',
          },
        }}
      >
        {refreshing
          ? <CircularProgress size={20} />
          : <CircularProgress size={20} variant="determinate" value={Math.min(100, (pull / PULL_THRESHOLD) * 100)} />}
      </Box>
      {children}
    </Box>
  );
}
