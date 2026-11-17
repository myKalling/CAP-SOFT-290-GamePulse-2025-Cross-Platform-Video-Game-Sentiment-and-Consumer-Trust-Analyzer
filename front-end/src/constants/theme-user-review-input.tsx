import { useState } from 'react';
import { useColorScheme } from 'react-native';
import { Pressable, Text, TextInput, View } from 'react-native';

import { usePermissions } from '@/hooks/use-permissions';

export default function ReviewInput({ gameName }: { gameName: string }) {
  const [reviews, setReviews] = useState<string[]>([]);
  const [draft, setDraft] = useState<string>('');
  const [error, setError] = useState<string>('');
  const { canAddReview } = usePermissions();
  const colorScheme = useColorScheme();
  const ink = { color: colorScheme === 'dark' ? '#FFFFFF' : '#000000' };

  const submitReview = (): void => {
    const text = draft.trim();
    if (!text) {
      setError('Please enter a review.');
      return;
    }
    setError('');
    setReviews([...reviews, text]);
    setDraft('');
  };

  return (
    <View style={{ marginBottom: 8 }}>
      {reviews.map((review, index) => (
        <Text key={index} style={ink}>{`• ${review}`}</Text>
      ))}

      {canAddReview ? (
        <View>
          <TextInput
            style={[ink, { borderWidth: 1, padding: 6 }]}
            value={draft}
            onChangeText={setDraft}
            placeholder={`Review ${gameName}`}
          />
          <Pressable onPress={submitReview}>
            <Text style={ink}>Add Review</Text>
          </Pressable>
          <Text style={ink}>{error}</Text>
        </View>
      ) : (
        <Text style={{ color: 'gray' }}>Sign in to add a review.</Text>
      )}
    </View>
  );
}

