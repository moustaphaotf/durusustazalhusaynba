import { Loader2, Pause, Play } from 'lucide-react'

import { useAudioPlayer } from '#/contexts/AudioPlayerContext'
import {
  displayTitle,
  formatFileSize,
  formatPublishedDate,
  getMediaStatus,
  hasArabicTitle,
} from '#/lib/teaching-utils'
import type { Teaching } from '#/lib/types'
import { cn } from '#/lib/utils'

interface TeachingRowProps {
  teaching: Teaching
}

export function TeachingRow({ teaching }: TeachingRowProps) {
  const {
    currentTeaching,
    isPlaying,
    isLoading,
    loadingTeachingId,
    playTeaching,
  } = useAudioPlayer()

  const title = displayTitle(teaching)
  const isArabic = hasArabicTitle(teaching)
  const status = getMediaStatus(teaching.download_status)
  const date = formatPublishedDate(teaching.published_at)
  const size = formatFileSize(teaching.file_size)
  const isActive = currentTeaching?.id === teaching.id
  const isThisLoading = isLoading && loadingTeachingId === teaching.id
  const showPause = isActive && isPlaying && !isThisLoading

  const metaParts = [
    date,
    teaching.category?.name,
    size,
  ].filter(Boolean)

  return (
    <article
      className={cn(
        'feature-card flex items-center gap-3 rounded-xl border border-[var(--line)] p-4',
        isActive && 'border-[var(--primary)]/25 ring-1 ring-[var(--primary)]/10',
      )}
    >
      <div className="min-w-0 flex-1">
        <h3
          className={cn(
            'text-[0.95rem] leading-snug font-semibold text-[var(--ink)]',
            isArabic && 'font-arabic text-[1rem] leading-relaxed',
          )}
        >
          {title}
        </h3>
        {metaParts.length > 0 ? (
          <p className="mt-1 text-[0.78rem] text-[var(--ink-muted)]">
            {metaParts.join(' · ')}
          </p>
        ) : null}
        {!status.canPlay ? (
          <p
            className={cn(
              'mt-1.5 text-[0.78rem]',
              status.tone === 'pending'
                ? 'text-[var(--pending)]'
                : 'text-[var(--ink-muted)]',
            )}
          >
            {status.label}
          </p>
        ) : null}
      </div>

      <button
        type="button"
        disabled={!status.canPlay || isThisLoading}
        onClick={() => void playTeaching(teaching)}
        className={cn(
          'flex h-12 w-12 shrink-0 items-center justify-center rounded-full transition-colors',
          status.canPlay
            ? 'bg-[var(--primary)] text-white hover:bg-[var(--primary-deep)] disabled:opacity-60'
            : 'cursor-not-allowed bg-[var(--surface-muted)] text-[var(--ink-muted)]',
        )}
        aria-label={
          showPause ? `Pause ${title}` : status.canPlay ? `Écouter ${title}` : status.label
        }
      >
        {isThisLoading ? (
          <Loader2 className="h-5 w-5 animate-spin" aria-hidden />
        ) : showPause ? (
          <Pause className="h-5 w-5 fill-current" aria-hidden />
        ) : (
          <Play className="h-5 w-5 fill-current" aria-hidden />
        )}
      </button>
    </article>
  )
}
