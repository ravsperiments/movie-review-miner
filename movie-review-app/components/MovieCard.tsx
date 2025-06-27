import React from 'react';
import { View, Text, Image } from 'react-native';
import { Movie } from '../types';

interface Props {
  movie: Movie;
}

export default function MovieCard({ movie }: Props) {
  return (
    <View className="flex-row bg-white rounded-lg m-2 overflow-hidden">
      <Image
        source={{ uri: movie.poster_url }}
        style={{ width: 80, height: 120 }}
        resizeMode="cover"
      />
      <View className="flex-1 p-2">
        <Text className="font-bold text-lg">{movie.title}</Text>
        <Text className="text-sm text-gray-600">{movie.language}</Text>
        <Text className="text-sm mt-2">{movie.review_summary}</Text>
      </View>
    </View>
  );
}
