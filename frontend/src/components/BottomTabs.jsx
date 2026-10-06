// Icons: per-icon ESM files (not the barrel, not the CJS deep path), so dev, tests and build all load only these.
import Paper from '@mui/material/Paper';
import BottomNavigation from '@mui/material/BottomNavigation';
import BottomNavigationAction from '@mui/material/BottomNavigationAction';
import HomeIcon from '@mui/icons-material/esm/HomeOutlined';
import CalendarIcon from '@mui/icons-material/esm/CalendarMonthOutlined';
import MapIcon from '@mui/icons-material/esm/MapOutlined';
import FavoritesIcon from '@mui/icons-material/esm/StarBorder';
import AlertsIcon from '@mui/icons-material/esm/NotificationsNoneOutlined';
import { useLocation } from 'wouter';

export const TABS = [
  { path: '/home', label: 'Home', Icon: HomeIcon },
  { path: '/calendar', label: 'Calendar', Icon: CalendarIcon },
  { path: '/map', label: 'Map', Icon: MapIcon },
  { path: '/favorites', label: 'Favorites', Icon: FavoritesIcon },
  { path: '/alerts', label: 'Alerts', Icon: AlertsIcon },
];

export const TAB_BAR_HEIGHT = 56;

// Phone layout: Home · Calendar · Map · Favorites · Alerts (architecture §3).
export default function BottomTabs() {
  const [location, navigate] = useLocation();
  const value = TABS.some((t) => t.path === location) ? location : false;
  return (
    <Paper
      component="nav"
      elevation={3}
      sx={{ position: 'fixed', left: 0, right: 0, bottom: 0, pb: 'env(safe-area-inset-bottom)', zIndex: 'appBar' }}
    >
      <BottomNavigation value={value} onChange={(_, path) => navigate(path)} showLabels sx={{ height: TAB_BAR_HEIGHT }}>
        {TABS.map(({ path, label, Icon }) => (
          <BottomNavigationAction key={path} value={path} label={label} icon={<Icon />} sx={{ minWidth: 0 }} />
        ))}
      </BottomNavigation>
    </Paper>
  );
}
