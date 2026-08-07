const { useState, useEffect } = React;

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [searchQuery, setSearchQuery] = useState('');
  const [notificationsCount, setNotificationsCount] = useState(3);
  const [telegramStatus, setTelegramStatus] = useState('connected');
  const [replayingId, setReplayingId] = useState(null);

  useEffect(() => {
    if (window.lucide) {
      window.lucide.createIcons();
    }
  }, [activeTab]);

  return (
    <div className="flex w-full h-full text-slate-100 bg-[#080C14] font-sans antialiased overflow-hidden">
      
      {/* ── PERSISTENT SIDEBAR ─────────────────────────────────────────── */}
      <aside className="w-64 bg-[#0D121F] border-r border-slate-800/80 flex flex-col justify-between flex-shrink-0 z-20">
        <div>
          {/* Logo */}
          <div className="p-5 flex items-center gap-3 border-b border-slate-800/60">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 via-indigo-500 to-purple-500 flex items-center justify-center text-white font-display font-extrabold text-xl shadow-lg glow-blue">
              H
            </div>
            <div>
              <h1 className="font-display font-bold text-lg tracking-wide text-white flex items-center gap-2">
                Helios <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-blue-500/20 text-blue-400 font-mono border border-blue-500/30">v3.0</span>
              </h1>
              <p className="text-[11px] text-slate-400 font-medium">Personal AI Employee</p>
            </div>
          </div>

          {/* Nav Items */}
          <nav className="p-3 space-y-1">
            <NavItem id="dashboard" label="Dashboard" icon="layout-dashboard" active={activeTab} setActive={setActiveTab} badge="Live" />
            <NavItem id="jobs" label="Discover Jobs" icon="compass" active={activeTab} setActive={setActiveTab} badge="91" />
            <NavItem id="applications" label="Applications" icon="kanban" active={activeTab} setActive={setActiveTab} />
            <NavItem id="automation" label="Automation Center" icon="cpu" active={activeTab} setActive={setActiveTab} />
            <NavItem id="recovery" label="Recovery Center" icon="alert-triangle" active={activeTab} setActive={setActiveTab} badge="2" badgeColor="bg-amber-500/20 text-amber-400 border-amber-500/30" />
            <NavItem id="company" label="Company Dossier" icon="building-2" active={activeTab} setActive={setActiveTab} />
            <NavItem id="resume" label="Resume Studio" icon="file-text" active={activeTab} setActive={setActiveTab} />
            <NavItem id="analytics" label="Analytics & Metrics" icon="bar-chart-3" active={activeTab} setActive={setActiveTab} />
            <NavItem id="telegram" label="Telegram Bot" icon="send" active={activeTab} setActive={setActiveTab} badge="Connected" badgeColor="bg-emerald-500/20 text-emerald-400 border-emerald-500/30" />
            <NavItem id="notifications" label="Notifications" icon="bell" active={activeTab} setActive={setActiveTab} badge={notificationsCount} />
            <NavItem id="settings" label="Candidate Profile" icon="sliders" active={activeTab} setActive={setActiveTab} />
          </nav>
        </div>

        {/* User Card */}
        <div className="p-3 border-t border-slate-800/60 bg-[#0A0E18]">
          <div className="flex items-center gap-3 p-2 rounded-lg bg-slate-900/80 border border-slate-800">
            <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center font-bold text-sm text-white border border-blue-400/40">
              VK
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold text-slate-200 truncate">Vinay Khosya</p>
              <p className="text-[10px] text-slate-400 truncate">vinay@example.com</p>
            </div>
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
          </div>
        </div>
      </aside>

      {/* ── MAIN CONTENT AREA ───────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col h-full overflow-hidden bg-[#080C14]">
        
        {/* Top Header Bar */}
        <header className="h-16 border-b border-slate-800/80 bg-[#0D121F]/80 backdrop-blur-md px-6 flex items-center justify-between z-10 flex-shrink-0">
          <div className="flex items-center gap-4 w-1/3">
            <div className="relative w-full">
              <i data-lucide="search" className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"></i>
              <input
                type="text"
                placeholder="Search jobs, companies, skills, or applications (Cmd + K)..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-4 py-1.5 bg-slate-900/90 border border-slate-800 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500/60 transition-colors"
              />
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* Telegram Status */}
            <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              Telegram Bot Active
            </div>

            {/* Quick Actions */}
            <button className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold flex items-center gap-1.5 transition-colors shadow-lg glow-blue">
              <i data-lucide="play" className="w-3.5 h-3.5"></i>
              Run Discovery
            </button>
          </div>
        </header>

        {/* Tab View Router */}
        <main className="flex-1 overflow-y-auto p-6 space-y-6">
          {activeTab === 'dashboard' && <DashboardView setActiveTab={setActiveTab} />}
          {activeTab === 'jobs' && <JobsView />}
          {activeTab === 'applications' && <ApplicationsView />}
          {activeTab === 'automation' && <AutomationView />}
          {activeTab === 'recovery' && <RecoveryView replayingId={replayingId} setReplayingId={setReplayingId} />}
          {activeTab === 'company' && <CompanyView />}
          {activeTab === 'resume' && <ResumeView />}
          {activeTab === 'analytics' && <AnalyticsView />}
          {activeTab === 'telegram' && <TelegramView />}
          {activeTab === 'notifications' && <NotificationsView />}
          {activeTab === 'settings' && <SettingsView />}
        </main>
      </div>
    </div>
  );
}

/* ── NAV ITEM COMPONENT ─────────────────────────────────────────────── */
function NavItem({ id, label, icon, active, setActive, badge, badgeColor = "bg-blue-500/20 text-blue-400 border-blue-500/30" }) {
  const isSelected = active === id;
  return (
    <button
      onClick={() => setActive(id)}
      className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all ${
        isSelected
          ? 'bg-blue-600/15 text-blue-400 border border-blue-500/30 font-semibold'
          : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 border border-transparent'
      }`}
    >
      <div className="flex items-center gap-2.5">
        <i data-lucide={icon} className={`w-4 h-4 ${isSelected ? 'text-blue-400' : 'text-slate-400'}`}></i>
        <span>{label}</span>
      </div>
      {badge && (
        <span className={`text-[10px] px-2 py-0.5 rounded-full border font-mono ${badgeColor}`}>
          {badge}
        </span>
      )}
    </button>
  );
}

/* ── 1. DASHBOARD VIEW (MISSION CONTROL) ────────────────────────────── */
function DashboardView({ setActiveTab }) {
  return (
    <div className="space-y-6">
      {/* Hero Section */}
      <div className="glass-card p-6 rounded-2xl border border-slate-800 relative overflow-hidden bg-gradient-to-r from-slate-900/90 via-slate-900/60 to-blue-950/40">
        <div className="absolute right-0 top-0 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl pointer-events-none"></div>
        <div className="relative z-10 flex justify-between items-start">
          <div>
            <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-medium mb-3">
              <i data-lucide="sparkles" className="w-3.5 h-3.5"></i> 24/7 Autonomous AI Employee Active
            </div>
            <h2 className="text-2xl font-display font-bold text-white">Good Morning, Vinay</h2>
            <p className="text-sm text-slate-400 mt-1 max-w-xl">
              Helios worked overnight. It scanned <strong>4,821</strong> positions across 12 portals, filtered <strong>91 eligible jobs</strong>, and submitted <strong>8 applications</strong>.
            </p>

            <div className="flex items-center gap-6 mt-5 text-xs text-slate-300">
              <span className="flex items-center gap-1.5"><i data-lucide="check-circle-2" className="w-4 h-4 text-emerald-400"></i> 4,821 scanned</span>
              <span className="flex items-center gap-1.5"><i data-lucide="filter" className="w-4 h-4 text-blue-400"></i> 91 eligible</span>
              <span className="flex items-center gap-1.5"><i data-lucide="send" className="w-4 h-4 text-purple-400"></i> 8 auto-applied</span>
              <span className="flex items-center gap-1.5"><i data-lucide="clock" className="w-4 h-4 text-amber-400"></i> 2 awaiting approval</span>
            </div>
          </div>

          <div className="bg-slate-900/90 p-4 rounded-xl border border-slate-800 min-w-[220px]">
            <p className="text-xs text-slate-400 font-medium">Upcoming Interview</p>
            <p className="text-sm font-bold text-white mt-1">Siemens AI Engineer</p>
            <p className="text-xs text-emerald-400 mt-0.5 font-medium">Tomorrow, 10:00 AM IST</p>
            <button 
              onClick={() => setActiveTab('company')}
              className="mt-3 w-full py-1.5 bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 border border-blue-500/30 rounded-lg text-xs font-semibold transition-colors"
            >
              View Interview Dossier
            </button>
          </div>
        </div>
      </div>

      {/* Quick Metrics Banner */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard title="Total Applications" value="274" change="+18 this week" icon="file-check" color="text-blue-400" />
        <StatCard title="Interview Rate" value="18.2%" change="+3.4% vs last month" icon="trending-up" color="text-emerald-400" />
        <StatCard title="Offers Received" value="4" change="2 pending decision" icon="award" color="text-purple-400" />
        <StatCard title="Current Confidence" value="94.6%" change="High accuracy" icon="shield-check" color="text-amber-400" />
      </div>

      {/* Activity Timeline & Live Pipeline Status */}
      <div className="grid grid-cols-3 gap-6">
        {/* Timeline */}
        <div className="col-span-2 glass-card p-5 rounded-xl border border-slate-800">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-display font-semibold text-sm text-white flex items-center gap-2">
              <i data-lucide="history" className="w-4 h-4 text-blue-400"></i> Overnight Activity Log
            </h3>
            <span className="text-xs text-slate-500">Live updates</span>
          </div>

          <div className="space-y-4">
            <TimelineItem time="09:20" title="Applied to Siemens — AI Engineer" desc="Confidence: 96% | Custom LaTeX Resume v18 compiled and uploaded" type="success" />
            <TimelineItem time="09:14" title="Skipped Amazon — Senior ML Lead" desc="Reason: Requires 5+ years experience (configured max is 3.0 yrs)" type="warn" />
            <TimelineItem time="08:52" title="Generated Tailored Resume v18" desc="Reordered PyTorch & FastAPI bullets based on JD keyword weights" type="info" />
            <TimelineItem time="08:30" title="Telegram Approval Received" desc="User approved Greenhouse application for Acme AI" type="success" />
            <TimelineItem time="08:12" title="Replay Engine Recovered Application" desc="Successfully recovered snapshot gh_777 after field selector update" type="info" />
          </div>
        </div>

        {/* Agent Health Monitor */}
        <div className="glass-card p-5 rounded-xl border border-slate-800 space-y-4">
          <h3 className="font-display font-semibold text-sm text-white flex items-center gap-2">
            <i data-lucide="activity" className="w-4 h-4 text-emerald-400"></i> AI Agent Status
          </h3>

          <AgentStatusRow name="Discovery Agent" status="Running" time="Every 6 hours" icon="compass" color="text-blue-400" />
          <AgentStatusRow name="Eligibility Gate" status="Active (7 Rules)" time="< 1ms pass" icon="shield" color="text-emerald-400" />
          <AgentStatusRow name="Ranking Agent" status="Scoring" time="Multi-dim 94%" icon="star" color="text-purple-400" />
          <AgentStatusRow name="Memory Service" status="Healthy" time="Redis Warm" icon="database" color="text-amber-400" />
          <AgentStatusRow name="Telegram Bot" status="Connected" time="1-click active" icon="send" color="text-emerald-400" />
        </div>
      </div>
    </div>
  );
}

/* ── 2. DISCOVER JOBS VIEW ─────────────────────────────────────────── */
function JobsView() {
  const [selectedJob, setSelectedJob] = useState(null);

  const mockJobs = [
    { id: 1, title: 'AI Developer & Automation Specialist', company: 'Siemens AI', location: 'India (Remote)', salary: '₹18,000,000 / yr', match: 96, confidence: 98, skills: ['Python', 'FastAPI', 'PyTorch', 'Docker'], missing: ['Kubernetes'] },
    { id: 2, title: 'Backend & Agentic AI Engineer', company: 'Acme Robotics', location: 'Bengaluru / Remote', salary: '₹22,000,000 / yr', match: 92, confidence: 94, skills: ['Python', 'FastAPI', 'PostgreSQL', 'Redis'], missing: ['Go'] },
    { id: 3, title: 'LLM Systems Engineer', company: 'DeepTech Labs', location: 'Remote', salary: '$140,000 / yr', match: 88, confidence: 91, skills: ['Python', 'LangChain', 'Vector DB'], missing: ['C++'] },
  ];

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-xl font-display font-bold text-white">Discover Jobs</h2>
          <p className="text-xs text-slate-400">Ranks & matches real-time portal listings against your candidate profile</p>
        </div>
        <div className="flex gap-2">
          <button className="px-3 py-1.5 bg-slate-900 border border-slate-800 text-xs text-slate-300 rounded-lg">Remote Only</button>
          <button className="px-3 py-1.5 bg-slate-900 border border-slate-800 text-xs text-slate-300 rounded-lg">Min 85% Match</button>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {mockJobs.map(j => (
          <div key={j.id} className="glass-card p-5 rounded-xl border border-slate-800 space-y-4 hover:border-blue-500/40 transition-all">
            <div className="flex justify-between items-start">
              <div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-500/20 text-blue-400 border border-blue-500/30">Greenhouse</span>
                <h4 className="font-bold text-sm text-white mt-1">{j.title}</h4>
                <p className="text-xs text-slate-400">{j.company} • {j.location}</p>
              </div>
              <div className="text-right">
                <span className="text-lg font-extrabold font-display text-emerald-400">{j.match}%</span>
                <p className="text-[10px] text-slate-500">Fit Score</p>
              </div>
            </div>

            <div className="text-xs text-slate-300 font-semibold">{j.salary}</div>

            <div className="space-y-1">
              <p className="text-[11px] text-slate-400">Matched Skills:</p>
              <div className="flex flex-wrap gap-1">
                {j.skills.map(s => <span key={s} className="px-2 py-0.5 bg-slate-800 text-slate-200 text-[10px] rounded">{s}</span>)}
              </div>
            </div>

            {j.missing.length > 0 && (
              <div className="space-y-1">
                <p className="text-[11px] text-slate-400">Missing Stack:</p>
                <div className="flex flex-wrap gap-1">
                  {j.missing.map(m => <span key={m} className="px-2 py-0.5 bg-rose-500/10 text-rose-400 border border-rose-500/20 text-[10px] rounded">{m}</span>)}
                </div>
              </div>
            )}

            <div className="pt-2 flex gap-2 border-t border-slate-800/60">
              <button onClick={() => setSelectedJob(j)} className="flex-1 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold transition-colors">
                View Match Breakdown
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Match Breakdown Modal Drawer */}
      {selectedJob && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex justify-end z-50">
          <div className="w-1/3 bg-[#0D121F] h-full p-6 border-l border-slate-800 space-y-6 overflow-y-auto">
            <div className="flex justify-between items-center">
              <h3 className="font-display font-bold text-lg text-white">Match Breakdown</h3>
              <button onClick={() => setSelectedJob(null)} className="text-slate-400 hover:text-white">✕</button>
            </div>

            <div>
              <h4 className="font-bold text-slate-200">{selectedJob.title}</h4>
              <p className="text-xs text-slate-400">{selectedJob.company}</p>
            </div>

            <div className="space-y-3 bg-slate-900/80 p-4 rounded-xl border border-slate-800">
              <ProgressBar label="Tech Stack Overlap" percent={95} />
              <ProgressBar label="Location Alignment" percent={100} />
              <ProgressBar label="Seniority Fit" percent={90} />
              <ProgressBar label="Role Keyword Relevancy" percent={87} />
            </div>

            <div className="space-y-2">
              <h5 className="text-xs font-semibold text-slate-300">Helios Recommendation:</h5>
              <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-xs text-emerald-400">
                ✅ <strong>AUTO_APPLY Recommended</strong> (Confidence: {selectedJob.confidence}%)
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ── 3. APPLICATIONS KANBAN VIEW ────────────────────────────────────── */
function ApplicationsView() {
  const columns = [
    { title: 'Eligible', count: 12, color: 'border-blue-500' },
    { title: 'Applied', count: 61, color: 'border-purple-500' },
    { title: 'OA / Coding', count: 8, color: 'border-amber-500' },
    { title: 'Interview', count: 4, color: 'border-emerald-500' },
    { title: 'Offer', count: 2, color: 'border-emerald-400' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-xl font-display font-bold text-white">Application Pipeline (CRM)</h2>
          <p className="text-xs text-slate-400">Real-time status tracking synced with MemoryService and Gmail</p>
        </div>
      </div>

      <div className="grid grid-cols-5 gap-4 overflow-x-auto">
        {columns.map(col => (
          <div key={col.title} className="glass-card p-3 rounded-xl border border-slate-800 space-y-3 min-h-[500px]">
            <div className={`flex justify-between items-center pb-2 border-b-2 ${col.color}`}>
              <h4 className="font-bold text-xs text-slate-200">{col.title}</h4>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 font-mono">{col.count}</span>
            </div>

            <div className="space-y-3">
              <div className="p-3 bg-slate-900/90 rounded-lg border border-slate-800 space-y-2 hover:border-slate-700">
                <p className="text-xs font-bold text-white">Siemens AI Engineer</p>
                <p className="text-[10px] text-slate-400">Applied 2h ago • Resume v18</p>
                <div className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 inline-block">
                  Interview Tomorrow 10 AM
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── 4. AUTOMATION CENTER VIEW ──────────────────────────────────────── */
function AutomationView() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-display font-bold text-white">Automation Center</h2>
        <p className="text-xs text-slate-400">Monitors Helios multi-agent execution pipeline & event bus</p>
      </div>

      {/* Animated Pipeline Graph */}
      <div className="glass-card p-6 rounded-2xl border border-slate-800">
        <h3 className="font-display font-semibold text-sm text-white mb-6">Execution Pipeline Architecture</h3>
        <div className="flex justify-between items-center gap-2 relative">
          <PipelineStep name="1. Discovery" status="Active" color="bg-blue-500" />
          <PipelineConnector />
          <PipelineStep name="2. Eligibility Gate" status="7 Hard Rules" color="bg-emerald-500" />
          <PipelineConnector />
          <PipelineStep name="3. Ranking Agent" status="Multi-dim 94%" color="bg-purple-500" />
          <PipelineConnector />
          <PipelineStep name="4. Resume Engine" status="LaTeX -> PDF" color="bg-amber-500" />
          <PipelineConnector />
          <PipelineStep name="5. Playwright Filler" status="Greenhouse/Lever" color="bg-blue-400" />
          <PipelineConnector />
          <PipelineStep name="6. Event Bus" status="Async Pub/Sub" color="bg-emerald-400" />
        </div>
      </div>
    </div>
  );
}

function PipelineStep({ name, status, color }) {
  return (
    <div className="flex-1 bg-slate-900/90 p-4 rounded-xl border border-slate-800 text-center space-y-1">
      <div className={`w-3 h-3 rounded-full ${color} mx-auto mb-2 animate-pulse`}></div>
      <p className="text-xs font-bold text-white">{name}</p>
      <p className="text-[10px] text-slate-400">{status}</p>
    </div>
  );
}

function PipelineConnector() {
  return <div className="w-8 h-0.5 bg-slate-800"></div>;
}

/* ── 5. RECOVERY CENTER VIEW ────────────────────────────────────────── */
function RecoveryView({ replayingId, setReplayingId }) {
  const triggerReplay = (id) => {
    setReplayingId(id);
    setTimeout(() => setReplayingId(null), 2000);
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-display font-bold text-white">Recovery Center & Replay Engine</h2>
        <p className="text-xs text-slate-400">Captures DOM HTML, error stack traces, and enables 1-Click application retries</p>
      </div>

      <div className="space-y-4">
        <div className="glass-card p-5 rounded-xl border border-amber-500/30 bg-amber-500/5 flex justify-between items-center">
          <div className="space-y-1">
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/20 text-amber-400 border border-amber-500/30">SNAPSHOT_ID: gh_777_178612</span>
            <h4 className="font-bold text-sm text-white">Greenhouse Selector Exception — Acme AI</h4>
            <p className="text-xs text-slate-400">Error: Field selector #first_name timed out waiting for input DOM rendering</p>
          </div>

          <button
            onClick={() => triggerReplay('gh_777')}
            disabled={replayingId === 'gh_777'}
            className="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-slate-950 rounded-lg text-xs font-bold transition-all shadow-lg flex items-center gap-2"
          >
            {replayingId === 'gh_777' ? 'Replaying Snapshot...' : '⚡ 1-Click Replay'}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ── 6. COMPANY INTELLIGENCE VIEW ───────────────────────────────────── */
function CompanyView() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-display font-bold text-white">Company Intelligence Dossier</h2>
        <p className="text-xs text-slate-400">Synthesizes tech stack, recent news, and tailored interview prep questions</p>
      </div>

      <div className="glass-card p-6 rounded-xl border border-slate-800 space-y-4">
        <h3 className="text-lg font-bold text-white">Siemens AI Engineering Dossier</h3>
        <p className="text-xs text-slate-400">Target Role: AI Automation Engineer</p>

        <div className="space-y-2 pt-2 border-t border-slate-800">
          <h4 className="text-xs font-bold text-blue-400">Likely Interview Questions:</h4>
          <ul className="text-xs space-y-1 text-slate-300 list-disc pl-5">
            <li>Why do you want to join Siemens as an AI Automation Engineer?</li>
            <li>How have you built agentic multi-stage pipelines using Python and FastAPI?</li>
            <li>Describe how you handle Playwright browser session timeouts and recovery snapshots.</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

/* ── 7. RESUME STUDIO VIEW ──────────────────────────────────────────── */
function ResumeView() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-display font-bold text-white">Resume Studio</h2>
        <p className="text-xs text-slate-400">Split LaTeX template editor, ATS score analyzer, and LuaLaTeX PDF preview</p>
      </div>

      <div className="grid grid-cols-2 gap-6 h-[550px]">
        <div className="glass-card p-4 rounded-xl border border-slate-800 flex flex-col">
          <h4 className="text-xs font-bold text-slate-300 mb-2">LaTeX Resume Source (v18)</h4>
          <textarea
            className="flex-1 bg-slate-900 p-3 text-xs font-mono text-slate-200 border border-slate-800 rounded-lg resize-none focus:outline-none"
            defaultValue={`\\documentclass{article}\n\\begin{document}\n\\title{Vinay Khosya - AI Engineer}\n\\maketitle\nEngineered agentic systems with Python, FastAPI, PyTorch.\n\\end{document}`}
          />
        </div>

        <div className="glass-card p-4 rounded-xl border border-slate-800 flex flex-col justify-center items-center text-center">
          <i data-lucide="file-check-2" className="w-12 h-12 text-blue-400 mb-2"></i>
          <h4 className="text-sm font-bold text-white">Compiled PDF Preview</h4>
          <p className="text-xs text-slate-400">LuaLaTeX compiled output (100% ATS Passed)</p>
        </div>
      </div>
    </div>
  );
}

/* ── 8. ANALYTICS VIEW ──────────────────────────────────────────────── */
function AnalyticsView() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-display font-bold text-white">Analytics & Metrics</h2>
        <p className="text-xs text-slate-400">Conversion funnel, rejection breakdown, and application performance</p>
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div className="glass-card p-5 rounded-xl border border-slate-800">
          <h4 className="text-xs font-bold text-slate-200 mb-4">Top Rejection Reasons</h4>
          <div className="space-y-3">
            <ProgressBar label="Title contains excluded keyword (e.g. PHP)" percent={45} color="bg-rose-500" />
            <ProgressBar label="Requires 5+ years experience" percent={30} color="bg-amber-500" />
            <ProgressBar label="Unmatched location restriction" percent={15} color="bg-blue-500" />
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── 9. TELEGRAM VIEW ───────────────────────────────────────────────── */
function TelegramView() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-display font-bold text-white">Telegram Integration</h2>
        <p className="text-xs text-slate-400">Bot status, command triggers, and 1-Click approval queue</p>
      </div>

      <div className="glass-card p-5 rounded-xl border border-slate-800 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <i data-lucide="send" className="w-5 h-5"></i>
            </div>
            <div>
              <h4 className="font-bold text-sm text-white">@HeliosAI_Bot</h4>
              <p className="text-xs text-emerald-400">Status: Active & Listening</p>
            </div>
          </div>

          <button className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-bold">
            Test /morning Briefing
          </button>
        </div>
      </div>
    </div>
  );
}

/* ── 10. NOTIFICATIONS VIEW ─────────────────────────────────────────── */
function NotificationsView() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-display font-bold text-white">Notifications Feed</h2>
        <p className="text-xs text-slate-400">Real-time alerts, telegram updates, and application milestones</p>
      </div>

      <div className="glass-card p-5 rounded-xl border border-slate-800 space-y-3">
        <div className="p-3 bg-slate-900/90 rounded-lg border border-slate-800 flex justify-between items-center">
          <div>
            <p className="text-xs font-bold text-white">Application Submitted to Siemens</p>
            <p className="text-[10px] text-slate-400">Confirmation ID: CONF_777 • 10m ago</p>
          </div>
          <span className="text-[10px] px-2 py-0.5 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded">Auto-Applied</span>
        </div>
      </div>
    </div>
  );
}

/* ── 11. SETTINGS VIEW ──────────────────────────────────────────────── */
function SettingsView() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-display font-bold text-white">Candidate Profile & Settings</h2>
        <p className="text-xs text-slate-400">Configure hard eligibility rules, target tech stack, and salary thresholds</p>
      </div>

      <div className="glass-card p-5 rounded-xl border border-slate-800 space-y-4 max-w-2xl">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-xs text-slate-400 block mb-1">Candidate Name</label>
            <input type="text" defaultValue="Vinay Khosya" className="w-full bg-slate-900 border border-slate-800 p-2 rounded text-xs text-white" />
          </div>
          <div>
            <label className="text-xs text-slate-400 block mb-1">Email</label>
            <input type="text" defaultValue="vinay@example.com" className="w-full bg-slate-900 border border-slate-800 p-2 rounded text-xs text-white" />
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── UTILITY HELPER COMPONENTS ───────────────────────────────────────── */
function StatCard({ title, value, change, icon, color }) {
  return (
    <div className="glass-card p-4 rounded-xl border border-slate-800">
      <div className="flex justify-between items-center">
        <span className="text-xs text-slate-400 font-medium">{title}</span>
        <i data-lucide={icon} className={`w-4 h-4 ${color}`}></i>
      </div>
      <p className="text-2xl font-bold font-display text-white mt-1">{value}</p>
      <p className="text-[11px] text-slate-500 mt-0.5">{change}</p>
    </div>
  );
}

function TimelineItem({ time, title, desc, type }) {
  const badgeColors = {
    success: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    warn: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    info: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  };

  return (
    <div className="flex items-start gap-4 p-3 bg-slate-900/60 rounded-xl border border-slate-800/80">
      <span className="font-mono text-xs text-slate-500 min-w-[45px]">{time}</span>
      <div className="flex-1 min-w-0">
        <h4 className="text-xs font-bold text-slate-200">{title}</h4>
        <p className="text-[11px] text-slate-400 mt-0.5">{desc}</p>
      </div>
      <span className={`text-[10px] px-2 py-0.5 rounded-full border font-mono ${badgeColors[type]}`}>
        {type.toUpperCase()}
      </span>
    </div>
  );
}

function AgentStatusRow({ name, status, time, icon, color }) {
  return (
    <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-900/80 border border-slate-800">
      <div className="flex items-center gap-2.5">
        <i data-lucide={icon} className={`w-4 h-4 ${color}`}></i>
        <div>
          <p className="text-xs font-bold text-slate-200">{name}</p>
          <p className="text-[10px] text-slate-500">{time}</p>
        </div>
      </div>
      <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">
        {status}
      </span>
    </div>
  );
}

function ProgressBar({ label, percent, color = "bg-blue-500" }) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-[11px]">
        <span className="text-slate-300">{label}</span>
        <span className="font-mono text-slate-400">{percent}%</span>
      </div>
      <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${percent}%` }}></div>
      </div>
    </div>
  );
}

// Mount App
ReactDOM.createRoot(document.getElementById('root')).render(<App />);
