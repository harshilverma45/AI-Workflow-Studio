export default function App() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto flex max-w-5xl flex-col gap-8 px-6 py-12">
        <header className="space-y-4">
          <p className="text-sm uppercase tracking-[0.3em] text-cyan-400">Loop Engineering Studio</p>
          <h1 className="text-4xl font-bold">Visualize AI self-improvement in real time</h1>
          <p className="max-w-2xl text-slate-300">
            This frontend shell is ready for the first execution flow, live logs, and the
            eventual React Flow visualization layer.
          </p>
        </header>

        <section className="grid gap-4 md:grid-cols-2">
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
            <h2 className="mb-2 text-xl font-semibold">Home</h2>
            <p className="text-slate-300">Prompt input, execution trigger, and the first loop step.</p>
          </div>
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
            <h2 className="mb-2 text-xl font-semibold">Execution</h2>
            <p className="text-slate-300">Workflow graph, current iteration, scores, and final answer.</p>
          </div>
        </section>
      </div>
    </main>
  )
}
