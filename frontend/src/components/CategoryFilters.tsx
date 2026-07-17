import type { CategoryFilterOption } from '#/lib/teaching-utils'
import { cn } from '#/lib/utils'

interface CategoryFiltersProps {
  options: CategoryFilterOption[]
  value: string
  onChange: (value: string) => void
}

export function CategoryFilters({
  options,
  value,
  onChange,
}: CategoryFiltersProps) {
  if (options.length === 0) return null

  return (
    <div
      className="mb-5 flex gap-2 overflow-x-auto pb-1 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
      role="tablist"
      aria-label="Filtrer par catégorie"
    >
      {options.map((option) => {
        const active = value === option.value
        return (
          <button
            key={option.value}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onChange(option.value)}
            className={cn(
              'shrink-0 rounded-full border px-4 py-2.5 text-[0.85rem] font-medium transition-colors',
              'min-h-11',
              active
                ? 'border-[var(--primary)] bg-[var(--primary)] text-white'
                : 'border-[var(--line)] bg-[var(--surface)] text-[var(--ink-soft)] hover:border-[var(--primary)]/30',
            )}
          >
            {option.label}
          </button>
        )
      })}
    </div>
  )
}
