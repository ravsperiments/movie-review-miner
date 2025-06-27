import React, { useEffect, useState, useCallback } from 'react';
import { View, FlatList, RefreshControl } from 'react-native';
import SearchBar from '../components/SearchBar';
import MovieCard from '../components/MovieCard';
import SuggestionCard from '../components/SuggestionCard';
import { fetchMovies, fetchRareGem } from '../lib/api';
import { Movie } from '../types';

export default function HomeScreen() {
  const [movies, setMovies] = useState<Movie[]>([]);
  const [rareGem, setRareGem] = useState<Movie | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = async (query = '') => {
    setRefreshing(true);
    const result = await fetchMovies(query);
    setMovies(result);
    const gem = await fetchRareGem();
    setRareGem(gem);
    setRefreshing(false);
  };

  useEffect(() => {
    load();
  }, []);

  const handleSearch = (text: string) => {
    load(text);
  };

  const onRefresh = useCallback(() => {
    load();
  }, []);

  return (
    <View className="flex-1 bg-gray-100">
      <SearchBar onSearch={handleSearch} />
      <FlatList
        data={movies}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => <MovieCard movie={item} />}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
      />
      <SuggestionCard movie={rareGem} />
    </View>
  );
}
