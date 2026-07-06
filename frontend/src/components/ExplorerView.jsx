import { ChevronLeft, ChevronRight } from 'lucide-react';
import ImageViewer from '../ImageViewer';
import { normalizeDistance, getRelativePath } from '../utils/formatters';

function ExplorerView({
  selectedGroup,
  currentImageIndex,
  objectInfo,
  fitsHeader,
  showFitsHeader,
  setShowFitsHeader,
  folderPath,
  imageRefreshKey,
  onPrevImage,
  onNextImage,
  onImageChange,
  onSetFavorite,
  onFetchFitsHeader,
  toast,
  defaultRender
}) {
  if (!selectedGroup) return null;

  const currentFile = selectedGroup.files[currentImageIndex];
  const isFitsFile = ['fits', 'fit', 'fts'].includes(currentFile.file_type.toLowerCase());

  return (
    <div className="max-w-7xl mx-auto">
      <div className="space-y-6">
        {/* Image Viewer */}
        <div className="bg-slate-900/50 backdrop-blur-md border border-white/10 rounded-xl p-6">
          <div className="mb-4">
            <h2 className="text-2xl font-bold">
              {selectedGroup.object}
              {objectInfo && objectInfo.name && (
                <span className="text-cyan-400 font-normal"> - {objectInfo.name}</span>
              )}
            </h2>
            {objectInfo && objectInfo.description && (
              <p className="text-sm text-slate-400 mt-2">{objectInfo.description}</p>
            )}
            {objectInfo && (objectInfo.type || objectInfo.constellation || objectInfo.distance) && (
              <div className="flex flex-wrap gap-4 text-xs text-slate-500 mt-2">
                {objectInfo.type && (
                  <span>Type: <span className="text-slate-300">{objectInfo.type}</span></span>
                )}
                {objectInfo.constellation && (
                  <span>Constellation: <span className="text-slate-300">{objectInfo.constellation}</span></span>
                )}
                {objectInfo.distance && (
                  <span>Distance: <span className="text-slate-300">{normalizeDistance(objectInfo.distance)}</span></span>
                )}
              </div>
            )}
          </div>

          <ImageViewer
            imagePath={currentFile.path}
            filename={currentFile.filename}
            fileType={currentFile.file_type}
            onSetFavorite={onSetFavorite}
            isFavorite={selectedGroup.favorite === currentFile.path}
            refreshKey={imageRefreshKey}
            objectName={selectedGroup.object}
            objectInfo={objectInfo}
            toast={toast}
            defaultRender={defaultRender}
          />

          {/* Navigation */}
          <div className="flex items-center justify-center gap-4 mt-4">
            <button
              onClick={onPrevImage}
              disabled={currentImageIndex === 0}
              className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded disabled:opacity-30 disabled:cursor-not-allowed transition"
            >
              <ChevronLeft className="w-5 h-5" />
              Prev
            </button>
            <span className="text-sm text-slate-400 px-4">
              Image {currentImageIndex + 1} of {selectedGroup.files.length}
            </span>
            <button
              onClick={onNextImage}
              disabled={currentImageIndex === selectedGroup.files.length - 1}
              className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded disabled:opacity-30 disabled:cursor-not-allowed transition"
            >
              Next
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Metadata */}
        <div className="bg-slate-900/50 backdrop-blur-md border border-white/10 rounded-xl p-6">
          <h3 className="text-lg font-bold mb-4">File Information</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="text-slate-400">Filename:</span>
              <p className="font-medium mt-1">{currentFile.filename}</p>
            </div>
            <div className="col-span-2">
              <span className="text-slate-400">Path:</span>
              <p className="font-medium mt-1 text-xs select-all cursor-text" title={currentFile.path}>
                {getRelativePath(currentFile.path, folderPath)}
              </p>
            </div>
            <div>
              <span className="text-slate-400">Type:</span>
              <p className="font-medium mt-1">{currentFile.file_type.toUpperCase()}</p>
            </div>
            <div>
              <span className="text-slate-400">Exposure:</span>
              <p className="font-medium mt-1">{currentFile.exptime}s</p>
            </div>
            <div>
              <span className="text-slate-400">Filter:</span>
              <p className="font-medium mt-1">{currentFile.filter}</p>
            </div>
            <div>
              <span className="text-slate-400">Instrument:</span>
              <p className="font-medium mt-1">{currentFile.instrument}</p>
            </div>
            <div>
              <span className="text-slate-400">Date:</span>
              <p className="font-medium mt-1">{currentFile.date}</p>
            </div>
            <div>
              <span className="text-slate-400">Session:</span>
              <p className="font-medium mt-1">{currentFile.session_date || 'N/A'}</p>
            </div>
          </div>

          {/* FITS Header Section */}
          {isFitsFile && (
            <div className="mt-6 pt-6 border-t border-slate-700">
              <button
                onClick={() => {
                  setShowFitsHeader(!showFitsHeader);
                  if (!showFitsHeader && !fitsHeader) {
                    onFetchFitsHeader(currentFile.path);
                  }
                }}
                className="flex items-center gap-2 text-cyan-400 hover:text-cyan-300 transition"
              >
                <span className="text-sm font-medium">
                  {showFitsHeader ? '▼' : '▶'} FITS Header Data
                </span>
              </button>

              {showFitsHeader && fitsHeader && (
                <div className="mt-4 bg-slate-800/50 rounded-lg p-4 max-h-96 overflow-y-auto">
                  <div className="grid grid-cols-1 gap-2 text-xs font-mono">
                    {Object.entries(fitsHeader).map(([key, value]) => (
                      <div key={key} className="flex gap-4">
                        <span className="text-cyan-400 font-bold min-w-[120px]">{key}:</span>
                        <span className="text-slate-300 break-all">{String(value)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {showFitsHeader && !fitsHeader && (
                <div className="mt-4 text-sm text-slate-500">Loading FITS header...</div>
              )}
            </div>
          )}
        </div>

        {/* File List */}
        <FileList
          selectedGroup={selectedGroup}
          currentImageIndex={currentImageIndex}
          onImageChange={onImageChange}
        />
      </div>
    </div>
  );
}

function FileList({ selectedGroup, currentImageIndex, onImageChange }) {
  return (
    <div className="bg-slate-900/50 backdrop-blur-md border border-white/10 rounded-xl p-6">
      <h3 className="text-lg font-bold mb-4">All Files ({selectedGroup.files.length})</h3>

      {/* Check if there are multiple sessions */}
      {selectedGroup.sessions && selectedGroup.sessions.length > 1 ? (
        /* Multi-session view */
        <div className="space-y-6">
          {selectedGroup.sessions.map((session, sessionIdx) => (
            <div key={sessionIdx} className="space-y-2">
              <div className="flex items-center gap-2 mb-3">
                <div className="h-px flex-1 bg-slate-700"></div>
                <h4 className="text-sm font-semibold text-cyan-400">
                  Session: {session.session_date} ({session.count} files)
                </h4>
                <div className="h-px flex-1 bg-slate-700"></div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {session.files.map((file, fileIdx) => {
                  // Find the global index of this file
                  const globalIdx = selectedGroup.files.findIndex(f => f.path === file.path);
                  return (
                    <button
                      key={fileIdx}
                      onClick={() => onImageChange(globalIdx)}
                      onMouseDown={(e) => e.preventDefault()}
                      className={`text-left p-3 rounded-lg border transition ${
                        currentImageIndex === globalIdx
                          ? 'bg-cyan-500/20 border-cyan-500'
                          : 'bg-slate-800/30 border-slate-700/50 hover:border-slate-600'
                      }`}
                    >
                      <div className="font-medium text-sm truncate">{file.filename}</div>
                      <div className="text-xs text-slate-400 mt-1">
                        {file.file_type.toUpperCase()} • {file.filter} • {file.exptime}s
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      ) : (
        /* Single session view */
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {selectedGroup.files.map((file, idx) => (
            <button
              key={idx}
              onClick={() => onImageChange(idx)}
              onMouseDown={(e) => e.preventDefault()}
              className={`text-left p-3 rounded-lg border transition ${
                currentImageIndex === idx
                  ? 'bg-cyan-500/20 border-cyan-500'
                  : 'bg-slate-800/30 border-slate-700/50 hover:border-slate-600'
              }`}
            >
              <div className="font-medium text-sm truncate">{file.filename}</div>
              <div className="text-xs text-slate-400 mt-1">
                {file.file_type.toUpperCase()} • {file.filter} • {file.exptime}s
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default ExplorerView;
