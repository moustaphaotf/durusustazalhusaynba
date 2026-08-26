import { useEffect } from 'react'

import { installGlobalErrorHandlers } from '#/lib/error-reporting'

export function ErrorReporter() {
  useEffect(() => {
    installGlobalErrorHandlers()
  }, [])

  return null
}
