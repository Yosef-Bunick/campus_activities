// Icons: per-icon ESM files (not the barrel, not the CJS deep path), so dev, tests and build all load only these.
import Badge from '@mui/material/Badge';
import Paper from '@mui/material/Paper';
import BottomNavigation from '@mui/material/BottomNavigation';
import BottomNavigationAction from '@mui/material/BottomNavigationAction';
import HomeIcon from '@mui/icons-material/esm/HomeOutlined';
import CalendarIcon from '@mui/icons-material/esm/CalendarMonthOutlined';
import MapIcon from '@mui/icons-material/esm/MapOutlined';
import FavoritesIcon from '@mui/icons-material/esm/StarBorder';
import AlertsIcon from '@mui/icons-material/esm/NotificationsNoneOutlined';
import { useQuery } from '@tanstack/react-query';
import { useLocation } from 'wouter';
import { apiGet } from '../api';

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
  // Unread alerts badge, polled like the event feeds (every 60 s).
  const { data: alerts } = useQuery({
    queryKey: ['alerts-unread'], queryFn: () => apiGet('/alerts/unread'), refetchInterval: 60000,
  });
  const unread = alerts?.unread ?? 0;
  const value = TABS.some((t) => t.path === location) ? location : false;
  return (
    <Paper
      component="nav"
      elevation={3}
      sx={{ position: 'fixed', left: 0, right: 0, bottom: 0, pb: 'env(safe-area-inset-bottom)', zIndex: 'appBar' }}
    >
      <BottomNavigation value={value} onChange={(_, path) => navigate(path)} showLabels sx={{ height: TAB_BAR_HEIGHT }}>
        {TABS.map(({ path, label, Icon }) => (
          <BottomNavigationAction
            key={path} value={path} label={label} sx={{ minWidth: 0 }}
            aria-label={path === '/alerts' && unread ? `${label}, ${unread} unread` : label}
            icon={path === '/alerts'
              ? <Badge color="error" badgeContent={unread} max={99}><Icon /></Badge>
              : <Icon />}
          />
        ))}
      </BottomNavigation>
    </Paper>
  );
}
