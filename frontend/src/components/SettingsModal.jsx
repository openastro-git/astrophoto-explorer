import { useState, useEffect, useRef } from 'react';
import {
  X, Plus, FlaskConical, Loader2, Info,
  FolderOpen, ScanSearch, Sliders, Trash2, Monitor, Palette
} from 'lucide-react';
import { testScanPattern, fetchPatternVariables } from '../api/astroApi';

const DEFAULT_IGNORE_SUGGESTIONS = ['light/', 'dark/', 'flat/', 'bias/', 'calibration/'];

const SECTIONS = [
  { id: 'general',    label: 'General',       icon: FolderOpen  },
  { id: 'scanner',    label: 'Scanner',       icon: ScanSearch  },
  { id: 'stretch',    label: 'Stretch',       icon: Sliders     },
  { id: 'appearance', label: 'Appearance',    icon: Palette     },
  { id: 'danger',     label: 'Danger Zone',   icon: Trash2      },
];

/* ─── tiny reusable primitives ─────────────────────────────────────────── */

function SectionHeading({ children }) {
  return (
    <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-3">
      {children}
    </h3>
  );
}

function FieldLabel({ children, hint }) {
  return (
    <div className="mb-1.5">
      <label className="text-sm font-medium text-slate-300">{children}</label>
      {hint && <p className="text-xs text-slate-500 mt-0.5">{hint}</p>}
    </div>
  );
}

function Card({ children, className = '' }) {
  return (
    <div className={`bg-slate-800/40 border border-slate-700/60 rounded-xl p-4 ${className}`}>
      {children}
    </div>
  );
}

/* ─── section panels ────────────────────────────────────────────────────── */

function GeneralSection({ defaultFolder, setDefaultFolder, defaultRender, setDefaultRender, onPastePath }) {
  return (
    <div className="space-y-5">
      <SectionHeading>General</SectionHeading>

      {/* Folder path */}
      <Card>
        <FieldLabel hint="The root folder that contains all your astrophotos.">
          Photos Location
        </FieldLabel>
        <input
          type="text"
          value={defaultFolder}
          onChange={(e) => setDefaultFolder(e.target.value)}
          className="w-full bg-slate-900/60 border border-slate-700 rounded-lg px-3 py-2 text-sm
            focus:outline-none focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400/20
            placeholder:text-slate-600 font-mono"
          placeholder="C:\Users\YourName\Pictures\Astro"
        />
        <button
          onClick={onPastePath}
          className="mt-2 text-xs text-cyan-400 hover:text-cyan-300 transition"
        >
          ↓ Paste from clipboard
        </button>
      </Card>

      {/* Render quality */}
      <Card>
        <FieldLabel hint="Resolution used when previewing non-FITS images. FITS always loads at full resolution.">
          Default Render Quality
        </FieldLabel>
        <div className="flex gap-3 mt-1">
          {[
            { value: 'HD', label: 'HD', sub: 'Full resolution' },
            { value: 'SD', label: 'SD', sub: 'Downsampled' },
          ].map(({ value, label, sub }) => (
            <label
              key={value}
              className={`flex-1 flex flex-col items-center gap-1 py-3 rounded-lg border cursor-pointer transition-all
                ${defaultRender === value
                  ? 'border-cyan-500/60 bg-cyan-500/10 text-cyan-300'
                  : 'border-slate-700 bg-slate-800/40 text-slate-400 hover:border-slate-500'}`}
            >
              <input
                type="radio"
                name="defaultRender"
                value={value}
                checked={defaultRender === value}
                onChange={(e) => setDefaultRender(e.target.value)}
                className="sr-only"
              />
              <Monitor className="w-4 h-4" />
              <span className="text-sm font-semibold">{label}</span>
              <span className="text-xs opacity-70">{sub}</span>
            </label>
          ))}
        </div>
      </Card>
    </div>
  );
}

function ScannerSection({
  defaultFolder, scanPattern, setScanPattern,
  ignoreFilters, setIgnoreFilters,
  variables,
  filterInput, setFilterInput,
  handleInsertVariable, handleAddFilter, handleRemoveFilter,
  handleAddSuggestion, handleFilterKeyDown, handleTestPattern,
  testLoading, testError, testResults, patternInputRef,
}) {
  const unusedSuggestions = DEFAULT_IGNORE_SUGGESTIONS.filter(s => !ignoreFilters.includes(s));

  return (
    <div className="space-y-5">
      <SectionHeading>Folder Pattern</SectionHeading>

      {/* Info box */}
      <div className="flex items-start gap-2.5 bg-cyan-500/5 border border-cyan-500/15 rounded-lg px-3.5 py-3">
        <Info className="w-4 h-4 text-cyan-400 mt-0.5 flex-shrink-0" />
        <p className="text-xs text-slate-400 leading-relaxed">
          Define how your folders map to metadata. Each <code className="text-cyan-300/80">$VARIABLE$</code> matches
          one folder level. Leave empty for auto-detection.
          <br />
          <span className="text-slate-500">
            e.g.&nbsp;
            <code className="text-cyan-300/70 bg-slate-800 px-1 py-0.5 rounded">$TARGETNAME$/$DATE$</code>
            &nbsp;→&nbsp;<code className="text-slate-400">M31/2025-06-15/master.fits</code>
          </span>
        </p>
      </div>

      {/* Pattern builder */}
      <Card>
        <FieldLabel>Folder Pattern</FieldLabel>

        {/* Pattern input */}
        <input
          ref={patternInputRef}
          type="text"
          value={scanPattern}
          onChange={(e) => setScanPattern(e.target.value)}
          className="w-full bg-slate-900/60 border border-slate-700 rounded-lg px-3 py-2 text-sm font-mono
            focus:outline-none focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400/20
            placeholder:text-slate-600"
          placeholder="e.g. $TARGETNAME$ or $TARGETNAME$/$DATE$"
        />

        {/* Variable chips */}
        <div className="mt-3">
          <p className="text-xs text-slate-500 mb-2">Click to insert at cursor</p>
          <div className="flex flex-wrap gap-1.5">
            {variables.map(v => (
              <button
                key={v.token}
                onClick={() => handleInsertVariable(v.token)}
                title={v.description}
                className="px-2.5 py-1 rounded-md text-xs font-mono
                  bg-cyan-500/10 text-cyan-300 border border-cyan-500/20
                  hover:bg-cyan-500/20 hover:border-cyan-500/40
                  active:scale-95 transition-all duration-100"
              >
                {v.token}
              </button>
            ))}
          </div>
        </div>
      </Card>

      {/* Ignore filters */}
      <SectionHeading>Ignore Filters</SectionHeading>
      <Card>
        <FieldLabel hint="Files whose path contains any of these substrings will be skipped.">
          Skip paths containing
        </FieldLabel>

        {/* Active tags */}
        {ignoreFilters.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-3">
            {ignoreFilters.map(f => (
              <span key={f} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs
                bg-orange-500/10 text-orange-300 border border-orange-500/20">
                <span className="font-mono">{f}</span>
                <button onClick={() => handleRemoveFilter(f)} className="hover:text-orange-100 transition">
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}
          </div>
        )}

        {/* Add input */}
        <div className="flex gap-2">
          <input
            type="text"
            value={filterInput}
            onChange={(e) => setFilterInput(e.target.value)}
            onKeyDown={handleFilterKeyDown}
            className="flex-1 bg-slate-900/60 border border-slate-700 rounded-lg px-3 py-1.5 text-xs font-mono
              focus:outline-none focus:border-cyan-400 placeholder:text-slate-600"
            placeholder="e.g. light/"
          />
          <button
            onClick={handleAddFilter}
            disabled={!filterInput.trim()}
            className="px-3 py-1.5 rounded-lg bg-slate-700 hover:bg-slate-600
              disabled:opacity-30 disabled:cursor-not-allowed transition text-xs flex items-center gap-1"
          >
            <Plus className="w-3.5 h-3.5" /> Add
          </button>
        </div>

        {/* Suggestions */}
        {unusedSuggestions.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2.5">
            <span className="text-xs text-slate-600 self-center mr-1">Suggestions:</span>
            {unusedSuggestions.map(s => (
              <button
                key={s}
                onClick={() => handleAddSuggestion(s)}
                className="px-2 py-0.5 rounded-full text-xs font-mono text-slate-500
                  border border-dashed border-slate-700 hover:border-slate-500 hover:text-slate-300 transition"
              >
                + {s}
              </button>
            ))}
          </div>
        )}
      </Card>

      {/* Test pattern */}
      <SectionHeading>Test Parse</SectionHeading>
      <Card>
        <FieldLabel hint="Scans a few files from your folder and shows what the parser detects.">
          Live preview
        </FieldLabel>

        <button
          onClick={handleTestPattern}
          disabled={testLoading || !defaultFolder || defaultFolder === '.'}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-sm font-medium
            bg-violet-600/15 text-violet-300 border border-violet-500/20
            hover:bg-violet-600/25 hover:border-violet-500/40
            disabled:opacity-30 disabled:cursor-not-allowed
            transition-all duration-150"
        >
          {testLoading
            ? <><Loader2 className="w-4 h-4 animate-spin" /> Scanning…</>
            : <><FlaskConical className="w-4 h-4" /> Test Pattern</>}
        </button>

        {testError && (
          <div className="mt-3 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
            <p className="text-xs text-red-300">{testError}</p>
          </div>
        )}

        {testResults && (
          <div className="mt-3 rounded-lg border border-slate-700 overflow-hidden">
            <div className="px-3 py-2 bg-slate-800/60 border-b border-slate-700/50 flex justify-between items-center">
              <span className="text-xs text-slate-400">
                Pattern: <code className="text-cyan-300">{testResults.pattern_description}</code>
              </span>
              <span className="text-xs text-slate-500">
                {testResults.results.length} sampled
              </span>
            </div>

            {testResults.results.length === 0 ? (
              <div className="px-3 py-4 text-center text-xs text-slate-500">
                No files found. Check path and filters.
              </div>
            ) : (
              <div className="divide-y divide-slate-700/30 max-h-64 overflow-y-auto">
                {testResults.results.map((r, i) => (
                  <div key={i} className="px-3 py-2 hover:bg-slate-700/20 transition">
                    {r.error ? (
                      <p className="text-xs text-red-400">{r.error}</p>
                    ) : (
                      <div className="space-y-0.5">
                        <p className="text-xs font-mono text-slate-500 truncate" title={r.relative_path}>
                          {r.relative_path}
                        </p>
                        <div className="flex flex-wrap gap-x-3 gap-y-0.5">
                          <span className="text-xs">
                            <span className="text-slate-500">Object </span>
                            <span className="text-cyan-300 font-semibold">{r.object}</span>
                          </span>
                          {r.session_date && (
                            <span className="text-xs">
                              <span className="text-slate-500">Date </span>
                              <span className="text-amber-300">{r.session_date}</span>
                            </span>
                          )}
                          {r.filter && r.filter !== 'N/A' && (
                            <span className="text-xs">
                              <span className="text-slate-500">Filter </span>
                              <span className="text-green-300">{r.filter}</span>
                            </span>
                          )}
                          <span className="text-xs">
                            <span className="text-slate-500">Via </span>
                            <span className={r.extraction_source === 'pattern' ? 'text-violet-300' : 'text-slate-400'}>
                              {r.extraction_source}
                            </span>
                          </span>
                          {r.instrument && r.instrument !== 'N/A' && (
                            <span className="text-xs">
                              <span className="text-slate-500">Camera </span>
                              <span className="text-slate-300">{r.instrument}</span>
                            </span>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </Card>
    </div>
  );
}

function StretchSection({ stretchSettings, setStretchSettings }) {
  const sliders = [
    {
      key: 'target_background',
      label: 'Target Background',
      min: 0.05, max: 0.3, step: 0.01,
      hint: 'Desired background brightness',
    },
    {
      key: 'shadows_clipping',
      label: 'Shadows Clipping',
      min: -5.0, max: 0, step: 0.1,
      hint: 'Shadow clipping in sigma units',
    },
    {
      key: 'contrast_boost',
      label: 'Contrast Boost',
      min: 0.8, max: 2.0, step: 0.05,
      hint: 'Contrast enhancement factor',
    },
  ];

  return (
    <div className="space-y-5">
      <SectionHeading>Stretch Parameters</SectionHeading>

      <Card className="space-y-5">
        {sliders.map(({ key, label, min, max, step, hint }) => (
          <div key={key}>
            <div className="flex justify-between items-baseline mb-1.5">
              <FieldLabel hint={hint}>{label}</FieldLabel>
              <span className="text-sm font-mono text-cyan-300 tabular-nums">
                {stretchSettings[key]}
              </span>
            </div>
            <input
              type="range"
              min={min} max={max} step={step}
              value={stretchSettings[key]}
              onChange={(e) => setStretchSettings(prev => ({
                ...prev,
                [key]: parseFloat(e.target.value),
              }))}
              className="w-full accent-cyan-500 cursor-pointer"
            />
            <div className="flex justify-between text-xs text-slate-600 mt-0.5">
              <span>{min}</span><span>{max}</span>
            </div>
          </div>
        ))}

        {/* Linked channels toggle */}
        <div className="flex items-center justify-between pt-2 border-t border-slate-700/60">
          <div>
            <p className="text-sm font-medium text-slate-300">Linked Channels</p>
            <p className="text-xs text-slate-500 mt-0.5">Apply same stretch to R, G, B channels</p>
          </div>
          <button
            onClick={() => setStretchSettings(prev => ({ ...prev, linked_channels: !prev.linked_channels }))}
            className={`relative w-11 h-6 rounded-full transition-colors duration-200
              ${stretchSettings.linked_channels ? 'bg-cyan-500' : 'bg-slate-700'}`}
          >
            <span className={`absolute top-1 w-4 h-4 rounded-full bg-white shadow transition-all duration-200
              ${stretchSettings.linked_channels ? 'left-6' : 'left-1'}`}
            />
          </button>
        </div>
      </Card>
    </div>
  );
}

function DangerSection({ onClearCache }) {
  return (
    <div className="space-y-5">
      <SectionHeading>Danger Zone</SectionHeading>

      <Card className="border-red-900/30 bg-red-950/10">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-lg bg-red-500/10 text-red-400 flex-shrink-0 mt-0.5">
            <Trash2 className="w-4 h-4" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-slate-200">Clear Catalog Cache</p>
            <p className="text-xs text-slate-500 mt-0.5">
              Removes all cached thumbnails and catalog data. Favorites are preserved.
              The catalog will be rebuilt on the next scan.
            </p>
            <button
              onClick={onClearCache}
              className="mt-3 px-4 py-1.5 rounded-lg bg-red-600/20 text-red-300 border border-red-600/30
                hover:bg-red-600/30 hover:border-red-500/50 text-sm font-medium transition-all"
            >
              Clear Cache
            </button>
          </div>
        </div>
      </Card>
    </div>
  );
}

function AppearanceSection({ theme, setTheme }) {
  const themes = [
    {
      id: 'deep-space',
      name: 'Deep Space',
      description: 'The classic obsidian view with bright cyan accents, optimized for high contrast catalog browsing.',
      previewColors: ['#020617', '#0f172a', '#06b6d4']
    },
    {
      id: 'nordic-frost',
      name: 'Nordic Frost',
      description: 'A frosty, relaxing palette based on the popular Nord theme. Cold grays and soft blue-teal accents.',
      previewColors: ['#2e3440', '#3b4252', '#88c0d0']
    },
    {
      id: 'everforest',
      name: 'Everforest',
      description: 'A warm, organic green-gray theme designed for visual comfort and reduced eye strain.',
      previewColors: ['#2d353b', '#343f44', '#7fbbb3']
    },
    {
      id: 'night-owl',
      name: 'Night Owl',
      description: 'A deep midnight-navy theme with soft pastel teal, blue and yellow accents.',
      previewColors: ['#011627', '#0d283f', '#7fdbca']
    },
    {
      id: 'dracula-mellow',
      name: 'Dracula Mellow',
      description: 'A classic, soft purple-gray VSCode layout with relaxed pink and cyan highlights.',
      previewColors: ['#282a36', '#44475a', '#ff79c6']
    },
    {
      id: 'tron',
      name: 'Tron Legacy',
      description: 'A dark cybernetic grid style featuring glowing neon light-cycle cyan and high-contrast orange highlights.',
      previewColors: ['#00040a', '#0a1629', '#00f2ff']
    }
  ];

  return (
    <div className="space-y-5">
      <SectionHeading>Appearance</SectionHeading>

      <div className="grid grid-cols-1 gap-4">
        {themes.map((t) => (
          <button
            key={t.id}
            onClick={() => setTheme(t.id)}
            className={`flex items-center text-left p-4 rounded-xl border transition-all duration-200 outline-none w-full
              ${theme === t.id
                ? 'border-cyan-500/60 bg-cyan-500/5 text-cyan-300 ring-1 ring-cyan-500/20'
                : 'border-slate-700/60 bg-slate-800/20 text-slate-400 hover:border-slate-600 hover:bg-slate-800/40'}`}
          >
            {/* Color Preview Block */}
            <div className="flex-shrink-0 flex items-center gap-1.5 p-1 bg-slate-900/60 border border-slate-700/60 rounded-lg mr-4">
              <span className="w-4 h-4 rounded-full border border-white/5" style={{ backgroundColor: t.previewColors[0] }} />
              <span className="w-4 h-4 rounded-full border border-white/5" style={{ backgroundColor: t.previewColors[1], marginLeft: '-6px' }} />
              <span className="w-4 h-4 rounded-full border border-white/5" style={{ backgroundColor: t.previewColors[2], marginLeft: '-6px' }} />
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-slate-100">{t.name}</span>
                {theme === t.id && (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 font-medium border border-cyan-500/25">
                    Active
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 mt-1 leading-relaxed">{t.description}</p>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

/* ─── main component ─────────────────────────────────────────────────────── */

function SettingsModal({
  showSettings,
  onClose,
  defaultFolder,
  setDefaultFolder,
  defaultRender,
  setDefaultRender,
  stretchSettings,
  setStretchSettings,
  scanPattern,
  setScanPattern,
  ignoreFilters,
  setIgnoreFilters,
  theme,
  setTheme,
  onSave,
  onClearCache,
  onPastePath,
}) {
  const [activeSection, setActiveSection] = useState('general');
  const [variables, setVariables] = useState([]);
  const [filterInput, setFilterInput] = useState('');
  const [testResults, setTestResults] = useState(null);
  const [testLoading, setTestLoading] = useState(false);
  const [testError, setTestError] = useState(null);
  const patternInputRef = useRef(null);

  const initialThemeRef = useRef(theme);

  useEffect(() => {
    if (showSettings) {
      initialThemeRef.current = theme;
      fetchPatternVariables()
        .then(data => { if (data.variables) setVariables(data.variables); })
        .catch(err => console.error('Error fetching variables:', err));
    }
  }, [showSettings]);

  const handleClose = () => {
    setTheme(initialThemeRef.current);
    onClose();
  };

  if (!showSettings) return null;

  /* ── handlers ── */
  const handleInsertVariable = (token) => {
    const input = patternInputRef.current;
    if (!input) { setScanPattern(prev => prev ? `${prev}/${token}` : token); return; }
    const start = input.selectionStart;
    const end = input.selectionEnd;
    const current = scanPattern || '';
    const newValue = (start === current.length || current === '')
      ? (current ? `${current}/${token}` : token)
      : current.substring(0, start) + token + current.substring(end);
    setScanPattern(newValue);
    setTimeout(() => {
      input.focus();
      input.setSelectionRange(start + token.length, start + token.length);
    }, 0);
  };

  const handleAddFilter = () => {
    const f = filterInput.trim();
    if (f && !ignoreFilters.includes(f)) {
      setIgnoreFilters(prev => [...prev, f]);
      setFilterInput('');
    }
  };

  const handleRemoveFilter = (f) => setIgnoreFilters(prev => prev.filter(x => x !== f));

  const handleAddSuggestion = (s) => {
    if (!ignoreFilters.includes(s)) setIgnoreFilters(prev => [...prev, s]);
  };

  const handleFilterKeyDown = (e) => { if (e.key === 'Enter') { e.preventDefault(); handleAddFilter(); } };

  const handleTestPattern = async () => {
    if (!defaultFolder || defaultFolder === '' || defaultFolder === '.') {
      setTestError('Set a folder path first'); return;
    }
    setTestLoading(true); setTestError(null); setTestResults(null);
    try {
      const data = await testScanPattern(defaultFolder, scanPattern, ignoreFilters, 8);
      if (data.error) setTestError(data.error); else setTestResults(data);
    } catch {
      setTestError('Failed to test pattern. Is the backend running?');
    } finally {
      setTestLoading(false);
    }
  };

  /* ── section content ── */
  const sectionContent = {
    general: (
      <GeneralSection
        defaultFolder={defaultFolder} setDefaultFolder={setDefaultFolder}
        defaultRender={defaultRender} setDefaultRender={setDefaultRender}
        onPastePath={onPastePath}
      />
    ),
    scanner: (
      <ScannerSection
        defaultFolder={defaultFolder}
        scanPattern={scanPattern} setScanPattern={setScanPattern}
        ignoreFilters={ignoreFilters} setIgnoreFilters={setIgnoreFilters}
        variables={variables}
        filterInput={filterInput} setFilterInput={setFilterInput}
        handleInsertVariable={handleInsertVariable}
        handleAddFilter={handleAddFilter}
        handleRemoveFilter={handleRemoveFilter}
        handleAddSuggestion={handleAddSuggestion}
        handleFilterKeyDown={handleFilterKeyDown}
        handleTestPattern={handleTestPattern}
        testLoading={testLoading} testError={testError} testResults={testResults}
        patternInputRef={patternInputRef}
      />
    ),
    stretch: (
      <StretchSection stretchSettings={stretchSettings} setStretchSettings={setStretchSettings} />
    ),
    appearance: (
      <AppearanceSection theme={theme} setTheme={setTheme} />
    ),
    danger: (
      <DangerSection onClearCache={onClearCache} />
    ),
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      {/* Modal shell — wide, fixed height */}
      <div
        className="bg-slate-900 border border-white/10 rounded-2xl shadow-2xl
          w-full max-w-4xl flex flex-col"
        style={{ height: 'min(90vh, 680px)' }}
      >
        {/* ── header ── */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700/60 flex-shrink-0">
          <div>
            <h2 className="text-lg font-bold tracking-tight">Settings</h2>
            <p className="text-xs text-slate-500 mt-0.5">Configure Astrophoto Explorer</p>
          </div>
          <div className="flex-h gap-3 flex items-center">
            <button
              onClick={handleClose}
              className="px-4 py-1.5 rounded-lg bg-slate-700/60 hover:bg-slate-700 text-sm text-slate-300 transition"
            >
              Cancel
            </button>
            <button
              onClick={onSave}
              className="px-5 py-1.5 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-sm font-semibold
                text-slate-900 shadow-md shadow-cyan-500/20 transition"
            >
              Save Changes
            </button>
            <button
              onClick={handleClose}
              className="text-slate-400 hover:text-slate-100 transition ml-1"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* ── body: sidebar + content ── */}
        <div className="flex flex-1 min-h-0">

          {/* Left nav sidebar */}
          <nav className="w-44 flex-shrink-0 border-r border-slate-700/60 py-4 px-2 space-y-0.5">
            {SECTIONS.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActiveSection(id)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium
                  transition-all duration-150 text-left
                  ${activeSection === id
                    ? 'bg-cyan-500/10 text-cyan-300 border border-cyan-500/20'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                  }`}
              >
                <Icon className="w-4 h-4 flex-shrink-0" />
                {label}
              </button>
            ))}
          </nav>

          {/* Right content panel — scrollable */}
          <div className="flex-1 overflow-y-auto px-6 py-5">
            {sectionContent[activeSection]}
          </div>
        </div>
      </div>
    </div>
  );
}

export default SettingsModal;
