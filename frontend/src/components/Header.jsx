import { Sparkles, Settings, X, Grid3x3, ArrowLeft, Map, Terminal } from 'lucide-react';

function Header({
  view,
  mainView,
  selectedGroup,
  folderPath,
  loading,
  searchQuery,
  setSearchQuery,
  onBackToGrid,
  onBackToGridFromSkyMap,
  onViewChange,
  onRescan,
  onSettingsClick,
  gridScrollPosition,
  showConsole,
  onConsoleToggle
}) {
  return (
    <header className="fixed top-0 left-0 right-0 bg-slate-900/80 backdrop-blur-md border-b border-white/10 p-4 z-40">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          {view === 'explorer' && (
            <button
              onClick={onBackToGrid}
              className="text-slate-400 hover:text-cyan-400 transition"
            >
              <ArrowLeft className="w-6 h-6" />
            </button>
          )}
          {view === 'skymap' && mainView === 'skymap' && gridScrollPosition > 0 && (
            <button
              onClick={onBackToGridFromSkyMap}
              className="text-slate-400 hover:text-cyan-400 transition"
              title="Back to Grid View"
            >
              <ArrowLeft className="w-6 h-6" />
            </button>
          )}
          <Sparkles className="w-8 h-8 text-cyan-400" />
          <h1 className="text-2xl font-bold tracking-tight">Astrophoto Explorer</h1>
          {view === 'explorer' && selectedGroup && (
            <span className="text-slate-400">/ {selectedGroup.object}</span>
          )}
        </div>

        {/* Center Search Bar - visible in grid and skymap views */}
        {(view === 'grid' || view === 'skymap') && (
          <div className="flex-1 flex items-center justify-center max-w-md gap-3">
            <div className="relative flex-1">
              <input
                type="text"
                placeholder="Search..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                title="Search by object name or filename"
                className="w-full bg-slate-800/50 border border-slate-700 rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-cyan-400 transition"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-2 top-1/2 transform -translate-y-1/2 text-slate-400 hover:text-slate-100 transition"
                  title="Clear search"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
            
            {/* View Toggle Buttons */}
            <div className="flex items-center gap-1 bg-slate-800/50 border border-slate-700 rounded-lg p-1">
              <button
                onClick={() => onViewChange('grid')}
                className={`p-2 rounded transition ${
                  mainView === 'grid'
                    ? 'bg-cyan-500 text-white'
                    : 'text-slate-400 hover:text-slate-100 hover:bg-slate-700'
                }`}
                title="Grid View"
              >
                <Grid3x3 className="w-5 h-5" />
              </button>
              <button
                onClick={() => onViewChange('skymap')}
                className={`p-2 rounded transition ${
                  mainView === 'skymap'
                    ? 'bg-cyan-500 text-white'
                    : 'text-slate-400 hover:text-slate-100 hover:bg-slate-700'
                }`}
                title="Sky Map View"
              >
                <Map className="w-5 h-5" />
              </button>
            </div>
          </div>
        )}

        <div className="flex items-center gap-4">
          {folderPath && (
            <>
              <button
                onClick={onRescan}
                disabled={loading}
                className="bg-cyan-500 hover:bg-cyan-600 px-4 py-2 rounded text-sm font-medium transition disabled:opacity-50 disabled:cursor-not-allowed"
                title={loading ? "Scan in progress..." : "Rescan directory for changes"}
              >
                Rescan
              </button>
            </>
          )}
          <button
            onClick={onConsoleToggle}
            className={`transition ${showConsole ? 'text-cyan-400' : 'text-slate-400 hover:text-cyan-400'}`}
            title="Toggle Console Logs"
          >
            <Terminal className="w-6 h-6" />
          </button>
          <button
            onClick={onSettingsClick}
            className="text-slate-400 hover:text-cyan-400 transition"
            title="Settings"
          >
            <Settings className="w-6 h-6" />
          </button>
        </div>
      </div>
    </header>
  );
}

export default Header;
