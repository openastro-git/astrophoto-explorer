import * as THREE from 'three';
import { raDecToVector3 } from './coordinateUtils';

// Create stars point cloud
export const createStars = (starsData, constellationLines) => {
  const starGeometry = new THREE.BufferGeometry();
  const starCount = starsData.features.length;
  const starPositions = new Float32Array(starCount * 3);
  const starColors = new Float32Array(starCount * 3);
  const starSizes = new Float32Array(starCount);

  // Extract constellation star coordinates to identify which stars are part of constellations
  const constellationStars = new Set();
  if (constellationLines) {
    constellationLines.features.forEach(feature => {
      if (feature.geometry.type === 'MultiLineString') {
        feature.geometry.coordinates.forEach(lineString => {
          lineString.forEach(([ra, dec]) => {
            const key = `${ra.toFixed(4)},${dec.toFixed(4)}`;
            constellationStars.add(key);
          });
        });
      }
    });
  }

  starsData.features.forEach((star, i) => {
    const [ra, dec] = star.geometry.coordinates;
    const pos = raDecToVector3(ra, dec, 100);
    
    const i3 = i * 3;
    starPositions[i3] = pos.x;
    starPositions[i3 + 1] = pos.y;
    starPositions[i3 + 2] = pos.z;
    
    // Color based on B-V index
    const bv = star.properties.bv || 0.5;
    let color;
    if (bv < 0) color = new THREE.Color(0x9bb0ff);
    else if (bv < 0.3) color = new THREE.Color(0xaabfff);
    else if (bv < 0.6) color = new THREE.Color(0xf8f7ff);
    else if (bv < 1.0) color = new THREE.Color(0xfff4ea);
    else if (bv < 1.5) color = new THREE.Color(0xffd2a1);
    else color = new THREE.Color(0xffcc6f);
    
    starColors[i3] = color.r;
    starColors[i3 + 1] = color.g;
    starColors[i3 + 2] = color.b;
    
    // Size based on magnitude (brighter stars = lower magnitude = bigger size)
    const mag = star.properties.mag;
    let size = Math.max(1.2, 7.5 - mag * 0.9);
    
    // Make constellation stars a bit bigger
    const key = `${ra.toFixed(4)},${dec.toFixed(4)}`;
    if (constellationStars.has(key)) {
      size = size * 1.5 + 0.5;
    }
    
    starSizes[i] = size;
  });

  starGeometry.setAttribute('position', new THREE.BufferAttribute(starPositions, 3));
  starGeometry.setAttribute('color', new THREE.BufferAttribute(starColors, 3));
  starGeometry.setAttribute('size', new THREE.BufferAttribute(starSizes, 1));
  starGeometry.computeBoundingSphere();

  const starMaterial = new THREE.ShaderMaterial({
    uniforms: {
      pointTexture: { value: new THREE.TextureLoader().load('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAQAAAAECAYAAACp8Z5+AAAAG0lEQVQYV2NkYGD4z8DAwMgABXAGjgEyDKgKAB5SAQXXw1jTAAAAAElFTkSuQmCC') },
      fovScale: { value: 1.0 }
    },
    vertexShader: `
      attribute float size;
      attribute vec3 color;
      varying vec3 vColor;
      uniform float fovScale;
      
      void main() {
        vColor = color;
        vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
        gl_PointSize = size * fovScale;
        gl_Position = projectionMatrix * mvPosition;
      }
    `,
    fragmentShader: `
      varying vec3 vColor;
      
      void main() {
        vec2 center = gl_PointCoord - vec2(0.5);
        float dist = length(center);
        if (dist > 0.5) discard;
        
        // Normalize distance to 0.0 - 1.0 range
        float r = dist * 2.0;
        
        // White core: Gaussian distribution at the center (narrow peak)
        float core = exp(- (r * r) * 9.0);
        
        // Colored glow: wider Gaussian distribution (representing PSF/scattering)
        float glow = exp(- (r * r) * 1.5);
        
        // Soft edge fade to ensure it reaches absolute 0 at the boundary (r = 1.0)
        float edgeFade = 1.0 - smoothstep(0.75, 1.0, r);
        float finalGlow = glow * edgeFade;
        
        // Blend star color and white core
        vec3 finalColor = mix(vColor, vec3(1.0), core);
        
        // Calculate transparency (ensure core is opaque and glow fades out)
        float alpha = max(core, finalGlow);
        
        gl_FragColor = vec4(finalColor * alpha, alpha);
      }
    `,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending
  });

  const stars = new THREE.Points(starGeometry, starMaterial);
  stars.frustumCulled = false;
  stars.renderOrder = 1;
  stars.matrixAutoUpdate = false;
  stars.updateMatrix();
  
  return stars;
};
