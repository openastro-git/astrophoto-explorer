import * as THREE from 'three';
import { raDecToVector3 } from './coordinateUtils';

// Create celestial equator
export const createCelestialEquator = () => {
  const points = [];
  const radius = 99.5;
  for (let ra = 0; ra <= 360; ra += 2) {
    points.push(raDecToVector3(ra, 0, radius));
  }
  const geometry = new THREE.BufferGeometry().setFromPoints(points);
  const material = new THREE.LineBasicMaterial({ 
    color: 0xff6b35, 
    opacity: 0.8, 
    transparent: true,
    depthTest: false,
    linewidth: 2
  });
  const line = new THREE.Line(geometry, material);
  
  // Add label
  const labelCanvas = document.createElement('canvas');
  labelCanvas.width = 512;
  labelCanvas.height = 64;
  const ctx = labelCanvas.getContext('2d');
  ctx.font = 'bold 36px -apple-system, BlinkMacSystemFont, avenir next, avenir, segoe ui, helvetica neue, Adwaita Sans, Cantarell, Ubuntu, roboto, noto, helvetica, arial, sans-serif';
  ctx.fillStyle = '#ff6b35';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.shadowColor = 'rgba(0, 0, 0, 0.9)';
  ctx.shadowBlur = 8;
  ctx.fillText('Celestial Equator', labelCanvas.width / 2, labelCanvas.height / 2);
  
  const texture = new THREE.CanvasTexture(labelCanvas);
  const spriteMaterial = new THREE.SpriteMaterial({ 
    map: texture, 
    transparent: true,
    opacity: 0.9,
    depthTest: false
  });
  const sprite = new THREE.Sprite(spriteMaterial);
  sprite.position.copy(raDecToVector3(90, 0, radius + 3));
  sprite.scale.set(15, 2, 1);
  
  const group = new THREE.Group();
  group.add(line);
  group.add(sprite);
  return group;
};
