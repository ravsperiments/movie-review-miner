### 📋 tasks.md — Web Interface

#### 🛠️ Milestone: Supabase & Listings
- [x] Load Supabase keys from `.env` at runtime (no build step)
- [x] Query the `vw_flat_movie_reviews` view and render first batch of reviews on `index.html`

#### 🔍 Milestone: Search Bar & Responsiveness
- [x] Add Algolia‑style search input with Material Symbols search icon
- [x] Style and position search input with inset icon and responsive padding
- [x] Implement mobile media‑queries: stack layout, resize fonts, scale images/cards

#### 💎 Milestone: Review Cards & Metadata
- [x] Fixed card dimensions: posters at 342×489 px with `object-fit: cover`, local placeholder
- [x] Truncate reviews to 4 lines with CSS clamp and add "Read full" links
- [x] Display metadata inline (Language, Sentiment) with equal flex cells and `<h4>` labels
