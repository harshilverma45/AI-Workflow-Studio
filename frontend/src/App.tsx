import { FormEvent, useEffect, useMemo, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import ReactFlow, { Background, Controls, Edge, Node } from 'reactflow'
import 'reactflow/dist/style.css'

type LiveExecutionResponse = { id: number; prompt: string }
type SavedExecution = { id: number; prompt: string; final_response: string; iterations: number }
type ExecutionHistory = SavedExecution & { history: Array<{ iteration_number: number; response: string; evaluation: string; score: number }> }

type StreamEvent = {
  type: 'execution_started' | 'iteration_completed' | 'execution_completed' | 'execution_failed'
  execution_id: number
  prompt?: string
  iteration_number?: number
  response?: string
  evaluation?: string
  score?: number
  final_response?: string
  detail?: string
}

const apiBase = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000/api'
const websocketBase = apiBase.replace(/^http/, 'ws').replace(/\/api$/, '')

const nodeStyle = { background: '#172554', border: '1px solid #38bdf8', color: '#e0f2fe', borderRadius: 10, padding: 12 }
const workflowNodes: Node[] = [
  { id: 'prompt', position: { x: 0, y: 110 }, data: { label: 'Prompt' }, style: nodeStyle },
  { id: 'draft', position: { x: 180, y: 40 }, data: { label: 'Generate draft' }, style: nodeStyle },
  { id: 'evaluate', position: { x: 180, y: 185 }, data: { label: 'Evaluate quality' }, style: nodeStyle },
  { id: 'answer', position: { x: 405, y: 110 }, data: { label: 'Final answer' }, style: { ...nodeStyle, background: '#164e63', borderColor: '#22d3ee' } },
]
const workflowEdges: Edge[] = [
  { id: 'prompt-draft', source: 'prompt', target: 'draft', animated: true },
  { id: 'draft-evaluate', source: 'draft', target: 'evaluate', animated: true },
  { id: 'evaluate-draft', source: 'evaluate', target: 'draft', label: 'Improve answer', labelStyle: { fill: '#cffafe', fontSize: 11, fontWeight: 600 }, labelBgStyle: { fill: '#164e63', stroke: '#22d3ee', strokeWidth: 1 }, labelBgPadding: [8, 5], labelBgBorderRadius: 6 },
  { id: 'evaluate-answer', source: 'evaluate', target: 'answer', animated: true },
]

export default function App() {
  const [prompt, setPrompt] = useState('Explain how iterative AI workflows improve a response.')
  const [events, setEvents] = useState<StreamEvent[]>([])
  const [execution, setExecution] = useState<LiveExecutionResponse | null>(null)
  const [isRunning, setIsRunning] = useState(false)
  const [activePanel, setActivePanel] = useState<'answer' | 'details'>('answer')
  const [historyOpen, setHistoryOpen] = useState(false)
  const [showAllIterations, setShowAllIterations] = useState(false)
  const [savedExecutions, setSavedExecutions] = useState<SavedExecution[]>([])
  const [error, setError] = useState<string | null>(null)
  const socketRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    void loadExecutions()
    return () => socketRef.current?.close()
  }, [])

  const iterations = useMemo(() => events.filter((event) => event.type === 'iteration_completed'), [events])
  const latestIteration = iterations[iterations.length - 1]
  const completedExecution = useMemo(
    () => [...events].reverse().find((event) => event.type === 'execution_completed'),
    [events],
  )
  const visibleIterations = showAllIterations ? iterations : iterations.slice(-1)
  const statusText = !isRunning
    ? 'Idle'
    : latestIteration
      ? `Preparing iteration ${(latestIteration.iteration_number ?? iterations.length) + 1}`
      : 'Generating first draft'

  async function runExecution(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!prompt.trim() || isRunning) return
    socketRef.current?.close()
    setEvents([])
    setExecution(null)
    setActivePanel('answer')
    setShowAllIterations(false)
    setError(null)
    setIsRunning(true)

    try {
      const response = await fetch(`${apiBase}/execute/live`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ prompt: prompt.trim() }),
      })
      if (!response.ok) throw new Error(`Execution request failed (${response.status}).`)
      const created = (await response.json()) as LiveExecutionResponse
      setExecution(created)
      const socket = new WebSocket(`${websocketBase}/ws/execution/${created.id}`)
      socketRef.current = socket
      socket.onmessage = (message) => {
        const streamEvent = JSON.parse(message.data) as StreamEvent
        setEvents((current) => [...current, streamEvent])
        if (streamEvent.type === 'execution_failed') setError(streamEvent.detail ?? 'Execution failed.')
        if (streamEvent.type === 'execution_completed') void loadExecutions()
      }
      socket.onerror = () => setError('Unable to receive execution progress from the WebSocket stream.')
      socket.onclose = () => setIsRunning(false)
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Unable to start execution.')
      setIsRunning(false)
    }
  }

  async function loadExecutions() {
    try {
      const response = await fetch(`${apiBase}/executions`)
      if (response.ok) setSavedExecutions(uniqueCompletedExecutions((await response.json()) as SavedExecution[]))
    } catch {
      // The history panel remains empty until the backend becomes available.
    }
  }

  async function openSavedExecution(executionId: number) {
    try {
      const response = await fetch(`${apiBase}/execution/${executionId}`)
      if (!response.ok) throw new Error(`Unable to load execution (${response.status}).`)
      const saved = (await response.json()) as ExecutionHistory
      setExecution({ id: saved.id, prompt: saved.prompt })
      setEvents([
        { type: 'execution_started', execution_id: saved.id, prompt: saved.prompt },
        ...saved.history.map((iteration) => ({ type: 'iteration_completed' as const, execution_id: saved.id, ...iteration })),
        { type: 'execution_completed', execution_id: saved.id, final_response: saved.final_response },
      ])
      setError(null)
      setIsRunning(false)
      setShowAllIterations(false)
      setActivePanel('answer')
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Unable to load execution.')
    }
  }

  return <main className="min-h-screen bg-slate-950 text-slate-100">
    <div className="mx-auto grid max-w-[1700px] gap-6 px-6 py-8 lg:h-[calc(100vh-4rem)] lg:grid-cols-[220px_minmax(0,1.1fr)_minmax(0,0.9fr)]">
      <aside className="hidden min-h-0 flex-col rounded-2xl border border-slate-800 bg-gradient-to-b from-slate-900 to-slate-950 p-3 shadow-xl shadow-slate-950/20 lg:flex">
        <button type="button" onClick={() => { void loadExecutions(); setHistoryOpen((open) => !open) }} className={`flex shrink-0 items-center justify-between rounded-xl border px-3 py-3 text-left text-sm font-semibold transition ${historyOpen ? 'border-cyan-400/70 bg-cyan-400/15 text-cyan-200' : 'border-slate-700 bg-slate-950/50 text-slate-200 hover:border-cyan-500/70 hover:text-cyan-200'}`}><span>History</span><span className={`flex h-5 min-w-5 items-center justify-center rounded-full px-1 text-xs ${historyOpen ? 'bg-cyan-400 text-slate-950' : 'bg-slate-800 text-slate-400'}`}>{savedExecutions.length}</span></button>
        {historyOpen ? <><p className="mt-5 px-1 text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Saved runs</p><div className="mt-3 min-h-0 flex-1 overflow-y-auto pr-1"><HistoryPanel executions={savedExecutions} onOpen={openSavedExecution} /></div></> : <div className="mt-5 rounded-xl border border-dashed border-slate-800 p-3 text-sm leading-6 text-slate-500">Open history to revisit saved answers.</div>}
      </aside>
      <section className="flex min-w-0 min-h-0 flex-col gap-6">
        <header className="shrink-0">
          <p className="text-sm font-medium uppercase tracking-[0.24em] text-cyan-400">Loop Engineering Studio</p>
          <h1 className="mt-3 text-4xl font-bold tracking-tight">Build better answers through iteration.</h1>
          <p className="mt-3 max-w-2xl text-slate-300">Follow the draft, critique, and refined answer as each loop completes.</p>
        </header>
        <><form onSubmit={runExecution} className="shrink-0 rounded-2xl border border-slate-800 bg-slate-900 p-5 shadow-xl shadow-slate-950/30">
          <label htmlFor="prompt" className="text-sm font-semibold text-slate-200">Prompt</label>
          <textarea id="prompt" value={prompt} onChange={(event) => setPrompt(event.target.value)} rows={5} className="mt-2 w-full resize-none rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-cyan-400" />
          <div className="mt-4 flex items-center justify-between gap-4"><p className="text-sm text-slate-400">API: {apiBase}</p><button type="submit" disabled={isRunning || !prompt.trim()} className="rounded-lg bg-cyan-400 px-4 py-2 font-semibold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-50">{isRunning ? 'Streaming...' : 'Run workflow'}</button></div>
        </form>
        <section className="h-[330px] shrink-0 overflow-hidden rounded-2xl border border-slate-800 bg-slate-900"><ReactFlow nodes={workflowNodes} edges={workflowEdges} fitView nodesDraggable={false} nodesConnectable={false} elementsSelectable={false}><Background color="#334155" gap={20} /><Controls showInteractive={false} /></ReactFlow></section></>
      </section>

      <aside className="flex min-w-0 min-h-0 flex-col overflow-hidden rounded-2xl border border-slate-800 bg-slate-900 p-5">
        <div className="grid shrink-0 grid-cols-[1fr_10rem] items-center gap-3"><h2 className="text-xl font-semibold">Your answer</h2><span className={`rounded-full px-3 py-1 text-center text-xs font-medium ${isRunning ? 'bg-cyan-400/15 text-cyan-300' : 'bg-slate-800 text-slate-300'}`}>{statusText}</span></div>
        <div className="mt-4 flex shrink-0 rounded-lg bg-slate-950 p-1 text-sm"><PanelButton active={activePanel === 'answer'} onClick={() => setActivePanel('answer')}>Answer</PanelButton>{execution && <PanelButton active={activePanel === 'details'} onClick={() => setActivePanel('details')}>How it improved</PanelButton>}</div>
        <div className="mt-5 min-h-0 flex-1 overflow-y-auto pr-1">
          {error && <p className="rounded-lg border border-rose-800 bg-rose-950/50 p-3 text-sm text-rose-200">{error}</p>}
          {!execution && !error && <p className="text-slate-400">Ask a question to receive an improved answer.</p>}
          {isRunning && !latestIteration && <div className="flex items-center gap-3 rounded-xl border border-cyan-900 bg-cyan-950/30 p-4 text-sm text-cyan-200"><span className="h-2 w-2 animate-pulse rounded-full bg-cyan-300" />Creating your answer...</div>}
          {activePanel === 'answer' && <SimpleAnswer latestIteration={latestIteration} completedExecution={completedExecution} isRunning={isRunning} />}
          {activePanel === 'details' && <DetailedTimeline iterations={iterations} visibleIterations={visibleIterations} showAllIterations={showAllIterations} setShowAllIterations={setShowAllIterations} latestIteration={latestIteration} completedExecution={completedExecution} execution={execution} />}
        </div>
      </aside>
    </div>
  </main>
}

function PanelButton({ active, children, onClick }: { active: boolean; children: string; onClick: () => void }) {
  return <button type="button" aria-pressed={active} onClick={onClick} className={`flex-1 rounded-md px-2 py-2 transition ${active ? 'bg-cyan-400 font-semibold text-slate-950' : 'text-slate-300 hover:text-white'}`}>{children}</button>
}

function HistoryPanel({ executions, onOpen }: { executions: SavedExecution[]; onOpen: (id: number) => void }) {
  if (!executions.length) return <p className="px-1 text-sm text-slate-400">No saved answers yet.</p>
  return <div className="space-y-2">{executions.map((saved) => <button type="button" key={saved.id} onClick={() => onOpen(saved.id)} className="group w-full rounded-xl border border-slate-800 bg-slate-950/70 p-3 text-left transition hover:border-cyan-500/70 hover:bg-cyan-950/20"><p className="line-clamp-3 text-sm font-medium leading-5 text-slate-100 transition group-hover:text-cyan-100">{saved.prompt}</p><div className="mt-3 flex items-center justify-between border-t border-slate-800 pt-2 text-xs"><span className="text-cyan-300">{saved.iterations} {saved.iterations === 1 ? 'refinement' : 'refinements'}</span><span className="text-slate-500 transition group-hover:text-cyan-300">Open</span></div></button>)}</div>
}

function uniqueCompletedExecutions(executions: SavedExecution[]) {
  const prompts = new Set<string>()
  return executions.filter((execution) => {
    if (!execution.final_response) return false
    const promptKey = execution.prompt.trim().replace(/\s+/g, ' ').toLocaleLowerCase()
    if (prompts.has(promptKey)) return false
    prompts.add(promptKey)
    return true
  })
}

function SimpleAnswer({ latestIteration, completedExecution, isRunning }: { latestIteration?: StreamEvent; completedExecution?: StreamEvent; isRunning: boolean }) {
  const answer = completedExecution?.final_response ?? latestIteration?.response
  if (!answer) return null
  return <div className="h-full"><section className="min-h-full rounded-xl border border-emerald-800 bg-emerald-950/40 p-5"><p className="text-xs font-semibold uppercase tracking-wide text-emerald-300">{completedExecution ? 'Your answer' : 'Answer in progress'}</p><Markdown content={answer} className="mt-3 text-slate-100" />{isRunning && <p className="mt-6 flex items-center gap-2 border-t border-emerald-900 pt-4 text-sm text-cyan-200"><span className="h-2 w-2 animate-pulse rounded-full bg-cyan-300" />Improving this answer...</p>}</section></div>
}

function DetailedTimeline({ iterations, visibleIterations, showAllIterations, setShowAllIterations, latestIteration, completedExecution, execution }: { iterations: StreamEvent[]; visibleIterations: StreamEvent[]; showAllIterations: boolean; setShowAllIterations: (shown: boolean | ((shown: boolean) => boolean)) => void; latestIteration?: StreamEvent; completedExecution?: StreamEvent; execution: LiveExecutionResponse | null }) {
  return <><p className="text-sm text-slate-400">Drafts, evaluation notes, and score changes are shown here.</p>{iterations.length > 1 && <button type="button" onClick={() => setShowAllIterations((shown) => !shown)} className="mt-4 text-sm font-medium text-cyan-300 hover:text-cyan-200">{showAllIterations ? 'Show latest iteration only' : `Show all ${iterations.length} iterations`}</button>}<div className="mt-5 space-y-5">{visibleIterations.map((iteration) => <IterationCard key={`${iteration.execution_id}-${iteration.iteration_number}`} event={iteration} previous={iterations[iterations.indexOf(iteration) - 1]} isLatest={iteration === latestIteration} />)}</div>{execution && completedExecution && <section className="mt-5 rounded-xl border border-emerald-800 bg-emerald-950/40 p-5"><p className="text-xs font-semibold uppercase tracking-wide text-emerald-300">Final answer</p><Markdown content={completedExecution.final_response ?? ''} className="mt-3 text-slate-100" /></section>}</>
}


function IterationCard({ event, previous, isLatest }: { event: StreamEvent; previous?: StreamEvent; isLatest: boolean }) {
  const scoreChange = previous?.score !== undefined && event.score !== undefined ? event.score - previous.score : undefined
  const label = event.iteration_number === 1 ? 'Draft answer' : 'Improved answer'
  return <article className={`rounded-xl border p-5 ${isLatest ? 'border-cyan-700 bg-cyan-950/20' : 'border-slate-800 bg-slate-950/70'}`}>
    <div className="flex flex-wrap items-center justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-wide text-cyan-300">Iteration {event.iteration_number}</p><h3 className="mt-1 text-lg font-semibold">{label}</h3></div><ScoreBadge score={event.score} change={scoreChange} /></div>
    <section className="mt-5"><p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Answer</p><Markdown content={event.response ?? ''} className="mt-2 text-slate-100" /></section>
    <section className="mt-5 border-t border-slate-800 pt-4"><p className="text-xs font-semibold uppercase tracking-wide text-amber-300">Critique and next improvement</p><Markdown content={event.evaluation ?? ''} className="mt-2 text-slate-300" /></section>
  </article>
}

function ScoreBadge({ score, change }: { score?: number; change?: number }) {
  return <div className="rounded-lg bg-slate-800 px-3 py-2 text-right"><p className="text-xs text-slate-400">Quality score</p><p className="font-semibold text-cyan-200">{score?.toFixed(2) ?? '--'}{change !== undefined && <span className={change >= 0 ? 'ml-2 text-emerald-300' : 'ml-2 text-rose-300'}>{change >= 0 ? '+' : ''}{change.toFixed(2)}</span>}</p></div>
}

function Markdown({ content, className }: { content: string; className?: string }) {
  return <div className={`markdown ${className ?? ''}`}><ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown></div>
}
