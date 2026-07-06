import * as THREE from 'three';

// Create Milky Way sphere with texture
export const createMilkyWay = (milkyWayImage, milkyWayOpacity, onLoad) => {
  const textureLoader = new THREE.TextureLoader();
  
  textureLoader.load(milkyWayImage, (texture) => {
    const geometry = new THREE.SphereGeometry(95, 64, 64);
    
    // Simple shader that just wraps the texture as-is (cylindrical projection)
    const material = new THREE.ShaderMaterial({
      uniforms: {
        milkyWayTexture: { value: texture },
        opacity: { value: milkyWayOpacity },
        flipH: { value: 1.0 }
      },
      vertexShader: `
        varying vec2 vUv;
        
        void main() {
          vUv = uv;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        uniform sampler2D milkyWayTexture;
        uniform float opacity;
        uniform float flipH;
        varying vec2 vUv;
        
        void main() {
          vec2 uv = vUv;
          if (flipH > 0.5) {
            uv.x = 1.0 - uv.x;
          }
          vec4 color = texture2D(milkyWayTexture, uv);
          gl_FragColor = vec4(color.rgb, color.a * opacity);
        }
      `,
      side: THREE.BackSide,
      transparent: true,
      depthWrite: false // Don't write to depth buffer so stars can render through
    });
    
    const milkyWay = new THREE.Mesh(geometry, material);
    milkyWay.renderOrder = 0; // Render Milky Way first (before stars)
    
    // Apply final tweaked rotation values
    milkyWay.rotation.x = 117.4 * Math.PI / 180;
    milkyWay.rotation.y = -29.2 * Math.PI / 180;
    milkyWay.rotation.z = 90.2 * Math.PI / 180;
    
    onLoad(milkyWay, material);
  });
};
