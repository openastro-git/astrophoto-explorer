import * as THREE from 'three';
import { raDecToVector3 } from './coordinateUtils';

// Create celestial coordinate grid (RA/Dec)
export const createCelestialGrid = () => {
  const gridGroup = new THREE.Group();
  const gridColor = 0x4a9eff;
  const gridOpacity = 0.15;
  const radius = 99;

  // Declination circles (latitude lines) - every 15 degrees
  for (let dec = -75; dec <= 75; dec += 15) {
    const points = [];
    for (let ra = 0; ra <= 360; ra += 5) {
      points.push(raDecToVector3(ra, dec, radius));
    }
    const geometry = new THREE.BufferGeometry().setFromPoints(points);
    const material = new THREE.LineBasicMaterial({ 
      color: gridColor, 
      opacity: gridOpacity, 
      transparent: true,
      depthTest: false
    });
    const line = new THREE.Line(geometry, material);
    gridGroup.add(line);
  }

  // Right Ascension meridians (longitude lines) - every 2 hours (30 degrees)
  for (let ra = 0; ra < 360; ra += 30) {
    const points = [];
    for (let dec = -90; dec <= 90; dec += 5) {
      points.push(raDecToVector3(ra, dec, radius));
    }
    const geometry = new THREE.BufferGeometry().setFromPoints(points);
    const material = new THREE.LineBasicMaterial({ 
      color: gridColor, 
      opacity: gridOpacity, 
      transparent: true,
      depthTest: false
    });
    const line = new THREE.Line(geometry, material);
    gridGroup.add(line);
  }

  // Add RA hour labels
  for (let hour = 0; hour < 24; hour += 2) {
    const ra = hour * 15; // Convert hours to degrees
    const position = raDecToVector3(ra, 0, radius + 2);
    
    const labelCanvas = document.createElement('canvas');
    labelCanvas.width = 128;
    labelCanvas.height = 64;
    const ctx = labelCanvas.getContext('2d');
    ctx.font = 'bold 32px -apple-system, BlinkMacSystemFont, avenir next, avenir, segoe ui, helvetica neue, Adwaita Sans, Cantarell, Ubuntu, roboto, noto, helvetica, arial, sans-serif';
    ctx.fillStyle = '#4a9eff';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.shadowColor = 'rgba(0, 0, 0, 0.9)';
    ctx.shadowBlur = 6;
    ctx.fillText(`${hour}h`, labelCanvas.width / 2, labelCanvas.height / 2);
    
    const texture = new THREE.CanvasTexture(labelCanvas);
    const spriteMaterial = new THREE.SpriteMaterial({ 
      map: texture, 
      transparent: true,
      opacity: 0.7,
      depthTest: false
    });
    const sprite = new THREE.Sprite(spriteMaterial);
    sprite.position.copy(position);
    sprite.scale.set(8, 4, 1);
    gridGroup.add(sprite);
  }

  return gridGroup;
};
