import * as THREE from 'three';
import { raDecToVector3 } from './coordinateUtils';
import { constellationNames } from './constants';

// Create constellation lines and labels
export const createConstellations = (constellationLines) => {
  const lines = [];
  const labels = [];

  constellationLines.features.forEach(feature => {
    if (feature.geometry.type === 'MultiLineString') {
      feature.geometry.coordinates.forEach(lineString => {
        const points = lineString.map(([ra, dec]) => raDecToVector3(ra, dec, 100));
        const geometry = new THREE.BufferGeometry().setFromPoints(points);
        
        // Glow layer (thicker, more transparent)
        const glowMaterial = new THREE.LineBasicMaterial({ 
          color: 0x6496c8, 
          opacity: 0.15, 
          transparent: true,
          depthWrite: false,
          linewidth: 4
        });
        const glowLine = new THREE.Line(geometry.clone(), glowMaterial);
        glowLine.renderOrder = -1;
        lines.push(glowLine);
        
        // Main line (thinner, more opaque)
        const material = new THREE.LineBasicMaterial({ 
          color: 0x6496c8, 
          opacity: 0.6, 
          transparent: true,
          depthWrite: false,
          linewidth: 2
        });
        const line = new THREE.Line(geometry, material);
        lines.push(line);
      });
      
      // Add constellation label at center of first line
      if (feature.geometry.coordinates.length > 0 && feature.geometry.coordinates[0].length > 0) {
        const midIndex = Math.floor(feature.geometry.coordinates[0].length / 2);
        const [ra, dec] = feature.geometry.coordinates[0][midIndex];
        const position = raDecToVector3(ra, dec, 101);
        const fullName = constellationNames[feature.id] || feature.id;
        
        // Create label canvas
        const labelCanvas = document.createElement('canvas');
        labelCanvas.width = 512;
        labelCanvas.height = 64;
        const ctx = labelCanvas.getContext('2d');
        ctx.font = '32px -apple-system, BlinkMacSystemFont, avenir next, avenir, segoe ui, helvetica neue, Adwaita Sans, Cantarell, Ubuntu, roboto, noto, helvetica, arial, sans-serif';
        ctx.fillStyle = '#cbd5e1';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.shadowColor = 'rgba(0, 0, 0, 0.9)';
        ctx.shadowBlur = 8;
        ctx.fillText(fullName, labelCanvas.width / 2, labelCanvas.height / 2);
        
        const texture = new THREE.CanvasTexture(labelCanvas);
        const spriteMaterial = new THREE.SpriteMaterial({ 
          map: texture, 
          transparent: true,
          opacity: 0.8,
          depthTest: false
        });
        const sprite = new THREE.Sprite(spriteMaterial);
        sprite.position.copy(position);
        
        labels.push({ sprite, baseScale: 15 });
      }
    }
  });

  return { lines, labels };
};
