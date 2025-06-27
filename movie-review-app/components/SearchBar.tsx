import React, { useState } from 'react';
import { View, TextInput } from 'react-native';

interface Props {
  onSearch: (text: string) => void;
}

export default function SearchBar({ onSearch }: Props) {
  const [query, setQuery] = useState('');

  const handleChange = (text: string) => {
    setQuery(text);
    onSearch(text);
  };

  return (
    <View className="p-2">
      <TextInput
        placeholder="Search movies..."
        value={query}
        onChangeText={handleChange}
        style={{
          backgroundColor: '#fff',
          paddingHorizontal: 12,
          paddingVertical: 8,
          borderRadius: 8,
        }}
      />
    </View>
  );
}
