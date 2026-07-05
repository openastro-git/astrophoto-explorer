import { Grid3x3, Map } from 'lucide-react';

function EmptyState({ type, searchQuery }) {
  const isMap = type === 'map';
  const Icon = isMap ? Map : Grid3x3;

  if (type === 'no-folder') {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center text-slate-500">
          <Icon className="w-16 h-16 mx-auto mb-4 opacity-50" />
          <p className="text-lg">No folder configured</p>
          <p className="text-sm mt-2">Click settings to get started</p>
        </div>
      </div>
    );
  }

  if (type === 'no-objects') {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center text-slate-500">
          <Icon className="w-16 h-16 mx-auto mb-4 opacity-50" />
          <p className="text-lg">No objects found</p>
          <p className="text-sm mt-2">No FITS or image files in this folder</p>
        </div>
      </div>
    );
  }

  if (type === 'no-results') {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center text-slate-500">
          <Icon className="w-16 h-16 mx-auto mb-4 opacity-50" />
          <p className="text-lg">No results</p>
          <p className="text-sm mt-2">No matches for "{searchQuery}"</p>
        </div>
      </div>
    );
  }

  return null;
}

export default EmptyState;
