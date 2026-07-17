export function AppHeader() {
  return (
    <header className="pt-8 pb-6">
      <p className="island-kicker text-[var(--kicker)]">Enseignements en pulaar</p>
      <h1 className="display-title mt-2 text-[clamp(1.35rem,5vw,2rem)] leading-tight font-bold text-[var(--ink)]">
        Durus Oustaz Alhousseyni Bah
      </h1>
      <p className="mt-1 text-[0.92rem] font-medium text-[var(--ink-soft)]">Dakar</p>
      <p className="mt-4 max-w-prose text-[1rem] leading-relaxed text-[var(--ink-soft)]">
        Écoutez les enseignements islamiques audio du Oustaz, simplement sur votre
        téléphone.
      </p>
    </header>
  )
}
