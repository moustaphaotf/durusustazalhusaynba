import {
  HeadContent,
  Scripts,
  createRootRoute,
  Outlet,
} from '@tanstack/react-router'
import { TanStackRouterDevtoolsPanel } from '@tanstack/react-router-devtools'
import { TanStackDevtools } from '@tanstack/react-devtools'
import { useEffect } from 'react'

import { ErrorReporter } from '#/components/ErrorReporter'
import { AudioPlayerProvider } from '#/contexts/AudioPlayerContext'
import { reportCaughtError } from '#/lib/error-reporting'
import appCss from '../styles.css?url'

export const Route = createRootRoute({
  head: () => ({
    meta: [
      { charSet: 'utf-8' },
      {
        name: 'viewport',
        content: 'width=device-width, initial-scale=1',
      },
      {
        name: 'description',
        content:
          'Écoutez les enseignements islamiques audio en pulaar du Oustaz Alhousseyni Bah — Dakar.',
      },
      {
        title: 'Durus — Oustaz Alhousseyni Bah, Dakar',
      },
    ],
    links: [
      { rel: 'stylesheet', href: appCss },
      {
        rel: 'stylesheet',
        href: 'https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,700&family=Noto+Naskh+Arabic:wght@400;600&family=Source+Sans+3:wght@400;500;600;700&display=swap',
      },
    ],
  }),
  component: RootComponent,
  shellComponent: RootDocument,
  errorComponent: RootErrorComponent,
})

function RootErrorComponent({ error }: { error: unknown }) {
  useEffect(() => {
    reportCaughtError(error, 'router.errorComponent')
  }, [error])

  return (
    <div className="mx-auto flex min-h-[50vh] max-w-lg flex-col items-center justify-center gap-4 px-6 text-center">
      <h1 className="font-display text-2xl text-stone-900">
        Une erreur est survenue
      </h1>
      <p className="text-stone-600">
        L&apos;équipe a été notifiée. Rechargez la page ou réessayez plus tard.
      </p>
    </div>
  )
}

function RootComponent() {
  return (
    <AudioPlayerProvider>
      <ErrorReporter />
      <Outlet />
    </AudioPlayerProvider>
  )
}

function RootDocument({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <head>
        <HeadContent />
      </head>
      <body>
        {children}
        <TanStackDevtools
          config={{ position: 'bottom-right' }}
          plugins={[
            {
              name: 'Tanstack Router',
              render: <TanStackRouterDevtoolsPanel />,
            },
          ]}
        />
        <Scripts />
      </body>
    </html>
  )
}
