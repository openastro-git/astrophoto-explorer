import { useEffect, lazy, Suspense } from 'react';
const SkyMapThree = lazy(() => import('./SkyMapThree'));
import { useToast } from './useToast';
import Toast from './Toast';
import Header from './components/Header';
import SettingsModal from './components/SettingsModal';
import GridView from './components/GridView';
import ExplorerView from './components/ExplorerView';
import LoadingView from './components/LoadingView';
import EmptyState from './components/EmptyState';
import { useAppState } from './hooks/useAppState';
import { filterGroups } from './utils/formatters';
import * as api from './api/astroApi';
import TerminalConsole from './components/TerminalConsole';

function App() {
  const { toasts, removeToast, success, error, warning, info } = useToast();
  const toast = { success, error, warning, info };

  const state = useAppState(toast);
  const {
    groups, setGroups,
    selectedGroup, setSelectedGroup,
    currentImageIndex, setCurrentImageIndex,
    folderPath, setFolderPath,
    loading,
    scanProgress,
    showSettings, setShowSettings,
    defaultFolder, setDefaultFolder,
    view, setView,
    mainView, setMainView,
    objectInfo, setObjectInfo,
    showFitsHeader, setShowFitsHeader,
    fitsHeader, setFitsHeader,
    ws,
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
  } = state;

  useEffect(() => {
    loadSettings();

    // Check URL for object parameter
    const params = new URLSearchParams(window.location.search);
    const objectName = params.get('object');
    if (objectName) {
      window.initialObjectName = objectName;
    }
  }, []);
  
  // Apply theme styling dynamically to document root
  useEffect(() => {
    const htmlEl = document.documentElement;
    const themeClasses = ['theme-deep-space', 'theme-nordic-frost', 'theme-everforest', 'theme-night-owl', 'theme-dracula-mellow', 'theme-tron'];
    themeClasses.forEach(cls => htmlEl.classList.remove(cls));
    htmlEl.classList.add(`theme-${theme}`);
  }, [theme]);

  // Handle URL object parameter after groups are loaded
  useEffect(() => {
    if (groups.length > 0 && window.initialObjectName) {
      const group = groups.find(g => g.object === window.initialObjectName);
      if (group) {
        handleGroupClick(group);
      }
      delete window.initialObjectName;
    }
  }, [groups]);

  // Cleanup WebSocket on component unmount
  useEffect(() => {
    return () => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        console.log('Closing WebSocket on component unmount');
        ws.close();
      }
    };
  }, [ws]);

  const saveSettings = async () => {
    try {
      const data = await api.saveSettings(defaultFolder, defaultRender, stretchSettings, scanPattern, ignoreFilters, theme);
      if (data.status === 'saved') {
        const cleanPath = defaultFolder.replace(/\\\s/g, ' ').trim();
        setFolderPath(cleanPath);
        setDefaultFolder(cleanPath);
        setDefaultRender(defaultRender);
        setTheme(theme);
        setShowSettings(false);
        setImageRefreshKey(prev => prev + 1);
        scanFolder(cleanPath, false, true);
      }
    } catch (err) {
      console.error('Error saving settings:', err);
      error('Error saving settings. Make sure the backend is running.');
    }
  };

  const clearCache = async () => {
    if (!confirm('Clear all cached thumbnails and catalog data?')) {
      return;
    }

    try {
      const data = await api.clearCache();
      if (data.status) {
        success('Cache cleared successfully. Rescanning...');
        if (folderPath) {
          scanFolder(folderPath, true, true);
        }
      }
    } catch (err) {
      console.error('Error clearing cache:', err);
      error('Error clearing cache. Make sure the backend is running.');
    }
  };

  const handleGroupClick = (group) => {
    // Sort files: processed images first, then FITS files
    const sortedFiles = [...group.files].sort((a, b) => {
      const aIsFits = ['fits', 'fit', 'fts'].includes(a.file_type.toLowerCase());
      const bIsFits = ['fits', 'fit', 'fts'].includes(b.file_type.toLowerCase());

      if (aIsFits && !bIsFits) return 1;
      if (!aIsFits && bIsFits) return -1;
      return 0;
    });

    const sortedGroup = { ...group, files: sortedFiles };

    // Find the index of the favorite file, or default to 0
    let initialIndex = 0;
    if (group.favorite) {
      const favoriteIndex = sortedFiles.findIndex(f => f.path === group.favorite);
      if (favoriteIndex !== -1) {
        initialIndex = favoriteIndex;
      }
    }

    // Save the current view before switching to explorer
    setPreviousView(view);

    // Save scroll position if coming from grid
    if (view === 'grid') {
      setGridScrollPosition(window.scrollY);
    }

    // Save the object name if coming from skymap
    if (view === 'skymap') {
      setLastViewedObject(group.object);
    }

    setSelectedGroup(sortedGroup);
    setCurrentImageIndex(initialIndex);
    setView('explorer');

    // Prevent auto-scroll
    requestAnimationFrame(() => {
      window.scrollTo(0, 0);
    });

    // Fetch object information
    fetchObjectInfo(group.object);

    // Update URL
    const params = new URLSearchParams(window.location.search);
    params.set('object', group.object);
    window.history.pushState({}, '', `${window.location.pathname}?${params}`);
  };

  const handleBackToGrid = () => {
    setView(previousView);
    setMainView(previousView);
    setSelectedGroup(null);
    setSearchQuery('');

    if (previousView === 'skymap' && lastViewedObject) {
      setSkyMapTarget(lastViewedObject);
    }

    if (previousView === 'grid' && gridScrollPosition > 0) {
      requestAnimationFrame(() => {
        window.scrollTo(0, gridScrollPosition);
      });
    }

    window.history.pushState({}, '', window.location.pathname);
  };

  const handleBackToGridFromSkyMap = () => {
    setMainView('grid');
    setView('grid');
    setSkyMapTarget('');

    requestAnimationFrame(() => {
      window.scrollTo(0, gridScrollPosition);
    });
  };

  const handleViewChange = (newView) => {
    if (newView === 'grid') {
      setMainView('grid');
      setView('grid');
      if (view === 'skymap' && gridScrollPosition > 0) {
        requestAnimationFrame(() => {
          window.scrollTo(0, gridScrollPosition);
        });
      }
    } else if (newView === 'skymap') {
      if (view === 'grid') {
        setGridScrollPosition(window.scrollY);
      }
      setMainView('skymap');
      setView('skymap');
    }
  };

  const handleNavigateToSkyMap = (group) => {
    setGridScrollPosition(window.scrollY);
    setMainView('skymap');
    setView('skymap');
    setSkyMapTarget(group.object);
  };

  const handlePrevImage = () => {
    if (selectedGroup && currentImageIndex > 0) {
      handleImageChange(currentImageIndex - 1);
    }
  };

  const handleNextImage = () => {
    if (selectedGroup && currentImageIndex < selectedGroup.files.length - 1) {
      handleImageChange(currentImageIndex + 1);
    }
  };

  const fetchObjectInfo = async (objectName) => {
    try {
      const data = await api.fetchObjectInfo(objectName);
      if (!data.error) {
        setObjectInfo(data);
      } else {
        setObjectInfo(null);
      }
    } catch (err) {
      console.error('Error fetching object info:', err);
      setObjectInfo(null);
    }
  };

  const fetchFitsHeader = async (filePath) => {
    try {
      const data = await api.fetchFitsHeader(filePath);
      if (!data.error) {
        setFitsHeader(data);
      } else {
        setFitsHeader(null);
      }
    } catch (err) {
      console.error('Error fetching FITS header:', err);
      setFitsHeader(null);
    }
  };

  const handleImageChange = (index) => {
    setCurrentImageIndex(index);

    const file = selectedGroup.files[index];
    if (['fits', 'fit', 'fts'].includes(file.file_type.toLowerCase())) {
      fetchFitsHeader(file.path);
    } else {
      setFitsHeader(null);
    }
    setShowFitsHeader(false);
  };

  const handleSetFavorite = async (filePath) => {
    if (!selectedGroup) return;

    try {
      const data = await api.setFavorite(selectedGroup.object, filePath);
      if (data.success) {
        const thumbData = await api.regenerateThumbnail(selectedGroup.object, filePath);

        setSelectedGroup(prev => ({
          ...prev,
          favorite: filePath,
          thumbnail: thumbData.thumbnail || prev.thumbnail
        }));

        setGroups(prev => prev.map(g =>
          g.object === selectedGroup.object
            ? { ...g, favorite: filePath, thumbnail: thumbData.thumbnail || g.thumbnail }
            : g
        ));

        const message = document.createElement('div');
        message.className = 'fixed top-20 right-8 bg-green-500 text-white px-4 py-2 rounded-lg shadow-lg z-50';
        message.textContent = 'Favorite set! Thumbnail updated.';
        document.body.appendChild(message);
        setTimeout(() => message.remove(), 2000);
      }
    } catch (err) {
      console.error('Error setting favorite:', err);
      error('Error setting favorite. Make sure the backend is running.');
    }
  };

  const handlePastePath = () => {
    if (navigator.clipboard && navigator.clipboard.readText) {
      navigator.clipboard.readText()
        .then(text => {
          const trimmed = text.trim();
          if (trimmed) {
            setDefaultFolder(trimmed);
          }
        })
        .catch(err => {
          console.log('Could not read clipboard:', err);
        });
    }
  };

  const filteredGroups = filterGroups(groups, searchQuery);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans">
      {/* Toast Notifications */}
      {toasts.map(toast => (
        <Toast
          key={toast.id}
          message={toast.message}
          type={toast.type}
          duration={toast.duration}
          onClose={() => removeToast(toast.id)}
        />
      ))}

      {/* Settings Modal */}
      <SettingsModal
        showSettings={showSettings}
        onClose={() => setShowSettings(false)}
        defaultFolder={defaultFolder}
        setDefaultFolder={setDefaultFolder}
        defaultRender={defaultRender}
        setDefaultRender={setDefaultRender}
        stretchSettings={stretchSettings}
        setStretchSettings={setStretchSettings}
        scanPattern={scanPattern}
        setScanPattern={setScanPattern}
        ignoreFilters={ignoreFilters}
        setIgnoreFilters={setIgnoreFilters}
        theme={theme}
        setTheme={setTheme}
        onSave={saveSettings}
        onClearCache={clearCache}
        onPastePath={handlePastePath}
      />

      {/* Header */}
      <Header
        view={view}
        mainView={mainView}
        selectedGroup={selectedGroup}
        folderPath={folderPath}
        loading={loading}
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
        onBackToGrid={handleBackToGrid}
        onBackToGridFromSkyMap={handleBackToGridFromSkyMap}
        onViewChange={handleViewChange}
        onRescan={() => scanFolder(folderPath, true, true)}
        onSettingsClick={() => setShowSettings(true)}
        gridScrollPosition={gridScrollPosition}
        showConsole={showConsole}
        onConsoleToggle={() => setShowConsole(prev => !prev)}
      />

      {/* Main Content */}
      <main className="pt-20 p-8">
        {loading ? (
          <LoadingView scanProgress={scanProgress} />
        ) : view === 'grid' ? (
          <div className="pt-6">
            {!folderPath || folderPath === '' ? (
              <EmptyState type="no-folder" />
            ) : groups.length === 0 ? (
              <EmptyState type="no-objects" />
            ) : filteredGroups.length === 0 ? (
              <EmptyState type="no-results" searchQuery={searchQuery} />
            ) : (
              <GridView
                folderPath={folderPath}
                groups={filteredGroups}
                onGroupClick={handleGroupClick}
                onNavigateToSkyMap={handleNavigateToSkyMap}
              />
            )}
          </div>
        ) : view === 'skymap' ? (
          <div className="fixed top-[72px] left-0 right-0 bottom-0">
            {!folderPath || folderPath === '' ? (
              <EmptyState type="no-folder" />
            ) : groups.length === 0 ? (
              <EmptyState type="no-objects" />
            ) : (
              <div className="w-full h-full">
                <Suspense fallback={
                  <div className="w-full h-full flex flex-col items-center justify-center bg-slate-950">
                    <div className="w-12 h-12 border-4 border-sky-500 border-t-transparent rounded-full animate-spin mb-4" />
                    <div className="text-sky-400 font-semibold">Loading 3D Sky Map Component...</div>
                  </div>
                }>
                  <SkyMapThree
                    groups={groups}
                    onObjectClick={handleGroupClick}
                    milkyWayOpacity={0.35}
                    searchQuery={searchQuery}
                    targetObject={skyMapTarget}
                    onTargetReached={() => setSkyMapTarget('')}
                  />
                </Suspense>
              </div>
            )}
          </div>
        ) : (
          <ExplorerView
            selectedGroup={selectedGroup}
            currentImageIndex={currentImageIndex}
            objectInfo={objectInfo}
            fitsHeader={fitsHeader}
            showFitsHeader={showFitsHeader}
            setShowFitsHeader={setShowFitsHeader}
            folderPath={folderPath}
            imageRefreshKey={imageRefreshKey}
            onPrevImage={handlePrevImage}
            onNextImage={handleNextImage}
            onImageChange={handleImageChange}
            onSetFavorite={handleSetFavorite}
            onFetchFitsHeader={fetchFitsHeader}
            toast={toast}
            defaultRender={defaultRender}
          />
        )}
      </main>

      {/* Terminal Console */}
      <TerminalConsole visible={showConsole} />
    </div>
  );
}

export default App;
