import { StyleSheet, Image, SafeAreaView } from 'react-native';
import { useLocalSearchParams } from 'expo-router';
import { ThemedView } from '@/components/themed-view';
import { ThemedText } from '@/components/themed-text';
import ReviewInput from '@/constants/theme-user-review-input';
import { Game } from '@/components/gamecard';
import { useEffect, useState } from 'react';
import { read } from '../../api/fetch-wrapper';

export default function GameDetailsScreen() {
    const { id } = useLocalSearchParams<{ id: string }>();
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [game, setGame] = useState<Game | null>(null);
    const [gameReviews, setGameReviews] = useState<any[]>([]);

    useEffect(() => {
        const fetchGame = async () => {
            setLoading(true);
            try {
                const gameData = await read(`games/${id}`);
                const gameReviewsData = await read(`games/${id}/reviews`);
                setGame(gameData);
                setGameReviews(gameReviewsData);
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
                {game.AverageSentiment != null && (
                    <ThemedView
                        style={[
                            styles.sentimentBadge,
                            game.ImageURL != null ? styles.sentimentOverlay : styles.sentimentInline,
                        ]}
                    >
                        <ThemedText style={styles.sentimentText}>
                            Average Sentiment: {game.AverageSentiment.toFixed(2)}
                        </ThemedText>
                    </ThemedView>
                )}
                <ThemedView style={styles.content}>
                    <ThemedText style={styles.title} numberOfLines={1}>
                        {game.Title}
                    </ThemedText>
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
    card: {
        backgroundColor: "#FFFFFF",
        minHeight: 300,
        borderRadius: 14,
        overflow: "hidden",
        marginVertical: 8,
        marginHorizontal: 16,
        borderWidth: 1,
        borderColor: "#E5E5EA",
        // iOS Shadow
        shadowColor: "#000",
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.08,
        shadowRadius: 4,
        // Android Shadow
        elevation: 3,
    },
    hoveredEffect: {
        transform: [{ scale: 1.03 }],
        borderColor: "#BA191C",
        shadowOpacity: 0.2,
        elevation: 6,
    },
    coverImage: {
        width: "100%",
        height: 160,
        resizeMode: "cover",
        backgroundColor: "#F2F2F7",
    },
    sentimentBadge: {
        backgroundColor: "rgba(255, 255, 255, 0.95)",
        paddingHorizontal: 10,
        paddingVertical: 5,
        borderRadius: 20,
        borderWidth: 1,
        borderColor: "#BA191C",
    },
    sentimentOverlay: {
        position: "absolute",
        top: 12,
        right: 12,
        zIndex: 1,
    },
    sentimentInline: {
        alignSelf: "flex-start",
        marginTop: 14,
        marginLeft: 14,
        marginBottom: -4,
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
});