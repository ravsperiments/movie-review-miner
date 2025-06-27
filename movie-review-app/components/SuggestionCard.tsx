import React from 'react';
import { View, Text, Image } from 'react-native';
import { Movie } from '../types';

interface Props {
  movie: Movie | null;
}

export default function SuggestionCard({ movie }: Props) {
  if (!movie) return null;

  return (
    <View className="bg-indigo-100 rounded-lg m-2 p-2">
      <Text className="font-bold mb-1">Rare Gem</Text>
      <View className="flex-row items-center">
        <Image
          source={{ uri: movie.poster_url }}
          style={{ width: 60, height: 90, borderRadius: 4 }}
        />
        <View className="flex-1 ml-2">
          <Text className="font-semibold">{movie.title}</Text>
          <Text className="text-xs text-gray-600">{movie.language}</Text>
        </View>
      </View>
    </View>
  );
}
