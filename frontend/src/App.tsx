import { useEffect, useState } from 'react'
import { ChevronDown, Infinity, Menu, X } from 'lucide-react'
import Home from './pages/Home'

const BG_VIDEO = 'https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260511_230229_7c9bc431-46cf-489a-948d-e8144d8eb5d4.mp4'

type InfoPanel = 'project' | 'technology' | 'team'

type NavLink = {
  label: string
  active?: boolean
  panel?: InfoPanel
  href?: string
}

const navLinks: NavLink[] = [
  { label: 'Home', active: true },
  { label: 'Project', panel: 'project' },
  { label: 'Tech Used', panel: 'technology' },
  { label: 'GitHub', href: 'https://github.com/Uhimanshu9/ClaimIQ' },
  { label: 'Our Team', panel: 'team' },
]

const panelContent: Record<InfoPanel, { title: string; description: string; sections?: Array<{ heading: string; items: string[] }> }> = {
  project: {
    title: 'About Claim IQ',
    description: 'Claim IQ is a document intelligence assistant. Upload policy and claim PDFs, build a searchable knowledge base, and receive answers grounded in the documents you have indexed.',
  },
  technology: {
    title: 'Technology & architecture',
    description: 'Claim IQ is built as a document intelligence platform with a browser client, an API and background-processing layer, and dedicated data services.',
    sections: [
      {
        heading: 'Frontend',
        items: [
          'React — component-based user interface for upload, chat, provider selection, and chat history.',
          'Vite — local development server and optimized production build pipeline.',
          'TypeScript — type-safe landing-page and application UI code.',
          'Tailwind CSS — responsive layout, liquid-glass styling, and consistent design tokens.',
          'lucide-react — lightweight icons used across navigation and actions.',
        ],
      },
      {
        heading: 'Backend & processing',
        items: [
          'FastAPI — REST API for document upload, indexing status, queries, providers, cancellation, and chat history.',
          'Docker Compose — runs the API, worker, MongoDB, Valkey, and Qdrant together in a reproducible local environment.',
          'Valkey + RQ — queues long-running PDF extraction and indexing jobs outside the web request.',
          'PyPDF and LangChain splitting — extracts PDF content and divides it into retrievable chunks.',
        ],
      },
      {
        heading: 'Data & AI services',
        items: [
          'MongoDB — stores uploaded-document records, indexing state, and non-empty conversations in the chat_history collection.',
          'Qdrant — stores document chunk vectors and returns the most relevant evidence for each question.',
          'OpenAI text-embedding-3-small — creates one consistent vector representation for the Qdrant collection.',
          'Gemini, OpenAI, or Amazon Bedrock — selectable providers that generate the final answer from retrieved document context.',
        ],
      },
      {
        heading: 'How the architecture works',
        items: [
          'Upload flow: Browser → FastAPI → MongoDB document record → Valkey/RQ job → PDF extraction and chunking → OpenAI embeddings → Qdrant.',
          'Question flow: Browser → FastAPI → query expansion → Qdrant similarity search → selected AI provider → grounded answer and sources returned to chat.',
          'History flow: Browser → FastAPI → MongoDB chat_history; only chats with messages are persisted.',
        ],
      },
    ],
  },
  team: {
    title: 'Our team',
    description: 'Claim IQ is built and maintained by Himanshu Dahiya. The project focuses on making complex policy and claim documents easier to search, understand, and use.',
  },
}

function NavigationLinks({ mobile = false, onSelect }: { mobile?: boolean; onSelect?: (link: NavLink) => void }) {
  return (
    <>
      {navLinks.map((link) => (
        link.href ? (
          <a
            key={link.label}
            href={link.href}
            target="_blank"
            rel="noreferrer"
            className={mobile
              ? 'flex items-center justify-between w-full px-4 py-3 rounded-lg text-sm transition-colors text-white/70 hover:text-white hover:bg-white/5'
              : 'flex items-center gap-0.5 px-3 py-1.5 rounded-md text-sm transition-colors text-white/70 hover:text-white'}
          >
            {link.label}
          </a>
        ) : (
        <button
          key={link.label}
          type="button"
          onClick={() => onSelect?.(link)}
          className={mobile
            ? `flex items-center justify-between w-full px-4 py-3 rounded-lg text-sm transition-colors ${link.active ? 'bg-white/15 text-white' : 'text-white/70 hover:text-white hover:bg-white/5'}`
            : `flex items-center gap-0.5 px-3 py-1.5 rounded-md text-sm transition-colors ${link.active ? 'bg-white/15 text-white' : 'text-white/70 hover:text-white'}`}
        >
          {link.label}
        </button>
        )
      ))}
    </>
  )
}

export default function App() {
  const [menuOpen, setMenuOpen] = useState(false)
  const [infoPanel, setInfoPanel] = useState<InfoPanel | null>(null)
  const [isChatPage, setIsChatPage] = useState(() => window.location.pathname === '/chat')

  useEffect(() => {
    const syncRoute = () => setIsChatPage(window.location.pathname === '/chat')
    window.addEventListener('popstate', syncRoute)
    return () => window.removeEventListener('popstate', syncRoute)
  }, [])

  const openChat = () => {
    window.history.pushState({}, '', '/chat')
    setMenuOpen(false)
    setIsChatPage(true)
  }

  const openHome = (event: React.MouseEvent<HTMLAnchorElement>) => {
    event.preventDefault()
    window.history.pushState({}, '', '/')
    setIsChatPage(false)
  }

  const handleNavSelection = (link: NavLink) => {
    setMenuOpen(false)
    if (link.panel) setInfoPanel(link.panel)
  }

  if (isChatPage) return <Home />

  return (
    <div className="relative w-full h-screen overflow-hidden">
      <video className="absolute inset-0 w-full h-full object-cover" autoPlay muted loop playsInline src={BG_VIDEO} />

      <nav className="absolute top-0 left-0 right-0 z-20 flex items-center justify-between px-5 sm:px-8 py-5">
        <a href="/" onClick={openHome} className="flex items-center gap-2 text-white font-medium text-base" aria-label="Equilibrium home">
          <Infinity size={22} strokeWidth={1.5} />
          <span>Claim IQ</span>
        </a>

        <div className="hidden md:flex liquid-glass items-center gap-1 rounded-xl px-2 py-2">
          <NavigationLinks onSelect={handleNavSelection} />
        </div>

        <div className="hidden md:flex items-center gap-3">
          <button type="button" className="liquid-glass text-white text-sm font-medium px-4 py-2.5 rounded-full hover:bg-white/5 transition-colors">Log in</button>
          <button type="button" onClick={openChat} className="bg-white text-black text-sm font-medium px-4 py-2.5 rounded-full hover:bg-white/90 transition-colors">Begin Now</button>
        </div>

        <button
          type="button"
          className="md:hidden liquid-glass text-white p-2 rounded-lg"
          onClick={() => setMenuOpen((open) => !open)}
          aria-label={menuOpen ? 'Close navigation menu' : 'Open navigation menu'}
          aria-expanded={menuOpen}
        >
          {menuOpen ? <X size={18} /> : <Menu size={18} />}
        </button>
      </nav>

      {menuOpen && (
        <div className="absolute top-[72px] left-4 right-4 z-30 md:hidden liquid-glass rounded-2xl p-4 flex flex-col gap-1">
          <NavigationLinks mobile onSelect={handleNavSelection} />
          <div className="flex gap-2 mt-2 pt-3 border-t border-white/10">
            <button type="button" className="liquid-glass flex-1 text-white text-sm font-medium px-4 py-2.5 rounded-full hover:bg-white/5 transition-colors">Log in</button>
            <button type="button" onClick={openChat} className="flex-1 bg-white text-black text-sm font-medium px-4 py-2.5 rounded-full hover:bg-white/90 transition-colors">Begin Now</button>
          </div>
        </div>
      )}

      <main id="home" className="absolute bottom-0 left-0 z-20 px-6 sm:px-12 pb-10 sm:pb-16 max-w-2xl">
        <h1 className="text-white text-4xl sm:text-5xl lg:text-6xl font-medium leading-tight tracking-tight mb-4">Understand Every Claim with Confidence</h1>
        <p className="text-white/60 text-sm leading-relaxed mb-7 max-w-md">Upload policy and claim documents, build a searchable knowledge base, and get clear answers grounded in the information your team has indexed.</p>
        <div className="flex flex-wrap items-center gap-3">
          <button type="button" onClick={openChat} className="bg-white text-black text-sm sm:text-base font-medium px-6 sm:px-7 py-3 rounded-full hover:bg-white/90 transition-colors">Start Today</button>
          <button type="button" onClick={() => setInfoPanel('project')} className="liquid-glass text-white text-sm sm:text-base font-medium px-6 sm:px-7 py-3 rounded-full hover:bg-white/5 transition-colors">Discover How</button>
        </div>
      </main>

      {infoPanel && (
        <div className="absolute inset-0 z-40 flex items-center justify-center px-5 bg-black/50" role="dialog" aria-modal="true" aria-labelledby="info-panel-title">
          <section className="liquid-glass w-full max-w-3xl max-h-[85vh] overflow-y-auto rounded-2xl p-6 sm:p-8 text-white">
            <div className="flex items-start justify-between gap-5">
              <div>
                <p className="text-white/55 text-sm mb-2">Claim IQ</p>
                <h2 id="info-panel-title" className="text-2xl sm:text-3xl font-medium tracking-tight">{panelContent[infoPanel].title}</h2>
              </div>
              <button type="button" onClick={() => setInfoPanel(null)} className="liquid-glass p-2 rounded-lg text-white hover:bg-white/5 transition-colors" aria-label="Close information panel"><X size={18} /></button>
            </div>
            <p className="mt-5 text-white/70 leading-relaxed text-sm sm:text-base">{panelContent[infoPanel].description}</p>
            {panelContent[infoPanel].sections && (
              <div className="mt-6 grid gap-5 sm:grid-cols-2">
                {panelContent[infoPanel].sections.map((section) => (
                  <article key={section.heading} className="rounded-xl bg-white/5 p-4">
                    <h3 className="text-sm font-medium text-white">{section.heading}</h3>
                    <ul className="mt-3 space-y-2 text-xs leading-relaxed text-white/65">
                      {section.items.map((item) => <li key={item}>{item}</li>)}
                    </ul>
                  </article>
                ))}
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  )
}
