

// Pagination state
let currentPage = 1;
const pageSize = 10;

async function loadReviews(page = currentPage) {
  currentPage = page;
  const list = document.getElementById('review-list');
  list.textContent = 'Loading reviews...';

  let supabase;
  try {
    const module = await import('./supabase.js');
    supabase = module.supabase;
  } catch (err) {
    console.error('Error loading Supabase config', err);
    list.textContent = `Error initializing Supabase: ${err.message}`;
    return;
  }

  let data, error, count;
  try {
    const from = (currentPage - 1) * pageSize;
    const to = from + pageSize - 1;
    ({ data, error, count } = await supabase
      .from('vw_flat_movie_reviews')
      .select('*', { count: 'exact' })
      .order('created_at', { ascending: false })
      .range(from, to));
  } catch (err) {
    console.error('Unexpected error querying reviews', err);
    list.textContent = `Unexpected error querying reviews: ${err.message}`;
    return;
  }

  if (error) {
    console.error('Error loading reviews', error);
    list.textContent = `Failed to load reviews: ${error.message}`;
    return;
  }

  if (!data || data.length === 0) {
    list.textContent = 'No reviews found. Make sure the backend pipeline has run.';
    return;
  }

  list.textContent = '';
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
    const title = movie.title || movie.blog_title || 'Untitled';
    const reviewText = movie.short_review || movie.review || '';
    // Render title, language, sentiment, truncated review, and 'Read full' link
    const readLink = movie.link
      ? `<a href="${movie.link}" target="_blank" class="read-full">Read full</a>`
      : '';
    const language = movie.language || 'Unknown';
    const sentiment = movie.sentiment || 'Unknown';
    content.innerHTML =
      '<h3>' + title + '</h3>' +
      '<div class="review-meta">' +
        '<div><h4>Language:</h4><span>' + language + '</span></div>' +
        '<div><h4>Sentiment:</h4><span>' + sentiment + '</span></div>' +
      '</div>' +
      '<p>' + reviewText + '</p>' +
      readLink;

    div.appendChild(img);
    div.appendChild(content);
    list.appendChild(div);
  });

  function updatePagination(total) {
    const prevBtn = document.getElementById('prev-page');
    const nextBtn = document.getElementById('next-page');
    const info = document.getElementById('page-info');
    const totalPages = Math.ceil(total / pageSize) || 1;
    info.textContent = `Page ${currentPage} of ${totalPages}`;
    prevBtn.disabled = currentPage <= 1;
    nextBtn.disabled = currentPage >= totalPages;
  }
  updatePagination(count || 0);
}

document.addEventListener('DOMContentLoaded', () => {
  loadReviews();
  document.getElementById('prev-page').addEventListener('click', () => {
    if (currentPage > 1) loadReviews(currentPage - 1);
  });
  document.getElementById('next-page').addEventListener('click', () => {
    loadReviews(currentPage + 1);
  });
});
