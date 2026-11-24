import { useState } from 'react';
import { Pressable, StyleSheet, Text, TextInput, useColorScheme, View } from 'react-native';

import { Colors } from '@/constants/theme';
import { usePermissions } from '@/hooks/use-permissions';

export default function ReviewInput({ gameName }: { gameName: string }) {
  const [reviews, setReviews] = useState<string[]>([]);
  const [draft, setDraft] = useState<string>('');
  const [error, setError] = useState<string>('');
  const { canAddReview } = usePermissions();
  const colorScheme = useColorScheme();
  const colors = colorScheme === 'dark' ? Colors.dark : Colors.light;

  const submitReview = (): void => {
    const text = draft.trim();
    if (!text) {
      setError('Please enter a review.');
      return;
    }
    setError('');
    setReviews((previous) => [...previous, text]);
    setDraft('');
  };

  return (
    <View style={[styles.container, { backgroundColor: colors.backgroundElement }]}>
      <Text style={[styles.notice, { color: colors.textSecondary }]}>
        Reviews are temporary and are not saved.
      </Text>
      {reviews.map((review, index) => (
        <Text key={index} style={[styles.review, { color: colors.text }]}>{`• ${review}`}</Text>
      ))}

      {canAddReview ? (
        <View>
          <TextInput
            style={[styles.input, { color: colors.text, borderColor: colors.textSecondary }]}
            value={draft}
            onChangeText={setDraft}
            placeholder={`Review ${gameName}`}
            placeholderTextColor={colors.textSecondary}
            accessibilityLabel={`Review ${gameName}`}
            multiline
          />
          <Pressable style={styles.button} onPress={submitReview} accessibilityRole="button">
            <Text style={styles.buttonText}>Add Review</Text>
          </Pressable>
          {error ? <Text style={[styles.error, { color: colors.text }]}>{error}</Text> : null}
        </View>
      ) : (
        <Text style={{ color: colors.textSecondary }}>Sign in to add a review.</Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginTop: 12,
    padding: 10,
    borderRadius: 8,
  },
  notice: {
    fontSize: 12,
    marginBottom: 8,
  },
  review: {
    marginBottom: 8,
  },
  input: {
    borderWidth: 1,
    borderRadius: 6,
    padding: 8,
    minHeight: 44,
  },
  button: {
    alignSelf: 'flex-start',
    backgroundColor: Colors.tabs.background,
    borderRadius: 6,
    marginTop: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  buttonText: {
    color: '#FFFFFF',
    fontWeight: '600',
  },
  error: {
    marginTop: 8,
  },
});
 