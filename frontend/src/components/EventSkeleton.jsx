import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import Skeleton from '@mui/material/Skeleton';

// Grey placeholder cards shaped like EventCard, so pages feel instant while
// events load instead of showing a spinner (ADR-033).
export default function EventSkeleton({ count = 3 }) {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }} aria-busy="true" aria-label="Loading events">
      {Array.from({ length: count }, (_, i) => (
        <Card key={i} variant="outlined" sx={{ p: 1.5 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 1 }}>
            <Skeleton variant="text" width="55%" height={26} />
            <Skeleton variant="rounded" width={56} height={22} />
          </Box>
          <Skeleton variant="text" width="80%" />
        </Card>
      ))}
    </Box>
  );
}
