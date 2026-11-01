import * as Device from 'expo-device';
import { Platform, Pressable, StyleSheet } from 'react-native';
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
      <SafeAreaView style={[styles.safeArea, {flex: 1}]}>

        <ThemedText type="title" style={styles.title}>
          About Us
        </ThemedText>
        
        <ThemedView style={styles.content}>
          <ThemedText>
            We are a student-lead team that created this website from start to finish as part of our capstone project.
          </ThemedText>
          <ThemedView>
            <ThemedText>
              Our Roles:
            </ThemedText>
            <ThemedList items={[
              { item: 'Front-EndDevelopment -> Ava Ortiz' },
              { item: 'Database/ Data-Cleaning -> Ryan Michael' },
              { item: 'Ai Pipeline/ API-> Kenny Gallardo' }
            ]} />
          </ThemedView>
        </ThemedView>

        <ThemedView style={styles.content}>
          <ThemedText>
            About Gamepulse
          </ThemedText>
          <ThemedText>
           I plan on keeping up with everyone's progress to get this site closer every week to being completed.
          </ThemedText>
        </ThemedView>

        <ThemedView>
          <ThemedText>
            Kenny's GitHub Repo
          </ThemedText> 
                  <ExternalLink href="https://github.com/myKalling" asChild>
                    <Pressable>
                      <ThemedText type="link">GitHub</ThemedText>
                      <SymbolView
                        name={{ ios: 'arrow.up.right.square', web: 'link' }}
                        size={12}
                      />
                    </Pressable>
                  </ExternalLink>
        </ThemedView>
        <ThemedView style={styles.content}>
          <ThemedText>Contact Us</ThemedText>
            <ThemedText>For any inquiries or feedback, please reach out to us individually:</ThemedText>

              <ThemedView style={{ gap: Spacing.three }}>
                <ThemedText>
                  Ava Ortiz:
                </ThemedText>
                <EmailLink recipient="avaortiz1507@gmail.com" subject="Inquiry" body="Hello Ava," />
                <ThemedText>
                  Ryan Michael:
                </ThemedText>
                <EmailLink recipient="ryannitroo@gmail.com" subject="Inquiry" body="Hello Ryan," />
                <ThemedText>
                  Kenny Gallardo:
                </ThemedText>
                <EmailLink recipient="owner@mykalling.net" subject="Inquiry" body="Hello Kenny," />
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
  content: {
    gap: Spacing.three,
    alignSelf: 'stretch',
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.four,
    borderRadius: Spacing.four,
  },
});
