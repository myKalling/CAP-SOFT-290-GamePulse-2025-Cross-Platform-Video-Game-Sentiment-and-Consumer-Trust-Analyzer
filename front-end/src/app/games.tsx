import { StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import type { Game } from '@/components/gamecard';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { BottomTabInset, MaxContentWidth, Spacing } from '@/constants/theme';
import FreeGamesList from '@/components/themed-free-games-list';
import PaidGamesList from '@/components/themed-paid-games-list';
import { useEffect, useState } from 'react';

import { read } from '../api/fetch-wrapper'
import { Link } from 'expo-router';

export default function GamesScreen() {
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
    <ThemedView style={[styles.container, { flex: 1 }]}>
      <SafeAreaView style={[styles.safeArea, { flex: 1 }]}>

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


        <ThemedView style={styles.columnsContainer}>
          <ThemedView style={styles.column}>
         
            <FreeGamesList />
            {/* <AddReviewButton /> */}
          </ThemedView>

          <ThemedView style={styles.column}>
            
            <PaidGamesList />
            {/* <AddReviewButton /> */}
          </ThemedView>
        </ThemedView>

        <View style={styles.footer}>
          <View style={styles.link} >
            <Link href="/credits" style={{ marginRight: 5, ...styles.coloredBlock }}>Credits</Link>
          </View>
        </View>

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
});