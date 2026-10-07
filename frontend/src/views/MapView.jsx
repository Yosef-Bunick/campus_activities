import { lazy, Suspense, useLayoutEffect, useMemo, useRef, useState } from 'react';
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
import { useAuth } from '../contexts/AuthContext';
import { toApiParams, useFilter } from '../contexts/FilterContext';
import { useEvents, useRooms } from '../hooks/useEvents';
import { roomLabel } from '../lib/labels';
import { addDays, nyDateKey, nyToDate } from '../lib/time';

const FilterSheet = lazy(() => import('../components/FilterSheet'));
const RoomLimit = lazy(() => import('../components/RoomLimit'));
const MAP_SRC = '/maps/campus.webp'; // WCC_MAP2.png; pins are 0..1 of its width/height
const MAP_RATIO = 892 / 590;
const MAX_ZOOM = 5;

// Campus map: each room's pin shows how many events match the shared filter.
// Tap a room to see its events. Floor-plan SVGs come later, per floor.
export default function MapView() {
  const { filter, active } = useFilter();
  const { can } = useAuth();
  const [when, setWhen] = useState('today'); // 'now' | 'today'
  const [zoom, setZoom] = useState(1); // 1 = whole map fits the screen; up to MAX_ZOOM
  const [room, setRoom] = useState(null);
  const [filterOpen, setFilterOpen] = useState(false);
  const pinch = useRef(null);
  const viewportRef = useRef(null);
  const anchor = useRef(null); // map point under the screen centre, kept there while zooming
  const { data: rooms = [] } = useRooms();

  // Never below "fits the screen" (1), never past MAX_ZOOM.
  const zoomTo = (z) => {
    const el = viewportRef.current;
    const next = z < 1.01 ? 1 : Math.min(MAX_ZOOM, z); // snap float drift back to "fit"
    if (!el || next === zoom) return;
    const box = el.firstElementChild;
    if (box.offsetWidth) {
      anchor.current = {
        x: (el.scrollLeft + el.clientWidth / 2 - box.offsetLeft) / box.offsetWidth,
        y: (el.scrollTop + el.clientHeight / 2 - box.offsetTop) / box.offsetHeight,
      };
    }
    setZoom(next);
  };

  // After a zoom, scroll so the same spot stays in the middle of the screen.
  useLayoutEffect(() => {
    const el = viewportRef.current;
    const a = anchor.current;
    if (!el || !a) return;
    const box = el.firstElementChild;
    el.scrollLeft = box.offsetLeft + a.x * box.offsetWidth - el.clientWidth / 2;
    el.scrollTop = box.offsetTop + a.y * box.offsetHeight - el.clientHeight / 2;
    anchor.current = null;
  }, [zoom]);

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
  // Off-campus and online events have no pin; they get their own list (ADR-032).
  const elsewhere = useMemo(
    () => (query.data || []).filter((e) => !e.room && e.status !== 'rejected'),
    [query.data],
  );
  const [elsewhereOpen, setElsewhereOpen] = useState(false);

  // Two-finger pinch zooms the map only (one finger still scrolls it).
  const dist = (t) => Math.hypot(t[0].clientX - t[1].clientX, t[0].clientY - t[1].clientY);
  const onTouchStart = (e) => { if (e.touches.length === 2) pinch.current = { d: dist(e.touches), z: zoom }; };
  const onTouchMove = (e) => {
    if (e.touches.length === 2 && pinch.current) {
      zoomTo(pinch.current.z * (dist(e.touches) / pinch.current.d));
    }
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
      {elsewhere.length > 0 && (
        <Button size="small" onClick={() => setElsewhereOpen(true)} sx={{ mx: 1.5, mb: 1, alignSelf: 'flex-start' }}>
          Off campus &amp; online ({elsewhere.length})
        </Button>
      )}

      <Box sx={{ position: 'relative', flex: 1, minHeight: 0 }}>
        <Box
          ref={viewportRef}
          data-testid="map-viewport"
          onTouchStart={onTouchStart} onTouchMove={onTouchMove} onTouchEnd={onTouchEnd}
          sx={{
            position: 'absolute', inset: 0, display: 'flex', touchAction: 'pan-x pan-y', bgcolor: (t) => (t.palette.mode === 'dark' ? '#1d2619' : '#cfe3b4') /* map's grass colour, dimmed in dark mode */,
            // Size container: the map's fitted width comes from CSS (cqw/cqh), so it
            // re-fits on every resize/rotation with no JS measuring. No scrollbars at fit.
            containerType: 'size', overflow: zoom > 1 ? 'auto' : 'hidden',
          }}
        >
          {/* Fitted width = min(container width, container height / MAP_RATIO), times zoom;
              margin auto centres it while it's smaller than the screen. */}
          <Box sx={{
            position: 'relative', flexShrink: 0, margin: 'auto', aspectRatio: `1 / ${MAP_RATIO}`,
            width: `calc(${zoom} * min(100cqw, ${100 / MAP_RATIO}cqh))`,
          }}>
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
          <IconButton aria-label="Zoom in" onClick={() => zoomTo(zoom * 1.4)}><AddIcon /></IconButton>
          <IconButton aria-label="Zoom out" onClick={() => zoomTo(zoom / 1.4)}><RemoveIcon /></IconButton>
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
            {can('map.manage') && (
              <Suspense fallback={null}><RoomLimit room={room} onSaved={setRoom} /></Suspense>
            )}
            <Button onClick={() => setRoom(null)}>Close</Button>
          </Box>
        )}
      </Drawer>
      <Drawer anchor="bottom" open={elsewhereOpen} onClose={() => setElsewhereOpen(false)}
        PaperProps={{ sx: { borderTopLeftRadius: 16, borderTopRightRadius: 16, maxHeight: '75dvh' } }}>
        <Box sx={{ p: 2, pb: 'calc(16px + env(safe-area-inset-bottom))', display: 'flex', flexDirection: 'column', gap: 1 }}>
          <Typography variant="h6" component="h2">Off campus &amp; online</Typography>
          <EventList query={{ ...query, data: elsewhere }} grouped={false} empty="Nothing off campus or online." />
          <Button onClick={() => setElsewhereOpen(false)}>Close</Button>
        </Box>
      </Drawer>
      <Suspense fallback={null}>
        {filterOpen && <FilterSheet open onClose={() => setFilterOpen(false)} />}
      </Suspense>
    </Box>
  );
}
