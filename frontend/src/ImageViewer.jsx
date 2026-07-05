import { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { Maximize2, Minimize2, Maximize, Star, Save } from 'lucide-react';
import ZoomNavigator from './components/ZoomNavigator';

function ImageViewer({ imagePath, filename, fileType, onLoad, onSetFavorite, isFavorite, refreshKey, objectName, objectInfo, toast, defaultRender = 'HD' }) {
  const isFitsFile = fileType === 'fits' || fileType === 'fit' || fileType === 'fts';
  
  const [zoom, setZoom] = useState(1);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  // Initialize imageSize based on file type and default render settings
  const [imageSize, setImageSize] = useState(() => {
    if (isFitsFile) return 'full';
    return defaultRender === 'HD' ? 'full' : 'large';
  });
  const [imageData, setImageData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [isInitialLoad, setIsInitialLoad] = useState(true);
  const [imageLoaded, setImageLoaded] = useState(false);
  const [loadedImageKey, setLoadedImageKey] = useState('');
  const [isExpanded, setIsExpanded] = useState(false);
  const [detectedMetadata, setDetectedMetadata] = useState(null);
  const [savingMetadata, setSavingMetadata] = useState(false);
  
  const containerRef = useRef(null);
  const imageRef = useRef(null);
  const previousImagePath = useRef(imagePath);
  const imageCache = useRef(new Map()); // Client-side cache for loaded images
  const previousRefreshKey = useRef(refreshKey);
  const loadingKeyRef = useRef('');

  // Helper to revoke all cached object URLs and free memory
  const revokeAllCachedUrls = () => {
    for (const [key, data] of imageCache.current.entries()) {
      if (data && data.image && data.image.startsWith('blob:')) {
        console.log('Revoking object URL:', data.image);
        URL.revokeObjectURL(data.image);
      }
    }
  };

  // Clear cache and reload when refreshKey changes (stretch settings changed)
  useEffect(() => {
    if (refreshKey !== previousRefreshKey.current && isFitsFile) {
      previousRefreshKey.current = refreshKey;
      // Clear the object URLs from browser memory
      revokeAllCachedUrls();
      imageCache.current.clear();
      // Force reload current image
      setLoadedImageKey('');
      loadingKeyRef.current = '';
      loadImage(imageSize);
    }
  }, [refreshKey, isFitsFile, imageSize]);

  // Clean up object URLs on unmount
  useEffect(() => {
    return () => {
      revokeAllCachedUrls();
      imageCache.current.clear();
    };
  }, []);

  // Reset when imagePath changes
  useEffect(() => {
    if (previousImagePath.current !== imagePath) {
      previousImagePath.current = imagePath;
      // Reset view state
      setZoom(1);
      setPosition({ x: 0, y: 0 });
      setIsInitialLoad(true);
      setImageLoaded(false);
      setLoadedImageKey('');
      loadingKeyRef.current = '';
    }
  }, [imagePath]);

  // Load image when imagePath or defaultRender changes
  useEffect(() => {
    // Determine correct size for this file type and settings
    const correctSize = isFitsFile ? 'full' : (defaultRender === 'HD' ? 'full' : 'large');
    
    // Only load if we don't have this exact image loaded
    const newKey = `${imagePath}:${correctSize}`;
    if (loadedImageKey !== newKey) {
      // Update imageSize state to match
      setImageSize(correctSize);
      // Reset zoom and position for new image
      setZoom(1);
      setPosition({ x: 0, y: 0 });
      setIsInitialLoad(true);
      setImageLoaded(false);
      // Load without awaiting
      loadImage(correctSize);
    }
  }, [imagePath, isFitsFile, defaultRender]);

  // Handle manual imageSize changes (e.g., HD button)
  useEffect(() => {
    const newKey = `${imagePath}:${imageSize}`;
    if (loadedImageKey !== newKey) {
      loadImage(imageSize);
    }
  }, [imageSize]);

  const applyBoundaryConstraints = (x, y, currentZoom) => {
    if (!containerRef.current || !imageRef.current || !imageLoaded) return { x, y };

    const container = containerRef.current.getBoundingClientRect();
    const containerWidth = container.width;
    const containerHeight = container.height;

    const img = imageRef.current;
    const imageWidth = img.naturalWidth;
    const imageHeight = img.naturalHeight;

    if (!imageWidth || !imageHeight) return { x, y };

    const scaleToFit = Math.min(
      containerWidth / imageWidth,
      containerHeight / imageHeight
    );

    const displayWidth = imageWidth * scaleToFit * currentZoom;
    const displayHeight = imageHeight * scaleToFit * currentZoom;

    if (displayWidth <= containerWidth) {
      x = 0;
    } else {
      const maxX = displayWidth / 2 - containerWidth / 2;
      const minX = -displayWidth / 2 + containerWidth / 2;
      x = Math.max(minX, Math.min(maxX, x));
    }

    if (displayHeight <= containerHeight) {
      y = 0;
    } else {
      const maxY = displayHeight / 2 - containerHeight / 2;
      const minY = -displayHeight / 2 + containerHeight / 2;
      y = Math.max(minY, Math.min(maxY, y));
    }

    return { x, y };
  };

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleWheel = (e) => {
      e.preventDefault();
      e.stopPropagation();

      const rect = container.getBoundingClientRect();
      const dx = e.clientX - rect.left;
      const dy = e.clientY - rect.top;

      const delta = e.deltaY > 0 ? 0.9 : 1.1;

      setZoom(prevZoom => {
        // Prevent zooming out beyond fit-to-screen (zoom = 1.0)
        const newZoom = Math.max(1, Math.min(prevZoom * delta, 10));

        setPosition(prevPos => {
          const pointX = (dx - rect.width / 2 - prevPos.x) / prevZoom;
          const pointY = (dy - rect.height / 2 - prevPos.y) / prevZoom;

          const newX = dx - rect.width / 2 - pointX * newZoom;
          const newY = dy - rect.height / 2 - pointY * newZoom;

          return applyBoundaryConstraints(newX, newY, newZoom);
        });

        return newZoom;
      });

      setIsInitialLoad(false);
    };

    container.addEventListener('wheel', handleWheel, { passive: false, capture: true });

    return () => {
      container.removeEventListener('wheel', handleWheel, { capture: true });
    };
  }, [imageData, imageLoaded, isExpanded]);

  const loadImage = async (sizeToLoad) => {
    if (!imagePath) return;

    const cacheKey = `${imagePath}:${sizeToLoad}`;
    if (loadingKeyRef.current === cacheKey) {
      // Already fetching this exact path and size
      return;
    }
    loadingKeyRef.current = cacheKey;
    
    // Check client-side cache first
    if (imageCache.current.has(cacheKey)) {
      const cachedData = imageCache.current.get(cacheKey);
      setImageData(cachedData);
      setLoadedImageKey(cacheKey);
      if (onLoad) onLoad(cachedData);
      setLoading(false);
      checkForDetectedMetadata(cachedData);
      return;
    }

    setLoading(true);
    try {
      const params = new URLSearchParams({
        size: sizeToLoad,
        ...(isFitsFile && { stretch: 'mtf' }),
        // Avoid cache-busting on initial loads, instead tie to settings refresh
        ...(refreshKey && { r: refreshKey })
      });

      const response = await fetch(
        `http://localhost:8000/api/preview/${encodeURIComponent(imagePath)}?${params}`
      );
      
      if (!response.ok) {
        throw new Error(`Failed to fetch preview image: ${response.statusText}`);
      }

      const blob = await response.blob();
      
      // Parse custom metadata headers from Response
      const shapeHeader = response.headers.get('X-Image-Shape');
      const shape = shapeHeader ? JSON.parse(shapeHeader) : null;
      const astrometryHeader = response.headers.get('X-Image-Astrometry');
      const astrometry = astrometryHeader ? JSON.parse(astrometryHeader) : null;
      
      const imageUrl = URL.createObjectURL(blob);
      const data = {
        image: imageUrl,
        shape: shape,
        stretch: response.headers.get('X-Image-Stretch') || '',
        size: response.headers.get('X-Image-Size') || sizeToLoad,
        file_type: response.headers.get('X-Image-FileType') || '',
        object: response.headers.get('X-Image-Object') || '',
        astrometry: astrometry
      };

      // Cap cache size at 15 to prevent memory leaks, evicting the oldest entry
      if (imageCache.current.size >= 15) {
        const oldestKey = imageCache.current.keys().next().value;
        const oldestData = imageCache.current.get(oldestKey);
        if (oldestData && oldestData.image && oldestData.image.startsWith('blob:')) {
          URL.revokeObjectURL(oldestData.image);
        }
        imageCache.current.delete(oldestKey);
      }
      
      // Store in cache
      imageCache.current.set(cacheKey, data);
      
      setImageData(data);
      setLoadedImageKey(cacheKey);
      setIsInitialLoad(false);  // Mark that initial load is complete
      if (onLoad) {
        onLoad(data);
      }
      checkForDetectedMetadata(data);
    } catch (error) {
      console.error('Error loading image:', error);
      // Reset loading key on error to allow retry
      loadingKeyRef.current = '';
    }
    setLoading(false);
  };

  const checkForDetectedMetadata = (data, info = objectInfo) => {
    console.log('Checking for detected metadata...', data);
    console.log('Object name from context:', objectName);
    
    // Check what metadata exists in the file
    const hasRA = data.astrometry?.ra !== undefined && data.astrometry?.ra !== null;
    const hasDec = data.astrometry?.dec !== undefined && data.astrometry?.dec !== null;
    
    console.log('File metadata - Has RA:', hasRA, 'Has Dec:', hasDec);
    
    // Show save button if: we have object name from context AND file is missing RA or Dec
    if (objectName && objectName !== 'Unknown' && (!hasRA || !hasDec)) {
      if (info && !info.error && (info.ra || info.dec)) {
        const metadata = {
          object_name: objectName,
          ra: info.ra,
          dec: info.dec,
          name: info.name,
          type: info.type
        };
        console.log('Setting detected metadata:', metadata);
        setDetectedMetadata(metadata);
      } else {
        console.log('No valid coordinates found in catalog');
        setDetectedMetadata(null);
      }
    } else {
      setDetectedMetadata(null);
    }
  };

  // Re-check metadata whenever objectInfo or imageData changes
  useEffect(() => {
    if (imageData) {
      checkForDetectedMetadata(imageData, objectInfo);
    }
  }, [objectInfo, imageData, objectName]);

  const handleSaveMetadata = async () => {
    if (!detectedMetadata || !imagePath) return;
    
    setSavingMetadata(true);
    try {
      const response = await fetch('http://localhost:8000/api/metadata/save', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          file_path: imagePath,
          object_name: detectedMetadata.object_name
        })
      });
      
      const result = await response.json();
      
      if (result.success) {
        // Clear cache and reload image to show updated metadata
        imageCache.current.clear();
        setLoadedImageKey('');
        setDetectedMetadata(null);
        
        // Force reload with cache bust
        const timestamp = Date.now();
        const params = new URLSearchParams({
          size: imageSize,
          ...(isFitsFile && { stretch: 'mtf' }),
          _t: timestamp  // Cache buster
        });
        
        try {
          const response = await fetch(
            `http://localhost:8000/api/preview/${encodeURIComponent(imagePath)}?${params}`
          );
          const data = await response.json();
          
          console.log('Reloaded image data after save:', data);
          console.log('Has astrometry?', 'astrometry' in data, data.astrometry);
          
          imageCache.current.set(`${imagePath}:${imageSize}`, data);
          setImageData(data);
          setLoadedImageKey(`${imagePath}:${imageSize}`);
          
          // Check metadata again - should not show button now
          checkForDetectedMetadata(data);
          
          toast.success('Metadata saved successfully!');
        } catch (error) {
          console.error('Error reloading image:', error);
          toast.error('Metadata saved but failed to reload image');
        }
      } else {
        toast.error(`Failed to save metadata: ${result.error || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error saving metadata:', error);
      toast.error('Failed to save metadata. Check console for details.');
    } finally {
      setSavingMetadata(false);
    }
  };

  const handleImageLoad = () => {
    setImageLoaded(true);
  };

  const handleZoomNavigatorPositionChange = (newPosition) => {
    const constrained = applyBoundaryConstraints(newPosition.x, newPosition.y, zoom);
    setPosition(constrained);
    setIsInitialLoad(false);
  };

  const handleMouseDown = (e) => {
    if (e.button === 0) {
      setIsDragging(true);
      setDragStart({
        x: e.clientX - position.x,
        y: e.clientY - position.y
      });
      e.preventDefault();
    }
  };

  const handleMouseMove = (e) => {
    if (isDragging) {
      const newX = e.clientX - dragStart.x;
      const newY = e.clientY - dragStart.y;

      const constrained = applyBoundaryConstraints(newX, newY, zoom);
      setPosition(constrained);
      setIsInitialLoad(false);
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleFitToScreen = () => {
    setZoom(1);
    setPosition({ x: 0, y: 0 });
    setIsInitialLoad(true);
  };

  const handleActualSize = () => {
    if (!imageRef.current || !containerRef.current || !imageLoaded) {
      console.warn('Image not loaded yet');
      return;
    }

    const containerWidth = containerRef.current.clientWidth;
    const containerHeight = containerRef.current.clientHeight;
    
    const imageWidth = imageRef.current.naturalWidth;
    const imageHeight = imageRef.current.naturalHeight;

    if (!imageWidth || !imageHeight) {
      console.warn('Image dimensions not available');
      return;
    }

    const scaleToFit = Math.min(
      containerWidth / imageWidth,
      containerHeight / imageHeight
    );

    const newZoom = 1 / scaleToFit;
    
    setZoom(newZoom);

    const constrained = applyBoundaryConstraints(0, 0, newZoom);
    setPosition(constrained);
    setIsInitialLoad(false);
  };

  const handleLoadFullSize = () => {
    if (imageSize !== 'full') {
      setImageSize('full');
      setZoom(1);
      setPosition({ x: 0, y: 0 });
      setIsInitialLoad(true);
    }
  };

  const handleReset = () => {
    setZoom(1);
    setPosition({ x: 0, y: 0 });
    // FITS files default to full resolution, others default to large
    const defaultSize = isFitsFile ? 'full' : 'large';
    setImageSize(defaultSize);
    setIsInitialLoad(true);
  };

  const handleToggleExpand = () => {
    setIsExpanded(!isExpanded);
  };

  const getActualZoomPercentage = () => {
    if (!imageRef.current || !containerRef.current || !imageLoaded) {
      return Math.round(zoom * 100);
    }

    const containerWidth = containerRef.current.clientWidth;
    const containerHeight = containerRef.current.clientHeight;
    
    const imageWidth = imageRef.current.naturalWidth;
    const imageHeight = imageRef.current.naturalHeight;

    if (!imageWidth || !imageHeight) {
      return Math.round(zoom * 100);
    }

    const scaleToFit = Math.min(
      containerWidth / imageWidth,
      containerHeight / imageHeight
    );

    const actualZoom = zoom * scaleToFit;
    return Math.round(actualZoom * 100);
  };

  const getTransformScale = () => {
    if (zoom === 1) {
      return 1;
    }
    if (!imageRef.current || !containerRef.current || !imageLoaded) {
      return zoom;
    }
    const containerWidth = containerRef.current.clientWidth;
    const containerHeight = containerRef.current.clientHeight;
    const imageWidth = imageRef.current.naturalWidth;
    const imageHeight = imageRef.current.naturalHeight;
    if (!imageWidth || !imageHeight) {
      return zoom;
    }
    const scaleToFit = Math.min(
      containerWidth / imageWidth,
      containerHeight / imageHeight
    );
    return zoom * scaleToFit;
  };

  const getCursorStyle = () => {
    if (isDragging) return 'grabbing';
    if (zoom > 1) return 'grab';
    return 'default';
  };

  const viewerContent = (
    <div className={`bg-slate-950 overflow-hidden ${isExpanded ? 'fixed inset-0 z-[100]' : 'relative rounded-lg'}`}>
      {/* Top-left filename label */}
      <div className="absolute top-4 left-4 z-10 bg-slate-900/90 backdrop-blur-sm rounded-lg px-3 py-2 border border-white/10 max-w-md">
        <div className="text-xs text-slate-400 truncate" title={filename}>
          {filename}
        </div>
      </div>

      {/* Zoom Navigator Minimap */}
      <ZoomNavigator
        zoom={zoom}
        position={position}
        imageRef={imageRef}
        containerRef={containerRef}
        imageLoaded={imageLoaded}
        onPositionChange={handleZoomNavigatorPositionChange}
      />

      <div className="absolute top-4 right-4 z-10 flex items-center gap-2 bg-slate-900/90 backdrop-blur-sm rounded-lg p-2 border border-white/10">
        <button
          onClick={handleFitToScreen}
          className={`p-2 hover:bg-slate-800 rounded transition ${zoom === 1 ? 'bg-cyan-500/20 text-cyan-400' : ''}`}
          title="Fit to Screen"
        >
          <Maximize className="w-4 h-4" />
        </button>

        <button
          onClick={handleActualSize}
          className="px-2 py-1 hover:bg-slate-800 rounded transition text-xs font-medium text-slate-100"
          title="1:1 Actual Pixels"
        >
          1:1
        </button>

        {defaultRender !== 'HD' && (
          <button
            onClick={handleLoadFullSize}
            className={`px-2 py-1 hover:bg-slate-800 rounded transition text-xs font-medium text-slate-100 ${imageSize === 'full' ? 'bg-cyan-500/20 text-cyan-400' : ''}`}
            title="Load HD Resolution"
          >
            HD
          </button>
        )}

        <div className="w-px h-6 bg-slate-700"></div>

        <button
          onClick={() => onSetFavorite && onSetFavorite(imagePath)}
          className={`p-2 hover:bg-slate-800 rounded transition ${isFavorite ? 'text-yellow-400' : 'text-slate-400'}`}
          title={isFavorite ? "Favorite (used for thumbnail)" : "Set as favorite"}
        >
          <Star className="w-4 h-4" fill={isFavorite ? "currentColor" : "none"} />
        </button>

        {detectedMetadata && (
          <button
            onClick={handleSaveMetadata}
            disabled={savingMetadata}
            className={`p-2 hover:bg-slate-800 rounded transition text-green-400 ${savingMetadata ? 'opacity-50 cursor-not-allowed' : ''}`}
            title={`Save detected metadata (${detectedMetadata.name || detectedMetadata.object_name})`}
          >
            <Save className="w-4 h-4" />
          </button>
        )}

        <button
          onClick={handleToggleExpand}
          className={`p-2 hover:bg-slate-800 rounded transition ${isExpanded ? 'bg-cyan-500/20 text-cyan-400' : ''}`}
          title={isExpanded ? "Exit Fullscreen" : "Fullscreen"}
        >
          {isExpanded ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
        </button>
      </div>

      <div
        ref={containerRef}
        className={`relative w-full overflow-hidden ${isExpanded ? 'h-screen' : 'h-[600px]'}`}
        style={{
          cursor: getCursorStyle(),
          touchAction: 'none',
          overscrollBehavior: 'contain'
        }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-slate-500">Loading image...</div>
          </div>
        ) : imageData && imageData.image ? (
          <div key={imageSize} className="absolute inset-0 flex items-center justify-center">
            <img
              key={imageData.image}
              ref={imageRef}
              src={imageData.image}
              alt={filename}
              className="max-w-none select-none"
              onLoad={handleImageLoad}
              style={{
                transform: `translate(${position.x}px, ${position.y}px) scale(${getTransformScale()})`,
                transformOrigin: 'center',
                transition: (isDragging || !isInitialLoad) ? 'none' : 'transform 0.3s ease-out',
                imageRendering: 'smooth',
                maxHeight: zoom === 1 ? '100%' : 'none',
                maxWidth: zoom === 1 ? '100%' : 'none'
              }}
              draggable={false}
            />
          </div>
        ) : imageData && imageData.error ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-red-400">Error: {imageData.error}</div>
          </div>
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-slate-500">No image data</div>
          </div>
        )}
      </div>

      <div className="absolute bottom-4 left-4 bg-slate-900/90 backdrop-blur-sm rounded-lg px-3 py-2 border border-white/10">
        <div className="text-xs text-slate-400">
          {imageData && imageData.shape && (
            <>
              {imageData.shape[1]} × {imageData.shape[0]} px
              {imageData.stretch && isFitsFile && ` • ${imageData.stretch.toUpperCase()}`}
              {imageData.size && ` • ${imageData.size}`}
              {` • ${getActualZoomPercentage()}%`}
            </>
          )}
          {!imageData && 'Loading...'}
        </div>
      </div>

      {!loading && imageData && imageData.image && (
        <div className="absolute bottom-4 right-4 bg-slate-900/90 backdrop-blur-sm rounded-lg px-3 py-2 border border-white/10">
          <div className="text-xs text-slate-400">
            Scroll: Zoom • Drag: Pan
          </div>
        </div>
      )}
    </div>
  );

  return isExpanded ? createPortal(viewerContent, document.body) : viewerContent;
}

export default ImageViewer;
