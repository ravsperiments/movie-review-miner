import { supabase } from './supabase';
import { Movie } from '../types';

export async function fetchMovies(query: string = ''): Promise<Movie[]> {
  let request = supabase
    .from('movies')
    .select('*')
    .order('created_at', { ascending: false });

  if (query) {
    request = request.textSearch('title', query, { type: 'websearch' });
  }

  const { data, error } = await request;
  if (error) {
    console.error('Error fetching movies', error);
    return [];
  }
  return (data as Movie[]) || [];
}

export async function fetchRareGem(): Promise<Movie | null> {
  const { data, error } = await supabase
    .from('movies')
    .select('*')
    .lt('popularity', 30)
    .gt('sentiment_score', 0.8)
    .order('created_at', { ascending: false })
    .limit(10);

  if (error) {
    console.error('Error fetching rare gem', error);
    return null;
  }

  if (data && data.length > 0) {
    const randomIndex = Math.floor(Math.random() * data.length);
    return data[randomIndex] as Movie;
  }
  return null;
}
