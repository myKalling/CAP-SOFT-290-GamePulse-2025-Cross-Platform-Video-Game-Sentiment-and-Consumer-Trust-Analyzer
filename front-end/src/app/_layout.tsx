import { DefaultTheme, Stack, ThemeProvider } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { StyleSheet, Text, View } from 'react-native';
import { GestureHandlerRootView } from 'react-native-gesture-handler';

import { BurgerMenu } from '@/components/burger-menu';
import { ExternalLink } from '@/components/external-link';
import { Colors } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { AuthProvider } from '../../authorization/authorization-login';

SplashScreen.preventAutoHideAsync();

export default function RootLayout() {
  const theme = useTheme();
  const navigationTheme = {
    ...DefaultTheme,
    colors: {
      ...DefaultTheme.colors,
      primary: Colors.tabs.background,
      background: theme.background,
      card: theme.background,
      text: theme.text,
    },
  };

  return (
    <AuthProvider>
      <GestureHandlerRootView style={styles.container}>
        <ThemeProvider value={navigationTheme}>
          <Stack
            screenOptions={{
              headerShown: true,
              headerStyle: { backgroundColor: theme.background },
              headerTintColor: theme.text,
              headerShadowVisible: false,
              headerLeft: () => <BurgerMenu />,
            }}>
            <Stack.Screen name="index" options={{ title: 'Home Page' }} />
            <Stack.Screen name="about" options={{ title: 'About' }} />
            <Stack.Screen name="account" options={{ title: 'Account' }} />
            <Stack.Screen name="games" options={{ title: 'Top 20 Games' }} />
            <Stack.Screen name="credits" options={{ title: 'Credits' }} />
          </Stack>
          <View style={styles.footer}>
            <ExternalLink
              href="https://github.com/myKalling/CAP-SOFT-290-GamePulse-2025-Cross-Platform-Video-Game-Sentiment-and-Consumer-Trust-Analyzer"
              style={styles.footerText}>
              Shared Github
            </ExternalLink>
            <Text style={styles.footerText}>© 2026 GamePulse</Text>
          </View>
        </ThemeProvider>
      </GestureHandlerRootView>
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