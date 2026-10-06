import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';

// Milestone 0 placeholder body for a page.
export default function PageStub({ title, children }) {
  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h5" component="h1" gutterBottom>{title}</Typography>
      <Typography variant="body2" color="text.secondary">{children}</Typography>
    </Box>
  );
}
