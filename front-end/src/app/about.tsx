import * as Device from 'expo-device';
import { Platform, Pressable, ScrollView, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { AnimatedIcon } from '@/components/animated-icon';
import { HintRow } from '@/components/hint-row';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { WebBadge } from '@/components/web-badge';
import { BottomTabInset, MaxContentWidth, Spacing } from '@/constants/theme';
import ThemedList from '@/components/themed-list';
import { ExternalLink } from '@/components/external-link';
import { SymbolView } from 'expo-symbols';
import EmailLink from '@/components/themed-email-link';


export default function AboutScreen() {
  return (
    <ThemedView style={[styles.container, {flex: 1}]}>
      <SafeAreaView style={styles.safeArea}>
        <ScrollView
          style={styles.scrollView}
          showsVerticalScrollIndicator={false}
          contentContainerStyle={styles.scrollContent}>

        <View style={styles.titleRow}>
                  <ThemedText type="title" style={[styles.title, { color: '#161a1d' }]}>
                    About 
                  </ThemedText>
                  {/* newline for spacing */}
                  <ThemedText type="title" style={[styles.title, { color: '#ba191b' }]}>
                    Us
                  </ThemedText>
                </View>
        
        <ThemedView style={styles.borderColor}>
          <ThemedText style={{ textAlign: 'center' }}>
            We are a student-lead team that created this website from start to finish as part of our capstone project.
          </ThemedText>
          </ThemedView>

          <ThemedView style={[styles.content, { alignItems: 'center' }]}>
            <ThemedText>
              Our Roles:
            </ThemedText>
            <ThemedList items={[
              { item: 'Front-End Development -> Ava Ortiz' },
              { item: 'Database/ Data-Cleaning -> Ryan Michael' },
              { item: 'Ai Pipeline/ API-> Kenny Gallardo' }
            ]} />
          </ThemedView>
        

        <ThemedView style={styles.borderColor}>
          <ThemedText style={{ textAlign: 'center' }}>
            About Gamepulse
          </ThemedText>
          <ThemedText style={{ textAlign: 'center' }}>
            GamePulse was created to find the top 20 games of 2025, both paid and unpaid to see if the games are "worth it".
            This is determined through actual data that we collected. This includes:
            reviews from IGDB, RAWG, and Xbox, written reviews by real players, 
            their overall ratings for each game, personal ratings,
            critic scores, and other relevant data.
          </ThemedText>
        </ThemedView>

        <ThemedView style={styles.content}>
          <ThemedText style={{ textAlign: 'center' }}>
            Github Link
          </ThemedText> 
                  <ExternalLink style={{ textAlign: 'center' }} href="https://github.com/myKalling/CAP-SOFT-290-GamePulse-2025-Cross-Platform-Video-Game-Sentiment-and-Consumer-Trust-Analyzer" >
                    <Pressable>
                      <ThemedText style={{ textDecorationLine: 'underline' }} type="link"> Shared GitHub</ThemedText>
                    </Pressable>
                  </ExternalLink>
        </ThemedView>
        <ThemedView style={styles.borderColor}>
          <ThemedText style={{ textAlign: 'center' }}>Contact Us</ThemedText>
            <ThemedText style={{ textAlign: 'center' }}>For any inquiries or feedback, please reach out to us individually:</ThemedText>

              <ThemedView style={[styles.borderColor, { gap: Spacing.three }]}>
                <ThemedText style={{ textAlign: 'center' }}>
                  Ava Ortiz:
                </ThemedText>
                <EmailLink recipient="avaortiz1507@gmail.com" subject="Inquiry" body="Hello Ava," />
                <ThemedText style={{ textAlign: 'center' }}>
                  Ryan Michael:
                </ThemedText>
                <EmailLink recipient="ryannitroo@gmail.com" subject="Inquiry" body="Hello Ryan," />
                <ThemedText style={{ textAlign: 'center' }}>
                  Kenny Gallardo:
                </ThemedText>
                <EmailLink recipient="owner@mykalling.net" subject="Inquiry" body="Hello Kenny," />
              </ThemedView>
            
        </ThemedView>
        </ScrollView>
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
    alignItems: 'center',
    maxWidth: MaxContentWidth,
    width: '100%',
  },
  scrollView: {
    flex: 1,
    width: '100%',
  },
  scrollContent: {
    flexGrow: 1,
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
  },
  borderColor:{
    textAlign: 'center',
    gap: Spacing.three,
    alignSelf: 'stretch',
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.four,
    borderRadius: Spacing.four,
    backgroundColor: '#dedce4',
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
});
