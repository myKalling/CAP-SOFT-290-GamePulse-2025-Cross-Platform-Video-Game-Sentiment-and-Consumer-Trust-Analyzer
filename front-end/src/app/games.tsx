import { StyleSheet, View, ScrollView, useWindowDimensions } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import GameCard from '@/components/gamecard';
import type { Game } from '@/components/gamecard';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { BottomTabInset, MaxContentWidth, Spacing } from '@/constants/theme';
import { useEffect, useState } from 'react';
import { read } from '../api/fetch-wrapper'
import { Link } from 'expo-router';

export default function GamesScreen() {
  const { width } = useWindowDimensions();
  const isWideScreen = width >= 768;

  const [freeGames, setFreeGames] = useState<Game[]>([]);
  const [paidGames, setPaidGames] = useState<Game[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchTopGames = async () => {
      setLoading(true);
      try {
        const freeGameData = await read("games/topfree");
        const paidGameData = await read("games/toppaid");
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
    <ThemedView style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <ScrollView
          style={styles.scrollView}
          contentContainerStyle={styles.scrollContent}
        >
          <View style={styles.titleContainer}>
            <View style={styles.titleRow}>
              <ThemedText type="title" style={[styles.title, { color: 'black', marginRight: Spacing.two }]}>
                Top
              </ThemedText>
              <ThemedText type="title" style={[styles.title, { color: '#ba191b', marginRight: Spacing.two }]}>
                20
              </ThemedText>
              <ThemedText type="title" style={[styles.title, { color: 'black' }]}>
                Games
              </ThemedText>
            </View>

            <View style={styles.titleRow}>
              <ThemedText type="title" style={[styles.title, { color: 'black', marginRight: Spacing.two }]}>
                of
              </ThemedText>
              <ThemedText type="title" style={[styles.title, { color: '#ba191b' }]}>
                2025
              </ThemedText>
            </View>
          </View>

          <ThemedView style={[
            styles.columnsContainer,
            { flexDirection: isWideScreen ? 'row' : 'column' },
          ]}>
            <ThemedView style={[styles.column, !isWideScreen && styles.mobileColumn]}>
              <ThemedText type="subtitle" style={styles.columnHeader}>
                Free to Play
              </ThemedText>

              {freeGames.map((game) => (
                <GameCard key={game.GameID} game={game} />
              ))}
            </ThemedView>

            <ThemedView style={[styles.column, !isWideScreen && styles.mobileColumn]}>
              <ThemedText type="subtitle" style={styles.columnHeader}>
                Pay to Play
              </ThemedText>

              {paidGames.map((game) => (
                <GameCard key={game.GameID} game={game} />
              ))}
            </ThemedView>
          </ThemedView>

          <ThemedView style={styles.footer}>
            <ThemedView style={styles.link}>
              <Link
                href="/credits"
                style={{ marginRight: 5, ...styles.coloredBlock }}
              >
                Credits
              </Link>
            </ThemedView>
          </ThemedView>

        </ScrollView>
      </SafeAreaView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  footer: {
    padding: 16,
    alignItems: 'center',
  },
  footerText: {
    fontSize: 14,
    color: '#888',
  },
  container: {
    flex: 1,
    flexDirection: 'row',
    justifyContent: 'center',
  },
  safeArea: {
    flex: 1,
    maxWidth: 1200,
    width: '100%',
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    alignItems: 'center',
    gap: Spacing.three,
    paddingHorizontal: Spacing.four,
    paddingBottom: BottomTabInset + Spacing.three,
  },
  columnsContainer: {
    flexDirection: 'row',
    alignSelf: 'stretch',
    gap: Spacing.four,
  },

  column: {
    flex: 1,
    gap: Spacing.two,
  },
  title: {
    textAlign: 'center',
  },
  columnHeader: {
    textAlign: 'center',
  },
  titleContainer: {
    alignItems: 'center',
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  link: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    gap: Spacing.three,
    alignSelf: 'stretch',
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.four,
    borderRadius: Spacing.four,
    textAlign: 'center',
  },
  coloredBlock: {
    backgroundColor: "#ba191c", // block color
    paddingVertical: 10,
    paddingHorizontal: 20,
    borderRadius: 8, // rounded corners
  },
  mobileColumn: {
    flex: 1,
    width: '100%',
  },
});