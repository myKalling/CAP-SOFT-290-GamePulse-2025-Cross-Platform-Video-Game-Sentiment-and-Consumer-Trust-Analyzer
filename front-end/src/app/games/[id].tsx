import { StyleSheet, Image, ScrollView } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams } from 'expo-router';
import { ThemedView } from '@/components/themed-view';
import { ThemedText } from '@/components/themed-text';
import ReviewInput from '@/constants/theme-user-review-input';
import { Game } from '@/components/gamecard';
import { useEffect, useState } from 'react';
import { read } from '../../api/fetch-wrapper';
import { Link } from 'expo-router';

export type Review = {
    ReviewID: number;
    GameID: number;
    Review: string;
    Sentiment: number;
    ReviewType: string;
};

export default function GameDetailsScreen() {
    const { id } = useLocalSearchParams<{ id: string }>();
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [game, setGame] = useState<Game | null>(null);
    const [HighReviews, setHighReviews] = useState<Review[]>([]);
    const [LowReviews, setLowReviews] = useState<Review[]>([]);

    useEffect(() => {
        const fetchGame = async () => {
            setLoading(true);
            try {
                const gameData = await read(`games/${id}`);
                const gameReviewsData = await read(`games/${id}/reviews`);
                setGame(gameData);
                setHighReviews(gameReviewsData.filter((review: Review) => review.ReviewType === 'High'));
                setLowReviews(gameReviewsData.filter((review: Review) => review.ReviewType === 'Low'));
            } catch (err) {
                setError(err instanceof Error ? err.message : String(err));
            } finally {
                setLoading(false);
            }
        };

        if (id) {
            fetchGame();
        } else {
            setLoading(false);
        }
    }, [id]);

    if (loading) {
        return (
            <ThemedView style={styles.container}>
                <ThemedText>Loading...</ThemedText>
            </ThemedView>
        );
    }

    if (error) {
        return (
            <ThemedView style={styles.container}>
                <ThemedText>{error}</ThemedText>
            </ThemedView>
        );
    }

    if (!game) {
        return (
            <ThemedView style={styles.container}>
                <ThemedText>Game not found.</ThemedText>
            </ThemedView>
        );
    }

    return (
        <ThemedView style={styles.container}>
            <SafeAreaView style={styles.safeArea}>
                <ScrollView contentContainerStyle={styles.scrollContent}>
                    <Link href="/games" asChild>
                        <ThemedText style={styles.backText}>Back to Games</ThemedText>
                    </Link>
                    {game.ImageURL != null && (
                        <Image source={{ uri: game.ImageURL }} style={styles.coverImage} />
                    )}
                    <ThemedView style={styles.content}>
                        <ThemedText type="title">
                            {game.Title}
                        </ThemedText>
                        {game.AverageSentiment != null && (
                            <ThemedText style={styles.sentimentText}>
                                Average Sentiment: {game.AverageSentiment.toFixed(2)}
                            </ThemedText>
                        )}
                        {game.Developers != null && (
                            <ThemedText style={styles.metaText} numberOfLines={1}>
                                Developers: <ThemedText style={styles.metaValue}>{game.Developers}</ThemedText>
                            </ThemedText>
                        )}
                        <ThemedText style={styles.priceText}>
                            Price:{" "}
                            {game.Price == null
                                ? "N/A"
                                : game.Price === 0
                                    ? "Free"
                                    : `$${game.Price.toFixed(2)}`}
                        </ThemedText>
                        {game.Genres != null && (
                            <ThemedText style={styles.genresText} numberOfLines={2}>
                                Genres: {game.Genres}
                            </ThemedText>
                        )}
                        <ReviewInput gameName={game.Title} />
                    </ThemedView>
                    <ThemedView style={styles.reviewsContainer}>
                        <ThemedText type="subtitle" style={styles.reviewsHeader}>
                            High Reviews
                        </ThemedText>
                        <ThemedView style={styles.highReviewsContainer}>
                            {HighReviews.map((review) => (
                                <ThemedView key={review.ReviewID} style={styles.reviewCard}>
                                    <ThemedText style={styles.highReviewSentimentText}>
                                        Sentiment Score: {review.Sentiment}
                                    </ThemedText>
                                    <ThemedText>{review.Review}</ThemedText>
                                </ThemedView>
                            ))}
                        </ThemedView>
                        <ThemedText type="subtitle" style={styles.reviewsHeader}>
                            Low Reviews
                        </ThemedText>
                        <ThemedView style={styles.lowReviewsContainer}>
                            {LowReviews.map((review) => (
                                <ThemedView key={review.ReviewID} style={styles.reviewCard}>
                                    <ThemedText style={styles.lowReviewSentimentText}>
                                        Sentiment Score: {review.Sentiment}
                                    </ThemedText>
                                    <ThemedText>{review.Review}</ThemedText>
                                </ThemedView>
                            ))}
                        </ThemedView>
                    </ThemedView>
                </ScrollView>
            </SafeAreaView>
        </ThemedView>
    );
}

const styles = StyleSheet.create({
    safeArea: {
        flex: 1,
        maxWidth: 1200,
        width: '100%',
    },
    scrollContent: {
        padding: 16,
        paddingBottom: 32,
        gap: 16,
    },
    backText: {
        color: '#BA191C',
        fontSize: 16,
        fontWeight: '500',
    },
    highReviewsContainer: {
        gap: 12,
    },
    lowReviewsContainer: {
        gap: 12,
    },
    reviewCard: {
        padding: 16,
        gap: 10,
        borderRadius: 14,
        borderWidth: 1,
        borderColor: '#E5E5EA',
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.08,
        shadowRadius: 4,
        elevation: 3,
    },
    highReviewsText: {
        fontSize: 16,
        fontWeight: 'bold',
    },
    highReviewSentimentText: {
        fontSize: 14,
        color: '#16A34A',
    },
    lowReviewsText: {
        fontSize: 16,
        fontWeight: 'bold',
    },
    lowReviewSentimentText: {
        fontSize: 14,
        color: '#BA191C',
    },
    container: {
        flex: 1,
        flexDirection: 'row',
        justifyContent: 'center',
    },
    coverImage: {
        width: "100%",
        height: 260,
        resizeMode: "cover",
        backgroundColor: "#F2F2F7",
    },
    sentimentText: {
        color: "#BA191C",
        fontWeight: "700",
        fontSize: 18,
    },
    content: {
        padding: 14,
    },
    metaText: {
        color: "#444444",
        fontSize: 13,
        marginBottom: 2,
    },
    metaValue: {
        color: "#222222",
        fontWeight: "500",
    },
    priceText: {
        color: "#BA191C",
        fontSize: 13,
        fontWeight: "700",
        marginBottom: 2,
    },
    genresText: {
        color: "#555555",
        fontSize: 12,
        lineHeight: 16,
    },
    reviewsContainer: {
        padding: 14,
    },
    reviewsHeader: {
        marginBottom: 10,
    },
});