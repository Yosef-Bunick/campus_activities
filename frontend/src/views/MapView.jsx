import { lazy, Suspense, useMemo, useRef, useState } from 'react';
import Badge from '@mui/material/Badge';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import ButtonBase from '@mui/material/ButtonBase';
import Drawer from '@mui/material/Drawer';
import IconButton from '@mui/material/IconButton';
import Paper from '@mui/material/Paper';
import ToggleButton from '@mui/material/ToggleButton';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';
import Typography from '@mui/material/Typography';
import AddIcon from '@mui/icons-material/esm/Add';
import RemoveIcon from '@mui/icons-material/esm/Remove';
import FilterIcon from '@mui/icons-material/esm/FilterList';
import EventList from '../components/EventList';
import { TAB_BAR_HEIGHT } from '../components/BottomTabs';
import { toApiParams, useFilter } from '../contexts/FilterContext';
import { useEvents, useRooms } from '../hooks/useEvents';
import { roomLabel } from '../lib/labels';
import { addDays, nyDateKey, nyToDate } from '../lib/time';

const FilterSheet = lazy(() => import('../components/FilterSheet'));
const MAP_SRC = '/maps/campus.webp'; // WCC_MAP2.png; pins are 0..1 of its width/height
const MAP_RATIO = 892 / 590;
const MIN_ZOOM = 1;
const MAX_ZOOM = 5;
const clamp = (z) => Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, z));

// Campus map: each room's pin shows how many events match the shared filter.
// Tap a room to see its events. Floor-plan SVGs come later, per floor.
export default function MapView() {
  const { filter, active } = useFilter();
  const [when, setWhen] = useState('today'); // 'now' | 'today'
  const [zoom, setZoom] = useState(1.6);
  const [room, setRoom] = useState(null);
  const [filterOpen, setFilterOpen] = useState(false);
  const pinch = useRef(null);
  const { data: rooms = [] } = useRooms();

  const params = useMemo(() => {
    const p = toApiParams(filter);
    if (when === 'now') p.set('happening_now', 'true');
    else p.set('end', nyToDate(addDays(nyDateKey(), 1)).toISOString());
    return p;
  }, [filter, when]);
  const query = useEvents(params);
  const byRoom = useMemo(() => {
    const m = new Map();
    for (const e of query.data || []) {
      if (e.status !== 'active' || !e.room) continue;
      m.set(e.room.id, [...(m.get(e.room.id) || []), e]);
    }
    return m;
  }, [query.data]);

  // Two-finger pinch zooms the map only (one finger still scrolls it).
  const dist = (t) => Math.hypot(t[0].clientX - t[1].clientX, t[0].clientY - t[1].clientY);
  const onTouchStart = (e) => { if (e.touches.length === 2) pinch.current = { d: dist(e.touches), z: zoom }; };
  const onTouchMove = (e) => {
    if (e.touches.length === 2 && pinch.current) setZoom(clamp(pinch.current.z * (dist(e.touches) / pinch.current.d)));
  };
  const onTouchEnd = () => { pinch.current = null; };

  const pinned = rooms.filter((r) => r.map_x != null && r.map_y != null);
  const roomEvents = room ? { ...query, data: byRoom.get(room.id) || [] } : null;

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: `calc(100dvh - 48px - ${TAB_BAR_HEIGHT}px - env(safe-area-inset-bottom) - env(safe-area-inset-top))` }}>
      <Box sx={{ p: 1.5, display: 'flex', alignItems: 'center', gap: 1 }}>
        <Typography variant="h5" component="h1" sx={{ flexGrow: 1 }}>Map</Typography>
        <ToggleButtonGroup exclusive size="small" value={when} onChange={(_, v) => v && setWhen(v)}>
          <ToggleButton value="now">Now</ToggleButton>
          <ToggleButton value="today">Today</ToggleButton>
        </ToggleButtonGroup>
        <Badge color="secondary" variant="dot" invisible={!active}>
          <IconButton aria-label="Filter" onClick={() => setFilterOpen(true)}><FilterIcon /></IconButton>
        </Badge>
      </Box>

      <Box sx={{ position: 'relative', flex: 1, minHeight: 0 }}>
        <Box
          data-testid="map-viewport"
          onTouchStart={onTouchStart} onTouchMove={onTouchMove} onTouchEnd={onTouchEnd}
          sx={{ position: 'absolute', inset: 0, overflow: 'auto', touchAction: 'pan-x pan-y', bgcolor: '#cfe3b4' }}
        >
          <Box sx={{ position: 'relative', width: `${zoom * 100}%`, aspectRatio: `1 / ${MAP_RATIO}` }}>
            <Box component="img" src={MAP_SRC} alt="Campus map" draggable={false}
              sx={{ width: '100%', height: '100%', display: 'block', userSelect: 'none' }} />
            {pinned.map((r) => {
              const count = byRoom.get(r.id)?.length || 0;
              return (
                <ButtonBase
                  key={r.id}
                  onClick={() => setRoom(r)}
                  aria-label={`${roomLabel(r)}: ${count} event${count === 1 ? '' : 's'}`}
                  sx={{
                    position: 'absolute', left: `${r.map_x * 100}%`, top: `${r.map_y * 100}%`,
                    transform: 'translate(-50%, -50%)', minWidth: 28, height: 28, px: 0.75, borderRadius: 14,
                    bgcolor: count ? 'error.main' : 'grey.600', color: '#fff', fontWeight: 700, fontSize: 13,
                    border: '2px solid #fff', boxShadow: 2,
                  }}
                >
                  {count || r.name}
                </ButtonBase>
              );
            })}
          </Box>
        </Box>
        <Paper sx={{ position: 'absolute', right: 12, bottom: 12, display: 'flex', flexDirection: 'column' }}>
          <IconButton aria-label="Zoom in" onClick={() => setZoom((z) => clamp(z * 1.4))}><AddIcon /></IconButton>
          <IconButton aria-label="Zoom out" onClick={() => setZoom((z) => clamp(z / 1.4))}><RemoveIcon /></IconButton>
        </Paper>
      </Box>

      <Drawer anchor="bottom" open={Boolean(room)} onClose={() => setRoom(null)}
        PaperProps={{ sx: { borderTopLeftRadius: 16, borderTopRightRadius: 16, maxHeight: '75dvh' } }}>
        {room && (
          <Box sx={{ p: 2, pb: 'calc(16px + env(safe-area-inset-bottom))', display: 'flex', flexDirection: 'column', gap: 1 }}>
            <Typography variant="h6" component="h2">{roomLabel(room)}</Typography>
            <Typography variant="body2" color="text.secondary">
              {room.floor != null && `Floor ${room.floor} · `}{when === 'now' ? 'Happening now' : 'Rest of today'}
            </Typography>
            <EventList query={roomEvents} grouped={false} empty="Nothing here right now." />
            <Button onClick={() => setRoom(null)}>Close</Button>
          </Box>
        )}
      </Drawer>
      <Suspense fallback={null}>
        {filterOpen && <FilterSheet open onClose={() => setFilterOpen(false)} />}
      </Suspense>
    </Box>
  );
}
