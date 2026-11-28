import { useEffect, useState } from 'react';
import { Pressable, StyleSheet, Text, TextInput, useColorScheme, View } from 'react-native';
import { useAuth } from '@/authorization/authorization-login';
import { Colors } from '@/constants/theme';
import { usePermissions } from '@/hooks/use-permissions';
import { read, create, update, del } from '../api/fetch-wrapper';

export type UserReview = {
  ReviewID: number;
  GameID: number;
  Review: string;
  ReviewDate: string;
  UserID: number;
};

export default function ReviewInput({ gameName, gameID }: {
  gameName: string;
  gameID: number;
}) {
  const [reviews, setReviews] = useState<UserReview[]>([]);
  const [draft, setDraft] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [editingReviewID, setEditingReviewID] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);

  const { canAddReview } = usePermissions();
  const { userID } = useAuth();
  const colorScheme = useColorScheme();
  const colors = colorScheme === 'dark' ? Colors.dark : Colors.light;

  const fetchReviews = async () => {
    if (userID === null || gameID == null) {
      return;
    }

    try {
      const reviewData = await read(
        `games/${gameID}/reviews/user?user_id=${userID}`
      );
      setReviews(reviewData);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  useEffect(() => {
    setReviews([]);
    setDraft('');
    setEditingReviewID(null);
    setError('');

    if (canAddReview && userID !== null && gameID != null) {
      fetchReviews();
    }
  }, [gameID, userID, canAddReview]);

  const submitReview = async () => {
    const text = draft.trim();
    if (!text) {
      setError('Please enter a review.');
      return;
    }
    if (!canAddReview || userID === null || gameID == null || loading) {
      return;
    }
    setError('');
    setLoading(true);
    try {
      if (editingReviewID !== null) {
        await update(`reviews/${editingReviewID}?user_id=${userID}`, {
          Review: text
        });
      } else {
        await create(`games/${gameID}/reviews?user_id=${userID}`, {
          Review: text
        });
      }
      setDraft('');
      setEditingReviewID(null);
      await fetchReviews();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };
  const editReview = (review: UserReview) => {
    setEditingReviewID(review.ReviewID);
    setDraft(review.Review);
    setError('');
  };
  const cancelEdit = () => {
    setEditingReviewID(null);
    setDraft('');
    setError('');
  };

  const deleteReview = async (reviewID: number) => {
    if (!canAddReview || userID === null || loading) {
      return;
    }
    setError('');
    setLoading(true);
    try {
      await del(`reviews/${reviewID}?user_id=${userID}`);
      if (editingReviewID === reviewID) {
        cancelEdit();
      }
      await fetchReviews();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={[styles.container, { backgroundColor: colors.backgroundElement }]}>
      {canAddReview && userID !== null ? (
        <View>
          <Text style={[styles.title, { color: colors.text }]}>
            Your Reviews
          </Text>

          {reviews.map((review) => (
            <View key={review.ReviewID} style={styles.review}>
              <Text style={{ color: colors.text }}>
                {review.Review}
              </Text>

              <Text style={[styles.reviewDate, { color: colors.textSecondary }]}>
                {review.ReviewDate?.slice(0, 10)}
              </Text>

              <View style={styles.buttonContainer}>
                <Pressable
                  style={styles.button}
                  onPress={() => editReview(review)}
                  disabled={loading}
                >
                  <Text style={styles.buttonText}>Edit</Text>
                </Pressable>

                <Pressable
                  style={[styles.button, styles.deleteButton]}
                  onPress={() => deleteReview(review.ReviewID)}
                  disabled={loading}
                >
                  <Text style={styles.buttonText}>Delete</Text>
                </Pressable>
              </View>
            </View>
          ))}

          <TextInput
            style={[styles.input, {
              color: colors.text,
              borderColor: colors.textSecondary
            }]}
            value={draft}
            onChangeText={setDraft}
            placeholder={`Review ${gameName}`}
            placeholderTextColor={colors.textSecondary}
            accessibilityLabel={`Review ${gameName}`}
            editable={!loading}
            multiline
          />

          <View style={styles.buttonContainer}>
            <Pressable
              style={styles.button}
              onPress={submitReview}
              accessibilityRole="button"
              disabled={loading}
            >
              <Text style={styles.buttonText}>
                {loading
                  ? 'Please wait...'
                  : editingReviewID !== null
                    ? 'Save Changes'
                    : 'Add Review'}
              </Text>
            </Pressable>

            {editingReviewID !== null && (
              <Pressable
                style={[styles.button, styles.cancelButton]}
                onPress={cancelEdit}
                disabled={loading}
              >
                <Text style={styles.buttonText}>Cancel</Text>
              </Pressable>
            )}
          </View>

          {error ? (
            <Text style={styles.error}>{error}</Text>
          ) : null}
        </View>
      ) : (
        <Text style={{ color: colors.textSecondary }}>
          Sign in to add a review.
        </Text>
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
  title: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 12,
  },
  review: {
    marginBottom: 12,
    padding: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#E5E5EA',
    gap: 6,
  },
  reviewDate: {
    fontSize: 12,
  },
  input: {
    borderWidth: 1,
    borderRadius: 6,
    padding: 8,
    minHeight: 80,
    textAlignVertical: 'top',
  },
  buttonContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  button: {
    alignSelf: 'flex-start',
    backgroundColor: Colors.tabs.background,
    borderRadius: 6,
    marginTop: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  deleteButton: {
    backgroundColor: '#BA191C',
  },
  cancelButton: {
    backgroundColor: '#666666',
  },
  buttonText: {
    color: '#FFFFFF',
    fontWeight: '600',
  },
  error: {
    marginTop: 8,
    color: '#BA191C',
  },
});