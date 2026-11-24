import { View, Text, Image, StyleSheet } from "react-native";
import ReviewInput from "@/constants/theme-user-review-input";

export type Game = {
    GameID: number;
    Title: string;
    Price: number | null;
    Developers?: string | null;
    Genres?: string | null;
    AverageSentiment?: number | null;
    ImageURL?: string | null;
};

export default function GameCard({ game }: { game: Game }) {
    return (
        <View style={styles.card}>
            {game.ImageURL != null && (
                <Image source={{ uri: game.ImageURL }} style={styles.coverImage} />
            )}
            {game.AverageSentiment != null && (
                <View
                    style={[
                        styles.sentimentBadge,
                        game.ImageURL != null ? styles.sentimentOverlay : styles.sentimentInline,
                    ]}
                >
                    <Text style={styles.sentimentText}>
                        Average Sentiment: {game.AverageSentiment.toFixed(2)}
                    </Text>
                </View>
            )}
            <View style={styles.content}>
                <Text style={styles.title} numberOfLines={1}>
                    {game.Title}
                </Text>
                {game.Developers != null && (
                    <Text style={styles.metaText} numberOfLines={1}>
                        Developers: <Text style={styles.metaValue}>{game.Developers}</Text>
                    </Text>
                )}
                <Text style={styles.priceText}>
                    Price:{" "}
                    {game.Price == null
                        ? "N/A"
                        : game.Price === 0
                            ? "Free"
                            : `$${game.Price.toFixed(2)}`}
                </Text>
                {game.Genres != null && (
                    <Text style={styles.genresText} numberOfLines={2}>
                        Genres: {game.Genres}
                    </Text>
                )}
                <ReviewInput gameName={game.Title} />
            </View>
        </View>
    );
}

const styles = StyleSheet.create({
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