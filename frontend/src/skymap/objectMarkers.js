import * as THREE from 'three';
import { raDecToVector3 } from './coordinateUtils';

// Helper function to create a circular marker texture
const createCircleTexture = () => {
  const canvas = document.createElement('canvas');
  canvas.width = 64;
  canvas.height = 64;
  const ctx = canvas.getContext('2d');
  
  // Draw circle with glow
  const centerX = canvas.width / 2;
  const centerY = canvas.height / 2;
  const radius = 12;
  
  // Outer glow
  const gradient = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, radius);
  gradient.addColorStop(0, 'rgba(6, 182, 212, 1)');
  gradient.addColorStop(0.7, 'rgba(6, 182, 212, 0.8)');
  gradient.addColorStop(1, 'rgba(6, 182, 212, 0)');
  
  ctx.fillStyle = gradient;
  ctx.beginPath();
  ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
  ctx.fill();
  
  // Inner bright circle
  ctx.fillStyle = 'rgba(6, 182, 212, 1)';
  ctx.beginPath();
  ctx.arc(centerX, centerY, radius * 0.6, 0, Math.PI * 2);
  ctx.fill();
  
  return canvas;
};

// Calculate angular distance between two RA/Dec positions (in degrees)
const angularDistance = (ra1, dec1, ra2, dec2) => {
  const toRad = Math.PI / 180;
  const dRa = (ra2 - ra1) * toRad;
  const dDec = (dec2 - dec1) * toRad;
  const lat1 = dec1 * toRad;
  const lat2 = dec2 * toRad;
  
  const a = Math.sin(dDec / 2) ** 2 + 
            Math.cos(lat1) * Math.cos(lat2) * Math.sin(dRa / 2) ** 2;
  const c = 2 * Math.asin(Math.sqrt(a));
  return c * 180 / Math.PI; // Return in degrees
};

// Group nearby objects into clusters
const clusterObjects = (objects, fov) => {
  // Threshold based on FOV - closer objects need clustering
  const threshold = Math.max(0.5, fov / 40); // Adaptive threshold
  const clusters = [];
  const processed = new Set();
  
  objects.forEach((obj, i) => {
    if (processed.has(i)) return;
    
    const cluster = [obj];
    processed.add(i);
    
    // Find all objects within threshold distance
    objects.forEach((other, j) => {
      if (i === j || processed.has(j)) return;
      
      const dist = angularDistance(
        obj.astrometry.ra, obj.astrometry.dec,
        other.astrometry.ra, other.astrometry.dec
      );
      
      if (dist < threshold) {
        cluster.push(other);
        processed.add(j);
      }
    });
    
    clusters.push(cluster);
  });
  
  return clusters;
};

// "Clock Face" positioning - arrange labels around a central point
const getClockPosition = (index, total, radius = 4) => {
  if (total === 1) return { x: 0, y: radius };
  
  // Distribute evenly around a circle
  const angle = (index / total) * Math.PI * 2 - Math.PI / 2; // Start at top
  return {
    x: Math.cos(angle) * radius,
    y: Math.sin(angle) * radius
  };
};

// Create object markers for groups with coordinates
export const createObjectMarkers = (groups, fov = 120) => {
  const markers = [];
  const objectsWithCoords = groups.filter(g => 
    g.astrometry && 
    g.astrometry.ra !== undefined && 
    g.astrometry.dec !== undefined
  );
  
  // Cluster nearby objects
  const clusters = clusterObjects(objectsWithCoords, fov);
  
  const circleTexture = new THREE.CanvasTexture(createCircleTexture());
  
  clusters.forEach(cluster => {
    if (cluster.length === 1) {
      // Single object - normal display
      const group = cluster[0];
      const position = raDecToVector3(group.astrometry.ra, group.astrometry.dec, 102);
      
      const markerMaterial = new THREE.SpriteMaterial({ 
        map: circleTexture,
        transparent: true,
        opacity: 0.9,
        depthTest: false,
        depthWrite: false
      });
      const markerSprite = new THREE.Sprite(markerMaterial);
      markerSprite.position.copy(position);
      markerSprite.scale.set(2, 2, 1);
      markerSprite.userData = { group, baseScale: 2, isCluster: false };
      markerSprite.renderOrder = 100;
      
      const sprite = createLabel(group.object, position, 3);
      sprite.userData = { 
        baseScale: 12, 
        markerPos: position.clone(),
        group,
        isCluster: false,
        minFov: 0 // Always visible
      };
      
      markers.push({ mesh: markerSprite, sprite, group, isCluster: false });
      
    } else {
      // Multiple objects close together - use clock face positioning
      const centerRa = cluster.reduce((sum, g) => sum + g.astrometry.ra, 0) / cluster.length;
      const centerDec = cluster.reduce((sum, g) => sum + g.astrometry.dec, 0) / cluster.length;
      const centerPos = raDecToVector3(centerRa, centerDec, 102);
      
      // Sort by brightness/importance if available, otherwise alphabetically
      cluster.sort((a, b) => a.object.localeCompare(b.object));
      
      cluster.forEach((group, index) => {
        const position = raDecToVector3(group.astrometry.ra, group.astrometry.dec, 102);
        
        // Create marker
        const markerMaterial = new THREE.SpriteMaterial({ 
          map: circleTexture,
          transparent: true,
          opacity: 0.9,
          depthTest: false,
          depthWrite: false
        });
        const markerSprite = new THREE.Sprite(markerMaterial);
        markerSprite.position.copy(position);
        markerSprite.scale.set(2, 2, 1);
        markerSprite.userData = { 
          group, 
          baseScale: 2, 
          isCluster: true,
          clusterSize: cluster.length 
        };
        markerSprite.renderOrder = 100;
        
        // Progressive disclosure: show fewer labels when zoomed out
        const minFovForLabel = getMinFovForCluster(cluster.length, index);
        
        // Clock face positioning
        const clockPos = getClockPosition(index, cluster.length);
        const labelOffset = new THREE.Vector3(
          clockPos.x,
          clockPos.y,
          0
        );
        
        const labelPos = position.clone().add(labelOffset);
        
        const sprite = createLabel(group.object, labelPos, 0);
        sprite.userData = { 
          baseScale: 12,
          markerPos: position.clone(),
          group,
          isCluster: true,
          clusterSize: cluster.length,
          minFov: minFovForLabel,
          clockIndex: index
        };
        
        markers.push({ 
          mesh: markerSprite, 
          sprite, 
          group, 
          isCluster: true,
          clusterSize: cluster.length 
        });
      });
    }
  });
  
  return markers;
};

// Helper to create label sprite
const createLabel = (text, position, yOffset = 3) => {
  const labelCanvas = document.createElement('canvas');
  labelCanvas.width = 512;
  labelCanvas.height = 64;
  const ctx = labelCanvas.getContext('2d');
  ctx.font = 'bold 36px -apple-system, BlinkMacSystemFont, avenir next, avenir, segoe ui, helvetica neue, Adwaita Sans, Cantarell, Ubuntu, roboto, noto, helvetica, arial, sans-serif';
  ctx.fillStyle = '#e2e8f0';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.shadowColor = 'rgba(0, 0, 0, 0.9)';
  ctx.shadowBlur = 8;
  ctx.fillText(text, labelCanvas.width / 2, labelCanvas.height / 2);
  
  const texture = new THREE.CanvasTexture(labelCanvas);
  const spriteMaterial = new THREE.SpriteMaterial({ 
    map: texture, 
    transparent: true,
    depthTest: false,
    depthWrite: false
  });
  const sprite = new THREE.Sprite(spriteMaterial);
  
  sprite.position.set(position.x, position.y + yOffset, position.z);
  sprite.scale.set(12, 1.5, 1);
  sprite.renderOrder = 200;
  
  return sprite;
};

// Determine minimum FOV needed to show this label (progressive disclosure)
const getMinFovForCluster = (clusterSize, index) => {
  if (clusterSize <= 2) return 0; // Always show if only 2 objects
  if (clusterSize <= 4) return index < 2 ? 0 : 60; // Show 2 at wide FOV, rest when zoomed
  if (clusterSize <= 6) return index < 2 ? 0 : index < 4 ? 60 : 40; // Progressive
  // For larger clusters, show progressively more as you zoom in
  if (index < 2) return 0;
  if (index < 4) return 80;
  if (index < 6) return 60;
  return 40;
};

// Update label visibility based on current FOV (call this from render loop)
export const updateLabelVisibility = (markers, fov) => {
  markers.forEach(marker => {
    if (marker.sprite && marker.sprite.userData.minFov !== undefined) {
      const shouldShow = fov <= marker.sprite.userData.minFov || marker.sprite.userData.minFov === 0;
      marker.sprite.visible = shouldShow;
    }
  });
};
