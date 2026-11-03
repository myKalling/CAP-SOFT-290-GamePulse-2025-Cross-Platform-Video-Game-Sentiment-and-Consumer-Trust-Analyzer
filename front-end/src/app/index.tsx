import * as Device from 'expo-device';
import { Platform, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { AnimatedIcon } from '@/components/animated-icon';
import { HintRow } from '@/components/hint-row';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { WebBadge } from '@/components/web-badge';
import { BottomTabInset, MaxContentWidth, Spacing } from '@/constants/theme';
import { Link } from 'expo-router';


export default function HomeScreen() {
  return (
    <ThemedView style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <ThemedText type="title" style={styles.title}>
         GamePulse
        </ThemedText>

        <ThemedText style={styles.content}>
         Find the top 20 games from 2025 for both free-to-play and pay-to-play. {"\n"} {"\n"}
          Real reviews written from players across multiple platforms such as Xbox, Steam, RAWG and IGDB.{"\n"} {"\n"}
          You can also add your own review. Your opinion matters! {"\n"}
        </ThemedText>

        <ThemedText style={styles.content}>
         Click below to sign in or browse through top games. No sign in necessary!
        </ThemedText>
        <View style={styles.link}>
          <Link href="/account" style={{ marginRight: 10 }}>Login</Link>
          <Link href="/games" style={{ marginRight: 10 }}>Games</Link>
        </View>
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
  content: {
    gap: Spacing.three,
    alignSelf: 'stretch',
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.four,
    borderRadius: Spacing.four,
    textAlign: 'center',
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
});