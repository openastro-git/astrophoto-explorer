import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import milkyWayImage from '../data/img/eso0932a.jpg';

// Import refactored modules
import { raDecToVector3, updateStereographicProjection } from './skymap/coordinateUtils';
import { useThreeScene } from './skymap/useThreeScene';
import { createStars } from './skymap/stars';
import { createMilkyWay } from './skymap/milkyWay';
import { createConstellations } from './skymap/constellations';
import { createCelestialGrid } from './skymap/celestialGrid';
import { createCelestialEquator } from './skymap/celestialEquator';
import { createNCPMarker } from './skymap/ncpMarker';
import { createObjectMarkers, updateLabelVisibility } from './skymap/objectMarkers';
import NavigationToolbar from './skymap/NavigationToolbar';
import InfoPanel from './skymap/InfoPanel';
import ObjectTooltip from './skymap/ObjectTooltip';

function SkyMapThree({ groups, onObjectClick, milkyWayOpacity = 0.35, searchQuery = '', targetObject = '', onTargetReached }) {
  const containerRef = useRef(null);
  const { sceneRef, cameraRef, rendererRef, animationFrameRef } = useThreeScene(containerRef, 120);

  const [dataLoaded, setDataLoaded] = useState(false);
  const [loadedData, setLoadedData] = useState({ stars: null, constellations: null });

  // Load star and constellation catalog data asynchronously on mount
  useEffect(() => {
    let active = true;
    Promise.all([
      fetch('./assets/data/stars.6.json').then(res => {
        if (!res.ok) throw new Error('Failed to load stars database');
        return res.json();
      }),
      fetch('./assets/data/constellations.lines.json').then(res => {
        if (!res.ok) throw new Error('Failed to load constellations database');
        return res.json();
      })
    ]).then(([stars, constellations]) => {
      if (active) {
        setLoadedData({ stars, constellations });
        setDataLoaded(true);
      }
    }).catch(err => {
      console.error('Error loading celestial data assets:', err);
    });
    return () => {
      active = false;
    };
  }, []);

  const controlsRef = useRef({
    isDragging: false,
    previousMouse: { x: 0, y: 0 },
    isAnimating: false,
    animationStartTime: 0,
    animationDuration: 1000,
    startQuaternion: new THREE.Quaternion(),
    targetQuaternion: new THREE.Quaternion()
  });

  const labelsRef = useRef([]);
  const objectMarkersRef = useRef([]);
  const milkyWayMeshRef = useRef(null);
  const milkyWayMaterialRef = useRef(null);
  const needsRenderRef = useRef(true);
  const lastRaycastTimeRef = useRef(0);
  const isInteractingRef = useRef(false);
  const lastInteractionTimeRef = useRef(0);
  const targetFpsRef = useRef(1);
  const starsRef = useRef(null);
  const celestialGridRef = useRef(null);
  const celestialEquatorRef = useRef(null);
  const ncpMarkerRef = useRef(null);

  const [hoveredObject, setHoveredObject] = useState(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });
  const [fov, setFov] = useState(120);
  const [showCelestialGrid, setShowCelestialGrid] = useState(true);
  const [showCelestialEquator, setShowCelestialEquator] = useState(true);

  // Level camera to celestial equator with animation
  const levelToEquator = () => {
    if (!cameraRef.current) return;

    const camera = cameraRef.current;
    const forward = new THREE.Vector3(0, 0, -1);
    forward.applyQuaternion(camera.quaternion);

    // Project forward onto the celestial equator plane (X-Z plane)
    const targetForward = new THREE.Vector3(forward.x, 0, forward.z);

    // Handle pole singularity
    if (targetForward.lengthSq() < 0.0001) {
      const localUp = new THREE.Vector3(0, 1, 0).applyQuaternion(camera.quaternion);
      targetForward.copy(localUp);
      targetForward.y = 0;
    }
    if (targetForward.lengthSq() < 0.0001) {
      targetForward.set(0, 0, -1);
    }
    targetForward.normalize();

    const lookAtMatrix = new THREE.Matrix4();
    lookAtMatrix.lookAt(camera.position, targetForward, new THREE.Vector3(0, 1, 0));

    controlsRef.current.startQuaternion.copy(camera.quaternion);
    controlsRef.current.targetQuaternion.setFromRotationMatrix(lookAtMatrix);
    controlsRef.current.isAnimating = true;
    controlsRef.current.animationStartTime = performance.now();

    needsRenderRef.current = true;
    lastInteractionTimeRef.current = performance.now();
  };

  // Initialize scene content (when refs are ready and data has loaded)
  useEffect(() => {
    if (!sceneRef.current || !cameraRef.current || !dataLoaded) return;

    const scene = sceneRef.current;
    const camera = cameraRef.current;

    // Create Milky Way
    createMilkyWay(milkyWayImage, milkyWayOpacity, (milkyWay, material) => {
      milkyWayMeshRef.current = milkyWay;
      milkyWayMaterialRef.current = material;
      scene.add(milkyWay);
      needsRenderRef.current = true;
    });

    // Create stars
    const stars = createStars(loadedData.stars, loadedData.constellations);
    starsRef.current = stars;
    scene.add(stars);

    // Create constellations
    const { lines, labels } = createConstellations(loadedData.constellations);
    lines.forEach(line => scene.add(line));
    labels.forEach(label => {
      scene.add(label.sprite);
      labelsRef.current.push(label);
    });

    needsRenderRef.current = true;
  }, [sceneRef, cameraRef, milkyWayOpacity, dataLoaded, loadedData]);

  // Update Milky Way opacity
  useEffect(() => {
    if (milkyWayMaterialRef.current) {
      milkyWayMaterialRef.current.uniforms.opacity.value = milkyWayOpacity;
      needsRenderRef.current = true;
    }
  }, [milkyWayOpacity]);

  // Handle celestial grid visibility
  useEffect(() => {
    if (!sceneRef.current) return;

    if (showCelestialGrid) {
      if (!celestialGridRef.current) {
        celestialGridRef.current = createCelestialGrid();
        sceneRef.current.add(celestialGridRef.current);
      }
      celestialGridRef.current.visible = true;
    } else if (celestialGridRef.current) {
      celestialGridRef.current.visible = false;
    }
    needsRenderRef.current = true;
  }, [showCelestialGrid]);

  // Handle celestial equator visibility
  useEffect(() => {
    if (!sceneRef.current) return;

    if (showCelestialEquator) {
      if (!celestialEquatorRef.current) {
        celestialEquatorRef.current = createCelestialEquator();
        sceneRef.current.add(celestialEquatorRef.current);
      }
      celestialEquatorRef.current.visible = true;
    } else if (celestialEquatorRef.current) {
      celestialEquatorRef.current.visible = false;
    }
    needsRenderRef.current = true;
  }, [showCelestialEquator]);

  // Handle NCP marker visibility
  useEffect(() => {
    if (!sceneRef.current) return;

    if (showCelestialGrid) {
      if (!ncpMarkerRef.current) {
        ncpMarkerRef.current = createNCPMarker();
        sceneRef.current.add(ncpMarkerRef.current);
      }
      ncpMarkerRef.current.visible = true;
    } else if (ncpMarkerRef.current) {
      ncpMarkerRef.current.visible = false;
    }
    needsRenderRef.current = true;
  }, [showCelestialGrid]);

  // Handle search query - point camera at matching object
  useEffect(() => {
    if (!searchQuery.trim() || !cameraRef.current || !groups.length) return;

    const query = searchQuery.toLowerCase().trim();
    const matchingGroup = groups.find(g =>
      g.object.toLowerCase() === query &&
      g.astrometry &&
      g.astrometry.ra !== undefined &&
      g.astrometry.dec !== undefined
    );

    if (matchingGroup) {
      const targetPos = raDecToVector3(
        matchingGroup.astrometry.ra,
        matchingGroup.astrometry.dec,
        100
      );

      const camera = cameraRef.current;
      const lookAtMatrix = new THREE.Matrix4();
      lookAtMatrix.lookAt(camera.position, targetPos, new THREE.Vector3(0, 1, 0));
      camera.quaternion.setFromRotationMatrix(lookAtMatrix);

      needsRenderRef.current = true;
      lastInteractionTimeRef.current = performance.now();
    }
  }, [searchQuery, groups]);

  // Handle target object navigation (animated)
  useEffect(() => {
    if (!targetObject.trim() || !cameraRef.current || !groups.length) return;

    const query = targetObject.toLowerCase().trim();
    const matchingGroup = groups.find(g =>
      g.object.toLowerCase() === query &&
      g.astrometry &&
      g.astrometry.ra !== undefined &&
      g.astrometry.dec !== undefined
    );

    if (matchingGroup) {
      const targetPos = raDecToVector3(
        matchingGroup.astrometry.ra,
        matchingGroup.astrometry.dec,
        100
      );

      const camera = cameraRef.current;
      const lookAtMatrix = new THREE.Matrix4();
      lookAtMatrix.lookAt(camera.position, targetPos, new THREE.Vector3(0, 1, 0));

      // Set up animation
      controlsRef.current.startQuaternion.copy(camera.quaternion);
      controlsRef.current.targetQuaternion.setFromRotationMatrix(lookAtMatrix);
      controlsRef.current.isAnimating = true;
      controlsRef.current.animationStartTime = performance.now();

      needsRenderRef.current = true;
      lastInteractionTimeRef.current = performance.now();

      // Notify parent when animation completes
      if (onTargetReached) {
        setTimeout(() => {
          onTargetReached();
        }, controlsRef.current.animationDuration);
      }
    }
  }, [targetObject, groups, onTargetReached]);

  // Update object markers when groups change
  useEffect(() => {
    if (!sceneRef.current || !cameraRef.current) return;

    const scene = sceneRef.current;

    // Remove old markers
    objectMarkersRef.current.forEach(marker => {
      scene.remove(marker.mesh);
      scene.remove(marker.sprite);
      if (marker.mesh.geometry) marker.mesh.geometry.dispose();
      marker.mesh.material.dispose();
      if (marker.mesh.material.map) marker.mesh.material.map.dispose();
      marker.sprite.material.map.dispose();
      marker.sprite.material.dispose();
    });
    objectMarkersRef.current = [];

    // Create new markers with current FOV
    const markers = createObjectMarkers(groups, fov);
    markers.forEach(marker => {
      scene.add(marker.mesh);
      scene.add(marker.sprite);
    });
    objectMarkersRef.current = markers;

    needsRenderRef.current = true;
  }, [groups, fov]);

  // Mouse controls and animation loop
  useEffect(() => {
    if (!cameraRef.current || !rendererRef.current) return;

    const camera = cameraRef.current;
    const renderer = rendererRef.current;

    const onMouseDown = (event) => {
      controlsRef.current.isAnimating = false;
      controlsRef.current.isDragging = true;
      controlsRef.current.previousMouse = { x: event.clientX, y: event.clientY };
      isInteractingRef.current = true;
      lastInteractionTimeRef.current = performance.now();
    };

    const onMouseMove = (event) => {
      if (controlsRef.current.isDragging) {
        const deltaX = event.clientX - controlsRef.current.previousMouse.x;
        const deltaY = event.clientY - controlsRef.current.previousMouse.y;
        const sensitivity = 0.002;

        const quaternionY = new THREE.Quaternion();
        quaternionY.setFromAxisAngle(new THREE.Vector3(0, 1, 0), deltaX * sensitivity);

        const quaternionX = new THREE.Quaternion();
        quaternionX.setFromAxisAngle(new THREE.Vector3(1, 0, 0), deltaY * sensitivity);

        camera.quaternion.premultiply(quaternionY);
        camera.quaternion.multiply(quaternionX);

        controlsRef.current.previousMouse = { x: event.clientX, y: event.clientY };
        needsRenderRef.current = true;
      }
    };

    const onMouseUp = () => {
      controlsRef.current.isDragging = false;
      isInteractingRef.current = false;
      lastInteractionTimeRef.current = performance.now();
      needsRenderRef.current = true;
    };

    const onWheel = (event) => {
      event.preventDefault();
      controlsRef.current.isAnimating = false;

      const newFov = camera.fov + event.deltaY * 0.05;
      camera.fov = Math.max(20, Math.min(180, newFov));
      setFov(camera.fov);
      updateStereographicProjection(camera);

      lastInteractionTimeRef.current = performance.now();
      needsRenderRef.current = true;
    };

    // Raycaster for object interaction
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    const onMouseClick = (event) => {
      if (controlsRef.current.isDragging) return;

      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(
        objectMarkersRef.current.map(m => m.mesh)
      );

      if (intersects.length > 0) {
        const marker = objectMarkersRef.current.find(m => m.mesh === intersects[0].object);
        if (marker && onObjectClick) {
          onObjectClick(marker.group);
        }
      }
    };

    const onHover = (event) => {
      if (controlsRef.current.isDragging) return;

      const now = Date.now();
      if (now - lastRaycastTimeRef.current < 100) return;
      lastRaycastTimeRef.current = now;

      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(
        objectMarkersRef.current.map(m => m.mesh)
      );

      if (intersects.length > 0) {
        const marker = objectMarkersRef.current.find(m => m.mesh === intersects[0].object);
        if (marker) {
          setHoveredObject(marker.group);
          setTooltipPos({ x: event.clientX - rect.left, y: event.clientY - rect.top });
          renderer.domElement.style.cursor = 'pointer';
        }
      } else {
        setHoveredObject(null);
        renderer.domElement.style.cursor = controlsRef.current.isDragging ? 'grabbing' : 'grab';
      }
    };

    renderer.domElement.addEventListener('mousedown', onMouseDown);
    renderer.domElement.addEventListener('mousemove', (e) => {
      onMouseMove(e);
      onHover(e);
    });
    renderer.domElement.addEventListener('mouseup', onMouseUp);
    renderer.domElement.addEventListener('click', onMouseClick);
    renderer.domElement.addEventListener('wheel', onWheel);
    renderer.domElement.style.cursor = 'grab';

    return () => {
      renderer.domElement.removeEventListener('mousedown', onMouseDown);
      renderer.domElement.removeEventListener('mousemove', onMouseMove);
      renderer.domElement.removeEventListener('mouseup', onMouseUp);
      renderer.domElement.removeEventListener('click', onMouseClick);
      renderer.domElement.removeEventListener('wheel', onWheel);
    };
  }, [cameraRef, rendererRef, onObjectClick]);

  // Animation loop
  useEffect(() => {
    if (!cameraRef.current || !rendererRef.current || !sceneRef.current) return;

    const camera = cameraRef.current;
    const renderer = rendererRef.current;
    const scene = sceneRef.current;
    let lastFrameTime = 0;

    const animate = (currentTime) => {
      animationFrameRef.current = requestAnimationFrame(animate);

      // Handle camera animation
      if (controlsRef.current.isAnimating) {
        const elapsed = currentTime - controlsRef.current.animationStartTime;
        const progress = Math.min(elapsed / controlsRef.current.animationDuration, 1);

        const easeProgress = progress < 0.5
          ? 2 * progress * progress
          : 1 - Math.pow(-2 * progress + 2, 2) / 2;

        camera.quaternion.slerpQuaternions(
          controlsRef.current.startQuaternion,
          controlsRef.current.targetQuaternion,
          easeProgress
        );

        needsRenderRef.current = true;
        lastInteractionTimeRef.current = currentTime;

        if (progress >= 1) {
          controlsRef.current.isAnimating = false;
        }
      }

      // Adaptive FPS
      const timeSinceInteraction = currentTime - lastInteractionTimeRef.current;
      if (controlsRef.current.isAnimating || timeSinceInteraction < 100) {
        targetFpsRef.current = 60;
      } else if (timeSinceInteraction < 1500) {
        targetFpsRef.current = 30;
      } else {
        targetFpsRef.current = 1;
      }

      const targetFrameTime = 1000 / targetFpsRef.current;
      const elapsed = currentTime - lastFrameTime;

      if (elapsed < targetFrameTime && !needsRenderRef.current && !controlsRef.current.isAnimating) {
        return;
      }

      lastFrameTime = currentTime;

      if (needsRenderRef.current || isInteractingRef.current || controlsRef.current.isAnimating) {
        // Update label visibility based on FOV (progressive disclosure)
        updateLabelVisibility(objectMarkersRef.current, camera.fov);

        // Update label scales
        const fovRadians = camera.fov * Math.PI / 180;
        const tanQuarterFov = Math.tan(fovRadians / 4);
        const referenceTanQuarterFov = Math.tan((60 * Math.PI / 180) / 4);
        const perspectiveScale = tanQuarterFov / referenceTanQuarterFov;
        const constellationSizeMultiplier = 1.25;

        const cameraDirection = new THREE.Vector3(0, 0, -1);
        cameraDirection.applyQuaternion(camera.quaternion);

        labelsRef.current.forEach(label => {
          if (label.sprite) {
            const spriteDirection = label.sprite.position.clone().normalize();
            const dotProduct = cameraDirection.dot(spriteDirection);
            const distanceScale = Math.max(0.3, dotProduct);
            const scale = label.baseScale * perspectiveScale * constellationSizeMultiplier * distanceScale;
            label.sprite.scale.set(scale, scale / 7.5, 1);
          }
        });

        // Update object marker scales
        const objectSizeMultiplier = 1.25;
        objectMarkersRef.current.forEach(marker => {
          if (marker.mesh && marker.mesh.userData.baseScale) {
            const baseScale = marker.mesh.userData.baseScale;
            const markerDirection = marker.mesh.position.clone().normalize();
            const dotProduct = cameraDirection.dot(markerDirection);
            const distanceScale = Math.max(0.3, dotProduct);
            const markerScale = baseScale * perspectiveScale * objectSizeMultiplier * distanceScale;
            marker.mesh.scale.set(markerScale, markerScale, 1);
          }

          if (marker.sprite && marker.sprite.userData.baseScale && marker.sprite.visible) {
            const baseScale = marker.sprite.userData.baseScale;
            const spriteDirection = marker.sprite.position.clone().normalize();
            const dotProduct = cameraDirection.dot(spriteDirection);
            const distanceScale = Math.max(0.3, dotProduct);
            const scale = baseScale * perspectiveScale * objectSizeMultiplier * distanceScale;
            marker.sprite.scale.set(scale, scale / 8, 1);
          }
        });

        // Update star sizes based on FOV
        if (starsRef.current && starsRef.current.material) {
          starsRef.current.visible = true;
          if (camera.fov <= 60) {
            const starScale = Math.max(1.0, Math.min(5.0, 60 / camera.fov * (5.0 / 3.0)));
            starsRef.current.material.uniforms.fovScale.value = starScale;
          } else {
            starsRef.current.material.uniforms.fovScale.value = 1.0;
          }
          starsRef.current.material.uniformsNeedUpdate = true;
        }

        renderer.render(scene, camera);
        needsRenderRef.current = false;
      }
    };

    animate(0);
  }, [cameraRef, rendererRef, sceneRef]);

  return (
    <div className="relative w-full h-full">
      <div ref={containerRef} className="w-full h-full" />

      {!dataLoaded && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-950/80 backdrop-blur-sm z-50">
          <div className="w-12 h-12 border-4 border-sky-500 border-t-transparent rounded-full animate-spin mb-4" />
          <div className="text-sky-400 font-semibold text-lg">Loading Star Catalog...</div>
          <div className="text-slate-400 text-sm mt-1">Downloading coordinates & constellations</div>
        </div>
      )}

      <NavigationToolbar
        showCelestialEquator={showCelestialEquator}
        setShowCelestialEquator={setShowCelestialEquator}
        showCelestialGrid={showCelestialGrid}
        setShowCelestialGrid={setShowCelestialGrid}
        onLevelToEquator={levelToEquator}
      />

      <InfoPanel starCount={loadedData.stars ? loadedData.stars.features.length : 0} fov={fov} />

      <ObjectTooltip hoveredObject={hoveredObject} tooltipPos={tooltipPos} />
    </div>
  );
}

export default SkyMapThree;
