import { useEffect, useRef, useState } from 'react'
import { createCase, parseEvidence, uploadEvidence } from './api'
import { isSupabaseConfigured, supabase } from './supabase'

const processingSteps = [
  'Uploading footage',
  'Reading video format',
  'Creating a common copy',
  'Detecting faces',
  'Mapping activities',
]

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

function UploadCard({ session, onSignIn }) {
  const inputRef = useRef(null)
  const [file, setFile] = useState(null)
  const [isDragging, setIsDragging] = useState(false)
  const [status, setStatus] = useState('idle')
  const [step, setStep] = useState(0)
  const [progress, setProgress] = useState(0)
  const [message, setMessage] = useState('')
  const [result, setResult] = useState(null)

  const handleFile = (selectedFile) => {
    if (!session) {
      onSignIn()
      return
    }
    if (!selectedFile) return
    const supported = ['video/mp4', 'video/quicktime', 'video/x-msvideo', 'video/x-matroska', 'video/webm']
    const extensionOk = /\.(dd|mp4|mov|avi|mkv|webm)$/i.test(selectedFile.name)
    if (!supported.includes(selectedFile.type) && !extensionOk) {
      setMessage('That file type isn’t supported. Try a DVR image (.dd) or MP4, MOV, AVI, MKV, or WEBM file.')
      setStatus('error')
      return
    }
    setFile(selectedFile)
    setStep(0)
    setProgress(0)
    setMessage('')
    setStatus('ready')
  }

  const reset = () => {
    setFile(null)
    setProgress(0)
    setStep(0)
    setStatus('idle')
    if (inputRef.current) inputRef.current.value = ''
  }

  const startProcessing = async () => {
    if (!session) {
      onSignIn()
      return
    }
    try {
      setStatus('processing')
      setStep(0)
      setProgress(12)
      const caseRecord = await createCase(session.access_token, {
        name: `Analysis: ${file.name}`,
        investigator: session.user.email || 'Authenticated investigator',
      })
      setStep(1)
      setProgress(45)
      const evidence = await uploadEvidence(session.access_token, caseRecord.id, file)
      setStep(2)
      setProgress(75)
      const parsed = await parseEvidence(session.access_token, evidence.id)
      setStep(4)
      setProgress(100)
      setResult({ caseRecord, evidence: parsed })
      setStatus('complete')
    } catch (error) {
      setMessage(error.message || 'The evidence could not be processed.')
      setStatus('error')
    }
  }

  return (
    <div className={`upload-card ${isDragging ? 'is-dragging' : ''}`}>
      {status === 'idle' || status === 'error' ? (
        <>
          <div className="upload-icon"><Icon name="cloud" size={26} /></div>
          <p className="eyebrow">START AN INVESTIGATION</p>
          <h2>Drop your footage here</h2>
          <p className="upload-copy">{session ? 'Upload a CCTV export and we’ll prepare it for forensic review.' : 'Sign in or create an account before uploading protected evidence.'}</p>
          <div
            className="drop-zone"
            onDragEnter={(event) => { event.preventDefault(); setIsDragging(true) }}
            onDragOver={(event) => event.preventDefault()}
            onDragLeave={() => setIsDragging(false)}
            onDrop={(event) => { event.preventDefault(); setIsDragging(false); handleFile(event.dataTransfer.files[0]) }}
          >
            <button className="button button-light" type="button" onClick={() => inputRef.current?.click()}>
              {session ? 'Choose a video' : 'Sign in to upload'} <Icon name="arrow" size={17} />
            </button>
            <span>{session ? 'or drag and drop it here' : 'Protected evidence upload requires sign-in'}</span>
            <small>DVR .DD, MP4, MOV, AVI, MKV or WEBM</small>
          </div>
          <input ref={inputRef} className="visually-hidden" type="file" accept="video/*" onChange={(event) => handleFile(event.target.files[0])} />
          {status === 'error' && <p className="error-message">{message}</p>}
        </>
      ) : status === 'ready' ? (
        <>
          <div className="file-badge"><span className="file-dot" /> VIDEO READY</div>
          <h2>Ready to process</h2>
          <p className="upload-copy file-name">{file?.name}</p>
          <div className="file-meta"><span>{file ? `${(file.size / (1024 * 1024)).toFixed(1)} MB` : 'Video file'}</span><span>•</span><span>Encrypted case workflow</span></div>
          <button className="button button-accent button-wide" type="button" onClick={startProcessing}>{session ? 'Start analysis' : 'Sign in to continue'} <Icon name="arrow" size={17} /></button>
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
          <p className="upload-copy">Evidence has been hashed and the parser result is stored with your case.</p>
          <div className="result-grid"><div><strong>{result?.evidence?.recordings?.length ?? 0}</strong><span>Recordings found</span></div><div><strong>{result?.evidence?.vendor || '—'}</strong><span>Parser vendor</span></div><div><strong>{result?.evidence?.sha256 ? '✓' : '—'}</strong><span>Integrity hash</span></div></div>
          <button className="button button-accent button-wide" type="button" onClick={reset}>Process another video <Icon name="refresh" size={16} /></button>
        </>
      )}
    </div>
  )
}

function AuthDialog({ onClose, onAuthenticated }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [mode, setMode] = useState('signIn')
  const [message, setMessage] = useState('')

  const submit = async (event) => {
    event.preventDefault()
    if (!supabase) return
    setMessage('')
    const action = mode === 'signIn'
      ? supabase.auth.signInWithPassword({ email, password })
      : supabase.auth.signUp({ email, password })
    const { data, error } = await action
    if (error) return setMessage(error.message)
    if (data.session) onAuthenticated(data.session)
    else setMessage('Check your email to confirm the account, then sign in.')
  }

  return <div className="auth-backdrop" role="presentation"><section className="auth-dialog" role="dialog" aria-modal="true" aria-label="Account access"><button className="auth-close" type="button" onClick={onClose}>×</button><p className="eyebrow accent-eyebrow">SECURE INVESTIGATOR ACCESS</p><h2>{mode === 'signIn' ? 'Sign in to your casework.' : 'Create your investigator account.'}</h2><form onSubmit={submit}><label>Email<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></label><label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} minLength="6" required /></label>{message && <p className="error-message">{message}</p>}<button className="button button-accent button-wide" type="submit">{mode === 'signIn' ? 'Sign in' : 'Create account'} <Icon name="arrow" size={16} /></button></form><button className="text-button" type="button" onClick={() => setMode(mode === 'signIn' ? 'signUp' : 'signIn')}>{mode === 'signIn' ? 'Need an account? Sign up' : 'Already have an account? Sign in'}</button></section></div>
}

function App() {
  const [session, setSession] = useState(null)
  const [showAuth, setShowAuth] = useState(false)

  useEffect(() => {
    if (!supabase) return undefined
    supabase.auth.getSession().then(({ data }) => setSession(data.session))
    const { data: listener } = supabase.auth.onAuthStateChange((_event, nextSession) => setSession(nextSession))
    return () => listener.subscription.unsubscribe()
  }, [])

  const signOut = () => supabase?.auth.signOut()
  return (
    <div className="app-shell">
      <header className="site-header">
        <a className="brand" href="#top" aria-label="DVR Forensics home"><span className="brand-mark"><span /><span /><span /></span><span>DVR <em>FORENSICS</em></span></a>
        <nav className="main-nav" aria-label="Main navigation"><a href="#about">About</a><a href="#capabilities">Capabilities</a><a href="#process">How it works</a></nav>
        {session ? <button className="header-action" type="button" onClick={signOut}>Sign out <Icon name="arrow" size={16} /></button> : <button className="header-action" type="button" onClick={() => setShowAuth(true)}>{isSupabaseConfigured ? 'Sign in' : 'Configure Supabase'} <Icon name="arrow" size={16} /></button>}
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
          <UploadCard session={session} onSignIn={() => setShowAuth(true)} />
        </section>

        <section className="statement-section" id="about">
          <div className="section-shell statement-inner"><p className="eyebrow">02 / WHY IT EXISTS</p><h2>Evidence should be<br /><span>easy to understand.</span></h2><div className="statement-bottom"><p>We’re building a simpler way to work with CCTV footage. DVR Forensics helps teams move from a difficult export to a reviewable record — without losing the details along the way.</p><a className="quiet-link" href="#process">See how it works <Icon name="arrow" size={16} /></a></div></div>
        </section>

        <section className="capabilities-section section-shell" id="capabilities">
          <div className="section-heading"><div><p className="eyebrow">03 / CAPABILITIES</p><h2>Less searching.<br /><span>More finding.</span></h2></div><p>Useful signals from the footage you have, arranged in a way that helps your investigation move forward.</p></div>
          <div className="feature-grid">{features.map((feature) => <article className="feature-card" key={feature.number}><div className="feature-top"><span className="feature-number">{feature.number}</span><span className="feature-icon"><Icon name={feature.icon} size={21} /></span></div><h3>{feature.title}</h3><p>{feature.text}</p></article>)}</div>
        </section>

        <section className="process-section section-shell" id="process">
          <div className="section-heading process-heading"><div><p className="eyebrow">04 / THE WORKFLOW</p><h2>From export<br /><span>to insight.</span></h2></div><p>A calm, traceable workflow that keeps the technical work in the background while you focus on the evidence.</p></div>
          <div className="timeline"><div className="timeline-progress" /><div className="timeline-item"><span className="timeline-number">01</span><div><h3>Upload your footage</h3><p>Bring in the original export from your camera or DVR system.</p></div><span className="timeline-icon"><Icon name="cloud" size={21} /></span></div><div className="timeline-item"><span className="timeline-number">02</span><div><h3>Normalize the format</h3><p>Prepare a consistent working copy while keeping the original safe.</p></div><span className="timeline-icon"><Icon name="scan" size={21} /></span></div><div className="timeline-item"><span className="timeline-number">03</span><div><h3>Surface the signals</h3><p>Review faces, movement, and activity moments on a clear timeline.</p></div><span className="timeline-icon"><Icon name="face" size={21} /></span></div><div className="timeline-item"><span className="timeline-number">04</span><div><h3>Review and report</h3><p>Turn what you found into a record your team can understand.</p></div><span className="timeline-icon"><Icon name="file" size={21} /></span></div></div>
        </section>

        <section className="closing-section"><div className="closing-orb" /><div className="section-shell closing-inner"><p className="eyebrow accent-eyebrow">READY WHEN YOU ARE</p><h2>Start with one<br /><span>video.</span></h2><a className="button button-accent" href="#upload-card">Upload footage <Icon name="arrow" size={17} /></a></div></section>
      </main>

      <footer className="site-footer"><a className="brand" href="#top"><span className="brand-mark"><span /><span /><span /></span><span>DVR <em>FORENSICS</em></span></a><span>Common format. Clearer evidence.</span><span>© 2026 DVR Forensics</span></footer>
      {showAuth && (isSupabaseConfigured ? <AuthDialog onClose={() => setShowAuth(false)} onAuthenticated={(nextSession) => { setSession(nextSession); setShowAuth(false) }} /> : <div className="auth-backdrop"><section className="auth-dialog"><button className="auth-close" type="button" onClick={() => setShowAuth(false)}>×</button><h2>Supabase needs configuration.</h2><p className="upload-copy">Copy <code>.env.example</code> to <code>.env.local</code> in the frontend and add the Supabase URL and publishable key.</p></section></div>)}
    </div>
  )
}

export default App
