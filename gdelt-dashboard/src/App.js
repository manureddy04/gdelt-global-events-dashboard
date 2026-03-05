import React, { useEffect, useState, useRef } from "react";
import axios from "axios";
import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Popup,
  useMap
} from "react-leaflet";
import L from "leaflet";
import "leaflet.heat";
import {
  Box,
  Drawer,
  Typography,
  TextField,
  Slider,
  Button,
  Switch
} from "@mui/material";

function HeatmapLayer({ events }) {
  const map = useMap();
  const heatLayerRef = useRef(null);

  useEffect(() => {
    if (!map) return;

    if (heatLayerRef.current) {
      map.removeLayer(heatLayerRef.current);
    }

    const heatData = events.map(e => [
      e.lat,
      e.lon,
      Math.abs(e.goldstein)
    ]);

    heatLayerRef.current = L.heatLayer(heatData, {
      radius: 25,
      blur: 20,
      maxZoom: 5
    }).addTo(map);

  }, [events, map]);

  return null;
}

function App() {
  const [events, setEvents] = useState([]);
  const [year, setYear] = useState(2013);
  const [search, setSearch] = useState("");
  const [heatMode, setHeatMode] = useState(false);
  const [autoPlay, setAutoPlay] = useState(false);

  useEffect(() => {
    axios
      .get(`http://127.0.0.1:8000/events-by-year?year=${year}`)
      .then(res => setEvents(res.data))
      .catch(err => console.error(err));
  }, [year]);

  // Timeline animation
  useEffect(() => {
    if (!autoPlay) return;

    const interval = setInterval(() => {
      setYear(prev => (prev >= 2013 ? 2003 : prev + 1));
    }, 1500);

    return () => clearInterval(interval);
  }, [autoPlay]);

  return (
    <Box sx={{ display: "flex", height: "100vh", background: "#121212" }}>

      {/* LEFT PANEL */}
      <Drawer
        variant="permanent"
        sx={{
          width: 280,
          "& .MuiDrawer-paper": {
            width: 280,
            background: "#1e1e1e",
            color: "white",
            padding: 3,
          },
        }}
      >
        <Typography variant="h6">🌍 World Changes Explorer</Typography>

        <TextField
          label="Search Country"
          variant="outlined"
          size="small"
          sx={{ mt: 3 }}
          fullWidth
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />

        <Typography sx={{ mt: 4 }}>Select Year: {year}</Typography>
        <Slider
          min={2003}
          max={2026}
          value={year}
          onChange={(e, val) => setYear(val)}
          sx={{ color: "#ff4d4d" }}
        />

        <Typography sx={{ mt: 3 }}>Heatmap Mode</Typography>
        <Switch
          checked={heatMode}
          onChange={() => setHeatMode(!heatMode)}
        />

        <Typography sx={{ mt: 3 }}>Auto Play Timeline</Typography>
        <Switch
          checked={autoPlay}
          onChange={() => setAutoPlay(!autoPlay)}
        />
      </Drawer>

      {/* MAP */}
      <Box sx={{ flexGrow: 1 }}>
        <MapContainer
          center={[20, 0]}
          zoom={2}
          style={{ height: "100%", width: "100%" }}
        >
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {heatMode ? (
            <HeatmapLayer events={events} />
          ) : (
            events
              .filter(e =>
                e.country.toLowerCase().includes(search.toLowerCase())
              )
              .map((event, index) => (
                <CircleMarker
                  key={index}
                  center={[event.lat, event.lon]}
                  radius={6}
                  pathOptions={{
                    color: event.goldstein < 0 ? "red" : "lime",
                  }}
                >
                  <Popup>
                    <strong>{event.country}</strong>
                    <br />
                    Goldstein: {event.goldstein}
                  </Popup>
                </CircleMarker>
              ))
          )}
        </MapContainer>
      </Box>

      {/* RIGHT PANEL */}
      <Drawer
        variant="permanent"
        anchor="right"
        sx={{
          width: 280,
          "& .MuiDrawer-paper": {
            width: 280,
            background: "#1e1e1e",
            color: "white",
            padding: 3,
          },
        }}
      >
        <Typography variant="h6">📊 Event Summary</Typography>
        <Typography sx={{ mt: 2 }}>
          Total Events: {events.length}
        </Typography>
        <Typography>
          Conflict: {events.filter(e => e.goldstein < 0).length}
        </Typography>
        <Typography>
          Cooperation: {events.filter(e => e.goldstein > 0).length}
        </Typography>
      </Drawer>
    </Box>
  );
}

export default App;