import { Loader2, Play } from 'lucide-react'

import { useAudioPlayer } from '#/contexts/AudioPlayerContext'
import { displayTitle, hasArabicTitle } from '#/lib/teaching-utils'
import type { Teaching } from '#/lib/types'
import { cn } from '#/lib/utils'

interface ResumeCardProps {
  teaching: Teaching
}

export function ResumeCard({ teaching }: ResumeCardProps) {
  const { playTeaching, isLoading, loadingTeachingId, resumePosition } =
    useAudioPlayer()

  const title = displayTitle(teaching)
  const isArabic = hasArabicTitle(teaching)
  const isThisLoading = isLoading && loadingTeachingId === teaching.id
  const saved = resumePosition ?? 0
  const showResumeHint = saved > 10

  return (
    <section
      className="rise-in feature-card mb-8 overflow-hidden rounded-2xl border border-[var(--line)]"
      aria-label="Reprendre l'écoute"
    >
      <div className="relative p-5 sm:p-6">
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.35]"
          style={{
            background:
              'radial-gradient(ellipse 80% 60% at 0% 0%, rgba(192,93,60,0.18), transparent 55%), radial-gradient(ellipse 60% 50% at 100% 100%, rgba(43,58,103,0.12), transparent 50%)',
          }}
        />
        <div className="relative">
          <p className="island-kicker text-[var(--accent)]">Reprendre l&apos;écoute</p>
          <h2
            className={cn(
              'mt-2 text-[1.05rem] leading-snug font-semibold text-[var(--ink)]',
              isArabic && 'font-arabic text-[1.1rem] leading-relaxed',
            )}
          >
            {title}
          </h2>
          {showResumeHint ? (
            <p className="mt-2 text-[0.8rem] text-[var(--ink-muted)]">
              Reprendre près de votre dernière position
            </p>
          ) : (
            <p className="mt-2 text-[0.8rem] text-[var(--ink-muted)]">
              Continuer cet enseignement
            </p>
          )}
          <button
            type="button"
            onClick={() => void playTeaching(teaching)}
            disabled={isThisLoading}
            className="btn-listen mt-5 inline-flex min-h-12 min-w-12 items-center justify-center gap-2 rounded-full px-6 py-3 text-[0.95rem] font-semibold text-white disabled:opacity-70"
            aria-label={`Reprendre ${title}`}
          >
            {isThisLoading ? (
              <Loader2 className="h-5 w-5 animate-spin" aria-hidden />
            ) : (
              <Play className="h-5 w-5 fill-current" aria-hidden />
            )}
            Reprendre
          </button>
        </div>
      </div>
    </section>
  )
}
