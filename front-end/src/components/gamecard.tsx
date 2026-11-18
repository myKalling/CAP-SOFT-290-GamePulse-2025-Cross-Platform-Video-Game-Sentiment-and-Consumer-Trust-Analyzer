import { View, Text, StyleSheet } from "react-native";

export type Game = {
    GameID: number;
    Title: string;
    Price: number | null;
    Developers?: string | null;
    Genres?: string | null;
    AverageSentiment?: number | null;
};

export default function GameCard({ game }: { game: Game }) {
    return (
        <View style={styles.card}>
            <Text style={styles.title}>{game.Title}</Text>
            {game.Developers != null && <Text>Developers: {game.Developers}</Text>}
            <Text>
                Price: {game.Price == null ? "N/A" : game.Price === 0 ? "Free" : `$${game.Price.toFixed(2)}`}
            </Text>
            {game.Genres != null && <Text>Genres: {game.Genres}</Text>}
            {game.AverageSentiment != null && (
                <Text>Average Sentiment: {game.AverageSentiment.toFixed(2)}</Text>
            )}
        </View>
    );
}

const styles = StyleSheet.create({
    card: {
        padding: 16,
        marginBottom: 12,
        backgroundColor: "#fff",
        borderRadius: 10,
        elevation: 3,
    },
    title: {
        fontSize: 18,
        fontWeight: "bold",
    },
});