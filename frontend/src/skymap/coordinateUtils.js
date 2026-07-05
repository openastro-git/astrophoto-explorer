import * as THREE from 'three';

// Convert RA/Dec to 3D position on sphere
export const raDecToVector3 = (ra, dec, radius = 100) => {
  // Convert RA (0-360°) and Dec (-90 to 90°) to spherical coordinates
  // RA increases eastward, so we negate it for proper orientation
  const phi = THREE.MathUtils.degToRad(90 - dec); // Polar angle from north pole
  const theta = THREE.MathUtils.degToRad(-ra); // Azimuthal angle (negated for celestial coords)
  
  return new THREE.Vector3(
    radius * Math.sin(phi) * Math.cos(theta),
    radius * Math.cos(phi),
    radius * Math.sin(phi) * Math.sin(theta)
  );
};

// Update stereographic projection matrix
export const updateStereographicProjection = (camera) => {
  const aspect = camera.aspect;
  const fov = camera.fov * Math.PI / 180; // Convert to radians
  const near = camera.near;
  const far = camera.far;
  
  // Stereographic projection: tan(θ/2) instead of tan(θ) for perspective
  // This reduces the fisheye effect at wide angles
  const top = near * Math.tan(fov / 4); // Divide by 4 instead of 2 for stereographic
  const height = 2 * top;
  const width = aspect * height;
  const left = -0.5 * width;
  
  // Build custom projection matrix for stereographic projection
  const x = 2 * near / width;
  const y = 2 * near / height;
  const a = (far + near) / (near - far);
  const b = 2 * far * near / (near - far);
  
  camera.projectionMatrix.set(
    x, 0, 0, 0,
    0, y, 0, 0,
    0, 0, a, b,
    0, 0, -1, 0
  );
  camera.projectionMatrixInverse.copy(camera.projectionMatrix).invert();
};
