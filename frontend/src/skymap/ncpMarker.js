import * as THREE from 'three';
import { raDecToVector3 } from './coordinateUtils';

// Create North Celestial Pole marker
export const createNCPMarker = () => {
  const group = new THREE.Group();
  const radius = 99.5;
  const ncpPosition = raDecToVector3(0, 90, radius);
  
  // Create crosshair marker (smaller)
  const crosshairSize = 3;
  const crosshairGeometry = new THREE.BufferGeometry();
  const crosshairVertices = new Float32Array([
    ncpPosition.x - crosshairSize, ncpPosition.y, ncpPosition.z,
    ncpPosition.x + crosshairSize, ncpPosition.y, ncpPosition.z,
    ncpPosition.x, ncpPosition.y, ncpPosition.z - crosshairSize,
    ncpPosition.x, ncpPosition.y, ncpPosition.z + crosshairSize,
  ]);
  crosshairGeometry.setAttribute('position', new THREE.BufferAttribute(crosshairVertices, 3));
  const crosshairMaterial = new THREE.LineBasicMaterial({ 
    color: 0xffeb3b, 
    opacity: 0.9, 
    transparent: true,
    depthTest: false,
    linewidth: 2
  });
  const crosshair = new THREE.LineSegments(crosshairGeometry, crosshairMaterial);
  group.add(crosshair);
  
  // Create circle around NCP (smaller)
  const circlePoints = [];
  for (let i = 0; i <= 32; i++) {
    const angle = (i / 32) * Math.PI * 2;
    const x = ncpPosition.x + Math.cos(angle) * 2;
    const z = ncpPosition.z + Math.sin(angle) * 2;
    circlePoints.push(new THREE.Vector3(x, ncpPosition.y, z));
  }
  const circleGeometry = new THREE.BufferGeometry().setFromPoints(circlePoints);
  const circleMaterial = new THREE.LineBasicMaterial({ 
    color: 0xffeb3b, 
    opacity: 0.9, 
    transparent: true,
    depthTest: false
  });
  const circle = new THREE.Line(circleGeometry, circleMaterial);
  group.add(circle);
  
  // Add label (keep same size)
  const labelCanvas = document.createElement('canvas');
  labelCanvas.width = 512;
  labelCanvas.height = 64;
  const ctx = labelCanvas.getContext('2d');
  ctx.font = 'bold 36px -apple-system, BlinkMacSystemFont, avenir next, avenir, segoe ui, helvetica neue, Adwaita Sans, Cantarell, Ubuntu, roboto, noto, helvetica, arial, sans-serif';
  ctx.fillStyle = '#ffeb3b';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.shadowColor = 'rgba(0, 0, 0, 0.9)';
  ctx.shadowBlur = 8;
  ctx.fillText('North Celestial Pole', labelCanvas.width / 2, labelCanvas.height / 2);
  
  const texture = new THREE.CanvasTexture(labelCanvas);
  const spriteMaterial = new THREE.SpriteMaterial({ 
    map: texture, 
    transparent: true,
    opacity: 0.9,
    depthTest: false
  });
  const sprite = new THREE.Sprite(spriteMaterial);
  sprite.position.copy(new THREE.Vector3(ncpPosition.x, ncpPosition.y - 5, ncpPosition.z));
  sprite.scale.set(18, 2.5, 1);
  group.add(sprite);
  
  return group;
};
