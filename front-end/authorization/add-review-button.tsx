import React from 'react';
import { Alert, Button, View } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { usePermissions } from '@/hooks/use-permissions';

export function AddReviewButton() {
  const { canAddReview } = usePermissions();

  return (
    <View style={{ margin: 10 }}>
      {canAddReview ? (
        <Button
          title="Add Review"
          onPress={() => Alert.alert('Review added!')}
        />
      ) : (
        <ThemedText style={{ color: 'gray' }}>
          You do not have permission to add reviews.
        </ThemedText>
      )}
    </View>
  );
}
