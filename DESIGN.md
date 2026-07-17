# Design System — Durus Oustaz Alhousseyni Bah, Dakar

## Product Context
- **What this is:** App web mobile-first pour écouter les enseignements islamiques audio en pulaar du Oustaz Alhousseyni Bah (Dakar), sans passer par Telegram.
- **Who it's for:** Auditeurs pulaarophones (Dakar / Afrique de l'Ouest) qui veulent lancer, mettre en pause et reprendre un enseignement comme dans une app podcast.
- **Space/industry:** Écoute audio / savoir religieux — croisement entre app podcast et bibliothèque d'un corpus unique.
- **Project type:** Content web app (accueil + reprise + liste filtrable + lecteur sticky), pas un site marketing ni un dashboard.
- **The one thing to remember:** « Écouter le savoir en pulaar, simplement, sur mon téléphone. » Proximité, accessibilité, zéro friction. Chaque décision design sert cette phrase.

## Aesthetic Direction
- **Direction:** Sahel calme — chaleur digne + focus sur l'écoute.
- **Decoration level:** intentionnelle — grain/texture papier subtil, rien de tape-à-l'œil, pensé pour mobile.
- **Mood:** Chaleureuse, humaine, respectueuse du savoir. Ni bibliothèque académique froide, ni app tech générique. Ancrage culturel ouest-africain assumé (indigo textile peul).
- **Reference sites:** Direction issue de /office-hours + expertise design (pas de recherche visuelle externe).

## Typography
- **Display/Hero (wordmark & titres):** Fraunces — serif chaud, donne de la dignité à « Durus » sans raideur.
- **Body / UI / Labels:** Source Sans 3 — humaniste, très lisible sur mobile.
- **Arabe (title_ar):** Noto Naskh Arabic — naskh lisible, harmonisé au corps. Alternative traditionnelle : Amiri.
- **Contrainte pulaar (À VÉRIFIER à l'implémentation):** le pulaar utilise ɓ ɗ ƴ ŋ. Confirmer que Fraunces + Source Sans 3 rendent ces glyphes. Repli garanti si manquants : Gentium Plus (display) + Andika ou Noto Sans (corps) — fonts SIL conçues pour les langues africaines.
- **Loading:** Google Fonts via `<link>` — `Fraunces:opsz,wght@9..144,500;9..144,700`, `Source+Sans+3:wght@400;500;600;700`, `Noto+Naskh+Arabic:wght@400;600`.
- **Scale (mobile-first):**
  - Wordmark / hero: 1.35–2rem (Fraunces 700)
  - Titre section: 1.2rem (Fraunces 700)
  - Titre carte / row: 0.92–1.05rem (Source Sans 3 600)
  - Corps: 1rem / 16px (Source Sans 3 400)
  - Métadonnées / sous-titres: 0.72–0.85rem (Source Sans 3 400, couleur atténuée)
  - Kicker / label: 0.65–0.7rem, uppercase, letter-spacing 0.14–0.16em, 700

## Color
- **Approach:** chaude, ancrée indigo — s'éloigne volontairement du vert/or « app islamique générique ».
- **Primary (marque):** `#2B3A67` indigo profond (dark: `#8FA0DA`) — héritage textile peul, confiance, dignité. Usage : wordmark, boutons secondaires, icône play de liste, accents de marque.
- **Accent (action ÉCOUTER / lancer):** `#C05D3C` terracotta (dark: `#DB7A52`) — le bouton qui invite à écouter, soleil du Sahel. Usage : bouton lecture principal, bouton « Reprendre », progression du lecteur. À réserver aux actions d'écoute.
- **Support (rare):** `#4E6B57` vert sauge (dark: `#6E8C77`) — clin d'œil discret, jamais un vert criard.
- **Neutrals (chauds, jamais froids):**
  - Fond: `#F7F1E7` sable papier (dark: `#171310` encre chaude)
  - Surface / cartes: `#FFFDF9` (dark: `#241D18`)
  - Texte encre: `#241C15` noir chaud (dark: `#F0E7D8` crème)
  - Texte atténué: `#6B5D4F` taupe (dark: `#B5A794`)
  - Ligne / bordure: `rgba(36,28,21,0.12)` (dark: `rgba(240,231,216,0.12)`)
- **Semantic:** succès `#3E7A5E` · attente/pending `#C9932E` ocre · erreur `#B23A34` · info = indigo primary.
  - **Règle états média:** `failed` et `skipped` restent neutres, pas alarmants (ce n'est pas la faute de l'auditeur). Utiliser le ton atténué, pas le rouge vif.
- **Dark mode:** redessiner les surfaces en encre chaude (pas de gris froid), réduire légèrement la saturation des accents, garder le contraste texte ≥ AA.

## Spacing
- **Base unit:** 4px.
- **Density:** confortable — usage à une main, rythme vertical généreux.
- **Cibles tactiles:** minimum 44–48px sur toute action (play, pills, boutons, rows).
- **Scale:** 2xs(2) xs(4) sm(8) md(16) lg(24) xl(32) 2xl(48) 3xl(64).

## Layout
- **Approach:** mobile-first, une seule colonne, actions dans la zone du pouce.
- **Grid:** colonne unique pleine largeur sur mobile ; desktop = même colonne centrée, max-width ~720px de contenu (page enveloppe ~1080px).
- **Structure V1 (route `/`):** header marque → bloc « Reprendre l'écoute » (traité comme un now-playing, presque une pochette) → filtres catégorie en pills → liste d'enseignements larges et tapables → lecteur sticky global en bas (mini → plein écran).
- **Max content width:** 720px (contenu), 1080px (page).
- **Border radius:** cartes 12–16px · lecteur 20px · boutons 10px · pills / play-icon rond 999px.

## Motion
- **Approach:** intentionnelle, sobre — respect du calme et de la perf mobile.
- **Easing:** enter(ease-out) · exit(ease-in) · move(ease-in-out).
- **Duration:** micro(50–100ms) · short(150–250ms) · medium(250–400ms) · long(400–700ms).
- **Signatures:** slide-up du lecteur sticky, transition play/pause douce, barre de progression animée, entrée douce (rise-in) de la carte « Reprendre ». Rien de clinquant.

## Deliberate Risks (là où Durus gagne son visage)
1. **Indigo + terracotta + sable** au lieu du vert/or islamique attendu — digne, ancré, mémorable, non générique.
2. **Texture papier + wordmark serif (Fraunces)** — âme et dignité des « durus » (leçons), chaleur = proximité.
3. **Carte « Reprendre l'écoute » traitée comme un now-playing** (pas un lien utilitaire) — frappe le wow n°1 : reprendre là où on s'est arrêté.

## Safe Choices (attendus d'une app d'écoute)
- Lecteur sticky bas, mini → plein écran (familiarité podcast).
- Filtres catégorie en pills + lignes de liste larges et tapables.
- Bloc « Reprendre » proéminent + play/pause/progression clairs.

## Decisions Log
| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-07-17 | Système design initial « Sahel calme » créé | /design-consultation, à partir de l'office-hours Durus. Mémorable = « écouter le savoir en pulaar, simplement, sur mon téléphone ». Direction libre (scaffold teal abandonné). |
| 2026-07-17 | Palette indigo/terracotta/sable au lieu du vert/or | Éviter le générique « app islamique », ancrer dans l'identité textile peul + chaleur du Sahel. |
| 2026-07-17 | Fraunces + Source Sans 3 + Noto Naskh Arabic | Dignité scolaire + lisibilité mobile ; repli SIL (Gentium/Andika) si glyphes pulaar ɓɗƴŋ manquants. |
