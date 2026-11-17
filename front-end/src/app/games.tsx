import { StyleSheet, FlatList } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import GameCard from '@/components/gamecard';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { BottomTabInset, MaxContentWidth, Spacing } from '@/constants/theme';
import { useEffect, useState } from 'react';
import { read } from '../api/fetch-wrapper'

export default function GamesScreen() {
  const [freeGames, setFreeGames] = useState<any[]>([]);
  const [paidGames, setPaidGames] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchTopGames = async () => {
      setLoading(true);
      try {
        const freeGameData = await read("procedures/games/top/free");
        const paidGameData = await read("procedures/games/top/paid");
        setFreeGames(freeGameData);
        setPaidGames(paidGameData);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setLoading(false);
      }
    };

    fetchTopGames();
  }, []);

  return (
    <ThemedView style={[styles.container, { flex: 1 }]}>
      <SafeAreaView style={[styles.safeArea, { flex: 1 }]}>

        <ThemedText type="title" style={styles.title}>
          Top 20 Games of 2025
        </ThemedText>

        <ThemedView style={styles.columnsContainer}>
          <ThemedView style={styles.column}>
            <ThemedText type="subtitle" style={styles.columnHeader}>
              Free to Play
            </ThemedText>
            <FlatList
              data={freeGames}
              keyExtractor={(item) => item.toString()}
              renderItem={({ item }) => <GameCard game={item} />}
            />
            {/* <AddReviewButton /> */}
          </ThemedView>

          <ThemedView style={styles.column}>
            <ThemedText type="subtitle" style={styles.columnHeader}>
              Pay to Play
            </ThemedText>
            <FlatList
              data={paidGames}
              keyExtractor={(item) => item.toString()}
              renderItem={({ item }) => <GameCard game={item} />}
            />
            {/* <AddReviewButton /> */}
          </ThemedView>
        </ThemedView>

      </SafeAreaView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    flexDirection: 'row',
  },
  safeArea: {
    flex: 1,
    paddingHorizontal: Spacing.four,
    alignItems: 'center',
    gap: Spacing.three,
    paddingBottom: BottomTabInset + Spacing.three,
    maxWidth: MaxContentWidth,
  },
  title: {
    textAlign: 'center',
  },
  columnsContainer: {
    flexDirection: 'row',
    alignSelf: 'stretch',
    flex: 1,
    gap: Spacing.four,
  },
  column: {
    flex: 1,
    gap: Spacing.two,
  },
  columnHeader: {
    textAlign: 'center',
  },
});