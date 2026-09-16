import { useEffect, useState } from "react";
import { MapContainer, Marker, TileLayer, useMapEvents, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";

// bundlers quebram o caminho padrao dos icones do Leaflet — aponta pros
// arquivos que o Vite ja processou como URL.
const markerImage = L.icon({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

const SERTAO_CENTRAL: [number, number] = [-5.2, -40.6];

function ClickToPlace({ onPick }: { onPick: (lat: number, lng: number) => void }) {
  useMapEvents({
    click(e) {
      onPick(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
}

function FlyTo({ position }: { position: [number, number] | null }) {
  const map = useMap();
  useEffect(() => {
    if (position) map.flyTo(position, 12);
  }, [position, map]);
  return null;
}

interface Props {
  lat: number | null;
  lng: number | null;
  onChange: (lat: number, lng: number) => void;
  height?: number;
}

export function MapPicker({ lat, lng, onChange, height = 320 }: Props) {
  const [search, setSearch] = useState("");
  const [searching, setSearching] = useState(false);
  const [flyTarget, setFlyTarget] = useState<[number, number] | null>(null);
  const [searchError, setSearchError] = useState<string | null>(null);

  const position: [number, number] | null = lat != null && lng != null ? [lat, lng] : null;

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!search.trim()) return;
    setSearching(true);
    setSearchError(null);
    try {
      const url = `https://photon.komoot.io/api/?q=${encodeURIComponent(search)}&limit=1&lat=-5.2&lon=-40.6&zoom=9`;
      const res = await fetch(url);
      const data = await res.json();
      const feature = data.features?.[0];
      if (!feature) {
        setSearchError("Nada encontrado. Clique direto no mapa para marcar.");
        return;
      }
      const [foundLng, foundLat] = feature.geometry.coordinates;
      onChange(foundLat, foundLng);
      setFlyTarget([foundLat, foundLng]);
    } catch {
      setSearchError("Busca indisponível agora. Clique direto no mapa para marcar.");
    } finally {
      setSearching(false);
    }
  }

  return (
    <div>
      <form onSubmit={handleSearch} style={{ display: "flex", gap: 8, marginBottom: 8 }}>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Buscar cidade para centralizar o mapa…"
          style={{ flex: 1 }}
        />
        <button className="btn secondary small" type="submit" disabled={searching}>
          {searching ? "Buscando…" : "Buscar"}
        </button>
      </form>
      {searchError && <p className="footnote" style={{ color: "var(--red)" }}>{searchError}</p>}
      <div style={{ height, borderRadius: 6, overflow: "hidden", border: "1px solid var(--line)" }}>
        <MapContainer center={position || SERTAO_CENTRAL} zoom={position ? 12 : 9} style={{ height: "100%", width: "100%" }}>
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <ClickToPlace onPick={onChange} />
          {position && <Marker position={position} icon={markerImage} draggable eventHandlers={{
            dragend: (e) => {
              const m = e.target.getLatLng();
              onChange(m.lat, m.lng);
            },
          }} />}
          <FlyTo position={flyTarget} />
        </MapContainer>
      </div>
      <p className="footnote">
        Clique no mapa para marcar (ou arraste o pino) — {position ? `${lat!.toFixed(5)}, ${lng!.toFixed(5)}` : "nenhuma coordenada ainda"}.
      </p>
    </div>
  );
}
