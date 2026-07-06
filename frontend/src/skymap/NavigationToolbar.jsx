// Navigation Toolbar Component
function NavigationToolbar({ 
  showCelestialEquator, 
  setShowCelestialEquator,
  showCelestialGrid,
  setShowCelestialGrid,
  onLevelToEquator
}) {
  return (
    <div className="absolute top-4 right-4 flex items-center gap-1 bg-slate-800/50 border border-slate-700 rounded-lg p-1 shadow-xl">
      <button
        onClick={() => setShowCelestialEquator(!showCelestialEquator)}
        className={`w-9 h-9 flex items-center justify-center rounded transition ${
          showCelestialEquator 
            ? 'bg-orange-500 text-white' 
            : 'text-slate-400 hover:text-slate-100 hover:bg-slate-700'
        }`}
        title="Celestial Equator - Earth's equator projected onto the sky"
      >
        <span className="text-xl leading-none">⊖</span>
      </button>
      
      <button
        onClick={() => setShowCelestialGrid(!showCelestialGrid)}
        className={`w-9 h-9 flex items-center justify-center rounded transition ${
          showCelestialGrid 
            ? 'bg-blue-500 text-white' 
            : 'text-slate-400 hover:text-slate-100 hover:bg-slate-700'
        }`}
        title="RA/Dec Grid - Right Ascension & Declination coordinate system (includes North Celestial Pole)"
      >
        <span className="text-xl leading-none">🌐</span>
      </button>
      
      <div className="w-px h-6 bg-slate-600 mx-0.5" />
      
      <button
        onClick={onLevelToEquator}
        className="w-9 h-9 flex items-center justify-center rounded transition text-slate-400 hover:text-slate-100 hover:bg-slate-700"
        title="Level View - Align camera to celestial equator"
      >
        <span className="text-xl leading-none">⌂</span>
      </button>
    </div>
  );
}

export default NavigationToolbar;
