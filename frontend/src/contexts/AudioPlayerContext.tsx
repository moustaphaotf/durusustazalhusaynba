import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'

import {
  ApiError,
  fetchTeachingMedia,
  getConflictStatus,
  isMediaConflict,
} from '#/lib/api'
import {
  computeResumeSeek,
  getMediaStatus,
} from '#/lib/teaching-utils'
import {
  getSavedPosition,
  loadResumeStorage,
  updatePosition,
} from '#/lib/resume-storage'
import type { Teaching } from '#/lib/types'

const LONG_PAUSE_MS = 5 * 60 * 1000
const TTL_REFRESH_THRESHOLD_SEC = 60
const POSITION_SAVE_INTERVAL_MS = 5000

interface SignedUrlState {
  url: string
  expiresAt: number
  obtainedAt: number
}

interface AudioPlayerContextValue {
  currentTeaching: Teaching | null
  isPlaying: boolean
  isLoading: boolean
  isExpanded: boolean
  currentTime: number
  duration: number
  error: string | null
  playTeaching: (teaching: Teaching, options?: { fromStart?: boolean }) => Promise<void>
  togglePlayPause: () => Promise<void>
  seek: (time: number) => void
  setExpanded: (expanded: boolean) => void
  loadingTeachingId: number | null
  resumeTeachingId: number | null
  resumePosition: number | null
}

const AudioPlayerContext = createContext<AudioPlayerContextValue | null>(null)

function formatTime(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return '0:00'
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

export function AudioPlayerProvider({ children }: { children: ReactNode }) {
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const signedUrlRef = useRef<SignedUrlState | null>(null)
  const lastPlaybackAtRef = useRef<number>(Date.now())
  const retryRef = useRef(false)
  const saveIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const currentTeachingRef = useRef<Teaching | null>(null)

  const [currentTeaching, setCurrentTeaching] = useState<Teaching | null>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [isExpanded, setIsExpanded] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [loadingTeachingId, setLoadingTeachingId] = useState<number | null>(null)
  const [resumeSnapshot, setResumeSnapshot] = useState(loadResumeStorage)

  useEffect(() => {
    currentTeachingRef.current = currentTeaching
  }, [currentTeaching])

  useEffect(() => {
    const audio = new Audio()
    audio.preload = 'metadata'
    audioRef.current = audio

    const onTimeUpdate = () => setCurrentTime(audio.currentTime)
    const onDurationChange = () => setDuration(audio.duration || 0)
    const onPlay = () => {
      setIsPlaying(true)
      lastPlaybackAtRef.current = Date.now()
    }
    const onPause = () => {
      setIsPlaying(false)
      const teaching = currentTeachingRef.current
      if (teaching && audio.currentTime > 0) {
        const next = updatePosition(teaching.id, audio.currentTime)
        setResumeSnapshot(next)
      }
    }
    const onEnded = () => {
      setIsPlaying(false)
      const teaching = currentTeachingRef.current
      if (teaching) {
        const next = updatePosition(teaching.id, 0)
        setResumeSnapshot(next)
      }
    }
    const onError = async () => {
      const teaching = currentTeachingRef.current
      if (!teaching || retryRef.current) {
        setError('Impossible de lire cet audio pour le moment.')
        setIsPlaying(false)
        return
      }
      retryRef.current = true
      try {
        const data = await fetchTeachingMedia(teaching.id)
        const obtainedAt = Date.now()
        signedUrlRef.current = {
          url: data.url,
          obtainedAt,
          expiresAt: obtainedAt + data.expires_in * 1000,
        }
        if (audioRef.current) {
          audioRef.current.src = data.url
          const saved = getSavedPosition(teaching.id)
          if (saved != null) {
            const seekTo = computeResumeSeek(saved, audioRef.current.duration)
            if (seekTo != null) audioRef.current.currentTime = seekTo
          }
          await audioRef.current.play()
        }
        setError(null)
      } catch {
        setError('Impossible de lire cet audio pour le moment.')
        setIsPlaying(false)
      }
    }

    audio.addEventListener('timeupdate', onTimeUpdate)
    audio.addEventListener('durationchange', onDurationChange)
    audio.addEventListener('play', onPlay)
    audio.addEventListener('pause', onPause)
    audio.addEventListener('ended', onEnded)
    audio.addEventListener('error', onError)

    const onPageHide = () => {
      const teaching = currentTeachingRef.current
      if (teaching && audio.currentTime > 0) {
        updatePosition(teaching.id, audio.currentTime)
      }
    }
    window.addEventListener('pagehide', onPageHide)

    return () => {
      audio.pause()
      audio.removeEventListener('timeupdate', onTimeUpdate)
      audio.removeEventListener('durationchange', onDurationChange)
      audio.removeEventListener('play', onPlay)
      audio.removeEventListener('pause', onPause)
      audio.removeEventListener('ended', onEnded)
      audio.removeEventListener('error', onError)
      window.removeEventListener('pagehide', onPageHide)
      audioRef.current = null
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (isPlaying && currentTeaching) {
      saveIntervalRef.current = setInterval(() => {
        const audio = audioRef.current
        if (audio && audio.currentTime > 0) {
          const next = updatePosition(currentTeaching.id, audio.currentTime)
          setResumeSnapshot(next)
        }
      }, POSITION_SAVE_INTERVAL_MS)
    } else if (saveIntervalRef.current) {
      clearInterval(saveIntervalRef.current)
      saveIntervalRef.current = null
    }
    return () => {
      if (saveIntervalRef.current) clearInterval(saveIntervalRef.current)
    }
  }, [isPlaying, currentTeaching])

  const remainingTtl = useCallback(() => {
    const signed = signedUrlRef.current
    if (!signed) return 0
    return Math.max(0, (signed.expiresAt - Date.now()) / 1000)
  }, [])

  const needsUrlRefresh = useCallback(() => {
    const sincePlayback = Date.now() - lastPlaybackAtRef.current
    const longPause = sincePlayback > LONG_PAUSE_MS
    return longPause && remainingTtl() < TTL_REFRESH_THRESHOLD_SEC
  }, [remainingTtl])

  const loadSignedUrl = useCallback(
    async (teachingId: number, force = false) => {
      if (
        !force &&
        signedUrlRef.current &&
        currentTeaching?.id === teachingId &&
        remainingTtl() > TTL_REFRESH_THRESHOLD_SEC
      ) {
        return signedUrlRef.current.url
      }

      const data = await fetchTeachingMedia(teachingId)
      const obtainedAt = Date.now()
      signedUrlRef.current = {
        url: data.url,
        obtainedAt,
        expiresAt: obtainedAt + data.expires_in * 1000,
      }
      return data.url
    },
    [currentTeaching?.id, remainingTtl],
  )

  const playTeaching = useCallback(
    async (teaching: Teaching, options?: { fromStart?: boolean }) => {
      const status = getMediaStatus(teaching.download_status)
      if (!status.canPlay) return

      const audio = audioRef.current
      if (!audio) return

      setError(null)
      retryRef.current = false

      if (currentTeaching?.id === teaching.id && signedUrlRef.current) {
        if (needsUrlRefresh()) {
          setIsLoading(true)
          try {
            const url = await loadSignedUrl(teaching.id, true)
            audio.src = url
          } finally {
            setIsLoading(false)
          }
        }
        if (audio.paused) {
          await audio.play()
        } else {
          audio.pause()
        }
        return
      }

      setLoadingTeachingId(teaching.id)
      setIsLoading(true)

      try {
        const url = await loadSignedUrl(teaching.id, true)
        audio.src = url
        setCurrentTeaching(teaching)
        setIsExpanded(false)

        await new Promise<void>((resolve, reject) => {
          const onReady = () => {
            audio.removeEventListener('loadedmetadata', onReady)
            audio.removeEventListener('error', onFail)
            resolve()
          }
          const onFail = () => {
            audio.removeEventListener('loadedmetadata', onReady)
            audio.removeEventListener('error', onFail)
            reject(new Error('metadata load failed'))
          }
          audio.addEventListener('loadedmetadata', onReady)
          audio.addEventListener('error', onFail)
          audio.load()
        })

        if (!options?.fromStart) {
          const saved = getSavedPosition(teaching.id)
          if (saved != null) {
            const seekTo = computeResumeSeek(saved, audio.duration)
            if (seekTo != null) audio.currentTime = seekTo
          }
        } else {
          audio.currentTime = 0
        }

        await audio.play()
        const next = updatePosition(teaching.id, audio.currentTime)
        setResumeSnapshot(next)
      } catch (err) {
        if (isMediaConflict(err)) {
          const conflictStatus = getConflictStatus(err as ApiError)
          if (conflictStatus) {
            setCurrentTeaching({ ...teaching, download_status: conflictStatus })
          }
          setError(getMediaStatus(conflictStatus ?? teaching.download_status).label)
        } else {
          setError('Impossible de charger cet audio.')
        }
      } finally {
        setIsLoading(false)
        setLoadingTeachingId(null)
      }
    },
    [currentTeaching?.id, loadSignedUrl, needsUrlRefresh],
  )

  const togglePlayPause = useCallback(async () => {
    if (!currentTeaching) return
    await playTeaching(currentTeaching)
  }, [currentTeaching, playTeaching])

  const seek = useCallback((time: number) => {
    const audio = audioRef.current
    if (!audio) return
    audio.currentTime = time
    setCurrentTime(time)
  }, [])

  const resumeTeachingId = resumeSnapshot.lastTeachingId
  const resumePosition = resumeTeachingId
    ? (resumeSnapshot.positions[String(resumeTeachingId)]?.time ?? null)
    : null

  const value = useMemo<AudioPlayerContextValue>(
    () => ({
      currentTeaching,
      isPlaying,
      isLoading,
      isExpanded,
      currentTime,
      duration,
      error,
      playTeaching,
      togglePlayPause,
      seek,
      setExpanded: setIsExpanded,
      loadingTeachingId,
      resumeTeachingId,
      resumePosition,
    }),
    [
      currentTeaching,
      isPlaying,
      isLoading,
      isExpanded,
      currentTime,
      duration,
      error,
      playTeaching,
      togglePlayPause,
      seek,
      loadingTeachingId,
      resumeTeachingId,
      resumePosition,
    ],
  )

  return (
    <AudioPlayerContext.Provider value={value}>
      {children}
    </AudioPlayerContext.Provider>
  )
}

export function useAudioPlayer() {
  const ctx = useContext(AudioPlayerContext)
  if (!ctx) {
    throw new Error('useAudioPlayer must be used within AudioPlayerProvider')
  }
  return ctx
}

export { formatTime }
