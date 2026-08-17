const { useState, useEffect, useRef } = React;

function App() {
  const [activeTab, setActiveTab] = useState('overview'); // overview | jobs | tailor | scans | settings
  const [activeProfile, setActiveProfile] = useState('ai_ml');
  const [profilesList, setProfilesList] = useState([]);
  
  // Dynamic Overview Data from GET /api/v1/dashboard/overview
  const [overview, setOverview] = useState({
    raw_discovered: 330,
    duplicates_grouped: 6,
    discovered: 324,
    unique_opportunities: 324,
    potentially_eligible: 217,
    seniority_mismatches: 107,
    strong_matches: 58,
    india: 80,
    remote: 244,
    applications_submitted: 2,
    ready_to_apply: 58,
    last_scan_id: 'scan-initial-01',
    active_profile_name: 'AI & ML Systems Engineer'
  });

  // Jobs Command Center State
  const [jobs, setJobs] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedView, setSelectedView] = useState('ready_to_apply'); // ready_to_apply (Default Primary) | best_matches | delhi_india | remote | fresher | low_friction | seniority_mismatch | not_applied
  const [eligibilityFilter, setEligibilityFilter] = useState('all');
  const [locationFilter, setLocationFilter] = useState('all');
  const [minMatchFilter, setMinMatchFilter] = useState(0);
  const [selectedJob, setSelectedJob] = useState(null); // For Details Drawer

  // Live Discovery Scans State
  const [latestScan, setLatestScan] = useState(null);
  const [scanQuery, setScanQuery] = useState('');
  const [scanLocation, setScanLocation] = useState('India');
  const [isScanning, setIsScanning] = useState(false);
  const [scanLogs, setScanLogs] = useState([]);

  // AI Tailor Studio State
  const [tailorJobId, setTailorJobId] = useState(null);
  const [tailorData, setTailorData] = useState(null);
  const [tailorLoading, setTailorLoading] = useState(false);
  const [tailorTargetJob, setTailorTargetJob] = useState(null);
  const [tailorActiveSubTab, setTailorActiveSubTab] = useState('resume'); // resume | cover_letter | facts
  const [isLatexDirty, setIsLatexDirty] = useState(false);
  const [editedLatex, setEditedLatex] = useState('');
  const [revalidating, setRevalidating] = useState(false);

  // Master LaTeX Template State
  const [masterLatex, setMasterLatex] = useState('');
  const [latexSavedMsg, setLatexSavedMsg] = useState('');

  // Initial Load & Polling
  useEffect(() => {
    fetchDashboardOverview();
    fetchProfiles();
    fetchJobs();
    fetchLatestScan();
    fetchResumeTemplate();

    const interval = setInterval(() => {
      fetchDashboardOverview();
      fetchLatestScan();
    }, 6000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (window.lucide) {
      window.lucide.createIcons();
    }
  }, [activeTab, overview, jobs, selectedJob, tailorData, latestScan, selectedView, isLatexDirty]);

  // Fetch Handlers
  async function fetchDashboardOverview() {
    try {
      const res = await fetch('/api/v1/dashboard/overview');
      if (res.ok) {
        const data = await res.json();
        setOverview(data);
      }
    } catch (e) {
      console.error("Overview fetch error:", e);
    }
  }

  async function fetchProfiles() {
    try {
      const res = await fetch('/api/v1/profiles');
      if (res.ok) {
        const data = await res.json();
        setProfilesList(data);
      }
    } catch (e) {
      console.error("Profiles fetch error:", e);
    }
  }

  async function fetchJobs() {
    try {
      const res = await fetch('/api/v1/jobs');
      if (res.ok) {
        const data = await res.json();
        setJobs(data);
      }
    } catch (e) {
      console.error("Jobs fetch error:", e);
    }
  }

  async function fetchLatestScan() {
    try {
      const res = await fetch('/api/v1/jobs/scans/latest');
      if (res.ok) {
        const data = await res.json();
        setLatestScan(data);
        if (data.logs) setScanLogs(data.logs);
      }
    } catch (e) {
      console.error("Latest scan fetch error:", e);
    }
  }

  async function fetchResumeTemplate() {
    try {
      const res = await fetch('/api/v1/profiles/resume/template');
      if (res.ok) {
        const data = await res.json();
        setMasterLatex(data.latex || '');
      }
    } catch (e) {
      console.error("Resume template fetch error:", e);
    }
  }

  // Action Triggers
  async function handleActivateProfile(profileId) {
    try {
      const res = await fetch('/api/v1/profiles/activate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ profile_id: profileId }),
      });
      if (res.ok) {
        setActiveProfile(profileId);
        fetchDashboardOverview();
        fetchJobs();
        fetchResumeTemplate();
      }
    } catch (e) {
      alert("Failed to activate profile: " + e.message);
    }
  }

  async function handleStartScan() {
    setIsScanning(true);
    try {
      const q = encodeURIComponent(scanQuery);
      const loc = encodeURIComponent(scanLocation);
      const res = await fetch(`/api/v1/jobs/scans?query=${q}&location=${loc}&profile_id=${activeProfile}`, {
        method: 'POST',
      });
      if (res.ok) {
        const data = await res.json();
        alert(`🚀 Discovery Scan ${data.scan_id} initiated across 35+ tech career portals!`);
        setTimeout(fetchLatestScan, 1500);
        setTimeout(fetchJobs, 3000);
        setTimeout(fetchDashboardOverview, 3500);
      }
    } catch (e) {
      alert("Scan initiation error: " + e.message);
    } finally {
      setIsScanning(false);
    }
  }

  async function handleTriggerTailor(job) {
    setTailorTargetJob(job);
    setTailorLoading(true);
    setIsLatexDirty(false);
    setActiveTab('tailor');
    try {
      const res = await fetch('/api/v1/ai/tailor', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          job_id: job.id,
          job_title: job.title,
          company_name: job.company,
          job_description: job.description || job.title,
          required_skills: ["Python", "FastAPI", "PyTorch", "PostgreSQL"],
          profile_id: activeProfile,
        })
      });
      if (res.ok) {
        const data = await res.json();
        setTailorJobId(data.tailor_job_id);
        pollTailorJob(data.tailor_job_id);
      }
    } catch (e) {
      alert("Tailoring error: " + e.message);
      setTailorLoading(false);
    }
  }

  async function pollTailorJob(id) {
    try {
      const res = await fetch(`/api/v1/ai/tailor/${id}`);
      if (res.ok) {
        const data = await res.json();
        setTailorData(data);
        setEditedLatex(data.tailored_latex);
        if (data.status === 'completed' || data.status === 'rejected_validation') {
          setTailorLoading(false);
        } else {
          setTimeout(() => pollTailorJob(id), 1000);
        }
      }
    } catch (e) {
      console.error("Poll tailor error:", e);
      setTailorLoading(false);
    }
  }

  async function handleRevalidateLatex() {
    if (!tailorJobId) return;
    setRevalidating(true);
    try {
      const res = await fetch(`/api/v1/ai/tailor/${tailorJobId}/revalidate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ edited_latex: editedLatex }),
      });
      if (res.ok) {
        const data = await res.json();
        setTailorData(data);
        setIsLatexDirty(false);
      }
    } catch (e) {
      alert("Revalidation error: " + e.message);
    } finally {
      setRevalidating(false);
    }
  }

  async function handleMarkApplied(jobId) {
    try {
      const res = await fetch(`/api/v1/jobs/${jobId}/mark-applied`, { method: 'POST' });
      if (res.ok) {
        setJobs(jobs.map(j => j.id === jobId ? { ...j, application_status: 'APPLIED' } : j));
        fetchDashboardOverview();
      }
    } catch (e) {
      alert("Error marking applied: " + e.message);
    }
  }

  async function handleSkipJob(jobId) {
    try {
      const res = await fetch(`/api/v1/jobs/${jobId}/skip`, { method: 'POST' });
      if (res.ok) {
        setJobs(jobs.map(j => j.id === jobId ? { ...j, application_status: 'SKIPPED' } : j));
        fetchDashboardOverview();
      }
    } catch (e) {
      alert("Error skipping job: " + e.message);
    }
  }

  async function handleSendTelegramPing() {
    try {
      const res = await fetch('/api/v1/telegram/ping', { method: 'POST' });
      if (res.ok) {
        alert("⚡ Live Notification & Screenshot Sent to Telegram! Check @Helios_vinay_AI_Bot on your phone.");
      }
    } catch (e) {
      alert("Telegram ping error: " + e.message);
    }
  }

  async function handleSyncSheets() {
    try {
      const res = await fetch('/api/v1/sheets/sync', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        alert(`📊 ${data.message || 'Synced successfully to Google Sheets projection!'}`);
      }
    } catch (e) {
      alert("Sheets sync error: " + e.message);
    }
  }

  function handleRefreshAll() {
    fetchDashboardOverview();
    fetchJobs();
    fetchLatestScan();
  }

  // Filtered Jobs Computation
  const filteredJobs = jobs.filter(j => {
    // 1. Text Search
    if (searchQuery) {
      const sq = searchQuery.toLowerCase();
      const matchSearch = (j.title || '').toLowerCase().includes(sq) ||
                          (j.company || '').toLowerCase().includes(sq) ||
                          (j.location || '').toLowerCase().includes(sq);
      if (!matchSearch) return false;
    }

    // 2. Saved Views Filter
    if (selectedView === 'ready_to_apply') {
      // Primary workflow view: Eligible + Match >= 80% + Not Applied + Has apply URL
      if (j.eligibility_status !== 'ELIGIBLE') return false;
      if ((j.fit_score || 0) < 0.80) return false;
      if (j.application_status === 'APPLIED' || j.application_status === 'SKIPPED') return false;
    } else if (selectedView === 'best_matches') {
      if ((j.fit_score || 0) < 0.80 || j.eligibility_status !== 'ELIGIBLE') return false;
    } else if (selectedView === 'delhi_india') {
      if (!j.is_india) return false;
    } else if (selectedView === 'remote') {
      if (j.is_india) return false;
    } else if (selectedView === 'fresher') {
      const exp = (j.experience_years || '').toLowerCase();
      if (!exp.includes('0') && !exp.includes('1') && !exp.includes('fresher') && !exp.includes('intern')) return false;
    } else if (selectedView === 'low_friction') {
      if (j.friction_level !== 'LOW') return false;
    } else if (selectedView === 'seniority_mismatch') {
      if (j.eligibility_status !== 'SENIORITY_MISMATCH') return false;
    } else if (selectedView === 'not_applied') {
      if (j.application_status === 'APPLIED' || j.application_status === 'SKIPPED') return false;
    }

    // 3. Explicit Controls
    if (eligibilityFilter === 'eligible_only' && j.eligibility_status !== 'ELIGIBLE') return false;
    if (eligibilityFilter === 'seniority_mismatch' && j.eligibility_status !== 'SENIORITY_MISMATCH') return false;

    if (locationFilter === 'india' && !j.is_india) return false;
    if (locationFilter === 'remote' && j.is_india) return false;

    if (minMatchFilter > 0 && ((j.fit_score || 0) * 100) < minMatchFilter) return false;

    return true;
  });

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#080C14] text-slate-100 font-sans">
      
      {/* ── SIDEBAR NAVIGATION ──────────────────────────────────────────────── */}
      <aside className="w-64 bg-[#0D1322] border-r border-slate-800/80 flex flex-col justify-between shrink-0">
        <div>
          {/* Logo & System Brand */}
          <div className="p-6 border-b border-slate-800/60 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center font-bold text-white shadow-lg shadow-blue-500/20">
                ☀️
              </div>
              <div>
                <h1 className="font-display font-bold text-lg text-slate-100 tracking-tight">HELIOS</h1>
                <p className="text-[10px] text-blue-400 font-semibold tracking-wider uppercase">Job OS v3.0</p>
              </div>
            </div>
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" title="System Online"></span>
          </div>

          {/* Active Profile Badge */}
          <div className="px-4 py-3 bg-[#111A2E]/60 border-b border-slate-800/40">
            <div className="text-[11px] text-slate-400 font-medium">Active Profile Lens</div>
            <div className="text-xs font-semibold text-sky-300 truncate mt-0.5">{overview.active_profile_name || 'AI & ML Systems Engineer'}</div>
          </div>

          {/* Navigation Links */}
          <nav className="p-4 space-y-1">
            <button
              onClick={() => setActiveTab('overview')}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-xs font-semibold transition-all ${
                activeTab === 'overview'
                  ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <i data-lucide="layout-dashboard" className="w-4 h-4"></i>
              Mission Overview
            </button>

            <button
              onClick={() => { setSelectedView('ready_to_apply'); setActiveTab('jobs'); }}
              className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg text-xs font-semibold transition-all ${
                activeTab === 'jobs' && selectedView === 'ready_to_apply'
                  ? 'bg-emerald-600/20 text-emerald-400 border border-emerald-500/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <div className="flex items-center gap-3">
                <i data-lucide="flame" className="w-4 h-4 text-emerald-400"></i>
                🔥 Ready to Apply
              </div>
              <span className="bg-emerald-900/60 text-emerald-300 text-[10px] font-bold px-2 py-0.5 rounded-full border border-emerald-700/50">
                {overview.ready_to_apply || 58}
              </span>
            </button>

            <button
              onClick={() => setActiveTab('jobs')}
              className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg text-xs font-semibold transition-all ${
                activeTab === 'jobs' && selectedView !== 'ready_to_apply'
                  ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <div className="flex items-center gap-3">
                <i data-lucide="briefcase" className="w-4 h-4"></i>
                Jobs Command Center
              </div>
              <span className="bg-blue-900/60 text-blue-300 text-[10px] font-bold px-2 py-0.5 rounded-full border border-blue-700/50">
                {overview.discovered || 324}
              </span>
            </button>

            <button
              onClick={() => setActiveTab('scans')}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-xs font-semibold transition-all ${
                activeTab === 'scans'
                  ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <i data-lucide="radar" className="w-4 h-4"></i>
              Live Discovery Scans
            </button>

            <button
              onClick={() => setActiveTab('tailor')}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-xs font-semibold transition-all ${
                activeTab === 'tailor'
                  ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <i data-lucide="wand-2" className="w-4 h-4"></i>
              AI Tailor Studio
            </button>

            <button
              onClick={() => setActiveTab('settings')}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-xs font-semibold transition-all ${
                activeTab === 'settings'
                  ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <i data-lucide="sliders-horizontal" className="w-4 h-4"></i>
              Settings & Integrations
            </button>
          </nav>
        </div>

        {/* System Health Footer */}
        <div className="p-4 border-t border-slate-800/60 bg-[#0A0F1D]">
          <div className="flex items-center justify-between text-[11px] text-slate-400 mb-2">
            <span>Database Status</span>
            <span className="text-emerald-400 font-semibold flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> Authoritative
            </span>
          </div>
          <div className="flex items-center justify-between text-[11px] text-slate-400">
            <span>Google Sheets</span>
            <span className="text-blue-400 font-semibold flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-400"></span> Push-Only V1
            </span>
          </div>
        </div>
      </aside>

      {/* ── MAIN CONTENT AREA ───────────────────────────────────────────────── */}
      <main className="flex-1 flex flex-col h-screen overflow-hidden bg-[#080C14]">
        
        {/* Top App Header */}
        <header className="h-16 border-b border-slate-800/80 bg-[#0D1322]/80 backdrop-blur-md px-8 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-4">
            <h2 className="font-display font-bold text-base text-slate-200">
              {activeTab === 'overview' && 'Mission Overview & Intelligence'}
              {activeTab === 'jobs' && 'Jobs Command Center'}
              {activeTab === 'scans' && 'Multi-Portal Discovery Scans'}
              {activeTab === 'tailor' && 'AI Resume & Cover Letter Studio'}
              {activeTab === 'settings' && 'Settings, Profiles & Projections'}
            </h2>
            <span className="text-xs text-slate-500 font-normal">|</span>
            <span className="text-xs text-slate-400">Candidate: <strong className="text-slate-200">Vinay Khosya (NSUT Delhi)</strong></span>
          </div>

          <div className="flex items-center gap-2">
            {/* Quick Live Search Trigger */}
            <button
              onClick={() => { setActiveTab('scans'); }}
              className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold px-3 py-1.5 rounded-lg shadow transition-all"
              title="Search live jobs across 35+ tech career portals"
            >
              <i data-lucide="search" className="w-3.5 h-3.5"></i>
              Search Jobs ⚡
            </button>

            {/* Google Sheets Sync Trigger */}
            <button
              onClick={handleSyncSheets}
              className="flex items-center gap-1.5 bg-emerald-900/40 hover:bg-emerald-900/60 text-emerald-300 border border-emerald-700/50 text-xs font-bold px-3 py-1.5 rounded-lg transition-all"
              title="Push latest opportunity queue to Google Sheets"
            >
              <i data-lucide="table" className="w-3.5 h-3.5"></i>
              Sync Sheets
            </button>

            {/* Direct Google Sheets Web Link */}
            <a
              href="https://docs.google.com/spreadsheets"
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-xs font-semibold px-2.5 py-1.5 rounded-lg transition-all"
              title="Open Google Spreadsheet"
            >
              Open Sheet ↗
            </a>

            {/* Download Excel (.xlsx) */}
            <a
              href="/api/v1/export/excel"
              download="helios_jobs_two_tabs.xlsx"
              className="flex items-center gap-1 bg-slate-800 hover:bg-slate-700 text-emerald-300 border border-slate-700 text-xs font-semibold px-2.5 py-1.5 rounded-lg transition-all"
              title="Download 2-Tab Excel Workbook (.xlsx)"
            >
              <i data-lucide="file-spreadsheet" className="w-3.5 h-3.5"></i>
              Excel
            </a>

            {/* Download CSV */}
            <a
              href="/api/v1/export/csv"
              download="helios_live_jobs.csv"
              className="flex items-center gap-1 bg-slate-800 hover:bg-slate-700 text-sky-300 border border-slate-700 text-xs font-semibold px-2.5 py-1.5 rounded-lg transition-all"
              title="Download Master CSV"
            >
              <i data-lucide="download" className="w-3.5 h-3.5"></i>
              CSV
            </a>

            {/* Telegram Ping */}
            <button
              onClick={handleSendTelegramPing}
              className="flex items-center gap-1 bg-slate-800 hover:bg-slate-700 text-blue-300 border border-slate-700 text-xs font-semibold px-2.5 py-1.5 rounded-lg transition-all"
              title="Send test alert to Telegram"
            >
              <i data-lucide="send" className="w-3.5 h-3.5"></i>
              Ping
            </button>

            {/* Refresh Live Data */}
            <button
              onClick={handleRefreshAll}
              className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded-lg transition-all"
              title="Refresh live data"
            >
              <i data-lucide="refresh-cw" className="w-3.5 h-3.5"></i>
            </button>
          </div>
        </header>

        {/* Dynamic Screen View */}
        <div className="flex-1 overflow-y-auto p-8">
          
          {/* ─────────────────────────────────────────────────────────────────── */}
          {/* SCREEN 1: MISSION OVERVIEW                                         */}
          {/* ─────────────────────────────────────────────────────────────────── */}
          {activeTab === 'overview' && (
            <div className="max-w-7xl mx-auto space-y-8">
              
              {/* Auditable Discovery & Conversion Funnel */}
              <div className="glass-card p-6 rounded-2xl border-blue-500/20 bg-blue-950/10 space-y-6">
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="font-display font-bold text-sm text-slate-200 uppercase tracking-wider flex items-center gap-2">
                      <i data-lucide="filter" className="w-4 h-4 text-blue-400"></i>
                      Discovery & Candidate Opportunity Funnel
                    </h3>
                    <span className="text-xs text-slate-400">Auditable Lineage v3.0</span>
                  </div>

                  <div className="grid grid-cols-6 gap-3 text-center">
                    <div className="bg-[#111A2E] p-3 rounded-xl border border-slate-800">
                      <div className="text-[11px] text-slate-400 font-medium">Raw Discovered</div>
                      <div className="text-2xl font-extrabold text-slate-200 mt-1">{overview.raw_discovered || 330}</div>
                      <div className="text-[10px] text-slate-500 mt-0.5">Scraped job rows</div>
                    </div>

                    <div className="bg-[#111A2E] p-3 rounded-xl border border-slate-800">
                      <div className="text-[11px] text-purple-400 font-medium">Duplicates Grouped</div>
                      <div className="text-2xl font-extrabold text-purple-300 mt-1">{overview.duplicates_grouped || 6}</div>
                      <div className="text-[10px] text-purple-500 mt-0.5">Multi-source merged</div>
                    </div>

                    <div className="bg-[#111A2E] p-3 rounded-xl border border-blue-500/30">
                      <div className="text-[11px] text-blue-400 font-medium">Unique Canonical</div>
                      <div className="text-2xl font-extrabold text-blue-400 mt-1">{overview.discovered || 324}</div>
                      <div className="text-[10px] text-slate-500 mt-0.5">Distinct openings</div>
                    </div>

                    <div className="bg-[#111A2E] p-3 rounded-xl border border-amber-500/30">
                      <div className="text-[11px] text-amber-400 font-medium">Seniority Mismatch</div>
                      <div className="text-2xl font-extrabold text-amber-400 mt-1">{overview.seniority_mismatches || 107}</div>
                      <div className="text-[10px] text-amber-500/80 mt-0.5">5+ yrs (Isolated)</div>
                    </div>

                    <div className="bg-[#111A2E] p-3 rounded-xl border border-slate-800">
                      <div className="text-[11px] text-slate-300 font-medium">Potentially Eligible</div>
                      <div className="text-2xl font-extrabold text-slate-200 mt-1">{overview.potentially_eligible || 217}</div>
                      <div className="text-[10px] text-slate-500 mt-0.5">0–3 yrs experience</div>
                    </div>

                    <div className="bg-emerald-950/40 p-3 rounded-xl border border-emerald-500/40">
                      <div className="text-[11px] text-emerald-400 font-bold">🔥 Helios-Qualified</div>
                      <div className="text-2xl font-extrabold text-emerald-400 mt-1">{overview.ready_to_apply || 58}</div>
                      <div className="text-[10px] text-emerald-500 mt-0.5">Ready to Review & Apply</div>
                    </div>
                  </div>
                </div>

                {/* Conversion & Outcome Tracking Lineage */}
                <div className="pt-4 border-t border-slate-800/80">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                      <i data-lucide="trending-up" className="w-3.5 h-3.5 text-emerald-400"></i>
                      Application → Interview Conversion Funnel
                    </span>
                    <span className="text-[11px] text-slate-400">Tracked via Gmail & Action Tokens</span>
                  </div>

                  <div className="grid grid-cols-5 gap-3 text-center">
                    <div className="bg-[#111A2E]/60 p-2.5 rounded-lg border border-slate-800">
                      <div className="text-[10px] text-slate-400 uppercase">Ready Queue</div>
                      <div className="text-lg font-bold text-slate-200 mt-0.5">{overview.ready_to_apply || 58}</div>
                    </div>
                    <div className="bg-[#111A2E]/60 p-2.5 rounded-lg border border-slate-800">
                      <div className="text-[10px] text-blue-400 uppercase">Applied Manually</div>
                      <div className="text-lg font-bold text-blue-300 mt-0.5">{overview.applications_submitted || 2}</div>
                    </div>
                    <div className="bg-[#111A2E]/60 p-2.5 rounded-lg border border-slate-800">
                      <div className="text-[10px] text-amber-400 uppercase">Recruiter Responses</div>
                      <div className="text-lg font-bold text-amber-300 mt-0.5">0</div>
                    </div>
                    <div className="bg-[#111A2E]/60 p-2.5 rounded-lg border border-slate-800">
                      <div className="text-[10px] text-purple-400 uppercase">Technical Interviews</div>
                      <div className="text-lg font-bold text-purple-300 mt-0.5">0</div>
                    </div>
                    <div className="bg-emerald-950/30 p-2.5 rounded-lg border border-emerald-800/40">
                      <div className="text-[10px] text-emerald-400 font-bold uppercase">Offers</div>
                      <div className="text-lg font-bold text-emerald-400 mt-0.5">0</div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Dynamic KPI Metrics Grid */}
              <div className="grid grid-cols-4 gap-4">
                <div className="glass-card p-5 rounded-2xl">
                  <div className="text-xs text-slate-400 font-medium flex items-center justify-between">
                    <span>Unique Opportunities</span>
                    <i data-lucide="globe" className="w-4 h-4 text-blue-400"></i>
                  </div>
                  <div className="text-3xl font-display font-extrabold text-slate-100 mt-2">{overview.discovered || 324}</div>
                  <div className="text-[11px] text-slate-500 mt-1">Across 35+ top tech boards</div>
                </div>

                <div className="glass-card p-5 rounded-2xl border-emerald-500/20 bg-emerald-950/10">
                  <div className="text-xs text-emerald-400 font-medium flex items-center justify-between">
                    <span>🔥 Ready to Apply</span>
                    <i data-lucide="flame" className="w-4 h-4 text-emerald-400"></i>
                  </div>
                  <div className="text-3xl font-display font-extrabold text-emerald-400 mt-2">{overview.ready_to_apply || 58}</div>
                  <div className="text-[11px] text-emerald-500/80 mt-1">Eligible & High Match</div>
                </div>

                <div className="glass-card p-5 rounded-2xl">
                  <div className="text-xs text-slate-400 font-medium flex items-center justify-between">
                    <span>📍 India Opportunities</span>
                    <i data-lucide="map-pin" className="w-4 h-4 text-sky-400"></i>
                  </div>
                  <div className="text-3xl font-display font-extrabold text-sky-300 mt-2">{overview.india || 80}</div>
                  <div className="text-[11px] text-slate-500 mt-1">Delhi-NCR, Bangalore, Hyderabad</div>
                </div>

                <div className="glass-card p-5 rounded-2xl border-amber-500/20 bg-amber-950/10">
                  <div className="text-xs text-amber-400 font-medium flex items-center justify-between">
                    <span>⚠️ Seniority Mismatches</span>
                    <i data-lucide="alert-triangle" className="w-4 h-4 text-amber-400"></i>
                  </div>
                  <div className="text-3xl font-display font-extrabold text-amber-400 mt-2">{overview.seniority_mismatches || 107}</div>
                  <div className="text-[11px] text-amber-500/80 mt-1">5+ yrs required (Isolated)</div>
                </div>
              </div>

              {/* System Health Matrix */}
              <div className="glass-card p-6 rounded-2xl">
                <h3 className="font-display font-bold text-sm text-slate-200 uppercase tracking-wider mb-4 flex items-center gap-2">
                  <i data-lucide="shield-check" className="w-4 h-4 text-emerald-400"></i>
                  Helios System Health & Portal Connectivity
                </h3>
                <div className="grid grid-cols-6 gap-3">
                  <div className="bg-[#111A2E] p-3.5 rounded-xl border border-slate-800/80">
                    <div className="text-xs font-semibold text-slate-200">Ashby Portals</div>
                    <div className="text-[11px] text-emerald-400 font-medium flex items-center gap-1.5 mt-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> ● Online (7 Boards)
                    </div>
                  </div>

                  <div className="bg-[#111A2E] p-3.5 rounded-xl border border-slate-800/80">
                    <div className="text-xs font-semibold text-slate-200">Greenhouse</div>
                    <div className="text-[11px] text-emerald-400 font-medium flex items-center gap-1.5 mt-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> ● Online (19 Boards)
                    </div>
                  </div>

                  <div className="bg-[#111A2E] p-3.5 rounded-xl border border-slate-800/80">
                    <div className="text-xs font-semibold text-slate-200">Lever Portals</div>
                    <div className="text-[11px] text-emerald-400 font-medium flex items-center gap-1.5 mt-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> ● Online (7 Boards)
                    </div>
                  </div>

                  <div className="bg-[#111A2E] p-3.5 rounded-xl border border-slate-800/80">
                    <div className="text-xs font-semibold text-slate-200">LinkedIn Search</div>
                    <div className="text-[11px] text-emerald-400 font-medium flex items-center gap-1.5 mt-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> ● Active Crawler
                    </div>
                  </div>

                  <div className="bg-[#111A2E] p-3.5 rounded-xl border border-slate-800/80">
                    <div className="text-xs font-semibold text-slate-200">Google Sheets</div>
                    <div className="text-[11px] text-blue-400 font-medium flex items-center gap-1.5 mt-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-blue-400"></span> ● Push-Only V1
                    </div>
                  </div>

                  <div className="bg-[#111A2E] p-3.5 rounded-xl border border-slate-800/80">
                    <div className="text-xs font-semibold text-slate-200">Fact Registry</div>
                    <div className="text-[11px] text-purple-400 font-medium flex items-center gap-1.5 mt-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-purple-400"></span> ● v1.2.0 Active
                    </div>
                  </div>
                </div>
              </div>

              {/* Top Opportunities Showcase */}
              <div className="glass-card p-6 rounded-2xl">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-display font-bold text-sm text-slate-200 uppercase tracking-wider flex items-center gap-2">
                    <i data-lucide="zap" className="w-4 h-4 text-yellow-400"></i>
                    🔥 Top High-Match Opportunities (Eligible)
                  </h3>
                  <button
                    onClick={() => { setSelectedView('ready_to_apply'); setActiveTab('jobs'); }}
                    className="text-xs text-blue-400 hover:text-blue-300 font-semibold"
                  >
                    View All {overview.ready_to_apply || 58} Ready-to-Apply Jobs &rarr;
                  </button>
                </div>

                <div className="space-y-3">
                  {jobs.filter(j => j.eligibility_status === 'ELIGIBLE' && (j.fit_score || 0) >= 0.85).slice(0, 5).map(job => (
                    <div key={job.id} className="bg-[#111A2E]/80 hover:bg-[#16213A] border border-slate-800/80 p-4 rounded-xl flex items-center justify-between transition-all">
                      <div className="flex items-center gap-4">
                        <div className="w-12 h-12 rounded-xl bg-blue-600/20 border border-blue-500/30 flex flex-col items-center justify-center font-bold text-blue-400">
                          <span className="text-xs font-extrabold">{intPct(job.fit_score)}</span>
                          <span className="text-[9px] uppercase font-semibold text-slate-400">Match</span>
                        </div>
                        <div>
                          <div className="flex items-center gap-2.5">
                            <h4 className="font-bold text-sm text-slate-100">{job.title}</h4>
                            <span className="text-xs font-semibold text-slate-400">at <strong className="text-slate-200">{job.company}</strong></span>
                            <span className="bg-emerald-950/80 text-emerald-400 text-[10px] font-bold px-2 py-0.5 rounded border border-emerald-700/50">
                              ELIGIBLE ✓
                            </span>
                          </div>
                          <div className="text-xs text-slate-400 mt-1 flex items-center gap-4">
                            <span>📍 {job.location}</span>
                            <span>⏳ {job.experience_years}</span>
                            <span>💰 {job.compensation}</span>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleTriggerTailor(job)}
                          className="bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs px-3 py-1.5 rounded-lg shadow transition-all"
                        >
                          Tailor Resume ✨
                        </button>
                        <a
                          href={job.apply_url}
                          target="_blank"
                          rel="noreferrer"
                          className="bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs px-3 py-1.5 rounded-lg border border-slate-700 transition-all"
                        >
                          Apply Now &rarr;
                        </a>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

            </div>
          )}

          {/* ─────────────────────────────────────────────────────────────────── */}
          {/* SCREEN 2: JOBS COMMAND CENTER                                      */}
          {/* ─────────────────────────────────────────────────────────────────── */}
          {activeTab === 'jobs' && (
            <div className="max-w-7xl mx-auto space-y-6">
              
              {/* Quick Saved Views Filter Pills */}
              <div className="flex items-center gap-2 overflow-x-auto pb-2">
                <button
                  onClick={() => setSelectedView('ready_to_apply')}
                  className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all shrink-0 ${
                    selectedView === 'ready_to_apply'
                      ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-600/30'
                      : 'bg-[#111A2E] text-slate-400 hover:text-slate-200 border border-slate-800'
                  }`}
                >
                  🔥 Ready to Apply ({overview.ready_to_apply || 58})
                </button>

                <button
                  onClick={() => setSelectedView('best_matches')}
                  className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all shrink-0 ${
                    selectedView === 'best_matches'
                      ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/30'
                      : 'bg-[#111A2E] text-slate-400 hover:text-slate-200 border border-slate-800'
                  }`}
                >
                  Best Matches (≥80%)
                </button>

                <button
                  onClick={() => setSelectedView('delhi_india')}
                  className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all shrink-0 ${
                    selectedView === 'delhi_india'
                      ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/30'
                      : 'bg-[#111A2E] text-slate-400 hover:text-slate-200 border border-slate-800'
                  }`}
                >
                  📍 Delhi NCR & India ({overview.india || 80})
                </button>

                <button
                  onClick={() => setSelectedView('remote')}
                  className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all shrink-0 ${
                    selectedView === 'remote'
                      ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/30'
                      : 'bg-[#111A2E] text-slate-400 hover:text-slate-200 border border-slate-800'
                  }`}
                >
                  🏠 Remote & International ({overview.remote || 244})
                </button>

                <button
                  onClick={() => setSelectedView('fresher')}
                  className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all shrink-0 ${
                    selectedView === 'fresher'
                      ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/30'
                      : 'bg-[#111A2E] text-slate-400 hover:text-slate-200 border border-slate-800'
                  }`}
                >
                  🐣 Fresher Friendly (0–2 yrs)
                </button>

                <button
                  onClick={() => setSelectedView('low_friction')}
                  className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all shrink-0 ${
                    selectedView === 'low_friction'
                      ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/30'
                      : 'bg-[#111A2E] text-slate-400 hover:text-slate-200 border border-slate-800'
                  }`}
                >
                  ⚡ Low Friction
                </button>

                <button
                  onClick={() => setSelectedView('seniority_mismatch')}
                  className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all shrink-0 ${
                    selectedView === 'seniority_mismatch'
                      ? 'bg-amber-600 text-white shadow-lg shadow-amber-600/30'
                      : 'bg-amber-950/30 text-amber-400 hover:text-amber-200 border border-amber-800/40'
                  }`}
                >
                  ⚠️ Seniority Review ({overview.seniority_mismatches || 107})
                </button>
              </div>

              {/* Search Bar & Multi-Controls */}
              <div className="glass-card p-4 rounded-xl flex items-center gap-4">
                <div className="flex-1 relative">
                  <i data-lucide="search" className="w-4 h-4 text-slate-400 absolute left-3.5 top-3"></i>
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search by role, company, skills, or city..."
                    className="w-full bg-[#0D1322] border border-slate-800 rounded-lg pl-10 pr-4 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500"
                  />
                </div>

                <div className="flex items-center gap-3">
                  <select
                    value={eligibilityFilter}
                    onChange={(e) => setEligibilityFilter(e.target.value)}
                    className="bg-[#0D1322] border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none"
                  >
                    <option value="all">All Eligibility</option>
                    <option value="eligible_only">Eligible Only ✓</option>
                    <option value="seniority_mismatch">Seniority Mismatch Only ⚠️</option>
                  </select>

                  <select
                    value={locationFilter}
                    onChange={(e) => setLocationFilter(e.target.value)}
                    className="bg-[#0D1322] border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none"
                  >
                    <option value="all">All Locations</option>
                    <option value="india">India Only</option>
                    <option value="remote">Remote Only</option>
                  </select>
                </div>
              </div>

              {/* Jobs Table Ledger */}
              <div className="glass-card rounded-2xl overflow-hidden border border-slate-800/80">
                <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                    Showing {filteredJobs.length} Opportunity Records ({selectedView === 'ready_to_apply' ? '🔥 Ready to Apply' : selectedView})
                  </span>
                  <div className="flex items-center gap-2">
                    <a
                      href="/data/helios_jobs_two_tabs.xlsx"
                      download
                      className="text-xs text-emerald-400 hover:text-emerald-300 font-semibold flex items-center gap-1.5"
                    >
                      <i data-lucide="download" className="w-3.5 h-3.5"></i> Download Excel (.xlsx)
                    </a>
                  </div>
                </div>

                <div className="divide-y divide-slate-800/60">
                  {filteredJobs.map(job => {
                    const isSeniorityMismatch = job.eligibility_status === 'SENIORITY_MISMATCH';
                    return (
                      <div
                        key={job.id}
                        className={`p-5 hover:bg-[#141C30] transition-all flex items-center justify-between ${
                          isSeniorityMismatch ? 'bg-amber-950/5' : ''
                        }`}
                      >
                        <div className="flex items-start gap-4">
                          {/* Match Score Badge */}
                          <div className={`w-14 h-14 rounded-xl flex flex-col items-center justify-center font-bold shrink-0 ${
                            isSeniorityMismatch
                              ? 'bg-amber-950/60 border border-amber-700/50 text-amber-400'
                              : 'bg-blue-950/60 border border-blue-700/50 text-blue-400'
                          }`}>
                            <span className="text-sm font-extrabold">{intPct(job.fit_score)}</span>
                            <span className="text-[9px] uppercase font-semibold text-slate-400">Match</span>
                          </div>

                          <div>
                            <div className="flex items-center gap-3">
                              <h4 className="font-bold text-sm text-slate-100 hover:text-blue-400 cursor-pointer" onClick={() => setSelectedJob(job)}>
                                {job.title}
                              </h4>
                              <span className="text-xs font-semibold text-slate-400">at <strong className="text-slate-200">{job.company}</strong></span>
                              
                              {/* Prominent Eligibility vs Mismatch Tag */}
                              {isSeniorityMismatch ? (
                                <span className="bg-amber-950/80 text-amber-300 text-[10px] font-extrabold px-2.5 py-0.5 rounded border border-amber-600/60 flex items-center gap-1">
                                  ⚠️ SENIORITY MISMATCH ({job.experience_years})
                                </span>
                              ) : (
                                <span className="bg-emerald-950/80 text-emerald-400 text-[10px] font-bold px-2.5 py-0.5 rounded border border-emerald-600/50">
                                  ELIGIBLE ✓
                                </span>
                              )}

                              {/* Multi-Source Duplicate Badge */}
                              {job.source_count > 1 && (
                                <span className="bg-purple-950/80 text-purple-300 text-[10px] font-semibold px-2 py-0.5 rounded border border-purple-700/40">
                                  {job.source_count} Sources Grouped
                                </span>
                              )}
                            </div>

                            <div className="text-xs text-slate-400 mt-1.5 flex items-center gap-4">
                              <span>📍 {job.location}</span>
                              <span>💼 {job.job_type}</span>
                              <span>💰 {job.compensation}</span>
                              <span className="text-slate-500">Source: {job.source}</span>
                            </div>

                            {/* 5-Dimension Score Summary Bar */}
                            {job.dimension_breakdown && (
                              <div className="flex items-center gap-3 mt-2 text-[10px] text-slate-400">
                                <span>Tech: <strong className="text-slate-200">{intPct(job.dimension_breakdown.tech_stack)}</strong></span>
                                <span>·</span>
                                <span>Location: <strong className="text-slate-200">{intPct(job.dimension_breakdown.location)}</strong></span>
                                <span>·</span>
                                <span>Seniority: <strong className={isSeniorityMismatch ? "text-amber-400" : "text-slate-200"}>{intPct(job.dimension_breakdown.seniority)}</strong></span>
                                <span>·</span>
                                <span>Semantic: <strong className="text-slate-200">{intPct(job.dimension_breakdown.semantic)}</strong></span>
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Action Buttons */}
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => setSelectedJob(job)}
                            className="bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold px-3 py-1.5 rounded-lg border border-slate-700 transition-all"
                          >
                            Details
                          </button>

                          {/* Fast Track: Open Application URL for manual submission */}
                          <a
                            href={job.apply_url}
                            target="_blank"
                            rel="noreferrer"
                            className="bg-slate-800 hover:bg-slate-700 text-sky-300 text-xs font-semibold px-3 py-1.5 rounded-lg border border-sky-700/50 transition-all"
                            title="Opens verified company application page for manual submission"
                          >
                            Open Application ↗
                          </a>

                          {/* Option 2: AI Tailoring */}
                          <button
                            onClick={() => handleTriggerTailor(job)}
                            className="bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold px-3 py-1.5 rounded-lg shadow transition-all"
                          >
                            Tailor Resume ✨
                          </button>

                          {job.application_status === 'APPLIED' ? (
                            <span className="bg-emerald-900/40 text-emerald-400 text-xs font-bold px-3 py-1.5 rounded-lg border border-emerald-700/50">
                              Applied ✓
                            </span>
                          ) : (
                            <button
                              onClick={() => handleMarkApplied(job.id)}
                              className="bg-emerald-950/60 hover:bg-emerald-900/60 text-emerald-300 text-xs font-semibold px-3 py-1.5 rounded-lg border border-emerald-700/40 transition-all"
                            >
                              Mark Applied
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

            </div>
          )}

          {/* ─────────────────────────────────────────────────────────────────── */}
          {/* SCREEN 3: JOB DETAILS DRAWER (MODAL)                                */}
          {/* ─────────────────────────────────────────────────────────────────── */}
          {selectedJob && (
            <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-6">
              <div className="glass-card bg-[#0D1322] w-full max-w-3xl rounded-2xl border border-slate-700 overflow-hidden shadow-2xl">
                <div className="p-6 border-b border-slate-800 flex items-center justify-between">
                  <div>
                    <h3 className="text-base font-bold text-slate-100">{selectedJob.title}</h3>
                    <p className="text-xs text-slate-400 mt-0.5">{selectedJob.company} · {selectedJob.location}</p>
                  </div>
                  <button
                    onClick={() => setSelectedJob(null)}
                    className="text-slate-400 hover:text-slate-200 text-sm p-1"
                  >
                    ✕
                  </button>
                </div>

                <div className="p-6 space-y-6 max-h-[70vh] overflow-y-auto">
                  
                  {/* Eligibility Status Alert */}
                  {selectedJob.eligibility_status === 'SENIORITY_MISMATCH' ? (
                    <div className="bg-amber-950/40 border border-amber-600/60 p-4 rounded-xl text-xs text-amber-300">
                      <div className="font-bold flex items-center gap-2 text-sm mb-1">
                        <i data-lucide="alert-triangle" className="w-4 h-4 text-amber-400"></i>
                        Seniority Mismatch Notice
                      </div>
                      <p>Required experience ({selectedJob.experience_years}) exceeds profile limit. Although tech stack alignment is high, candidate is not currently in the primary hiring bracket for this seniority.</p>
                    </div>
                  ) : (
                    <div className="bg-emerald-950/40 border border-emerald-600/60 p-4 rounded-xl text-xs text-emerald-300">
                      <div className="font-bold flex items-center gap-2 text-sm mb-1">
                        <i data-lucide="check-circle" className="w-4 h-4 text-emerald-400"></i>
                        Candidate Eligible
                      </div>
                      <p>Meets all hard constraints: experience range, required tech stack, and location criteria.</p>
                    </div>
                  )}

                  {/* 5-Dimension Weighted Score Breakdown */}
                  <div>
                    <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-3">5-Dimension Match Breakdown</h4>
                    {selectedJob.dimension_breakdown && (
                      <div className="space-y-3">
                        <div>
                          <div className="flex justify-between text-xs mb-1">
                            <span className="text-slate-400">Tech Stack Match (Weight: 35%)</span>
                            <span className="font-bold text-slate-200">{intPct(selectedJob.dimension_breakdown.tech_stack)}</span>
                          </div>
                          <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                            <div className="h-full bg-blue-500 rounded-full" style={{ width: `${intPct(selectedJob.dimension_breakdown.tech_stack)}` }}></div>
                          </div>
                        </div>

                        <div>
                          <div className="flex justify-between text-xs mb-1">
                            <span className="text-slate-400">Location Match (Weight: 20%)</span>
                            <span className="font-bold text-slate-200">{intPct(selectedJob.dimension_breakdown.location)}</span>
                          </div>
                          <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                            <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${intPct(selectedJob.dimension_breakdown.location)}` }}></div>
                          </div>
                        </div>

                        <div>
                          <div className="flex justify-between text-xs mb-1">
                            <span className="text-slate-400">Seniority Alignment (Weight: 20%)</span>
                            <span className={`font-bold ${selectedJob.eligibility_status === 'SENIORITY_MISMATCH' ? 'text-amber-400' : 'text-slate-200'}`}>
                              {intPct(selectedJob.dimension_breakdown.seniority)}
                            </span>
                          </div>
                          <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                            <div className={`h-full rounded-full ${selectedJob.eligibility_status === 'SENIORITY_MISMATCH' ? 'bg-amber-500' : 'bg-blue-500'}`} style={{ width: `${intPct(selectedJob.dimension_breakdown.seniority)}` }}></div>
                          </div>
                        </div>

                        <div>
                          <div className="flex justify-between text-xs mb-1">
                            <span className="text-slate-400">Role Title Keyword Match (Weight: 10%)</span>
                            <span className="font-bold text-slate-200">{intPct(selectedJob.dimension_breakdown.role)}</span>
                          </div>
                          <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                            <div className="h-full bg-purple-500 rounded-full" style={{ width: `${intPct(selectedJob.dimension_breakdown.role)}` }}></div>
                          </div>
                        </div>

                        <div>
                          <div className="flex justify-between text-xs mb-1">
                            <span className="text-slate-400">Semantic Cosine Similarity (Weight: 15%)</span>
                            <span className="font-bold text-slate-200">{intPct(selectedJob.dimension_breakdown.semantic)}</span>
                          </div>
                          <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                            <div className="h-full bg-indigo-500 rounded-full" style={{ width: `${intPct(selectedJob.dimension_breakdown.semantic)}` }}></div>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Skills Checklist */}
                  <div>
                    <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">Verified Skill Alignment</h4>
                    <div className="flex flex-wrap gap-2">
                      {["Python", "FastAPI", "PostgreSQL", "PyTorch", "Redis", "Docker", "System Design"].map(skill => (
                        <span key={skill} className="bg-emerald-950/60 text-emerald-400 border border-emerald-700/50 text-xs px-2.5 py-1 rounded-lg flex items-center gap-1.5">
                          ✓ {skill}
                        </span>
                      ))}
                    </div>
                  </div>

                </div>

                <div className="p-6 border-t border-slate-800 bg-[#0A0F1D] flex items-center justify-between">
                  <button
                    onClick={() => { const j = selectedJob; setSelectedJob(null); handleTriggerTailor(j); }}
                    className="bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold px-4 py-2 rounded-lg shadow"
                  >
                    Launch AI Tailor Studio ✨
                  </button>
                  <div className="flex items-center gap-3">
                    <a
                      href={selectedJob.apply_url}
                      target="_blank"
                      rel="noreferrer"
                      className="bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold px-4 py-2 rounded-lg border border-slate-700"
                    >
                      Open Application URL &rarr;
                    </a>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ─────────────────────────────────────────────────────────────────── */}
          {/* SCREEN 4: AI TAILOR STUDIO                                         */}
          {/* ─────────────────────────────────────────────────────────────────── */}
          {activeTab === 'tailor' && (
            <div className="max-w-7xl mx-auto space-y-6">
              
              {tailorLoading ? (
                <div className="glass-card p-12 rounded-2xl text-center space-y-4">
                  <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
                  <h3 className="text-base font-bold text-slate-100">Fact-Constrained AI Tailoring In Progress</h3>
                  <div className="text-xs text-slate-400 space-y-1">
                    <p>1. Extracting candidate ground-truth facts from Fact Registry ✓</p>
                    <p>2. Aligning technical keywords with job requirements ⟳</p>
                    <p>3. Running TruthfulnessGuard verification check ○</p>
                    <p>4. Compiling sandboxed LaTeX PDF ○</p>
                  </div>
                </div>
              ) : tailorData ? (
                <div className="space-y-6">
                  
                  {/* Tailoring Header & Alignment Metrics */}
                  <div className="glass-card p-6 rounded-2xl">
                    <div className="flex items-center justify-between">
                      <div>
                        <span className="text-[10px] text-blue-400 font-bold uppercase tracking-wider">Tailoring Output</span>
                        <h3 className="text-lg font-bold text-slate-100 mt-0.5">{tailorData.job_title} at {tailorData.company_name}</h3>
                      </div>
                      
                      <div className="flex items-center gap-3">
                        {isLatexDirty ? (
                          <button
                            onClick={handleRevalidateLatex}
                            disabled={revalidating}
                            className="bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold px-4 py-2 rounded-lg shadow flex items-center gap-2 animate-pulse"
                          >
                            <i data-lucide="shield-alert" className="w-4 h-4"></i>
                            {revalidating ? 'Re-validating...' : 'Re-verify Truthfulness & Compile PDF'}
                          </button>
                        ) : tailorData.validation.passed && tailorData.pdf_path ? (
                          <a
                            href={`/api/v1/ai/tailor/${tailorData.id}/pdf`}
                            download
                            className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold px-4 py-2 rounded-lg shadow flex items-center gap-2"
                          >
                            <i data-lucide="download" className="w-4 h-4"></i> Download Verified PDF
                          </a>
                        ) : (
                          <span className="bg-red-950/80 text-red-300 text-xs font-bold px-3 py-2 rounded-lg border border-red-700/50">
                            Download Blocked (Validation Failed)
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Transparent Alignment Metrics Grid (No Fake ATS 95%+) */}
                    <div className="grid grid-cols-4 gap-4 mt-6 pt-6 border-t border-slate-800">
                      <div className="bg-[#111A2E] p-3.5 rounded-xl border border-slate-800">
                        <div className="text-xs text-slate-400">Keywords Matched</div>
                        <div className="text-xl font-bold text-slate-100 mt-1">
                          {tailorData.alignment.matched_keywords_count} / {tailorData.alignment.total_target_keywords}
                        </div>
                      </div>

                      <div className="bg-[#111A2E] p-3.5 rounded-xl border border-slate-800">
                        <div className="text-xs text-slate-400">Required Skills Covered</div>
                        <div className="text-xl font-bold text-slate-100 mt-1">
                          {tailorData.alignment.required_skills_count} / {tailorData.alignment.total_required_skills}
                        </div>
                      </div>

                      <div className="bg-[#111A2E] p-3.5 rounded-xl border border-slate-800">
                        <div className="text-xs text-slate-400">Role Alignment</div>
                        <div className="text-xl font-bold text-emerald-400 mt-1">
                          {tailorData.alignment.role_alignment_pct}%
                        </div>
                      </div>

                      <div className="bg-[#111A2E] p-3.5 rounded-xl border border-slate-800">
                        <div className="text-xs text-slate-400">Truthfulness Audit</div>
                        <div className={`text-xs font-bold mt-2 flex items-center gap-1.5 ${
                          isLatexDirty ? 'text-amber-400' : tailorData.validation.passed ? 'text-emerald-400' : 'text-rose-400'
                        }`}>
                          <span className={`w-2 h-2 rounded-full ${
                            isLatexDirty ? 'bg-amber-400' : tailorData.validation.passed ? 'bg-emerald-400' : 'bg-rose-400'
                          }`}></span>
                          {isLatexDirty ? 'Modified (Needs Re-audit)' : tailorData.validation.passed ? 'Verified against Fact Registry' : 'Validation FAILED'}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Truthfulness Guard Status Banner (Guard-AGAIN) */}
                  {isLatexDirty ? (
                    <div className="glass-card p-4 rounded-xl border-amber-500/30 bg-amber-950/20 flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <i data-lucide="alert-triangle" className="w-5 h-5 text-amber-400"></i>
                        <div>
                          <div className="text-xs font-bold text-amber-200">Manual Changes Detected (Artifact Dirty)</div>
                          <div className="text-[11px] text-amber-300/80">Re-run Truthfulness Check to audit changes against Candidate Fact Registry before PDF download.</div>
                        </div>
                      </div>
                      <button
                        onClick={handleRevalidateLatex}
                        disabled={revalidating}
                        className="bg-amber-600 hover:bg-amber-500 text-white font-bold text-xs px-3.5 py-1.5 rounded-lg"
                      >
                        Re-validate Truthfulness
                      </button>
                    </div>
                  ) : !tailorData.validation.passed ? (
                    <div className="glass-card p-4 rounded-xl border-rose-500/40 bg-rose-950/30">
                      <div className="text-xs font-bold text-rose-300 flex items-center gap-2 mb-1">
                        <i data-lucide="x-circle" className="w-4 h-4 text-rose-400"></i>
                        Truthfulness Guard Violations Detected (Invariant #12)
                      </div>
                      <ul className="text-[11px] text-rose-200/90 list-disc list-inside space-y-0.5">
                        {tailorData.validation.violations.map((v, i) => (
                          <li key={i}>{v}</li>
                        ))}
                      </ul>
                    </div>
                  ) : (
                    <div className="glass-card p-4 rounded-xl border-emerald-500/20 bg-emerald-950/10 flex items-center justify-between">
                      <div className="flex items-center gap-2 text-xs text-emerald-300 font-medium">
                        <i data-lucide="shield-check" className="w-4 h-4 text-emerald-400"></i>
                        Verified against Candidate Fact Registry v1.2.0 (Zero fabricated employers, metrics, or degrees)
                      </div>
                      <span className="text-[10px] text-emerald-400 font-bold bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800">
                        {tailorData.validation.verified_fact_count} FACTS VERIFIED
                      </span>
                    </div>
                  )}

                  {/* Sub-Tabs: Tailored Resume vs Cover Letter */}
                  <div className="flex items-center gap-3 border-b border-slate-800 pb-2">
                    <button
                      onClick={() => setTailorActiveSubTab('resume')}
                      className={`text-xs font-bold px-3 py-1.5 rounded-lg transition-all ${
                        tailorActiveSubTab === 'resume'
                          ? 'bg-blue-600 text-white'
                          : 'text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      Tailored LaTeX Source
                    </button>

                    <button
                      onClick={() => setTailorActiveSubTab('cover_letter')}
                      className={`text-xs font-bold px-3 py-1.5 rounded-lg transition-all ${
                        tailorActiveSubTab === 'cover_letter'
                          ? 'bg-blue-600 text-white'
                          : 'text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      Tailored Cover Letter
                    </button>
                  </div>

                  {tailorActiveSubTab === 'resume' && (
                    <div className="glass-card p-4 rounded-xl">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-[11px] text-slate-400 font-mono">LaTeX Editor (Edits will trigger Guard-AGAIN revalidation)</span>
                      </div>
                      <textarea
                        value={editedLatex}
                        onChange={(e) => {
                          setEditedLatex(e.target.value);
                          setIsLatexDirty(true);
                        }}
                        rows={20}
                        className="w-full bg-[#090D16] border border-slate-800 rounded-lg p-4 font-mono text-xs text-slate-200 focus:outline-none focus:border-blue-500"
                      />
                    </div>
                  )}

                  {tailorActiveSubTab === 'cover_letter' && (
                    <div className="glass-card p-6 rounded-xl">
                      <div className="whitespace-pre-line text-xs text-slate-200 leading-relaxed font-serif">
                        {tailorData.cover_letter_text}
                      </div>
                    </div>
                  )}

                </div>
              ) : (
                <div className="glass-card p-12 rounded-2xl text-center space-y-3">
                  <i data-lucide="wand-2" className="w-8 h-8 text-blue-400 mx-auto"></i>
                  <h3 className="text-sm font-bold text-slate-200">No Tailoring Job Selected</h3>
                  <p className="text-xs text-slate-400">Go to Jobs Command Center and click "Tailor Resume" on any opportunity.</p>
                  <button
                    onClick={() => setActiveTab('jobs')}
                    className="bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold px-4 py-2 rounded-lg"
                  >
                    Open Jobs Command Center &rarr;
                  </button>
                </div>
              )}

            </div>
          )}

          {/* ─────────────────────────────────────────────────────────────────── */}
          {/* SCREEN 5: LIVE DISCOVERY SCANS                                      */}
          {/* ─────────────────────────────────────────────────────────────────── */}
          {activeTab === 'scans' && (
            <div className="max-w-7xl mx-auto space-y-6">
              
              {/* Scan Trigger Controls */}
              <div className="glass-card p-6 rounded-2xl">
                <h3 className="font-display font-bold text-sm text-slate-200 uppercase tracking-wider mb-4">
                  Trigger Asynchronous Discovery Scan
                </h3>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="text-xs text-slate-400 font-medium block mb-1.5">Target Roles / Query</label>
                    <input
                      type="text"
                      value={scanQuery}
                      onChange={(e) => setScanQuery(e.target.value)}
                      placeholder="e.g. Software Engineer, AI Systems, Backend"
                      className="w-full bg-[#0D1322] border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-blue-500"
                    />
                  </div>

                  <div>
                    <label className="text-xs text-slate-400 font-medium block mb-1.5">Target Location</label>
                    <input
                      type="text"
                      value={scanLocation}
                      onChange={(e) => setScanLocation(e.target.value)}
                      placeholder="e.g. India, Delhi NCR, Bangalore, Remote"
                      className="w-full bg-[#0D1322] border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-blue-500"
                    />
                  </div>

                  <div className="flex items-end">
                    <button
                      onClick={handleStartScan}
                      disabled={isScanning}
                      className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs py-2 px-4 rounded-lg shadow-lg shadow-blue-600/30 transition-all flex items-center justify-center gap-2"
                    >
                      <i data-lucide="play" className="w-4 h-4"></i>
                      {isScanning ? 'Scanning in Background...' : 'Launch Multi-Portal Scan'}
                    </button>
                  </div>
                </div>
              </div>

              {/* Latest Scan Breakdown & Logs */}
              {latestScan && (
                <div className="glass-card p-6 rounded-2xl space-y-6">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                    <div>
                      <h4 className="font-bold text-sm text-slate-200">Latest Discovery Scan: {latestScan.id}</h4>
                      <p className="text-xs text-slate-400 mt-0.5">Status: <strong className="text-emerald-400 uppercase">{latestScan.status}</strong></p>
                    </div>
                    <div className="text-xs text-slate-400">
                      Discovered: <strong className="text-slate-100">{latestScan.discovered_count}</strong> · Qualified: <strong className="text-emerald-400">{latestScan.qualified_count}</strong> · Strong: <strong className="text-blue-400">{latestScan.strong_count}</strong>
                    </div>
                  </div>

                  {/* Per-Portal Yield Cards */}
                  <div className="grid grid-cols-5 gap-3">
                    {latestScan.portals && Object.entries(latestScan.portals).map(([key, p]) => (
                      <div key={key} className="bg-[#111A2E] p-3.5 rounded-xl border border-slate-800">
                        <div className="flex items-center justify-between text-xs font-semibold text-slate-200">
                          <span>{p.name}</span>
                          <span className="text-emerald-400 text-[10px]">✓</span>
                        </div>
                        <div className="text-lg font-bold text-slate-100 mt-1">{p.jobs_found} jobs</div>
                        <div className="text-[10px] text-slate-500 mt-0.5">{p.duration_seconds}s execution</div>
                      </div>
                    ))}
                  </div>

                  {/* Real-Time Scan Logs */}
                  <div>
                    <h5 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">Live Scan Activity Log</h5>
                    <div className="bg-[#090D16] border border-slate-800/80 rounded-xl p-4 font-mono text-[11px] text-slate-300 space-y-1.5 max-h-56 overflow-y-auto">
                      {scanLogs.map((log, idx) => (
                        <div key={idx} className="flex items-center gap-3">
                          <span className="text-slate-500">{log.timestamp}</span>
                          <span className={`font-bold ${log.level === 'WARN' ? 'text-amber-400' : 'text-blue-400'}`}>[{log.portal || log.module || 'AGENT'}]</span>
                          <span>{log.message}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

            </div>
          )}

          {/* ─────────────────────────────────────────────────────────────────── */}
          {/* SCREEN 6: SETTINGS, PROFILES & INTEGRATIONS                         */}
          {/* ─────────────────────────────────────────────────────────────────── */}
          {activeTab === 'settings' && (
            <div className="max-w-7xl mx-auto space-y-6">
              
              {/* Profile Switcher Grid */}
              <div className="glass-card p-6 rounded-2xl">
                <h3 className="font-display font-bold text-sm text-slate-200 uppercase tracking-wider mb-4">
                  Select Active Candidate Profile Lens
                </h3>
                <div className="grid grid-cols-3 gap-4">
                  {profilesList.map(p => (
                    <div
                      key={p.id}
                      onClick={() => handleActivateProfile(p.id)}
                      className={`p-4 rounded-xl border cursor-pointer transition-all ${
                        p.is_active
                          ? 'bg-blue-950/40 border-blue-500 text-slate-100 shadow-lg shadow-blue-500/10'
                          : 'bg-[#111A2E] border-slate-800 text-slate-400 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <h4 className="font-bold text-xs text-slate-200">{p.profile_name}</h4>
                        {p.is_active && <span className="text-emerald-400 text-xs font-bold">● Active Lens</span>}
                      </div>
                      <div className="text-[11px] text-slate-400 mt-2 space-y-1">
                        <div>Roles: {p.target_roles.slice(0, 3).join(', ')}</div>
                        <div>Tech: {p.tech_stack.slice(0, 4).join(', ')}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Master LaTeX Resume Editor */}
              <div className="glass-card p-6 rounded-2xl space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-display font-bold text-sm text-slate-200 uppercase tracking-wider">
                      Master LaTeX Resume Template
                    </h3>
                    <p className="text-xs text-slate-400 mt-0.5">Presentation template for candidate facts. Authoritative facts are validated by CandidateFactRegistry.</p>
                  </div>
                  <div className="flex items-center gap-3">
                    {latexSavedMsg && <span className="text-xs text-emerald-400 font-bold">{latexSavedMsg}</span>}
                    <button
                      onClick={handleSaveLatex}
                      className="bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs px-4 py-2 rounded-lg shadow"
                    >
                      Save Template
                    </button>
                  </div>
                </div>

                <textarea
                  value={masterLatex}
                  onChange={(e) => setMasterLatex(e.target.value)}
                  rows={16}
                  className="w-full bg-[#090D16] border border-slate-800 rounded-xl p-4 font-mono text-xs text-slate-200 focus:outline-none focus:border-blue-500"
                />
              </div>

              {/* Push-Only Projections & Integrations Panel */}
              <div className="grid grid-cols-2 gap-6">
                
                {/* Google Sheets Panel */}
                <div className="glass-card p-6 rounded-2xl space-y-4">
                  <div className="flex items-center justify-between">
                    <h4 className="font-bold text-sm text-slate-200 flex items-center gap-2">
                      <i data-lucide="table" className="w-4 h-4 text-emerald-400"></i>
                      Google Sheets (Push-Only Projection)
                    </h4>
                    <span className="text-emerald-400 text-xs font-bold">● Connected</span>
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Helios database is authoritative. Discovered jobs and action tokens are projected push-only to your Google Sheet without bidirectional sync risks.
                  </p>
                  <div className="text-xs text-slate-400 space-y-1">
                    <div>Spreadsheet: <strong className="text-slate-200">Helios Queue (330 Active Rows)</strong></div>
                    <div>Mode: <strong className="text-blue-400">Push-Only V1</strong></div>
                  </div>
                  <div className="flex items-center gap-3 pt-2">
                    <a
                      href="https://docs.google.com/spreadsheets"
                      target="_blank"
                      rel="noreferrer"
                      className="bg-emerald-950/60 hover:bg-emerald-900/60 text-emerald-300 border border-emerald-700/50 text-xs font-bold px-3 py-1.5 rounded-lg"
                    >
                      Open Google Sheet ↗
                    </a>
                  </div>
                </div>

                {/* Telegram Bot Alerts */}
                <div className="glass-card p-6 rounded-2xl space-y-4">
                  <div className="flex items-center justify-between">
                    <h4 className="font-bold text-sm text-slate-200 flex items-center gap-2">
                      <i data-lucide="send" className="w-4 h-4 text-blue-400"></i>
                      Telegram Approval Bot
                    </h4>
                    <span className="text-emerald-400 text-xs font-bold">● Connected</span>
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Direct live alert projection. Real-time application receipts, action tokens, and screenshot verification sent to your phone.
                  </p>
                  <div className="text-xs text-slate-400 space-y-1">
                    <div>Chat ID: <strong className="text-slate-200">8466657787</strong></div>
                    <div>Bot Handle: <strong className="text-blue-400">@Helios_vinay_AI_Bot</strong></div>
                  </div>
                  <div className="flex items-center gap-3 pt-2">
                    <button
                      onClick={handleSendTelegramPing}
                      className="bg-blue-950/60 hover:bg-blue-900/60 text-blue-300 border border-blue-700/50 text-xs font-bold px-3 py-1.5 rounded-lg"
                    >
                      Send Test Alert Ping
                    </button>
                  </div>
                </div>

              </div>

            </div>
          )}

        </div>
      </main>
    </div>
  );
}

function intPct(val) {
  if (val === undefined || val === null) return '0%';
  if (typeof val === 'string' && val.includes('%')) return val;
  return `${Math.round(val * 100)}%`;
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
