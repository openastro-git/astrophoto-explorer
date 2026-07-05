const API_BASE = 'http://localhost:8000';

export async function loadSettings() {
  const response = await fetch(`${API_BASE}/api/settings`);
  return await response.json();
}

export async function saveSettings(defaultFolder, defaultRender, stretchSettings, scanPattern = '', ignoreFilters = [], theme = 'deep-space') {
  const cleanPath = defaultFolder.replace(/\\\s/g, ' ').trim();
  
  const response = await fetch(`${API_BASE}/api/settings`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      default_folder: cleanPath,
      default_render: defaultRender,
      scan_pattern: scanPattern,
      ignore_filters: ignoreFilters,
      stretch: stretchSettings,
      theme: theme
    }),
  });
  return await response.json();
}

export async function clearCache() {
  const response = await fetch(`${API_BASE}/api/cache`, {
    method: 'DELETE',
  });
  return await response.json();
}

export async function fetchObjectInfo(objectName) {
  const response = await fetch(`${API_BASE}/api/object/info/${encodeURIComponent(objectName)}`);
  return await response.json();
}

export async function fetchFitsHeader(filePath) {
  const response = await fetch(`${API_BASE}/api/fits/header/${encodeURIComponent(filePath)}`);
  return await response.json();
}

export async function testScanPattern(path, pattern, ignoreFilters, limit = 5) {
  const response = await fetch(`${API_BASE}/api/scan/test-pattern`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      path,
      pattern,
      ignore_filters: ignoreFilters,
      limit
    }),
  });
  return await response.json();
}

export async function fetchPatternVariables() {
  const response = await fetch(`${API_BASE}/api/scan/variables`);
  return await response.json();
}

export async function setFavorite(objectName, filePath) {
  const response = await fetch(`${API_BASE}/api/favorite`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      object_name: objectName,
      file_path: filePath
    }),
  });
  return await response.json();
}

export async function regenerateThumbnail(objectName, filePath) {
  const response = await fetch(`${API_BASE}/api/thumbnail/regenerate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      object_name: objectName,
      file_path: filePath
    }),
  });
  return await response.json();
}

export function createScanWebSocket(path, force, callbacks) {
  const websocket = new WebSocket(`${API_BASE.replace('http', 'ws')}/ws/scan`);

  websocket.onopen = () => {
    console.log('WebSocket connected');
    callbacks.onOpen?.();
    websocket.send(JSON.stringify({ path, force }));
  };

  websocket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('WebSocket message:', data);
    callbacks.onMessage?.(data);
  };

  websocket.onerror = (error) => {
    console.error('WebSocket error:', error);
    callbacks.onError?.(error);
  };

  websocket.onclose = (event) => {
    console.log('WebSocket closed', event.code, event.reason);
    callbacks.onClose?.(event);
  };

  return websocket;
}

export function createLogsWebSocket(callbacks) {
  const websocket = new WebSocket(`${API_BASE.replace('http', 'ws')}/ws/logs`);

  websocket.onopen = () => {
    console.log('Logs WebSocket connected');
    callbacks.onOpen?.();
  };

  websocket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    callbacks.onMessage?.(data);
  };

  websocket.onerror = (error) => {
    console.error('Logs WebSocket error:', error);
    callbacks.onError?.(error);
  };

  websocket.onclose = (event) => {
    console.log('Logs WebSocket closed', event.code, event.reason);
    callbacks.onClose?.(event);
  };

  return websocket;
}
