import { StyleSheet, Image } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams } from 'expo-router';
import { ThemedView } from '@/components/themed-view';
import { ThemedText } from '@/components/themed-text';
import ReviewInput from '@/constants/theme-user-review-input';
import { Game } from '@/components/gamecard';
import { useEffect, useState } from 'react';
import { read } from '../../api/fetch-wrapper';

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
                setHighReviews(gameReviewsData.filter((review: Review) => review.ReviewType === 'high'));
                setLowReviews(gameReviewsData.filter((review: Review) => review.ReviewType === 'low'));
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
                {game.ImageURL != null && (
                    <Image source={{ uri: game.ImageURL }} style={styles.coverImage} />
                )}
                <ThemedView style={styles.content}>
                    <ThemedText type="subtitle">
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
                        Reviews
                    </ThemedText>
                    <ThemedText type="subtitle" style={styles.reviewsHeader}>
                        High Reviews
                    </ThemedText>
                    {HighReviews.map((review) => (
                        <ThemedText key={review.ReviewID}>{review.Review}</ThemedText>
                    ))}
                    <ThemedText type="subtitle" style={styles.reviewsHeader}>
                        Low Reviews
                    </ThemedText>
                    {LowReviews.map((review) => (
                        <ThemedText key={review.ReviewID}>{review.Review}</ThemedText>
                    ))}
                </ThemedView>
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
    container: {
        flex: 1,
        flexDirection: 'row',
        justifyContent: 'center',
    },
    coverImage: {
        width: "100%",
        height: 160,
        resizeMode: "cover",
        backgroundColor: "#F2F2F7",
    },
    sentimentText: {
        color: "#BA191C",
        fontWeight: "700",
        fontSize: 12,
    },
    content: {
        padding: 14,
    },
    title: {
        color: "#111111",
        fontSize: 18,
        fontWeight: "700",
        marginBottom: 6,
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