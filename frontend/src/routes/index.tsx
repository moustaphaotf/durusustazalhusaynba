import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/')({ component: Home })

function Home() {
  return (
    <main className="flex min-h-screen items-center justify-center p-8">
      <div className="max-w-xl text-center">
        <p className="text-sm font-medium tracking-wide text-muted-foreground uppercase">
          Durus
        </p>
        <h1 className="mt-3 text-4xl font-bold tracking-tight">
          Bibliothèque en construction
        </h1>
        <p className="mt-4 text-lg text-muted-foreground">
          Plateforme de consultation des enseignements audio — synchronisation
          Telegram à venir.
        </p>
      </div>
    </main>
  )
}
