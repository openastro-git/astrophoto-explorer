function LoadingView({ scanProgress }) {
  return (
    <div className="flex flex-col items-center justify-center h-96">
      <div className="text-slate-400 mb-2 text-lg">
        {scanProgress ? scanProgress.message : 'Loading...'}
      </div>
      {scanProgress && scanProgress.current_file && (
        <div className="text-slate-500 text-sm mb-4 max-w-2xl truncate">
          {scanProgress.current_file}
        </div>
      )}
      {scanProgress && scanProgress.total > 0 && (
        <div className="w-96">
          <div className="bg-slate-800 rounded-full h-4 overflow-hidden">
            <div
              className="bg-cyan-500 h-full transition-all duration-300"
              style={{ width: `${(scanProgress.current / scanProgress.total) * 100}%` }}
            />
          </div>
          <div className="text-xs text-slate-500 mt-2 text-center">
            {scanProgress.current} / {scanProgress.total} files
            {scanProgress.stage && ` • ${scanProgress.stage}`}
          </div>
        </div>
      )}
    </div>
  );
}

export default LoadingView;
