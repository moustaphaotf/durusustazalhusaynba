import { ChevronDown, ChevronUp, Loader2, Pause, Play, X } from 'lucide-react'

import { formatTime, useAudioPlayer } from '#/contexts/AudioPlayerContext'
import { displayTitle, hasArabicTitle } from '#/lib/teaching-utils'
import { cn } from '#/lib/utils'

export function StickyPlayer() {
  const {
    currentTeaching,
    isPlaying,
    isLoading,
    isExpanded,
    currentTime,
    duration,
    error,
    togglePlayPause,
    seek,
    setExpanded,
  } = useAudioPlayer()

  if (!currentTeaching) return null

  const title = displayTitle(currentTeaching)
  const isArabic = hasArabicTitle(currentTeaching)
  const progress = duration > 0 ? (currentTime / duration) * 100 : 0

  return (
    <div
      className={cn(
        'player-slide-up fixed inset-x-0 bottom-0 z-50 border-t border-[var(--line)] bg-[var(--surface-strong)] shadow-[0_-8px_32px_rgba(36,28,21,0.12)]',
        isExpanded ? 'top-0 flex flex-col' : '',
      )}
      role="region"
      aria-label="Lecteur audio"
    >
      {isExpanded ? (
        <div className="flex items-center justify-between border-b border-[var(--line)] px-4 py-3">
          <button
            type="button"
            onClick={() => setExpanded(false)}
            className="flex h-11 w-11 items-center justify-center rounded-full text-[var(--ink-soft)] hover:bg-[var(--surface-muted)]"
            aria-label="Réduire le lecteur"
          >
            <ChevronDown className="h-6 w-6" />
          </button>
          <p className="island-kicker text-[var(--kicker)]">En écoute</p>
          <button
            type="button"
            onClick={() => setExpanded(false)}
            className="flex h-11 w-11 items-center justify-center rounded-full text-[var(--ink-soft)] hover:bg-[var(--surface-muted)]"
            aria-label="Fermer le lecteur étendu"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
      ) : null}

      <div
        className={cn(
          'page-wrap mx-auto w-full max-w-[720px]',
          isExpanded ? 'flex flex-1 flex-col justify-center px-4 py-8' : 'px-4 py-3',
        )}
      >
        {isExpanded ? (
          <div className="text-center">
            <div className="mx-auto mb-8 flex h-40 w-40 items-center justify-center rounded-[20px] bg-[var(--primary)]/10">
              <div className="flex h-20 w-20 items-center justify-center rounded-full bg-[var(--accent)] text-white">
                {isLoading ? (
                  <Loader2 className="h-10 w-10 animate-spin" />
                ) : isPlaying ? (
                  <Pause className="h-10 w-10 fill-current" />
                ) : (
                  <Play className="h-10 w-10 fill-current" />
                )}
              </div>
            </div>
            <h2
              className={cn(
                'display-title text-[1.35rem] leading-snug font-bold text-[var(--ink)]',
                isArabic && 'font-arabic text-[1.5rem] leading-relaxed',
              )}
            >
              {title}
            </h2>
            {currentTeaching.category ? (
              <p className="mt-2 text-[0.85rem] text-[var(--ink-muted)]">
                {currentTeaching.category.name}
              </p>
            ) : null}
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setExpanded(true)}
            className="mb-2 flex w-full items-center gap-3 text-left"
            aria-label="Agrandir le lecteur"
          >
            <div className="min-w-0 flex-1">
              <p className="island-kicker text-[var(--kicker)]">En écoute</p>
              <p
                className={cn(
                  'truncate text-[0.92rem] font-semibold text-[var(--ink)]',
                  isArabic && 'font-arabic',
                )}
              >
                {title}
              </p>
            </div>
            <ChevronUp className="h-5 w-5 shrink-0 text-[var(--ink-muted)]" aria-hidden />
          </button>
        )}

        <div className={cn('flex items-center gap-3', isExpanded && 'mt-8')}>
          <button
            type="button"
            onClick={() => void togglePlayPause()}
            disabled={isLoading}
            className="btn-listen flex h-12 w-12 shrink-0 items-center justify-center rounded-full text-white disabled:opacity-70"
            aria-label={isPlaying ? 'Pause' : 'Lecture'}
          >
            {isLoading ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : isPlaying ? (
              <Pause className="h-5 w-5 fill-current" />
            ) : (
              <Play className="h-5 w-5 fill-current" />
            )}
          </button>

          <div className="min-w-0 flex-1">
            <input
              type="range"
              min={0}
              max={duration || 100}
              step={0.1}
              value={currentTime}
              onChange={(e) => seek(Number(e.target.value))}
              className="player-range w-full"
              aria-label="Progression"
              style={
                {
                  '--progress': `${progress}%`,
                } as React.CSSProperties
              }
            />
            <div className="mt-1 flex justify-between text-[0.72rem] text-[var(--ink-muted)]">
              <span>{formatTime(currentTime)}</span>
              <span>{formatTime(duration)}</span>
            </div>
          </div>
        </div>

        {error ? (
          <p className="mt-2 text-[0.8rem] text-[var(--ink-muted)]" role="alert">
            {error}
          </p>
        ) : null}
      </div>
    </div>
  )
}
