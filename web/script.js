

// Pagination state
let currentPage = 1;
const pageSize = 2;
let totalPages = 1;

// Observer instance for infinite loading
let observer;

// Batch-loading control: auto-load up to this many pages per batch,
// then require manual click to continue.
const autoBatchSize = 5;
let pagesLoadedInBatch = 0;
let loadMoreBtn;


/**
 * Load a single page of reviews.
 * @param {number} page - page number to load
 */
async function loadReviews(page = currentPage) {
  // continue batch until threshold, batch reset on manual click
  currentPage = page;
  
  if (loadMoreBtn) {
    loadMoreBtn.hidden = true; // hide it unless we explicitly unhide later
  }

  const list = document.getElementById('review-list');
  if (page === 1) {
    list.textContent = 'Loading reviews...';
  }

  let supabase;
  try {
    const module = await import('./supabase.js');
    supabase = module.supabase;
  } catch (err) {
    console.error('Error loading Supabase config', err);
    if (page === 1) {
      list.textContent = `Error initializing Supabase: ${err.message}`;
    }
    return;
  }

  let data, error, count;
  try {
    const from = (currentPage - 1) * pageSize;
    const to = from + pageSize - 1;
    ({ data, error, count } = await supabase
      .from('vw_flat_movie_reviews')
      .select('*', { count: 'exact' })
      .range(from, to));
  } catch (err) {
    console.error('Unexpected error querying reviews', err);
    if (page === 1) {
      list.textContent = `Unexpected error querying reviews: ${err.message}`;
    }
    return;
  }

  if (error) {
    console.error('Error loading reviews', error);
    if (page === 1) {
      list.textContent = `Failed to load reviews: ${error.message}`;
    }
    return;
  }

  if (!data || data.length === 0) {
    if (page === 1) {
      list.textContent = 'No reviews found. Make sure the backend pipeline has run.';
    }
    return;
  }

  if (page === 1) {
    list.textContent = '';
  }
  data.forEach((movie) => {
    const div = document.createElement('div');
    div.className = 'review';

    const img = document.createElement('img');
    img.className = 'poster';
    if (movie.poster_path) {
      img.src = `https://image.tmdb.org/t/p/w342/${movie.poster_path}`;
      img.alt = movie.title || '';
    } else {
      // Local placeholder image
      img.src = new URL('./Noimage.svg.png', import.meta.url).href;
      img.alt = 'No image available';
    }

    const content = document.createElement('div');
    content.className = 'review-content';
    // movie title line (grey) above the main title

    console.log(movie.movie_title);
    if (movie.movie_title) {
      const mt = document.createElement('p');
      mt.className = 'movie-title-grey';
      mt.textContent = movie.movie_title;
      content.appendChild(mt);
    }
    const title = movie.blog_title || movie.movie_title || 'Untitled';
    const h3 = document.createElement('h3');
    h3.textContent = title;
    content.appendChild(h3);
    // metadata
    const meta = document.createElement('div');
    meta.className = 'review-meta';
    const language = movie.language || 'Unknown';
    const sentiment = movie.sentiment || 'Unknown';
    meta.innerHTML =
      '<div><h4>Language:</h4><span>' + language + '</span></div>' +
      '<div><h4>Sentiment:</h4><span>' + sentiment + '</span></div>';
    content.appendChild(meta);
    // review excerpt
    const p = document.createElement('p');
    p.textContent = movie.short_review || movie.review || '';
    content.appendChild(p);
    // read full link
    if (movie.link) {
      const a = document.createElement('a');
      a.href = movie.link;
      a.target = '_blank';
      a.className = 'read-full';
      a.textContent = 'Read full';
      content.appendChild(a);
    }

    div.appendChild(img);
    div.appendChild(content);
    list.appendChild(div);
  });

    // Update total pages for infinite scroll
    totalPages = Math.ceil((count || 0) / pageSize) || 1;

    // Debug log
    console.log({
      currentPage,
      totalPages,
      pagesLoadedInBatch,
      autoBatchSize,
      shouldPause: pagesLoadedInBatch >= autoBatchSize && currentPage < totalPages
    });

  // Track pages loaded in current batch and show manual trigger if needed
  pagesLoadedInBatch += 1;
  //const loadMoreBtn = document.getElementById('load-more');
  
  if (pagesLoadedInBatch >= autoBatchSize && currentPage < totalPages) {
    // stop automatic infinite-loading until user clicks to resume
    observer.disconnect();
    loadMoreBtn.hidden = false;
  }

}

document.addEventListener('DOMContentLoaded', () => {
  // Initial load + infinite observer
  pagesLoadedInBatch = 0;
  loadReviews();
  const sentinel = document.getElementById('scroll-sentinel');
  loadMoreBtn = document.getElementById('load-more');
  loadMoreBtn.hidden = true;
  loadMoreBtn.addEventListener('click', () => {
    // reset batch counter and load next page, then resume auto-loading
    pagesLoadedInBatch = 0;
    loadMoreBtn.hidden = true;
    if (currentPage < totalPages) loadReviews(currentPage + 1);
    observer.observe(sentinel);
  });
  observer = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting && currentPage < totalPages && pagesLoadedInBatch < autoBatchSize) {
      loadReviews(currentPage + 1);
    }
  }, { rootMargin: '200px' });
  observer.observe(sentinel);
});
