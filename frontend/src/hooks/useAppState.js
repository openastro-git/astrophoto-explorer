import { useState, useEffect } from 'react';
import { loadSettings as loadSettingsAPI, createScanWebSocket } from '../api/astroApi';

export function useAppState(toast) {
  const [groups, setGroups] = useState([]);
  const [selectedGroup, setSelectedGroup] = useState(null);
  const [currentImageIndex, setCurrentImageIndex] = useState(0);
  const [folderPath, setFolderPath] = useState('');
  const [loading, setLoading] = useState(false);
  const [scanProgress, setScanProgress] = useState(null);
  const [showSettings, setShowSettings] = useState(false);
  const [defaultFolder, setDefaultFolder] = useState('');
  const [view, setView] = useState('grid');
  const [mainView, setMainView] = useState('grid');
  const [objectInfo, setObjectInfo] = useState(null);
  const [showFitsHeader, setShowFitsHeader] = useState(false);
  const [fitsHeader, setFitsHeader] = useState(null);
  const [ws, setWs] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [skyMapTarget, setSkyMapTarget] = useState('');
  const [imageRefreshKey, setImageRefreshKey] = useState(0);
  const [gridScrollPosition, setGridScrollPosition] = useState(0);
  const [previousView, setPreviousView] = useState('grid');
  const [lastViewedObject, setLastViewedObject] = useState('');
  const [defaultRender, setDefaultRender] = useState('HD');
  const [showConsole, setShowConsole] = useState(false);
  const [scanPattern, setScanPattern] = useState('');
  const [ignoreFilters, setIgnoreFilters] = useState([]);
  const [theme, setTheme] = useState('deep-space');

  const [stretchSettings, setStretchSettings] = useState({
    target_background: 0.17,
    shadows_clipping: -2.8,
    contrast_boost: 1.1,
    linked_channels: true,
  });

  const loadSettings = async () => {
    try {
      const data = await loadSettingsAPI();
      const folder = data.default_folder || '';
      setDefaultFolder(folder);
      setFolderPath(folder);

      // Load stretch settings
      if (data.stretch) {
        setStretchSettings(prev => ({
          target_background: data.stretch.target_background ?? prev.target_background,
          shadows_clipping: data.stretch.shadows_clipping ?? prev.shadows_clipping,
          contrast_boost: data.stretch.contrast_boost ?? prev.contrast_boost,
          linked_channels: data.stretch.linked_channels ?? prev.linked_channels,
        }));
      }

      // Load default render setting
      if (data.default_render) {
        setDefaultRender(data.default_render);
      }

      // Load scan pattern and ignore filters
      if (data.scan_pattern !== undefined) {
        setScanPattern(data.scan_pattern || '');
      }
      if (data.ignore_filters !== undefined) {
        setIgnoreFilters(data.ignore_filters || []);
      }
      if (data.theme) {
        setTheme(data.theme);
      }

      // Only scan if we have a valid folder path
      if (folder && folder !== '.' && folder !== '' && folder.length > 1) {
        scanFolder(folder, false);
      }
    } catch (error) {
      console.error('Error loading settings:', error);
    }
  };

  const scanFolder = async (path = folderPath, force = false, userTriggered = false) => {
    if (!path || path === '') {
      return;
    }

    // Prevent multiple simultaneous scans
    if (loading) {
      console.warn('Scan already in progress, ignoring new scan request');
      return;
    }

    // Close any existing WebSocket connection
    if (ws) {
      console.log('Closing existing WebSocket connection');
      ws.close();
      setWs(null);
    }

    setLoading(true);
    setScanProgress({ stage: 'connecting', message: 'Connecting...', current: 0, total: 0 });

    try {
      const websocket = createScanWebSocket(path, force, {
        onOpen: () => {
          setScanProgress({ stage: 'connected', message: 'Loading...', current: 0, total: 0 });
        },
        onMessage: (data) => {
          if (data.type === 'progress') {
            setScanProgress(data);
          } else if (data.type === 'complete') {
            console.log('Scan complete, groups count:', data.data?.groups?.length || 0);
            if (data.data.error) {
              toast.error(`Error: ${data.data.error}`);
              setGroups([]);
            } else {
              const groupsData = data.data.groups || [];
              console.log('Setting groups:', groupsData.length, 'groups');
              setGroups(groupsData);
            }
            setScanProgress(null);
            setLoading(false);
            websocket.close();
            setWs(null);
          } else if (data.type === 'error') {
            toast.error(`Error: ${data.message}`);
            setScanProgress(null);
            setLoading(false);
            websocket.close();
            setWs(null);
          }
        },
        onError: (error) => {
          if (userTriggered) {
            toast.error('WebSocket connection failed. Please check if backend is running.');
          }
          setScanProgress(null);
          setLoading(false);
          setWs(null);
        },
        onClose: (event) => {
          setWs(null);
          if (loading && !groups.length) {
            setScanProgress(null);
            setLoading(false);
          }
        }
      });

      setWs(websocket);
    } catch (error) {
      console.error('Error with WebSocket:', error);
      if (userTriggered) {
        toast.error('Failed to connect via WebSocket. Please check if backend is running.');
      }
      setScanProgress(null);
      setLoading(false);
      setWs(null);
    }
  };

  return {
    groups, setGroups,
    selectedGroup, setSelectedGroup,
    currentImageIndex, setCurrentImageIndex,
    folderPath, setFolderPath,
    loading, setLoading,
    scanProgress, setScanProgress,
    showSettings, setShowSettings,
    defaultFolder, setDefaultFolder,
    view, setView,
    mainView, setMainView,
    objectInfo, setObjectInfo,
    showFitsHeader, setShowFitsHeader,
    fitsHeader, setFitsHeader,
    ws, setWs,
    searchQuery, setSearchQuery,
    skyMapTarget, setSkyMapTarget,
    imageRefreshKey, setImageRefreshKey,
    gridScrollPosition, setGridScrollPosition,
    previousView, setPreviousView,
    lastViewedObject, setLastViewedObject,
    stretchSettings, setStretchSettings,
    defaultRender, setDefaultRender,
    showConsole, setShowConsole,
    scanPattern, setScanPattern,
    ignoreFilters, setIgnoreFilters,
    theme, setTheme,
    loadSettings,
    scanFolder
  };
}
