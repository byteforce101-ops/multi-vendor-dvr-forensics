import { useEffect, useRef, useState } from 'react'

const workflowStages = [
  {
    number: '01',
    title: 'Insert footage',
    short: 'Bring in the original DVR export',
    description: 'Choose a video from your device. The original evidence stays untouched while a safe working copy is prepared.',
    icon: 'cloud',
    checks: ['MP4, MOV, AVI, MKV and WEBM supported', 'Original file remains unchanged', 'Upload is linked to your investigation'],
  },
  {
    number: '02',
    title: 'Parse the export',
    short: 'Read the vendor format and metadata',
    description: 'The parser reads the export structure, timestamps and camera details so different DVR formats can be reviewed together.',
    icon: 'scan',
    checks: ['Detect vendor and recording structure', 'Read timestamps and stream metadata', 'Create a consistent working copy'],
  },
  {
    number: '03',
    title: 'Forensic check',
    short: 'Verify integrity and surface signals',
    description: 'Integrity checks and review signals help you understand what is present in the footage without losing the chain of evidence.',
    icon: 'face',
    checks: ['Hash the working evidence copy', 'Check file integrity and continuity', 'Surface faces, movement and activity'],
  },
  {
    number: '04',
    title: 'Final output',
    short: 'Review and share a clear record',
    description: 'Finish with a readable result: the common copy, review signals and a traceable record ready for your investigation.',
    icon: 'file',
    checks: ['Review findings on a clear timeline', 'Keep source and working copies connected', 'Export a report-ready record'],
  },
]

const processingSteps = workflowStages.map((stage) => stage.title)

const features = [
  {
    number: '01',
    title: 'Works across vendors',
    text: 'Bring footage from different DVR and camera systems into one consistent workspace.',
    icon: 'layers',
  },
  {
    number: '02',
    title: 'One common format',
    text: 'Normalize difficult exports so every frame can be reviewed, compared, and shared.',
    icon: 'scan',
  },
  {
    number: '03',
    title: 'Find people faster',
    text: 'Surface faces and activity moments so investigators can focus on what matters.',
    icon: 'face',
  },
  {
    number: '04',
    title: 'Build a clear record',
    text: 'Keep your findings organized with a timeline that is ready for reporting.',
    icon: 'file',
  },
]

const Icon = ({ name, size = 20 }) => {
  const common = { width: size, height: size, viewBox: '0 0 24 24', fill: 'none', 'aria-hidden': true }
  const paths = {
    arrow: <><path d="M5 12h13" /><path d="m13 6 6 6-6 6" /></>,
    check: <path d="m5 12 4 4L19 6" />,
    chevron: <path d="m6 9 6 6 6-6" />,
    close: <><path d="m6 6 12 12" /><path d="m18 6-12 12" /></>,
    cloud: <><path d="M7.5 18h9.2a4.3 4.3 0 0 0 .8-8.52A6 6 0 0 0 6 10.8 3.6 3.6 0 0 0 7.5 18Z" /><path d="M12 11v6" /><path d="m9.5 13.5 2.5-2.5 2.5 2.5" /></>,
    layers: <><path d="m12 3 8 4.5-8 4.5-8-4.5L12 3Z" /><path d="m4 12 8 4.5 8-4.5" /><path d="m4 16.5 8 4.5 8-4.5" /></>,
    scan: <><path d="M4 8V5a1 1 0 0 1 1-1h3" /><path d="M16 4h3a1 1 0 0 1 1 1v3" /><path d="M20 16v3a1 1 0 0 1-1 1h-3" /><path d="M8 20H5a1 1 0 0 1-1-1v-3" /><path d="M8 12h8" /><path d="M12 8v8" /></>,
    face: <><circle cx="12" cy="12" r="8" /><path d="M9 10h.01M15 10h.01" /><path d="M8.8 14a4 4 0 0 0 6.4 0" /></>,
    file: <><path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9Z" /><path d="M14 3v6h6M8 13h8M8 17h5" /></>,
    play: <path d="m9 6 9 6-9 6V6Z" />,
    plus: <><path d="M12 5v14" /><path d="M5 12h14" /></>,
    refresh: <><path d="M20 11a8.1 8.1 0 0 0-14.9-3L3 11" /><path d="M3 5v6h6" /><path d="M4 13a8.1 8.1 0 0 0 14.9 3L21 13" /><path d="M21 19v-6h-6" /></>,
  }
  return <svg {...common} stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">{paths[name]}</svg>
}

function Globe() {
  return (
    <div className="globe-wrap" aria-hidden="true">
      <div className="globe-halo" />
      <div className="globe">
        <span className="globe-line globe-line-vertical globe-line-one" />
        <span className="globe-line globe-line-vertical globe-line-two" />
        <span className="globe-line globe-line-horizontal globe-line-three" />
        <span className="globe-line globe-line-horizontal globe-line-four" />
        <span className="globe-pole globe-pole-top" />
        <span className="globe-pole globe-pole-bottom" />
        <span className="globe-dot dot-one" />
        <span className="globe-dot dot-two" />
        <span className="globe-dot dot-three" />
        <span className="globe-dot dot-four" />
      </div>
    </div>
  )
}

function ProcessFlow() {
  const [selectedStage, setSelectedStage] = useState(0)
  const stage = workflowStages[selectedStage]

  const showNextStage = () => setSelectedStage((current) => (current + 1) % workflowStages.length)

  return (
    <div className="workflow-shell">
      <div className="workflow-steps" role="tablist" aria-label="Forensic process flow">
        {workflowStages.map((item, index) => (
          <button className={`workflow-step ${selectedStage === index ? 'selected' : ''}`} type="button" role="tab" aria-selected={selectedStage === index} key={item.number} onClick={() => setSelectedStage(index)}>
            <span className="workflow-step-top"><span className="workflow-step-number">{item.number}</span><span className="workflow-step-icon"><Icon name={item.icon} size={20} /></span></span>
            <strong>{item.title}</strong>
            <small>{item.short}</small>
            <span className="workflow-step-arrow"><Icon name="arrow" size={15} /></span>
          </button>
        ))}
      </div>
      <div className="workflow-detail" role="tabpanel">
        <div className="workflow-detail-top"><span className="file-badge"><span className="file-dot" /> ACTIVE STEP {stage.number}</span><span className="workflow-detail-count">{selectedStage + 1} / {workflowStages.length}</span></div>
        <h3>{stage.title}</h3>
        <p>{stage.description}</p>
        <div className="workflow-checks">{stage.checks.map((check) => <span key={check}><Icon name="check" size={14} />{check}</span>)}</div>
        <button className="button button-light" type="button" onClick={showNextStage}>{selectedStage === workflowStages.length - 1 ? 'Start at insert' : 'See next step'} <Icon name="arrow" size={17} /></button>
      </div>
    </div>
  )
}

function AuthModal({ mode, setMode, form, setForm, error, isSubmitting, onClose, onSubmit }) {
  const isSignUp = mode === 'signup'

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (!isSubmitting && event.target === event.currentTarget) onClose() }}>
      <div className="auth-modal" role="dialog" aria-modal="true" aria-labelledby="auth-title">
        <button className="modal-close" type="button" aria-label="Close sign in window" onClick={onClose} disabled={isSubmitting}><Icon name="close" size={19} /></button>
        <div className="auth-mark"><span className="brand-mark"><span /><span /><span /></span></div>
        <p className="eyebrow accent-eyebrow">SECURE YOUR INVESTIGATION</p>
        <h2 id="auth-title">{isSignUp ? 'Create your account' : 'Welcome back'}</h2>
        <p className="auth-copy">{isSignUp ? 'Create an account to upload and review your evidence.' : 'Sign in to continue with your video upload.'}</p>

        <div className="auth-tabs" role="tablist" aria-label="Authentication options">
          <button className={mode === 'signin' ? 'active' : ''} type="button" role="tab" aria-selected={mode === 'signin'} onClick={() => { setMode('signin'); setForm((current) => ({ ...current, name: '' })); }}>Sign in</button>
          <button className={isSignUp ? 'active' : ''} type="button" role="tab" aria-selected={isSignUp} onClick={() => setMode('signup')}>Sign up</button>
        </div>

        <form onSubmit={onSubmit}>
          {isSignUp && <label className="auth-field"><span>Your name</span><input type="text" autoComplete="name" value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} placeholder="Alex Morgan" required /></label>}
          <label className="auth-field"><span>Email address</span><input type="email" autoComplete="email" value={form.email} onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))} placeholder="you@example.com" required /></label>
          <label className="auth-field"><span>Password</span><input type="password" autoComplete={isSignUp ? 'new-password' : 'current-password'} value={form.password} onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))} placeholder="••••••••" minLength={6} required /></label>
          {error && <p className="auth-error" role="alert">{error}</p>}
          <button className="button button-accent button-wide auth-submit" type="submit" disabled={isSubmitting}>{isSubmitting ? 'Signing you in…' : isSignUp ? 'Create account' : 'Sign in and continue'} <Icon name="arrow" size={17} /></button>
        </form>
        <p className="auth-footnote">Your footage stays ready while you sign in.</p>
      </div>
    </div>
  )
}

function UploadCard() {
  const inputRef = useRef(null)
  const [file, setFile] = useState(null)
  const [pendingFile, setPendingFile] = useState(null)
  const [isDragging, setIsDragging] = useState(false)
  const [status, setStatus] = useState('idle')
  const [step, setStep] = useState(0)
  const [progress, setProgress] = useState(0)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isAuthOpen, setIsAuthOpen] = useState(false)
  const [authMode, setAuthMode] = useState('signin')
  const [authForm, setAuthForm] = useState({ name: '', email: '', password: '' })
  const [authError, setAuthError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    if (status !== 'processing') return undefined
    const timer = window.setInterval(() => {
      setStep((current) => {
        if (current >= processingSteps.length - 1) return current
        return current + 1
      })
      setProgress((current) => Math.min(current + 20, 100))
    }, 800)
    const finish = window.setTimeout(() => {
      setProgress(100)
      setStatus('complete')
    }, 4000)
    return () => {
      window.clearInterval(timer)
      window.clearTimeout(finish)
    }
  }, [status])

  const handleFile = (selectedFile) => {
    if (!selectedFile) return
    const supported = ['video/mp4', 'video/quicktime', 'video/x-msvideo', 'video/x-matroska', 'video/webm']
    const extensionOk = /\.(mp4|mov|avi|mkv|webm)$/i.test(selectedFile.name)
    if (!supported.includes(selectedFile.type) && !extensionOk) {
      setStatus('error')
      return
    }
    if (isAuthenticated) {
      setFile(selectedFile)
      setStep(0)
      setProgress(0)
      setStatus('ready')
      return
    }

    setPendingFile(selectedFile)
    setAuthError('')
    setIsAuthOpen(true)
  }

  const reset = () => {
    setFile(null)
    setProgress(0)
    setStep(0)
    setStatus('idle')
    if (inputRef.current) inputRef.current.value = ''
  }

  const closeAuth = () => {
    setIsAuthOpen(false)
    setPendingFile(null)
    if (inputRef.current) inputRef.current.value = ''
  }

  const submitAuth = (event) => {
    event.preventDefault()
    setIsSubmitting(true)
    window.setTimeout(() => {
      setIsAuthenticated(true)
      setFile(pendingFile)
      setStep(0)
      setProgress(0)
      setStatus('ready')
      setIsSubmitting(false)
      setIsAuthOpen(false)
      setPendingFile(null)
      setAuthForm({ name: '', email: '', password: '' })
    }, 450)
  }

  const startProcessing = () => setStatus('processing')

  return (
    <>
      <div className={`upload-card ${isDragging ? 'is-dragging' : ''}`}>
      {status === 'idle' || status === 'error' ? (
        <>
          <div className="upload-icon"><Icon name="cloud" size={26} /></div>
          <p className="eyebrow">START AN INVESTIGATION</p>
          <h2>Drop your footage here</h2>
          <p className="upload-copy">Upload a CCTV export and we’ll prepare it for forensic review.</p>
          <div
            className="drop-zone"
            onDragEnter={(event) => { event.preventDefault(); setIsDragging(true) }}
            onDragOver={(event) => event.preventDefault()}
            onDragLeave={() => setIsDragging(false)}
            onDrop={(event) => { event.preventDefault(); setIsDragging(false); handleFile(event.dataTransfer.files[0]) }}
          >
            <button className="button button-light" type="button" onClick={() => inputRef.current?.click()}>
              Choose a video <Icon name="arrow" size={17} />
            </button>
            <span>or drag and drop it here</span>
            <small>MP4, MOV, AVI, MKV or WEBM · up to 2 GB</small>
          </div>
          <input ref={inputRef} className="visually-hidden" type="file" accept="video/*" onChange={(event) => handleFile(event.target.files[0])} />
          {status === 'error' && <p className="error-message">That file type isn’t supported. Try an MP4, MOV, AVI, MKV, or WEBM file.</p>}
        </>
      ) : status === 'ready' ? (
        <>
          <div className="file-badge"><span className="file-dot" /> VIDEO READY</div>
          <h2>Ready to process</h2>
          <p className="upload-copy file-name">{file?.name}</p>
          <div className="file-meta"><span>{file ? `${(file.size / (1024 * 1024)).toFixed(1)} MB` : 'Video file'}</span><span>•</span><span>Local preview only</span></div>
          <button className="button button-accent button-wide" type="button" onClick={startProcessing}>Start analysis <Icon name="arrow" size={17} /></button>
          <button className="text-button" type="button" onClick={reset}>Choose another file</button>
        </>
      ) : status === 'processing' ? (
        <>
          <div className="processing-orbit"><span /><span /><span /></div>
          <p className="eyebrow">PROCESSING FOOTAGE</p>
          <h2>Making sense of every frame</h2>
          <p className="upload-copy file-name">{file?.name}</p>
          <div className="progress-track"><span style={{ width: `${progress}%` }} /></div>
          <div className="progress-label"><span>{processingSteps[step]}</span><strong>{progress}%</strong></div>
          <div className="processing-steps">
            {processingSteps.map((item, index) => <span className={index <= step ? 'active' : ''} key={item}><Icon name={index < step ? 'check' : 'chevron'} size={13} />{item}</span>)}
          </div>
        </>
      ) : (
        <>
          <div className="complete-icon"><Icon name="check" size={26} /></div>
          <p className="eyebrow">ANALYSIS COMPLETE</p>
          <h2>Your footage is ready</h2>
          <p className="upload-copy">A common copy has been prepared with the first review signals.</p>
          <div className="result-grid"><div><strong>04</strong><span>Faces found</span></div><div><strong>03</strong><span>Activity moments</span></div><div><strong>98%</strong><span>File integrity</span></div></div>
          <button className="button button-accent button-wide" type="button" onClick={reset}>Process another video <Icon name="refresh" size={16} /></button>
        </>
      )}
      </div>
      {isAuthOpen && <AuthModal mode={authMode} setMode={(nextMode) => { setAuthMode(nextMode); setAuthError('') }} form={authForm} setForm={setAuthForm} error={authError} isSubmitting={isSubmitting} onClose={closeAuth} onSubmit={submitAuth} />}
    </>
  )
}

function App() {
  return (
    <div className="app-shell">
      <header className="site-header">
        <a className="brand" href="#top" aria-label="DVR Forensics home"><span className="brand-mark"><span /><span /><span /></span><span>DVR <em>FORENSICS</em></span></a>
        <nav className="main-nav" aria-label="Main navigation"><a href="#about">About</a><a href="#capabilities">Capabilities</a><a href="#process">How it works</a></nav>
        <a className="header-action" href="#upload">Start an upload <Icon name="arrow" size={16} /></a>
      </header>

      <main id="top">
        <section className="hero-section" id="upload">
          <div className="hero-grid" />
          <div className="hero-content">
            <p className="eyebrow accent-eyebrow"><span className="live-dot" /> DIGITAL EVIDENCE, MADE CLEAR</p>
            <h1>Every frame<br /><span>tells a story.</span></h1>
            <p className="hero-copy">Turn complex CCTV exports into a clear, common format — then find the people, moments, and movement that matter.</p>
            <div className="hero-links"><a className="button button-accent" href="#upload-card">Upload footage <Icon name="arrow" size={17} /></a><a className="quiet-link" href="#about">Explore the platform <Icon name="chevron" size={15} /></a></div>
          </div>
          <Globe />
          <div className="hero-footer"><span>BUILT FOR THE INVESTIGATION</span><span className="hero-line" /><span>01 / 04</span></div>
        </section>

        <section className="upload-section section-shell" id="upload-card">
          <div className="section-intro"><p className="eyebrow">01 / BRING IT IN</p><h2>Start with the footage<br /><span>you already have.</span></h2><p>Different cameras. Different formats. One place to begin. Upload an export from your DVR and let the workflow take care of the technical first pass.</p></div>
          <UploadCard />
        </section>

        <section className="statement-section" id="about">
          <div className="section-shell statement-inner">
            <p className="eyebrow">02 / ABOUT FORENSICS</p>
            <h2>Make digital evidence<br /><span>clear and traceable.</span></h2>
            <div className="statement-bottom"><p>Digital forensics is the careful process of preserving, examining and explaining digital evidence. DVR Forensics applies that discipline to CCTV exports so your team can move from a difficult file to a reviewable record with confidence.</p><a className="quiet-link" href="#process">Explore the process <Icon name="arrow" size={16} /></a></div>
            <div className="about-grid"><article><span className="about-index">01</span><h3>Preserve the source</h3><p>Keep the original export safe and work from a connected copy.</p></article><article><span className="about-index">02</span><h3>Read the details</h3><p>Parse vendor formats, timestamps and metadata into one view.</p></article><article><span className="about-index">03</span><h3>Explain the finding</h3><p>Turn checks and signals into a record people can understand.</p></article></div>
          </div>
        </section>

        <section className="capabilities-section section-shell" id="capabilities">
          <div className="section-heading"><div><p className="eyebrow">03 / CAPABILITIES</p><h2>Less searching.<br /><span>More finding.</span></h2></div><p>Useful signals from the footage you have, arranged in a way that helps your investigation move forward.</p></div>
          <div className="feature-grid">{features.map((feature) => <article className="feature-card" key={feature.number}><div className="feature-top"><span className="feature-number">{feature.number}</span><span className="feature-icon"><Icon name={feature.icon} size={21} /></span></div><h3>{feature.title}</h3><p>{feature.text}</p></article>)}</div>
        </section>

        <section className="process-section section-shell" id="process">
          <div className="section-heading process-heading"><div><p className="eyebrow">04 / THE WORKFLOW</p><h2>From export<br /><span>to insight.</span></h2></div><p>A calm, visible workflow. Select a step to see what happens to your video before the final forensic output.</p></div>
          <ProcessFlow />
        </section>

        <section className="closing-section"><div className="closing-orb" /><div className="section-shell closing-inner"><p className="eyebrow accent-eyebrow">READY WHEN YOU ARE</p><h2>Start with one<br /><span>video.</span></h2><a className="button button-accent" href="#upload-card">Upload footage <Icon name="arrow" size={17} /></a></div></section>
      </main>

      <footer className="site-footer"><a className="brand" href="#top"><span className="brand-mark"><span /><span /><span /></span><span>DVR <em>FORENSICS</em></span></a><span>Common format. Clearer evidence.</span><span>© 2026 DVR Forensics</span></footer>
    </div>
  )
}

export default App
