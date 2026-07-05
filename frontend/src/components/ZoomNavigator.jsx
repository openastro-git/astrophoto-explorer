import { useEffect, useRef, useState } from 'react';

/**
 * ZoomNavigator - A minimap component that shows the current viewport position
 * when zoomed in on an image, similar to photo editing software.
 * 
 * @param {Object} props
 * @param {number} props.zoom - Current zoom level (1 = fit to screen)
 * @param {Object} props.position - Current pan position {x, y}
 * @param {Object} props.imageRef - Reference to the main image element
 * @param {Object} props.containerRef - Reference to the image container
 * @param {boolean} props.imageLoaded - Whether the image has loaded
 * @param {Function} props.onPositionChange - Callback to update main image position
 */
function ZoomNavigator({ zoom, position, imageRef, containerRef, imageLoaded, onPositionChange }) {
  const canvasRef = useRef(null);
  const [isVisible, setIsVisible] = useState(false);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [viewportRect, setViewportRect] = useState({ x: 0, y: 0, width: 0, height: 0 });
  const [minimapScale, setMinimapScale] = useState(1);

  // Only show when zoomed in beyond fit-to-screen
  useEffect(() => {
    setIsVisible(zoom > 1 && imageLoaded);
  }, [zoom, imageLoaded]);

  // Calculate viewport rectangle and draw minimap
  useEffect(() => {
    if (!isVisible || !canvasRef.current || !imageRef.current || !containerRef.current) {
      return;
    }

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const img = imageRef.current;
    const container = containerRef.current;

    // Get dimensions
    const imageWidth = img.naturalWidth;
    const imageHeight = img.naturalHeight;
    const containerRect = container.getBoundingClientRect();
    const containerWidth = containerRect.width;
    const containerHeight = containerRect.height;

    if (!imageWidth || !imageHeight) return;

    // Calculate minimap size (max 150x150, maintain aspect ratio)
    const maxMinimapSize = 150;
    const imageAspect = imageWidth / imageHeight;
    let minimapWidth, minimapHeight;

    if (imageAspect > 1) {
      minimapWidth = Math.min(maxMinimapSize, imageWidth / 10);
      minimapHeight = minimapWidth / imageAspect;
    } else {
      minimapHeight = Math.min(maxMinimapSize, imageHeight / 10);
      minimapWidth = minimapHeight * imageAspect;
    }

    // Set canvas size
    canvas.width = minimapWidth;
    canvas.height = minimapHeight;
    setDimensions({ width: minimapWidth, height: minimapHeight });

    // Draw image thumbnail
    ctx.clearRect(0, 0, minimapWidth, minimapHeight);
    
    // Draw the full image as thumbnail
    try {
      ctx.drawImage(img, 0, 0, minimapWidth, minimapHeight);
    } catch (e) {
      // If image isn't ready, draw a placeholder
      ctx.fillStyle = '#1e293b';
      ctx.fillRect(0, 0, minimapWidth, minimapHeight);
    }

    // Calculate viewport rectangle in minimap coordinates
    const scaleToFit = Math.min(
      containerWidth / imageWidth,
      containerHeight / imageHeight
    );

    // Viewport rectangle size in image coordinates (this is FIXED based on container size and zoom)
    const viewportWidthInImage = containerWidth / (scaleToFit * zoom);
    const viewportHeightInImage = containerHeight / (scaleToFit * zoom);

    // Convert to minimap coordinates
    const scale = minimapWidth / imageWidth;
    setMinimapScale(scale);
    
    // Fixed viewport rectangle size in minimap
    const rectWidth = viewportWidthInImage * scale;
    const rectHeight = viewportHeightInImage * scale;

    // The image is displayed centered and scaled by (scaleToFit * zoom)
    // position.x and position.y represent the offset of the image center from container center
    
    // When position = {0, 0}, the image center is at container center
    // The top-left of the image in container coords would be:
    const displayedWidth = imageWidth * scaleToFit * zoom;
    const displayedHeight = imageHeight * scaleToFit * zoom;
    const imageLeftInContainer = (containerWidth - displayedWidth) / 2 + position.x;
    const imageTopInContainer = (containerHeight - displayedHeight) / 2 + position.y;

    // Top-left corner of viewport in image coordinates
    // Container top-left (0, 0) maps to which point in the image?
    const visibleLeft = -imageLeftInContainer / (scaleToFit * zoom);
    const visibleTop = -imageTopInContainer / (scaleToFit * zoom);

    // Convert to minimap coordinates
    const rectX = visibleLeft * scale;
    const rectY = visibleTop * scale;

    setViewportRect({ x: rectX, y: rectY, width: rectWidth, height: rectHeight });

    // Draw semi-transparent overlay outside viewport
    ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
    
    // Top
    ctx.fillRect(0, 0, minimapWidth, rectY);
    // Bottom
    ctx.fillRect(0, rectY + rectHeight, minimapWidth, minimapHeight - rectY - rectHeight);
    // Left
    ctx.fillRect(0, rectY, rectX, rectHeight);
    // Right
    ctx.fillRect(rectX + rectWidth, rectY, minimapWidth - rectX - rectWidth, rectHeight);

    // Draw viewport rectangle
    ctx.strokeStyle = '#06b6d4'; // cyan-500
    ctx.lineWidth = 2;
    ctx.strokeRect(rectX, rectY, rectWidth, rectHeight);

  }, [isVisible, zoom, position, imageLoaded]);

  // Handle dragging the viewport rectangle
  const handleMouseDown = (e) => {
    if (!canvasRef.current) return;
    
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    // Check if click is inside viewport rectangle
    if (
      x >= viewportRect.x &&
      x <= viewportRect.x + viewportRect.width &&
      y >= viewportRect.y &&
      y <= viewportRect.y + viewportRect.height
    ) {
      // Store the offset from the rectangle's center
      const rectCenterX = viewportRect.x + viewportRect.width / 2;
      const rectCenterY = viewportRect.y + viewportRect.height / 2;
      setDragOffset({
        x: x - rectCenterX,
        y: y - rectCenterY
      });
      setIsDragging(true);
      e.preventDefault();
      e.stopPropagation();
    }
  };

  const handleMouseMove = (e) => {
    if (!isDragging || !canvasRef.current || !imageRef.current || !containerRef.current) return;

    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    // Adjust for the drag offset to keep the grab point consistent
    const rectCenterX = mouseX - dragOffset.x;
    const rectCenterY = mouseY - dragOffset.y;

    const img = imageRef.current;
    const container = containerRef.current;
    const imageWidth = img.naturalWidth;
    const imageHeight = img.naturalHeight;
    const containerRect = container.getBoundingClientRect();
    const containerWidth = containerRect.width;
    const containerHeight = containerRect.height;

    // Calculate scale to fit
    const scaleToFit = Math.min(
      containerWidth / imageWidth,
      containerHeight / imageHeight
    );

    // Convert rect center from minimap coords to image coords
    const imageCenterX = rectCenterX / minimapScale;
    const imageCenterY = rectCenterY / minimapScale;

    // Calculate viewport size in image coordinates
    const viewportWidthInImage = containerWidth / (scaleToFit * zoom);
    const viewportHeightInImage = containerHeight / (scaleToFit * zoom);

    // The viewport center in image coords should be at imageCenterX, imageCenterY
    // Calculate where the image needs to be positioned
    const displayedWidth = imageWidth * scaleToFit * zoom;
    const displayedHeight = imageHeight * scaleToFit * zoom;

    // We want imageCenterX/Y to be at the center of the container
    // Image center in container = containerWidth/2, containerHeight/2
    // Point imageCenterX in image should be at container center
    const imageLeftInContainer = containerWidth / 2 - imageCenterX * scaleToFit * zoom;
    const imageTopInContainer = containerHeight / 2 - imageCenterY * scaleToFit * zoom;

    // position.x/y is the offset from the default centered position
    const defaultLeft = (containerWidth - displayedWidth) / 2;
    const defaultTop = (containerHeight - displayedHeight) / 2;

    const newX = imageLeftInContainer - defaultLeft;
    const newY = imageTopInContainer - defaultTop;

    onPositionChange({ x: newX, y: newY });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  useEffect(() => {
    if (isDragging) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
      return () => {
        window.removeEventListener('mousemove', handleMouseMove);
        window.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDragging, viewportRect, minimapScale, dragOffset]);

  if (!isVisible) {
    return null;
  }

  return (
    <div 
      className="absolute bottom-4 right-4 z-10 bg-slate-900/70 backdrop-blur-sm rounded border border-white/10 shadow-xl cursor-pointer"
      style={{
        width: dimensions.width + 4,
        height: dimensions.height + 4,
        padding: '2px'
      }}
      onMouseDown={handleMouseDown}
    >
      <canvas
        ref={canvasRef}
        className="rounded"
        style={{
          display: 'block',
          imageRendering: 'auto',
          cursor: isDragging ? 'grabbing' : 'grab'
        }}
      />
    </div>
  );
}

export default ZoomNavigator;
