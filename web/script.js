import { supabase } from './supabase.js';

async function loadReviews() {
  const list = document.getElementById('review-list');
  const { data, error } = await supabase
    .from('vw_flat_movie_reviews')
    .select('*')
    .limit(10);

  if (error) {
    console.error('Error loading reviews', error);
    list.textContent = 'Failed to load reviews';
    return;
  }

  data.forEach((movie) => {
    const div = document.createElement('div');
    div.className = 'review';

    const img = document.createElement('img');
    img.className = 'poster';
    if (movie.poster_path) {
      img.src = `https://image.tmdb.org/t/p/w342/${movie.poster_path}`;
      img.alt = movie.title || '';
    }

    const content = document.createElement('div');
    content.className = 'review-content';
    const title = movie.title || movie.blog_title || 'Untitled';
    const reviewText = movie.short_review || movie.review || '';
    content.innerHTML = `<h4>${title}</h4><p>${reviewText}</p>`;

    div.appendChild(img);
    div.appendChild(content);
    list.appendChild(div);
  });
}

document.addEventListener('DOMContentLoaded', loadReviews);
