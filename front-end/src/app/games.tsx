import { StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { BottomTabInset, MaxContentWidth, Spacing } from '@/constants/theme';
import FreeGamesList from '@/components/themed-free-games-list';
import PaidGamesList from '@/components/themed-paid-games-list';
import { AddReviewButton } from '../../authorization/add-review-button';

export default function GamesScreen() {
  return (
    <ThemedView style={[styles.container, {flex: 1}]}>
      <SafeAreaView style={[styles.safeArea, {flex: 1}]}>

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
            <ThemedText type="subtitle" style={styles.columnHeader}>
              Free to Play
            </ThemedText>
            <FreeGamesList />
            {/* <AddReviewButton /> */}
          </ThemedView>

          <ThemedView style={styles.column}>
            <ThemedText type="subtitle" style={styles.columnHeader}>
              Pay to Play
            </ThemedText>
            <PaidGamesList />
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
  titleContainer: {
    alignItems: 'center',
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
});