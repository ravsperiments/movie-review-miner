### 📋 tasks.md — Web Interface

####  Day 1: Supabase & Listings
- [x] Load Supabase keys from `.env` at runtime (no build step)
- [x] Query the `vw_flat_movie_reviews` view and render first batch of reviews on `index.html`

####  Day 2: Search Bar & Responsiveness
- [x] Add Algolia‑style search input with Material Symbols search icon
- [x] Style and position search input with inset icon and responsive padding
- [x] Implement mobile media‑queries: stack layout, resize fonts, scale images/cards

#### Day 3: Review Cards & Metadata
- [x] Fixed card dimensions: posters at 342×489 px with `object-fit: cover`, local placeholder
- [x] Truncate reviews to 4 lines with CSS clamp and add "Read full" links
- [x] Display movie title line (grey) above the main title with CSS class `.movie-title-grey`
- [x] Display metadata inline (Language, Sentiment) with equal flex cells and `<h4>` labels
- [x] Replace pagination with infinite scrolling (auto-load on scroll using IntersectionObserver)

#### Day 4: Impement Search & Refactor DB Calls 
