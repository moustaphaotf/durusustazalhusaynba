import { createFileRoute } from '@tanstack/react-router'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Loader2 } from 'lucide-react'

import { AppHeader } from '#/components/AppHeader'
import { CategoryFilters } from '#/components/CategoryFilters'
import { ResumeCard } from '#/components/ResumeCard'
import { StickyPlayer } from '#/components/StickyPlayer'
import { TeachingRow } from '#/components/TeachingRow'
import { useAudioPlayer } from '#/contexts/AudioPlayerContext'
import { fetchCategories, fetchTeachingsPage } from '#/lib/api'
import { reportCaughtError } from '#/lib/error-reporting'
import {
  buildCategoryFilters,
  filterByCategory,
  filterPlayableTeachings,
  type CategoryFilterValue,
} from '#/lib/teaching-utils'
import type { Category, Teaching } from '#/lib/types'

export const Route = createFileRoute('/')({ component: Home })

const HOME_DISPLAY_COUNT = 10

function Home() {
  const { resumeTeachingId } = useAudioPlayer()

  const [allTeachings, setAllTeachings] = useState<Teaching[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [nextPage, setNextPage] = useState<string | null>(null)
  const [totalCount, setTotalCount] = useState<number | null>(null)
  const [categoryFilter, setCategoryFilter] =
    useState<CategoryFilterValue>('all')
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showAll, setShowAll] = useState(false)

  const loadInitial = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [teachingsPage, cats] = await Promise.all([
        fetchTeachingsPage(),
        fetchCategories(),
      ])
      setAllTeachings(teachingsPage.results)
      setNextPage(teachingsPage.next)
      setTotalCount(teachingsPage.count)
      setCategories(cats)
    } catch (err) {
      reportCaughtError(err, 'Home.loadInitial')
      setError('Impossible de charger les enseignements. Vérifiez votre connexion.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadInitial()
  }, [loadInitial])

  const playable = useMemo(
    () => filterPlayableTeachings(allTeachings),
    [allTeachings],
  )

  const categoryOptions = useMemo(
    () => buildCategoryFilters(playable, categories),
    [playable, categories],
  )

  const filtered = useMemo(
    () => filterByCategory(playable, categoryFilter),
    [playable, categoryFilter],
  )

  const resumeTeaching = useMemo(() => {
    if (!resumeTeachingId) return null
    return playable.find((t) => t.id === resumeTeachingId) ?? null
  }, [playable, resumeTeachingId])

  const displayed = showAll ? filtered : filtered.slice(0, HOME_DISPLAY_COUNT)
  const hasMoreInList = !showAll && filtered.length > HOME_DISPLAY_COUNT
  const canLoadMorePages = Boolean(nextPage)

  const loadMorePages = async () => {
    if (!nextPage || loadingMore) return
    setLoadingMore(true)
    try {
      const page = await fetchTeachingsPage(nextPage)
      setAllTeachings((prev) => [...prev, ...page.results])
      setNextPage(page.next)
      setTotalCount(page.count)
    } catch {
      setError('Impossible de charger plus d\'enseignements.')
    } finally {
      setLoadingMore(false)
    }
  }

  return (
    <div className="page-wrap pb-36">
      <AppHeader />

      {loading ? (
        <div className="flex items-center justify-center gap-3 py-16 text-[var(--ink-soft)]">
          <Loader2 className="h-6 w-6 animate-spin" aria-hidden />
          <span>Chargement des enseignements…</span>
        </div>
      ) : error ? (
        <div
          className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-6 text-center"
          role="alert"
        >
          <p className="text-[var(--ink-soft)]">{error}</p>
          <button
            type="button"
            onClick={() => void loadInitial()}
            className="btn-secondary mt-4 rounded-[10px] px-5 py-2.5 text-[0.9rem] font-semibold"
          >
            Réessayer
          </button>
        </div>
      ) : (
        <>
          {resumeTeaching ? <ResumeCard teaching={resumeTeaching} /> : null}

          <section aria-label="Liste des enseignements">
            <div className="mb-4 flex items-baseline justify-between gap-3">
              <h2 className="display-title text-[1.2rem] font-bold text-[var(--ink)]">
                Enseignements
              </h2>
              {totalCount != null ? (
                <span className="text-[0.75rem] text-[var(--ink-muted)]">
                  {playable.length} audio{playable.length > 1 ? 's' : ''}
                  {totalCount > playable.length ? ` sur ${totalCount}` : ''}
                </span>
              ) : null}
            </div>

            <CategoryFilters
              options={categoryOptions}
              value={categoryFilter}
              onChange={(v) => {
                setCategoryFilter(v as CategoryFilterValue)
                setShowAll(false)
              }}
            />

            {filtered.length === 0 ? (
              <div className="rounded-xl border border-dashed border-[var(--line)] p-8 text-center">
                <p className="text-[var(--ink-soft)]">
                  {categoryFilter === 'all'
                    ? 'Aucun enseignement audio disponible pour le moment.'
                    : 'Aucun enseignement dans cette catégorie.'}
                </p>
              </div>
            ) : (
              <ul className="flex flex-col gap-3">
                {displayed.map((teaching) => (
                  <li key={teaching.id}>
                    <TeachingRow teaching={teaching} />
                  </li>
                ))}
              </ul>
            )}

            <div className="mt-6 flex flex-col items-center gap-3">
              {hasMoreInList ? (
                <button
                  type="button"
                  onClick={() => setShowAll(true)}
                  className="btn-secondary min-h-11 rounded-[10px] px-6 py-2.5 text-[0.9rem] font-semibold"
                >
                  Voir les {filtered.length - HOME_DISPLAY_COUNT} suivants
                </button>
              ) : null}
              {showAll && canLoadMorePages ? (
                <button
                  type="button"
                  onClick={() => void loadMorePages()}
                  disabled={loadingMore}
                  className="btn-secondary inline-flex min-h-11 items-center gap-2 rounded-[10px] px-6 py-2.5 text-[0.9rem] font-semibold disabled:opacity-70"
                >
                  {loadingMore ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Chargement…
                    </>
                  ) : (
                    'Afficher plus'
                  )}
                </button>
              ) : null}
            </div>
          </section>
        </>
      )}

      <StickyPlayer />
    </div>
  )
}
