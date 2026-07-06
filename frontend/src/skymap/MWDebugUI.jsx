import { useState, useEffect } from 'react';

// Milky Way Debug UI Component - for initial alignment tweaking
function MWDebugUI({ milkyWayMeshRef, milkyWayMaterialRef, needsRenderRef }) {
  const [showMwDebug, setShowMwDebug] = useState(false);
  const [mwRotationX, setMwRotationX] = useState(117.4);
  const [mwRotationY, setMwRotationY] = useState(-29.2);
  const [mwRotationZ, setMwRotationZ] = useState(90.2);
  const [mwOpacity, setMwOpacity] = useState(0.33);
  const [mwFlipH, setMwFlipH] = useState(true);
  const [mwDragMode, setMwDragMode] = useState(false);

  // Update MW rotation
  useEffect(() => {
    if (milkyWayMeshRef.current) {
      milkyWayMeshRef.current.rotation.x = mwRotationX * Math.PI / 180;
      milkyWayMeshRef.current.rotation.y = mwRotationY * Math.PI / 180;
      milkyWayMeshRef.current.rotation.z = mwRotationZ * Math.PI / 180;
      if (needsRenderRef) needsRenderRef.current = true;
    }
  }, [mwRotationX, mwRotationY, mwRotationZ, milkyWayMeshRef, needsRenderRef]);

  // Update MW material
  useEffect(() => {
    if (milkyWayMaterialRef.current) {
      milkyWayMaterialRef.current.uniforms.opacity.value = mwOpacity;
      milkyWayMaterialRef.current.uniforms.flipH.value = mwFlipH ? 1.0 : 0.0;
      if (needsRenderRef) needsRenderRef.current = true;
    }
  }, [mwOpacity, mwFlipH, milkyWayMaterialRef, needsRenderRef]);

  const logCurrentRotation = () => {
    console.log('=== Milky Way Sphere Rotation ===');
    console.log('rotationX:', mwRotationX);
    console.log('rotationY:', mwRotationY);
    console.log('rotationZ:', mwRotationZ);
    console.log('opacity:', mwOpacity);
    console.log('flipH:', mwFlipH);
    console.log('\nCopy these values to apply permanently');
  };

  return (
    <>
      {/* Toggle Button */}
      {!showMwDebug && (
        <button 
          onClick={() => setShowMwDebug(true)}
          className="absolute top-4 right-4 px-3 py-2 bg-slate-900/80 backdrop-blur-md border border-white/10 rounded-lg text-xs text-slate-400 hover:text-white opacity-30 hover:opacity-100 transition-opacity"
          title="Show Milky Way adjustment controls"
        >
          ⚙️
        </button>
      )}

      {/* Debug Panel */}
      {showMwDebug && (
        <div className="absolute top-4 right-4 bg-slate-900/90 backdrop-blur-md border border-white/10 rounded-lg p-4 text-xs space-y-3 w-72">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-cyan-400 font-bold">Milky Way Rotation</h3>
            <button 
              onClick={() => setShowMwDebug(false)}
              className="text-slate-400 hover:text-white"
            >✕</button>
          </div>
          
          <div className="text-slate-400 text-[10px] mb-2">
            Rotate the Milky Way sphere to align with constellations
          </div>
          
          <div className="bg-slate-800/50 rounded p-2 mb-3">
            <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
              <input 
                type="checkbox" 
                checked={mwDragMode}
                onChange={(e) => setMwDragMode(e.target.checked)}
                className="w-4 h-4"
              />
              <span className="font-semibold">
                {mwDragMode ? '🔒 MW Drag Mode (Y-axis)' : '🎥 Camera Mode'}
              </span>
            </label>
            <div className="text-[10px] text-slate-400 mt-1">
              {mwDragMode 
                ? 'Drag left/right to spin MW around vertical axis' 
                : 'Drag to rotate camera view'}
            </div>
          </div>
          
          {/* Rotation X */}
          <div>
            <label className="text-slate-300 block mb-1">
              Rotation X (pitch): {mwRotationX.toFixed(1)}°
            </label>
            <div className="flex gap-2 items-center">
              <input 
                type="range" 
                min="-180" 
                max="180" 
                step="0.1" 
                value={mwRotationX}
                onChange={(e) => setMwRotationX(parseFloat(e.target.value))}
                className="flex-1"
              />
              <input 
                type="number" 
                min="-180" 
                max="180" 
                step="0.1" 
                value={mwRotationX.toFixed(1)}
                onChange={(e) => setMwRotationX(parseFloat(e.target.value) || 0)}
                className="w-16 px-1 py-0.5 bg-slate-700 border border-slate-600 rounded text-[11px] text-center"
              />
            </div>
            <div className="flex gap-2 mt-1">
              <button onClick={() => setMwRotationX(v => v - 10)} className="px-2 py-1 bg-slate-700 rounded text-[10px]">-10°</button>
              <button onClick={() => setMwRotationX(v => v - 1)} className="px-2 py-1 bg-slate-700 rounded text-[10px]">-1°</button>
              <button onClick={() => setMwRotationX(v => v + 1)} className="px-2 py-1 bg-slate-700 rounded text-[10px]">+1°</button>
              <button onClick={() => setMwRotationX(v => v + 10)} className="px-2 py-1 bg-slate-700 rounded text-[10px]">+10°</button>
              <button onClick={() => setMwRotationX(0)} className="px-2 py-1 bg-slate-700 rounded text-[10px]">Reset</button>
            </div>
          </div>
          
          {/* Rotation Y */}
          <div>
            <label className="text-slate-300 block mb-1">
              Rotation Y (yaw): {mwRotationY.toFixed(1)}°
            </label>
            <div className="flex gap-2 items-center">
              <input 
                type="range" 
                min="-180" 
                max="180" 
                step="0.1" 
                value={mwRotationY}
                onChange={(e) => setMwRotationY(parseFloat(e.target.value))}
                className="flex-1"
              />
              <input 
                type="number" 
                min="-180" 
                max="180" 
                step="0.1" 
                value={mwRotationY.toFixed(1)}
                onChange={(e) => setMwRotationY(parseFloat(e.target.value) || 0)}
                className="w-16 px-1 py-0.5 bg-slate-700 border border-slate-600 rounded text-[11px] text-center"
              />
            </div>
            <div className="flex gap-2 mt-1">
              <button onClick={() => setMwRotationY(v => v - 10)} className="px-2 py-1 bg-slate-700 rounded text-[10px]">-10°</button>
              <button onClick={() => setMwRotationY(v => v - 1)} className="px-2 py-1 bg-slate-700 rounded text-[10px]">-1°</button>
              <button onClick={() => setMwRotationY(v => v + 1)} className="px-2 py-1 bg-slate-700 rounded text-[10px]">+1°</button>
              <button onClick={() => setMwRotationY(v => v + 10)} className="px-2 py-1 bg-slate-700 rounded text-[10px]">+10°</button>
              <button onClick={() => setMwRotationY(0)} className="px-2 py-1 bg-slate-700 rounded text-[10px]">Reset</button>
            </div>
          </div>
          
          {/* Rotation Z */}
          <div>
            <label className="text-slate-300 block mb-1">
              Rotation Z (roll): {mwRotationZ.toFixed(1)}°
            </label>
            <div className="flex gap-2 items-center">
              <input 
                type="range" 
                min="-180" 
                max="180" 
                step="0.1" 
                value={mwRotationZ}
                onChange={(e) => setMwRotationZ(parseFloat(e.target.value))}
                className="flex-1"
              />
              <input 
                type="number" 
                min="-180" 
                max="180" 
                step="0.1" 
                value={mwRotationZ.toFixed(1)}
                onChange={(e) => setMwRotationZ(parseFloat(e.target.value) || 0)}
                className="w-16 px-1 py-0.5 bg-slate-700 border border-slate-600 rounded text-[11px] text-center"
              />
            </div>
            <div className="flex gap-2 mt-1">
              <button onClick={() => setMwRotationZ(v => v - 10)} className="px-2 py-1 bg-slate-700 rounded text-[10px]">-10°</button>
              <button onClick={() => setMwRotationZ(v => v - 1)} className="px-2 py-1 bg-slate-700 rounded text-[10px]">-1°</button>
              <button onClick={() => setMwRotationZ(v => v + 1)} className="px-2 py-1 bg-slate-700 rounded text-[10px]">+1°</button>
              <button onClick={() => setMwRotationZ(v => v + 10)} className="px-2 py-1 bg-slate-700 rounded text-[10px]">+10°</button>
              <button onClick={() => setMwRotationZ(0)} className="px-2 py-1 bg-slate-700 rounded text-[10px]">Reset</button>
            </div>
          </div>
          
          {/* Opacity */}
          <div>
            <label className="text-slate-300 block mb-1">
              Opacity: {(mwOpacity * 100).toFixed(0)}%
            </label>
            <input 
              type="range" 
              min="0" 
              max="1" 
              step="0.01" 
              value={mwOpacity}
              onChange={(e) => setMwOpacity(parseFloat(e.target.value))}
              className="w-full"
            />
            <div className="flex gap-2 mt-1">
              <button onClick={() => setMwOpacity(0)} className="px-2 py-1 bg-slate-700 rounded text-[10px]">Hide</button>
              <button onClick={() => setMwOpacity(0.15)} className="px-2 py-1 bg-slate-700 rounded text-[10px]">Default</button>
              <button onClick={() => setMwOpacity(0.5)} className="px-2 py-1 bg-slate-700 rounded text-[10px]">Bright</button>
            </div>
          </div>
          
          {/* Flip Horizontal */}
          <div className="flex gap-4">
            <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
              <input 
                type="checkbox" 
                checked={mwFlipH}
                onChange={(e) => setMwFlipH(e.target.checked)}
              />
              Flip Horizontal
            </label>
          </div>
          
          {/* Action Buttons */}
          <div className="pt-2 border-t border-white/10 space-y-2">
            <button 
              onClick={() => {
                setMwRotationX(0);
                setMwRotationY(0);
                setMwRotationZ(0);
              }}
              className="w-full px-3 py-1.5 bg-slate-700 hover:bg-slate-600 rounded text-white"
            >
              Reset All
            </button>
            <button 
              onClick={logCurrentRotation}
              className="w-full px-3 py-1.5 bg-cyan-600 hover:bg-cyan-700 rounded text-white"
            >
              Log Current Rotation
            </button>
          </div>
        </div>
      )}
    </>
  );
}

export default MWDebugUI;
