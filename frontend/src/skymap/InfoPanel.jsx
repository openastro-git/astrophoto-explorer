// Info Panel Component
function InfoPanel({ starCount, fov }) {
  return (
    <div className="absolute bottom-4 left-4 bg-slate-900/80 backdrop-blur-md border border-white/10 rounded-lg p-3 text-xs text-slate-400">
      <div>Drag to rotate view • Scroll to zoom</div>
      <div>FOV: {fov.toFixed(0)}°</div>
      <div className="mt-1 text-slate-500">Milky Way: ESO/S. Brunier</div>
    </div>
  );
}

export default InfoPanel;
