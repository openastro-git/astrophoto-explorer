import { Grid3x3, Sparkles, Navigation } from 'lucide-react';

function GridView({ 
  folderPath, 
  groups, 
  onGroupClick,
  onNavigateToSkyMap
}) {
  if (!folderPath || folderPath === '') {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center text-slate-500">
          <Grid3x3 className="w-16 h-16 mx-auto mb-4 opacity-50" />
          <p className="text-lg">No folder configured</p>
          <p className="text-sm mt-2">Click settings to get started</p>
        </div>
      </div>
    );
  }

  if (groups.length === 0) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center text-slate-500">
          <Grid3x3 className="w-16 h-16 mx-auto mb-4 opacity-50" />
          <p className="text-lg">No objects found</p>
          <p className="text-sm mt-2">No FITS or image files in this folder</p>
        </div>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
      {groups.map((group, idx) => {
        const hasAstrometry = group.astrometry && 
          group.astrometry.ra !== undefined && 
          group.astrometry.dec !== undefined;
        
        return (
          <div key={idx} className="relative">
            <button
              onClick={(e) => {
                e.currentTarget.blur();
                onGroupClick(group);
              }}
              className="group relative bg-slate-900/50 backdrop-blur-md border border-white/10 rounded-xl overflow-hidden hover:border-cyan-400 transition aspect-square w-full"
            >
              {group.thumbnail ? (
                <div className="absolute inset-0 bg-slate-800">
                  <img
                    src={`http://localhost:8000/api/thumbnail/${encodeURIComponent(group.thumbnail)}`}
                    alt={group.object}
                    className="w-full h-full object-cover opacity-70 group-hover:opacity-100 transition"
                    onError={(e) => {
                      e.target.style.display = 'none';
                    }}
                  />
                </div>
              ) : (
                <div className="absolute inset-0 flex items-center justify-center bg-slate-800">
                  <Sparkles className="w-12 h-12 text-slate-600" />
                </div>
              )}
              <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent" />
              <div className="absolute bottom-0 left-0 right-0 p-4">
                <h3 className="text-lg font-bold mb-1">{group.object}</h3>
                <p className="text-xs text-slate-400">{group.count} files</p>
                {group.session_date && (
                  <p className={`text-xs mt-1 ${
                    group.session_date === 'Multiple' 
                      ? 'text-cyan-400 font-medium' 
                      : 'text-slate-500'
                  }`}>
                    {group.session_date === 'Multiple' ? '📅 Multiple Sessions' : group.session_date}
                  </p>
                )}
              </div>
            </button>
            
            {/* Navigate button - only show if object has coordinates */}
            {hasAstrometry && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onNavigateToSkyMap(group);
                }}
                className="absolute top-2 right-2 p-2 bg-white/10 hover:bg-cyan-400/30 backdrop-blur-md border border-white/20 hover:border-cyan-400/50 rounded-lg shadow-lg transition-all duration-200 z-10"
                title={`Navigate to ${group.object} on sky map`}
              >
                <Navigation className="w-4 h-4 text-cyan-400" />
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
}

export default GridView;
