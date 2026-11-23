import { StyleSheet } from 'react-native';
import { useLocalSearchParams } from 'expo-router';
import { ThemedView } from '@/components/themed-view';
import { ThemedText } from '@/components/themed-text';

export default function GameDetailsScreen() {
    const { id } = useLocalSearchParams<{ id: string }>();

    return (
        <ThemedView style={styles.container}>
            <ThemedText type="title">Game Details</ThemedText>
            <ThemedText>Game ID: {id}</ThemedText>
        </ThemedView>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        padding: 20,
    }
});