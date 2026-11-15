import { DarkTheme, DefaultTheme, ThemeProvider } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { useColorScheme, View, Text, StyleSheet } from 'react-native';

import { AnimatedSplashOverlay } from '@/components/animated-icon';
import AppTabs from '@/components/app-tabs';
import { ExternalLink } from '@/components/external-link';
import { AuthProvider } from '../../authorization/authorization-login';

SplashScreen.preventAutoHideAsync();

export default function TabLayout() {
  const colorScheme = useColorScheme();
  return (
    <AuthProvider>
      <ThemeProvider value={DefaultTheme}>
        <View style={styles.container}>
          <AnimatedSplashOverlay />
          <AppTabs />
          <View style={styles.footer}>
            <Text style={styles.footerText}>© 2026 GamePulse</Text>
            <ExternalLink
              href="https://github.com/myKalling/CAP-SOFT-290-GamePulse-2025-Cross-Platform-Video-Game-Sentiment-and-Consumer-Trust-Analyzer"
              style={styles.footerText}>
              Shared Github
            </ExternalLink>
          </View>
          
        </View>
      </ThemeProvider>
    </AuthProvider>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  footer: {
    padding: 16,
    alignItems: 'center',
  },
  footerText: {
    fontSize: 14,
    color: '#888',
  },
});
