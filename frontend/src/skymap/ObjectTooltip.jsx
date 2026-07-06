// Object Tooltip Component
function ObjectTooltip({ hoveredObject, tooltipPos }) {
  if (!hoveredObject) return null;

  return (
    <div
      className="absolute pointer-events-none z-50"
      style={{
        left: tooltipPos.x + 15,
        top: tooltipPos.y + 15,
      }}
    >
      <div className="bg-slate-900/95 backdrop-blur-md border border-cyan-400/50 rounded-lg p-4 shadow-xl max-w-md">
        <div className="flex items-start gap-4">
          {hoveredObject.thumbnail && (
            <img
              src={`http://localhost:8000/api/thumbnail/${encodeURIComponent(hoveredObject.thumbnail)}`}
              alt={hoveredObject.object}
              className="w-32 h-32 object-cover rounded border border-cyan-400/30"
            />
          )}
          <div className="flex-1 min-w-0">
            <h4 className="font-bold text-cyan-400 text-base mb-2">{hoveredObject.object}</h4>
            <div className="text-sm text-slate-300 space-y-1">
              <div>{hoveredObject.count} files</div>
              {hoveredObject.astrometry && (
                <>
                  <div>RA: {hoveredObject.astrometry.ra.toFixed(2)}°</div>
                  <div>Dec: {hoveredObject.astrometry.dec.toFixed(2)}°</div>
                  {hoveredObject.astrometry.constellation && (
                    <div>Constellation: {hoveredObject.astrometry.constellation}</div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ObjectTooltip;
